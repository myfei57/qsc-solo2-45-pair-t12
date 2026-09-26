"""Snapshots state the watermark they cover and summarize that exact range."""

from dredgeops.store import Journal


def test_empty_snapshot_covers_nothing():
    snapshot = Journal().snapshot()
    assert snapshot.watermark == 0
    assert snapshot.count == 0
    assert snapshot.keys == ()
    assert snapshot.covers(1) is False
    assert snapshot.to_dict() == {
        "watermark": 0,
        "count": 0,
        "digest": snapshot.digest,
        "keys": [],
    }


def test_snapshot_states_its_watermark_and_count(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.append("b", 2, "b1")
    journal.commit("b1")

    snapshot = journal.snapshot()
    assert snapshot.watermark == 2
    assert snapshot.count == 2
    assert snapshot.keys == ("a", "b")
    assert snapshot.covers(2) is True
    assert snapshot.covers(3) is False


def test_digest_changes_when_the_covered_range_grows_even_without_net_state_change(journal):
    """A key written back to its old value must still move the snapshot summary."""
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    first = journal.snapshot()

    journal.open("b2")
    journal.append("a", 2, "b2")
    journal.commit("b2")
    journal.open("b3")
    journal.append("a", 1, "b3")
    journal.commit("b3")
    second = journal.snapshot()

    assert first.watermark == 1
    assert second.watermark == 3
    assert second.count == 3
    assert first.digest != second.digest


def test_snapshots_frozen_at_different_watermarks_have_different_digests(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    journal.open("b2")
    journal.append("b", 2, "b2")
    journal.commit("b2")

    at_one = journal.view(1)
    at_two = journal.view(2)
    assert at_one.snapshot_digest() != at_two.snapshot_digest()
    assert journal.snapshot().digest == at_two.snapshot_digest()


def test_tombstones_count_in_the_covered_range(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    first = journal.snapshot()

    journal.open("b2")
    journal.append_tombstone("a", "b2", "removed")
    journal.commit("b2")
    second = journal.snapshot()

    assert second.keys == ()
    assert second.count == 2
    assert first.digest != second.digest


def test_aborted_rows_are_outside_the_snapshot_range(journal):
    journal.open("kept")
    journal.append("a", 1, "kept")
    journal.commit("kept")
    journal.open("dropped")
    journal.append("b", 2, "dropped")
    journal.discard("dropped")

    snapshot = journal.snapshot()
    assert snapshot.watermark == 1
    assert snapshot.count == 1
    assert snapshot.keys == ("a",)


def test_snapshot_survives_restart_with_its_watermark(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("b1")
    first.append("a", {"x": [1, 2]}, "b1")
    first.append("b", 3, "b1")
    first.commit("b1")
    frozen = first.snapshot()

    second = Journal(directory)
    restored = second.snapshot()
    assert restored.watermark == frozen.watermark == 2
    assert restored.count == frozen.count == 2
    assert restored.digest == frozen.digest


def test_collapsed_row_digest_is_distinct_from_range_digest(journal):
    journal.open("b1")
    journal.append("a", 1, "b1")
    journal.commit("b1")
    journal.open("b2")
    journal.append("a", 2, "b2")
    journal.commit("b2")
    journal.open("b3")
    journal.append("a", 1, "b3")
    journal.commit("b3")

    assert journal.view().digest() == journal.view(1).digest()
    assert journal.view().snapshot_digest() != journal.view(1).snapshot_digest()
