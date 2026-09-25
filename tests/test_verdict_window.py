"""Judgement semantics: rolling window comparisons."""

import pytest

from dredgeops.verdict import Window, WindowEvaluator
from dredgeops.verdict.window import compare


def test_window_keeps_only_the_latest_samples():
    window = Window(3)
    for value in (1.0, 2.0, 3.0, 4.0):
        window.push(value)
    assert window.values() == (2.0, 3.0, 4.0)
    assert len(window) == 3
    assert window.is_full() is True
    assert window.size == 3


def test_window_average_and_span():
    window = Window(4)
    for value in (10.0, 14.0, 12.0):
        window.push(value)
    assert window.average() == 12.0
    assert window.span() == 4.0


def test_empty_window_reports_zero_statistics():
    window = Window(2)
    assert window.average() == 0.0
    assert window.span() == 0.0
    assert window.is_full() is False


def test_window_clear_drops_every_sample():
    window = Window(2)
    window.push(5.0)
    window.clear()
    assert window.values() == ()


def test_compare_requires_every_sample_to_agree():
    assert compare((2.0, 3.0, 4.0), 1.0, "above") is True
    assert compare((2.0, 0.5, 4.0), 1.0, "above") is False
    assert compare((0.5, 0.2), 1.0, "below") is True
    assert compare((), 1.0, "above") is False
    with pytest.raises(ValueError):
        compare((1.0,), 1.0, "sideways")


def test_evaluator_reports_insufficient_before_the_minimum():
    evaluator = WindowEvaluator(Window(3), 100.0, "above", 3)
    verdict = evaluator.push(130.0)
    assert verdict.verdict == "insufficient"
    assert verdict.samples == 1
    assert verdict.required == 3


def test_evaluator_reports_sustained_when_the_whole_window_agrees():
    evaluator = WindowEvaluator(Window(3), 100.0, "above", 3)
    for value in (120.0, 140.0, 160.0):
        verdict = evaluator.push(value)
    assert verdict.verdict == "sustained"
    assert verdict.average == 140.0
    assert verdict.span == 40.0
    assert verdict.to_dict()["required"] == 3


def test_evaluator_reports_transient_when_one_sample_disagrees():
    evaluator = WindowEvaluator(Window(3), 100.0, "above", 3)
    for value in (120.0, 40.0, 160.0):
        verdict = evaluator.push(value)
    assert verdict.verdict == "transient"
    assert evaluator.window.values() == (120.0, 40.0, 160.0)


def test_evaluator_rejects_an_unknown_mode():
    with pytest.raises(ValueError):
        WindowEvaluator(Window(2), 1.0, "sideways", 2)


def test_window_needs_a_positive_size():
    with pytest.raises(ValueError):
        Window(0)
