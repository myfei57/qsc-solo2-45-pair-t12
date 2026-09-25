"""Judgement semantics: current verdict against historical verdict."""

from dredgeops.verdict import VerdictHistory


def test_current_reports_the_latest_verdict():
    history = VerdictHistory("dens.efficiency")
    history.record("low", 3, 1)
    history.record("high", 7, 2)
    assert history.current() == "high"
    assert history.subject == "dens.efficiency"


def test_at_reports_the_verdict_frozen_at_an_earlier_watermark():
    history = VerdictHistory("dens.efficiency")
    history.record("low", 3, 1)
    history.record("high", 7, 2)
    assert history.at(3) == "low"
    assert history.at(6) == "low"
    assert history.at(7) == "high"


def test_at_reports_unknown_before_the_first_verdict():
    history = VerdictHistory("dens.efficiency")
    history.record("high", 7, 2)
    assert history.at(2) == "unknown"


def test_changed_since_detects_a_flip():
    history = VerdictHistory("drag.head")
    history.record("low", 2, 1, "reading=90")
    assert history.changed_since(2) is False
    history.record("high", 5, 2, "reading=180")
    assert history.changed_since(2) is True
    assert history.points()[0].detail == "reading=90"


def test_to_dict_lists_every_point():
    history = VerdictHistory("hopper.fullness")
    history.record("transient", 4, 1)
    history.record("sustained", 8, 2)
    payload = history.to_dict()
    assert payload["subject"] == "hopper.fullness"
    assert payload["current"] == "sustained"
    assert [point["watermark"] for point in payload["points"]] == [4, 8]
