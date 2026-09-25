"""Judgement semantics: bands and tolerance."""

import pytest

from dredgeops.errors import OutOfRangeError
from dredgeops.verdict import Band, HysteresisBand


def test_band_contains_its_limits():
    band = Band(900.0, 1300.0)
    assert band.contains(900.0) is True
    assert band.contains(1300.0) is True
    assert band.contains(899.9) is False
    assert band.low == 900.0
    assert band.high == 1300.0


def test_band_classifies_below_within_and_above():
    band = Band(10.0, 20.0)
    assert band.classify(9.0) == "below"
    assert band.classify(15.0) == "within"
    assert band.classify(21.0) == "above"


def test_band_require_rejects_an_out_of_range_value():
    band = Band(0.05, 20.0)
    assert band.require(1.5, "curve slope") == 1.5
    with pytest.raises(OutOfRangeError):
        band.require(21.0, "curve slope")


def test_band_rejects_an_inverted_range():
    with pytest.raises(ValueError):
        Band(10.0, 1.0)


def test_hysteresis_keeps_the_previous_verdict_inside_the_tolerance():
    band = HysteresisBand(0.4, 0.6, 0.05)
    assert band.classify(0.7) == "above"
    assert band.classify(0.61) == "above"
    assert band.classify(0.58) == "above"
    assert band.last == "above"


def test_hysteresis_flips_only_past_the_tolerance():
    band = HysteresisBand(0.4, 0.6, 0.05)
    assert band.classify(0.5) == "within"
    assert band.classify(0.3) == "below"
    assert band.classify(0.35) == "below"


def test_hysteresis_rejects_a_negative_tolerance():
    with pytest.raises(ValueError):
        HysteresisBand(0.4, 0.6, -0.1)
