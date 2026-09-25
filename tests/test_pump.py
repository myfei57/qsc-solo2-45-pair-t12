"""Pump sequencing, curve and load arithmetic."""

import pytest

from dredgeops.dens import DensService
from dredgeops.errors import PreGateError, StaleArtifactError

from support import issue_confirmation, ok


def test_pump_start_is_refused_before_flush_water_opens(services):
    with pytest.raises(PreGateError):
        services.pump.start(services.jet)
    assert services.pump.running() is False


def test_pump_start_is_accepted_once_flush_water_opens(services):
    ok(services.console, "POST", "/api/jet/open", {})
    services.pump.start(services.jet)
    assert services.pump.running() is True


def test_pump_stop_is_refused_before_the_overflow_door_shuts(services):
    ok(services.console, "POST", "/api/jet/open", {})
    services.pump.start(services.jet)
    with pytest.raises(PreGateError):
        services.pump.stop(services.overflow)
    assert services.pump.running() is True


def test_pump_stop_is_accepted_once_the_overflow_door_shuts(services):
    ok(services.console, "POST", "/api/jet/open", {})
    services.pump.start(services.jet)
    services.overflow.close()
    services.pump.stop(services.overflow)
    assert services.pump.running() is False


def test_emergency_stop_bypasses_the_overflow_interlock(services):
    ok(services.console, "POST", "/api/jet/open", {})
    services.pump.start(services.jet)
    services.pump.emergency_stop()
    assert services.pump.running() is False
    assert services.bus.count("pump.stopped") == 1


def test_shutdown_raises_the_arm_and_shuts_the_door_first(services):
    ok(services.console, "POST", "/api/pump/persist", {})
    services.drag.lower(services.pump)
    ok(services.console, "POST", "/api/jet/open", {})
    services.pump.start(services.jet)
    result = services.pump.shutdown(services.drag, services.overflow)
    assert result["running"] is False
    assert services.drag.lowered() is False
    assert services.overflow.closed() is True


def test_curve_recalibration_needs_a_confirmation(services):
    with pytest.raises(Exception) as failure:
        services.pump.recalibrate_curve(1.4, 2.0, "cfm-000404")
    assert "unknown confirmation" in str(failure.value)


def test_curve_recalibration_publishes_a_new_generation(services, console):
    confirmation_id = issue_confirmation(console, "pump.curve", "pump")
    row = services.pump.recalibrate_curve(1.4, 2.0, confirmation_id)
    assert row["generation"] == 1
    assert services.generations.current("pump.curve") == 1
    assert services.pump.curve() == {"slope": 1.4, "base": 2.0, "generation": 1}


def test_curve_recalibration_rejects_an_out_of_band_slope(services, console):
    confirmation_id = issue_confirmation(console, "pump.curve", "pump")
    with pytest.raises(Exception) as failure:
        services.pump.recalibrate_curve(30.0, 0.0, confirmation_id)
    assert "curve slope" in str(failure.value)


def test_curve_recalibration_refuses_a_confirmation_already_used(services, console):
    confirmation_id = issue_confirmation(console, "pump.curve", "pump")
    services.pump.recalibrate_curve(1.2, 0.0, confirmation_id)
    with pytest.raises(StaleArtifactError):
        services.pump.recalibrate_curve(1.3, 0.0, confirmation_id)


def test_discharge_follows_the_current_curve(services, console):
    assert services.pump.rate(10.0) == 10.0
    confirmation_id = issue_confirmation(console, "pump.curve", "pump")
    services.pump.recalibrate_curve(2.0, 0.0, confirmation_id)
    assert services.pump.rate(10.0) == 20.0
    assert services.pump.time_to_fill(10.0, 100.0) == 5.0


def test_discharge_is_zero_for_a_flat_or_negative_curve(services):
    assert services.pump.rate(0.0) == 0.0
    assert services.pump.time_to_fill(0.0, 100.0) == 0.0


def test_power_and_overload_follow_the_rated_load(services):
    power = services.pump.power(10.0, 20.0)
    assert power == pytest.approx(22.0)
    assert services.pump.power_factor(power, 800.0) == pytest.approx(0.0275)
    assert services.pump.overload(power, 800.0) is False
    assert services.pump.overload(power, 10.0) is True
    assert services.pump.power_factor(power, 0.0) == 0.0


def test_pressure_and_boost_arithmetic(services):
    pressure = services.pump.pressure(20.0, 5.0)
    assert pressure == pytest.approx(20.0 * 9.81 * 1.02 + 1.75)
    assert services.pump.boost_pressure(100.0, 120.0) == 20.0
    assert services.pump.boost_pressure(130.0, 120.0) == 0.0


def test_depth_rejects_a_negative_value(services):
    with pytest.raises(ValueError):
        services.pump.set_depth(-1)


def test_head_verdict_uses_the_dens_subsystem(services, console):
    dens = services.dens
    assert isinstance(dens, DensService)
    assert dens.view().calibrated is False
