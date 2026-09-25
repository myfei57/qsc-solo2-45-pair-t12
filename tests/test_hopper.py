"""Hopper gate, map, level estimate and discharge release."""

import pytest

from dredgeops.errors import OutOfRangeError, StaleArtifactError
from dredgeops.verdict import INSUFFICIENT, SUSTAINED

from support import build, issue_confirmation, ok


def test_gate_state_survives_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/hopper/gate", {})
    second = build(config)
    assert second.hopper.gate_open() is True
    assert second.hopper.view().to_dict()["gate_open"] is True


def test_fullness_uses_the_compartment_capacity(services):
    hopper = services.hopper
    assert hopper.capacity() == 150.0
    assert hopper.fullness(75.0) == 0.5
    assert hopper.full_verdict(149.0) is False
    assert hopper.full_verdict(150.0) is True


def test_sustained_full_needs_a_whole_window(services):
    hopper = services.hopper
    verdicts = [hopper.sustained_full(160.0).verdict for _ in range(3)]
    assert verdicts == [INSUFFICIENT, INSUFFICIENT, SUSTAINED]
    assert hopper.history().current() == SUSTAINED


def test_map_rebuild_needs_a_confirmation(services):
    with pytest.raises(Exception) as failure:
        services.hopper.rebuild({"bow": 10.0}, "cfm-000777")
    assert "unknown confirmation" in str(failure.value)


def test_map_rebuild_replaces_the_capacity(services, console):
    confirmation_id = issue_confirmation(console, "hopper.map", "hopper")
    row = services.hopper.rebuild({"bow": 30.0, "mid": 20.0}, confirmation_id)
    assert row["generation"] == 1
    assert services.hopper.capacity() == 50.0
    assert services.generations.current("hopper.map") == 1


def test_map_rebuild_rejects_a_non_positive_compartment(services, console):
    confirmation_id = issue_confirmation(console, "hopper.map", "hopper")
    with pytest.raises(OutOfRangeError):
        services.hopper.rebuild({"bow": 30.0, "mid": 0.0}, confirmation_id)


def test_map_rebuild_rejects_an_empty_map(services, console):
    confirmation_id = issue_confirmation(console, "hopper.map", "hopper")
    with pytest.raises(OutOfRangeError):
        services.hopper.rebuild({}, confirmation_id)


def test_probe_levels_and_average(services):
    services.hopper.set_probe("bow", 30.0)
    services.hopper.set_probe("mid", 60.0)
    assert services.hopper.probes()["mid"] == 60.0
    assert services.hopper.probes()["stern"] == 0.0
    assert services.hopper.average_level() == 30.0


def test_discharge_latch_blocks_and_releases(services):
    assert services.hopper.can_discharge() is True
    services.hopper.lock_discharge()
    assert services.hopper.can_discharge() is False
    assert services.hopper.view().to_dict()["discharge_blocked"] is True
    services.hopper.release_latch()
    assert services.hopper.can_discharge() is True


def test_level_estimate_follows_the_curve_generation(services, console):
    assert services.hopper.estimate_level(services.pump, 10.0) == 15.0
    confirmation_id = issue_confirmation(console, "pump.curve", "pump")
    services.pump.recalibrate_curve(2.0, 0.0, confirmation_id)
    assert services.hopper.estimate_level(services.pump, 10.0) == 30.0


def test_time_to_fill_uses_the_current_rate(services):
    assert services.hopper.time_to_fill(services.pump, 10.0) == 15.0


def test_wash_state_tracks_start_and_stop(services):
    assert services.hopper.wash_state()["running"] is False
    services.hopper.start_wash()
    assert services.hopper.wash_state()["running"] is True
    services.hopper.stop_wash()
    assert services.hopper.wash_state()["running"] is False


def test_baseline_expiry_is_reported_through_the_service(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, confirmation_id)
    services.dens.replace_probe()
    with pytest.raises(StaleArtifactError):
        services.dens.require_fresh_baseline()
