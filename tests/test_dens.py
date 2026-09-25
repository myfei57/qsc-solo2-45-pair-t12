"""Density baseline, samples and expiry."""

import pytest

from dredgeops.errors import OutOfRangeError, StaleArtifactError

from support import build, issue_confirmation, ok


def test_calibration_needs_a_confirmation(services):
    with pytest.raises(Exception) as failure:
        services.dens.calibrate(1050.0, "cfm-000555")
    assert "unknown confirmation" in str(failure.value)


def test_calibration_publishes_a_new_generation(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    row = services.dens.calibrate(1050.0, confirmation_id)
    assert row == {
        "baseline": 1050.0,
        "offset": 1050.0,
        "generation": 1,
        "tick": 0,
    }
    assert services.generations.current("dens.baseline") == 1
    assert services.bus.count("dens.baseline.set") == 1


def test_calibration_rejects_an_out_of_range_baseline(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    with pytest.raises(OutOfRangeError):
        services.dens.calibrate(500.0, confirmation_id)


def test_replacing_the_probe_expires_the_stored_baseline(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1010.0, confirmation_id)
    assert services.dens.require_fresh_baseline()["generation"] == 1
    assert services.dens.replace_probe() == 2
    with pytest.raises(StaleArtifactError):
        services.dens.require_fresh_baseline()


def test_efficiency_is_refused_while_the_baseline_is_expired(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1010.0, confirmation_id)
    services.dens.replace_probe()
    with pytest.raises(StaleArtifactError):
        services.dens.efficiency(1200.0)


def test_efficiency_follows_the_baseline_after_recalibration(services, console):
    first = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, first)
    services.dens.replace_probe()
    second = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1100.0, second)
    assert services.dens.efficiency(1200.0) == 100.0
    assert services.dens.offset() == 1100.0
    assert services.dens.generation() == 3


def test_samples_are_capped_at_the_limit(services):
    for index in range(60):
        services.dens.add_sample(1000.0 + index)
    samples = services.dens.samples()
    assert len(samples) == 50
    assert samples[-1]["reading"] == 1059.0
    assert services.dens.sample_average() == pytest.approx(1034.5)


def test_samples_survive_a_restart(config):
    first = build(config)
    first.dens.add_sample(1010.0)
    second = build(config)
    assert second.dens.samples()[0]["reading"] == 1010.0
    assert second.dens.sample_average() == 1010.0


def test_view_reports_the_calibrated_state(services, console):
    assert services.dens.view().to_dict()["calibrated"] is False
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1020.0, confirmation_id)
    payload = ok(console, "GET", "/api/dens/verdict?reading=1200")
    assert payload["verdict"] == "high"
    assert payload["generation"] == 1
