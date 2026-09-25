"""Write semantics: restart replays the committed prefix only."""

from dredgeops.store import Journal


def test_restart_replays_only_entries_at_or_below_the_watermark(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("committed")
    first.append("pump/state", {"depth": 9}, "committed", generation=2)
    first.commit("committed")
    first.open("open")
    first.append("pump/running", {"running": True}, "open")

    second = Journal(directory)
    assert second.watermark == 1
    assert second.read("pump/state") == {"depth": 9}
    assert second.read("pump/running") is None


def test_restart_keeps_uncommitted_batch_open_and_replayable(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("draft")
    first.append("dens/baseline", {"baseline": 1010.0}, "draft")

    second = Journal(directory)
    assert second.pending_batches() == ("draft",)
    assert second.commit("draft") == 1
    assert second.read("dens/baseline") == {"baseline": 1010.0}


def test_restart_keeps_aborted_batch_out_of_the_view(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("dropped")
    first.append("a", 1, "dropped")
    first.discard("dropped")
    first.open("kept")
    first.append("b", 2, "kept")
    first.commit("kept")

    second = Journal(directory)
    assert second.aborted_batches() == ("dropped",)
    assert second.read("a") is None
    assert second.read("b") == 2


def test_restart_preserves_the_generation_of_committed_rows(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("curve")
    first.append("pump/curve", {"slope": 1.2}, "curve", generation=4)
    first.commit("curve")

    second = Journal(directory)
    assert second.generation_of("pump/curve") == 4
    assert [entry.generation for entry in second.history("pump/curve")] == [4]


def test_restart_recovers_the_digest_of_the_committed_view(tmp_path):
    directory = str(tmp_path / "stream")
    first = Journal(directory)
    first.open("unit")
    first.append("a", 1, "unit")
    first.append("b", {"nested": [1, 2, 3]}, "unit")
    first.commit("unit")
    digest = first.snapshot().digest

    second = Journal(directory)
    assert second.snapshot().digest == digest
    assert second.snapshot().watermark == 2
