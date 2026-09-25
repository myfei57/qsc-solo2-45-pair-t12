"""State machine: ordered multi-stage procedures."""

import pytest

from dredgeops.errors import DuplicateStageError, OutOfSequenceError, UnknownStageError
from dredgeops.interlock import StageSequence

STAGES = ("position", "lower", "flush", "start", "discharge", "stop")


def test_stage_advance_in_order_closes_each_stage():
    sequence = StageSequence("suction", STAGES)
    for stage in STAGES:
        assert sequence.advance(stage) == stage
    assert sequence.completed() == STAGES


def test_out_of_order_advance_is_refused():
    sequence = StageSequence("suction", STAGES)
    with pytest.raises(OutOfSequenceError):
        sequence.advance("start")
    assert sequence.completed() == ()


def test_advance_reports_the_stage_that_is_still_open():
    sequence = StageSequence("suction", STAGES)
    sequence.advance("position")
    with pytest.raises(OutOfSequenceError):
        sequence.advance("flush")


def test_unknown_stage_is_refused():
    sequence = StageSequence("suction", STAGES)
    with pytest.raises(UnknownStageError):
        sequence.advance("calibrate")


def test_repeating_a_closed_stage_is_refused():
    sequence = StageSequence("suction", STAGES)
    sequence.advance("position")
    with pytest.raises(DuplicateStageError):
        sequence.advance("position")


def test_next_required_reports_complete_after_the_last_stage():
    sequence = StageSequence("suction", STAGES)
    assert sequence.next_required() == "position"
    for stage in STAGES:
        sequence.advance(stage)
    assert sequence.next_required() is None
    assert sequence.state() == {
        "procedure": "suction",
        "stages": list(STAGES),
        "completed": list(STAGES),
        "next": "complete",
    }


def test_reset_reopens_the_procedure():
    sequence = StageSequence("suction", STAGES)
    sequence.advance("position")
    sequence.reset()
    assert sequence.completed() == ()
    assert sequence.is_done("position") is False


def test_a_procedure_needs_at_least_one_stage():
    with pytest.raises(ValueError):
        StageSequence("empty", ())
