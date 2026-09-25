"""Suction arm drop gate, head verdicts and winch."""

import pytest

from dredgeops.errors import PreGateError, StaleArtifactError

from support import issue_confirmation, ok


def test_arm_drop_is_refused_before_the_pump_state_is_durable(services):
    with pytest.raises(PreGateError):
        services.drag.lower(services.pump)
    assert services.drag.lowered() is False


def test_arm_drop_is_accepted_after_the_pump_state_is_durable(services):
    services.pump.set_depth(12)
    services.pump.persist()
    assert services.drag.lower(services.pump) == 12
    assert services.drag.lowered() is True
    assert services.drag.depth() == 12


def test_restart_recovers_the_pump_state_then_drops_the_arm(services):
    services.pump.set_depth(9)
    services.pump.persist()
    assert services.drag.restart(services.pump) == 9
    assert services.bus.count("drag.lowered") == 1


def test_head_verdict_uses_the_baseline_in_force(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, confirmation_id)
    verdict = services.drag.head(services.dens, 1150.0)
    assert verdict == {
        "verdict": "high",
        "efficiency": 150.0,
        "baseline": 1000.0,
        "generation": 1,
    }


def test_head_verdict_is_refused_with_an_expired_baseline(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, confirmation_id)
    services.dens.replace_probe()
    with pytest.raises(StaleArtifactError):
        services.drag.head(services.dens, 1150.0)


def test_head_verdict_is_refused_before_any_calibration(services):
    with pytest.raises(StaleArtifactError):
        services.drag.head(services.dens, 1150.0)


def test_suction_pressure_starts_past_the_free_lift(services):
    assert services.drag.head_pressure(10, 1100.0) == pytest.approx(107.91)
    assert services.drag.suction_pressure(9.0) == 0.0
    assert services.drag.suction_pressure(15.0) == 3.0


def test_winch_reports_whether_the_angle_is_limited(services):
    result = services.drag.set_winch(24.5, 80.0)
    assert result["limited"] is True
    assert services.drag.winch()["cable_out"] == 24.5
    assert services.drag.angle_limit(20.0, 70.0) is False
    assert services.drag.view().line_count == 0


def test_lift_clears_the_lowered_flag(services):
    services.pump.persist()
    services.drag.lower(services.pump)
    services.drag.lift()
    assert services.drag.lowered() is False
    assert services.bus.count("drag.lifted") == 1
