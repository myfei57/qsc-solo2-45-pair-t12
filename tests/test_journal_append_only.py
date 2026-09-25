"""Write semantics: append-only stream, commit watermark, visibility."""

import pytest

from dredgeops.errors import (
    BatchNotPendingError,
    CommitOrderError,
    DuplicateBatchError,
    MaintenanceError,
    UnknownKeyError,
)
from dredgeops.store import EntryKind, Journal


def test_uncommitted_record_is_invisible_to_reads(journal):
    journal.open("b1")
    journal.append("pump/running", {"running": True}, "b1")
    assert journal.read("pump/running") is None
    assert journal.has("pump/running") is False
    assert journal.watermark == 0


def test_record_becomes_visible_once_the_batch_commits(journal):
    journal.open("b1")
    journal.append("pump/running", {"running": True}, "b1")
    watermark = journal.commit("b1")
    assert watermark == 1
    assert journal.read("pump/running") == {"running": True}


def test_commit_moves_the_watermark_to_the_end_of_the_batch(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.append("b", 2, "b1")
    journal.append("c", 3, "b1")
    assert journal.commit("b1") == 3
    assert journal.watermark == 3
    assert journal.committed_count == 3


def test_commit_refuses_to_jump_an_earlier_open_batch(journal):
    journal.open("first")
    journal.append("a", 1, "first")
    journal.open("second")
    journal.append("b", 2, "second")
    with pytest.raises(CommitOrderError):
        journal.commit("second")
    assert journal.watermark == 0


def test_commit_twice_for_the_same_batch_is_refused(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    with pytest.raises(BatchNotPendingError):
        journal.commit("b1")


def test_discard_drops_an_uncommitted_batch_without_publishing_it(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    assert journal.discard("b1") == 1
    assert journal.read("a") is None
    assert journal.aborted_batches() == ("b1",)
    journal.open("b2")
    journal.append("b", 2, "b2")
    assert journal.commit("b2") == 2
    assert journal.read("b") == 2
    assert journal.read("a") is None


def test_append_without_an_open_batch_is_refused(journal):
    with pytest.raises(BatchNotPendingError):
        journal.append("a", 1, "missing")


def test_opening_the_same_batch_twice_is_refused(journal):
    journal.open("b1")
    with pytest.raises(DuplicateBatchError):
        journal.open("b1")


def test_maintenance_mode_keeps_writes_out_of_the_stream(journal):
    journal.set_read_only(True)
    journal.open("b1")
    with pytest.raises(MaintenanceError):
        journal.append("a", 1, "b1")
    assert journal.entries() == ()


def test_unknown_key_raises_when_required(journal):
    with pytest.raises(UnknownKeyError):
        journal.require("nothing/here")


def test_stream_keeps_every_row_in_sequence(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.append("b", 2, "b1")
    journal.append_tombstone("a", "b1", "cancelled")
    journal.commit("b1")
    kinds = [entry.kind for entry in journal.entries()]
    assert kinds == [EntryKind.PUT, EntryKind.PUT, EntryKind.TOMBSTONE]
    assert [entry.seq for entry in journal.entries()] == [1, 2, 3]
    assert journal.read("a") is None
    assert journal.read("b") == 2


def test_keys_are_returned_sorted_by_prefix(journal):
    journal.open("b1")
    journal.append("pump/state", 1, "b1")
    journal.append("pump/curve", 2, "b1")
    journal.append("jet/open", 3, "b1")
    journal.commit("b1")
    assert journal.keys("pump/") == ("pump/curve", "pump/state")
    assert journal.keys() == ("jet/open", "pump/curve", "pump/state")


def test_history_keeps_committed_rows_for_a_key(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    journal.open("b2")
    journal.append("a", 2, "b2")
    journal.commit("b2")
    assert [entry.value for entry in journal.history("a")] == [1, 2]
    assert journal.generation_of("a") == 0


def test_transaction_publishes_every_key_as_one_unit(journal):
    with journal.transaction("unit") as batch:
        journal.append("a", 1, batch)
        journal.append("b", 2, batch)
    assert journal.read("a") == 1
    assert journal.read("b") == 2
    assert journal.watermark == 2


def test_transaction_discards_everything_when_the_body_raises(journal):
    with pytest.raises(RuntimeError):
        with journal.transaction("unit") as batch:
            journal.append("a", 1, batch)
            raise RuntimeError("operator aborted the step")
    assert journal.read("a") is None
    assert journal.pending_batches() == ()
    assert len(journal.aborted_batches()) == 1


def test_memory_only_journal_replays_nothing(journal):
    plain = Journal()
    with plain.transaction("unit") as batch:
        plain.append("a", 1, batch)
    assert plain.read("a") == 1
    assert plain.directory is None
