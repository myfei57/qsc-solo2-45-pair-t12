"""Version semantics: snapshots and baselines expire."""

import pytest

from dredgeops.clock import LogicalClock
from dredgeops.errors import StaleArtifactError
from dredgeops.store import Journal
from dredgeops.version import Artifacts, Generations


def make(tmp_path):
    journal = Journal(str(tmp_path / "stream"))
    clock = LogicalClock()
    return Artifacts(journal, clock), clock, Generations(journal)


def test_recorded_artifact_reports_its_generation_and_tick(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    clock.advance(4)
    ref = artifacts.record("snapshot", "control.snapshot", 2, "abc123")
    assert ref.generation == 2
    assert ref.tick == 4
    assert artifacts.get("snapshot", "control.snapshot").digest == "abc123"


def test_require_current_accepts_an_artifact_inside_its_limit(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    generations.advance("control.snapshot", "snap")
    artifacts.record("snapshot", "control.snapshot", 1, "abc123")
    clock.advance(3)
    ref = artifacts.require_current("snapshot", "control.snapshot", 5, generations)
    assert ref.digest == "abc123"


def test_require_current_refuses_an_artifact_older_than_the_limit(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    generations.advance("control.snapshot", "snap")
    artifacts.record("snapshot", "control.snapshot", 1, "abc123")
    clock.advance(9)
    with pytest.raises(StaleArtifactError):
        artifacts.require_current("snapshot", "control.snapshot", 5, generations)


def test_require_current_refuses_an_artifact_from_a_superseded_generation(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    generations.advance("control.snapshot", "snap")
    artifacts.record("snapshot", "control.snapshot", 1, "abc123")
    generations.advance("control.snapshot", "snap")
    with pytest.raises(StaleArtifactError):
        artifacts.require_current("snapshot", "control.snapshot", 100, generations)


def test_require_current_refuses_a_missing_artifact(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    with pytest.raises(StaleArtifactError):
        artifacts.require_current("baseline", "dens", 10, generations)


def test_stale_reports_true_once_the_limit_passes(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    generations.advance("control.snapshot", "snap")
    artifacts.record("snapshot", "control.snapshot", 1, "abc123")
    assert artifacts.stale("snapshot", "control.snapshot", 5, generations) is False
    clock.advance(6)
    assert artifacts.stale("snapshot", "control.snapshot", 5, generations) is True


def test_age_grows_with_the_logical_clock(tmp_path):
    artifacts, clock, generations = make(tmp_path)
    artifacts.record("snapshot", "control.snapshot", 0, "abc123")
    clock.advance(7)
    assert artifacts.age("snapshot", "control.snapshot") == 7
