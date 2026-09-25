"""Flush water valve."""

from support import call, ok


def test_jet_reports_closed_until_it_opens(services):
    assert services.jet.is_open() is False
    assert services.jet.view().to_dict() == {"open": False}


def test_closed_jet_delivers_no_pressure(services):
    assert services.jet.pressure(50.0) == 0.0
    assert services.jet.nozzle_state(50.0) == {"open": False, "pressure": 0.0}


def test_opened_jet_delivers_pressure(services):
    services.jet.open_jet()
    assert services.jet.pressure(50.0) == 50.0
    assert services.jet.nozzle_state(50.0)["open"] is True


def test_close_reports_the_closed_state(services, console):
    ok(console, "POST", "/api/jet/open", {})
    body = ok(console, "POST", "/api/jet/close", {})
    assert body["open"] is False
    assert call(console, "GET", "/api/jet/pressure?flow=10").body["pressure"] == 0.0


def test_jet_position_survives_a_restart(config):
    from support import build

    first = build(config)
    ok(first.console, "POST", "/api/jet/open", {})
    second = build(config)
    assert second.jet.is_open() is True
    assert second.jet.nozzle_state(0.0)["pressure"] == 30.0
