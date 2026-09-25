"""Overflow door and spill arithmetic."""

from support import build, issue_confirmation, ok


def test_overflow_flow_is_zero_while_shut(services):
    services.overflow.close()
    assert services.overflow.closed() is True
    assert services.overflow.flow(100.0, 2.0) == 0.0


def test_overflow_flow_when_the_door_is_open(services):
    assert services.overflow.flow(100.0, 2.0) == 4.0


def test_spill_verdict_needs_an_open_door_and_a_high_level(services):
    assert services.overflow.spill_verdict(150.0, 150.0) is True
    assert services.overflow.spill_verdict(100.0, 150.0) is False
    services.overflow.close()
    assert services.overflow.spill_verdict(150.0, 150.0) is False


def test_residual_ignores_a_negative_level(services):
    assert services.overflow.residual(-5.0) == 0.0
    assert services.overflow.residual(10.0) == 6.0
    assert services.bus.count("overflow.closed") == 0


def test_judge_full_uses_the_hopper_capacity(services):
    assert services.overflow.judge_full(services.hopper, 150.0) is True
    assert services.overflow.judge_full(services.hopper, 140.0) is False


def test_capacity_cache_is_refreshed_after_a_map_rebuild(services, console):
    assert services.overflow.capacity(services.hopper) == 150.0
    confirmation_id = issue_confirmation(console, "hopper.map", "hopper")
    services.hopper.rebuild({"bow": 20.0}, confirmation_id)
    assert services.overflow.capacity(services.hopper) == 20.0
    assert services.overflow.view().to_dict()["cached_capacity"] == 20.0


def test_door_position_survives_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/overflow/close", {})
    second = build(config)
    assert second.overflow.closed() is True
