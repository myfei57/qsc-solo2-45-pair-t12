"""Write semantics: pump state is restored from the committed stream."""

from support import build, call, ok


def test_persisted_pump_state_survives_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/pump/persist", {})
    second = build(config)
    assert second.pump.persisted() is True
    assert second.pump.depth() == 6


def test_running_flag_returns_after_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/jet/open", {})
    ok(first.console, "POST", "/api/pump/start", {})
    second = build(config)
    assert second.pump.running() is True
    assert second.jet.is_open() is True


def test_stopped_pump_stays_stopped_after_a_restart(config):
    first = build(config)
    ok(first.console, "POST", "/api/jet/open", {})
    ok(first.console, "POST", "/api/pump/start", {})
    ok(first.console, "POST", "/api/overflow/close", {})
    ok(first.console, "POST", "/api/pump/stop", {})
    second = build(config)
    assert second.pump.running() is False
    assert second.overflow.closed() is True


def test_curve_generation_survives_a_restart(config):
    first = build(config)
    confirmation_id = ok(
        first.console,
        "POST",
        "/api/confirmation",
        {"name": "pump.curve", "subject": "pump", "ttl_ticks": 5},
    )["confirmation_id"]
    ok(
        first.console,
        "POST",
        "/api/pump/curve",
        {"slope": 1.6, "base": 1.0, "confirmation_id": confirmation_id},
    )
    second = build(config)
    assert second.pump.curve() == {"slope": 1.6, "base": 1.0, "generation": 1}
    assert second.generations.current("pump.curve") == 1


def test_uncommitted_pump_state_is_not_restored(config):
    first = build(config)
    ok(first.console, "POST", "/api/pump/persist", {})
    first.journal.open("draft")
    first.journal.append("pump/state", {"depth": 99, "tick": 0}, "draft", generation=0)
    second = build(config)
    assert second.pump.depth() == 6
    assert call(second.console, "GET", "/api/journal/pending").body["pending"] == ["draft"]
