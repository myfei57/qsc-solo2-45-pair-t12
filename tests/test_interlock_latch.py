"""State machine: latch set and clear conditions."""

import pytest

from dredgeops.errors import LatchClearError, LatchSetError
from dredgeops.interlock import Latch


def make() -> Latch:
    return Latch("valve.discharge", ("sea_closed", "pressure_low"), ("sea_closed",))


def test_latch_sets_only_when_every_set_condition_holds():
    latch = make()
    latch.set({"sea_closed": True, "pressure_low": True})
    assert latch.is_set is True


def test_latch_keeps_its_position_when_a_set_condition_is_unmet():
    latch = make()
    with pytest.raises(LatchSetError):
        latch.set({"sea_closed": True, "pressure_low": False})
    assert latch.is_set is False


def test_unmet_set_conditions_are_named():
    latch = make()
    assert latch.unmet_set_conditions({"sea_closed": True}) == ("pressure_low",)


def test_latch_clears_only_when_every_clear_condition_holds():
    latch = make()
    latch.set({"sea_closed": True, "pressure_low": True})
    with pytest.raises(LatchClearError):
        latch.clear({"sea_closed": False})
    assert latch.is_set is True
    latch.clear({"sea_closed": True})
    assert latch.is_set is False


def test_unmet_clear_conditions_are_named():
    latch = make()
    assert latch.unmet_clear_conditions({}) == ("sea_closed",)


def test_restore_adopts_a_recovered_position():
    latch = make()
    latch.restore(True)
    assert latch.is_set is True
    latch.restore(False)
    assert latch.is_set is False


def test_state_lists_both_condition_sets():
    state = make().state()
    assert state["set_conditions"] == ["sea_closed", "pressure_low"]
    assert state["clear_conditions"] == ["sea_closed"]


def test_a_latch_needs_conditions_on_both_transitions():
    with pytest.raises(ValueError):
        Latch("broken", (), ("sea_closed",))
