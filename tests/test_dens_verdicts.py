"""Judgement semantics: density verdicts and their history."""

import pytest

from dredgeops.errors import StaleArtifactError
from dredgeops.verdict import INSUFFICIENT, SUSTAINED, TRANSIENT

from support import issue_confirmation


def calibrated(services, console, baseline: float = 1000.0):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    return services.dens.calibrate(baseline, confirmation_id)


def test_verdict_is_high_above_the_threshold(services, console):
    calibrated(services, console)
    assert services.dens.verdict_of(1100.0) == "high"
    assert services.dens.verdict_of(1050.0) == "low"


def test_sustained_verdict_needs_a_whole_window(services, console):
    calibrated(services, console)
    verdicts = [services.dens.sustained_verdict(1300.0).verdict for _ in range(3)]
    assert verdicts == [INSUFFICIENT, INSUFFICIENT, SUSTAINED]


def test_sustained_verdict_is_transient_when_one_reading_drops(services, console):
    calibrated(services, console)
    services.dens.sustained_verdict(1300.0)
    services.dens.sustained_verdict(1010.0)
    verdict = services.dens.sustained_verdict(1300.0)
    assert verdict.verdict == TRANSIENT


def test_verdict_history_keeps_current_and_historical_verdicts(services, console):
    calibrated(services, console)
    services.dens.verdict_of(1300.0)
    earlier = services.journal.watermark
    services.dens.replace_probe()
    calibrated(services, console, 1100.0)
    services.dens.verdict_of(1010.0)
    history = services.dens.history()
    assert history.current() == "low"
    assert history.at(earlier) == "high"
    assert history.changed_since(earlier) is True


def test_second_calibration_with_the_same_confirmation_is_refused(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, confirmation_id)
    with pytest.raises(StaleArtifactError):
        services.dens.calibrate(1001.0, confirmation_id)


def test_confirmation_past_its_ttl_is_refused(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens", ttl_ticks=2)
    services.clock.advance(3)
    with pytest.raises(StaleArtifactError):
        services.dens.calibrate(1000.0, confirmation_id)
