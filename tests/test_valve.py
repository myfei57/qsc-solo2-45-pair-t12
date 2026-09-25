"""Sea valve, discharge alarm latch and stroke."""

import pytest

from dredgeops.errors import LatchSetError, PreGateError

from support import build, ok


def test_sea_valve_is_refused_before_the_hopper_gate_opens(services):
    with pytest.raises(PreGateError):
        services.valve.open_sea(services.hopper)
    assert services.valve.sea_open() is False


def test_sea_valve_opens_once_the_hopper_gate_is_open(services):
    services.hopper.open_gate()
    row = services.valve.open_sea(services.hopper)
    assert row["sea_open"] is True
    assert services.valve.sea_open() is True
    assert services.bus.count("valve.sea.opened") == 1


def test_discharge_alarm_cannot_latch_while_the_sea_valve_is_open(services):
    services.hopper.open_gate()
    services.valve.open_sea(services.hopper)
    with pytest.raises(LatchSetError):
        services.valve.set_alarm(services.hopper)
    assert services.valve.alarm_active() is False
    assert services.hopper.can_discharge() is True


def test_discharge_alarm_clears_and_frees_the_latch(services):
    services.valve.set_alarm(services.hopper)
    assert services.valve.alarm_active() is True
    assert services.hopper.can_discharge() is False
    assert services.valve.discharge_ready(services.hopper) is False
    services.valve.clear_alarm(services.hopper)
    assert services.valve.alarm_active() is False
    assert services.valve.discharge_ready(services.hopper) is True
    assert services.bus.count("valve.alarm.changed") == 2


def test_stroke_verdict_reports_seated_within_tolerance(services):
    row = services.valve.set_stroke(40.0, 41.5)
    assert row["verdict"] == "seated"
    assert services.valve.stroke_verdict(40.0, 50.0) == "traveling"
    assert services.valve.stroke()["target"] == 41.5


def test_alarm_position_survives_a_restart(config):
    first = build(config)
    first.valve.set_alarm(first.hopper)
    second = build(config)
    assert second.valve.alarm_active() is True
    assert second.hopper.can_discharge() is False


def test_sea_valve_position_survives_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/hopper/gate", {})
    ok(first.console, "POST", "/api/valve/sea", {})
    second = build(config)
    assert second.valve.sea_open() is True
    assert second.valve.view().to_dict() == {"sea_open": True, "alarm": False}
