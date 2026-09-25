"""Version semantics: parameter generations."""

import pytest

from dredgeops.errors import StaleArtifactError
from dredgeops.store import Journal
from dredgeops.version import Generations


def test_generation_starts_at_zero_before_the_first_issue(journal):
    assert Generations(journal).current("pump.curve") == 0


def test_advance_publishes_the_next_generation(journal):
    generations = Generations(journal)
    assert generations.advance("pump.curve", "curve-gen") == 1
    assert generations.advance("pump.curve", "curve-gen") == 2
    assert generations.current("pump.curve") == 2


def test_is_current_matches_the_published_generation(journal):
    generations = Generations(journal)
    generations.advance("dens.baseline", "dens-gen")
    assert generations.is_current("dens.baseline", 1) is True
    assert generations.is_current("dens.baseline", 0) is False


def test_require_current_rejects_a_superseded_generation(journal):
    generations = Generations(journal)
    generations.advance("dens.baseline", "dens-gen")
    generations.advance("dens.baseline", "dens-gen")
    with pytest.raises(StaleArtifactError):
        generations.require_current("dens.baseline", 1, "density baseline")


def test_all_lists_every_parameter_generation(journal):
    generations = Generations(journal)
    generations.advance("pump.curve", "curve-gen")
    generations.advance("dens.baseline", "dens-gen")
    generations.advance("dens.baseline", "dens-gen")
    assert generations.all() == {"dens.baseline": 2, "pump.curve": 1}


def test_generation_survives_a_restart(tmp_path):
    directory = str(tmp_path / "stream")
    first = Generations(Journal(directory))
    first.advance("hopper.map", "map-gen")

    second = Generations(Journal(directory))
    assert second.current("hopper.map") == 1
