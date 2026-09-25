"""Write semantics: rollback and tombstones."""

import pytest

from dredgeops.errors import RollbackError
from dredgeops.store import EntryKind, Journal


def test_rollback_tombstones_a_value_that_had_no_earlier_record(journal):
    journal.open("write")
    journal.append("dens/baseline", {"baseline": 1010.0}, "write")
    journal.commit("write")
    assert journal.rollback("write") == 1
    assert journal.read("dens/baseline") is None
    last = journal.entries()[-1]
    assert last.kind is EntryKind.TOMBSTONE
    assert last.reason == "rolled back"


def test_rollback_restores_the_previous_committed_value(journal):
    journal.open("first")
    journal.append("pump/curve", {"slope": 1.0}, "first")
    journal.commit("first")
    journal.open("second")
    journal.append("pump/curve", {"slope": 2.0}, "second")
    journal.commit("second")
    assert journal.rollback("second") == 1
    assert journal.read("pump/curve") == {"slope": 1.0}


def test_rollback_of_a_multi_key_batch_restores_every_key(journal):
    journal.open("seed")
    journal.append("a", "old-a", "seed")
    journal.append("b", "old-b", "seed")
    journal.commit("seed")
    journal.open("update")
    journal.append("a", "new-a", "update")
    journal.append("b", "new-b", "update")
    journal.commit("update")
    assert journal.rollback("update") == 2
    assert journal.read("a") == "old-a"
    assert journal.read("b") == "old-b"


def test_rollback_requires_a_committed_batch(journal):
    journal.open("draft")
    journal.append("a", 1, "draft")
    with pytest.raises(RollbackError):
        journal.rollback("draft")


def test_rollback_of_an_unknown_batch_is_refused(journal):
    with pytest.raises(RollbackError):
        journal.rollback("never-seen")


def test_rolled_back_rows_stay_in_the_stream_as_history(journal):
    journal.open("write")
    journal.append("a", 1, "write")
    journal.commit("write")
    journal.rollback("write")
    values = [entry.value for entry in journal.history("a")]
    assert values == [1, None]
    kinds = [entry.kind for entry in journal.history("a")]
    assert kinds == [EntryKind.PUT, EntryKind.TOMBSTONE]
    assert len(journal.entries()) == 2


def test_rollback_keeps_the_watermark_moving_forward(tmp_path):
    journal = Journal(str(tmp_path / "stream"))
    journal.open("write")
    journal.append("a", 1, "write")
    journal.commit("write")
    journal.rollback("write")
    assert journal.watermark == 2
    assert journal.pending_batches() == ()


def test_rollback_survives_a_restart(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("write")
    first.append("a", 1, "write")
    first.commit("write")
    first.rollback("write")

    second = Journal(directory)
    assert second.read("a") is None
    assert second.watermark == 2
