"""End to end behaviour across the subsystem contracts."""

from dredgeops.config import Config
from dredgeops.console.server import ControlServer

from support import WEB_DIR, build, call, ok, refused


def run_sequence(console) -> None:
    ok(console, "POST", "/api/clock/advance", {"steps": 1})
    ok(console, "POST", "/api/pump/persist", {})
    ok(console, "POST", "/api/drag/lower", {"depth": 11})
    ok(console, "POST", "/api/jet/open", {})
    ok(console, "POST", "/api/pump/start", {})
    ok(console, "POST", "/api/hopper/gate", {})
    ok(console, "POST", "/api/valve/sea", {})
    ok(console, "POST", "/api/overflow/close", {})
    ok(console, "POST", "/api/pos/line/next", {"id": "L-1"})


def test_full_suction_line_sequence_runs_in_order(console):
    run_sequence(console)
    assert ok(console, "POST", "/api/pos/line/done", {"length": 128.5}) == {
        "done": 1,
        "latched": False,
    }
    track = ok(console, "GET", "/api/pos/track")
    assert track == {"total": 1, "closed": 1, "open": 0}
    state = ok(console, "GET", "/api/state")
    assert state["subsystems"]["pump"]["running"] is True
    assert state["subsystems"]["valve"]["sea_open"] is True
    assert state["subsystems"]["hopper"]["gate_open"] is True


def test_out_of_order_pump_start_is_reported(console):
    response = refused(console, "POST", "/api/pump/start", {})
    assert response.status == 409
    assert response.body["error"] == "pump: flush water is not open"
    assert call(console, "GET", "/api/journal/keys").body["keys"] == []


def test_valve_order_is_enforced_across_subsystems(console):
    ok(console, "POST", "/api/overflow/close", {})
    response = refused(console, "POST", "/api/valve/sea", {})
    assert response.status == 409
    ok(console, "POST", "/api/hopper/gate", {})
    assert ok(console, "POST", "/api/valve/sea", {})["sea_open"] is True


def test_restart_restores_every_subsystem(config):
    first = build(config)
    run_sequence(first.console)
    ok(first.console, "POST", "/api/pos/line/done", {"length": 100.0})

    second = build(config)
    assert second.pump.running() is True
    assert second.pump.persisted() is True
    assert second.jet.is_open() is True
    assert second.drag.lowered() is True
    assert second.drag.depth() == 11
    assert second.hopper.gate_open() is True
    assert second.valve.sea_open() is True
    assert second.overflow.closed() is True
    assert second.pos.latch() is False
    assert second.pos.done_lines() == 1
    assert second.audit.sequence > 0
    assert second.journal.watermark > 0


def test_two_runs_of_the_same_sequence_agree(tmp_path):
    digests = []
    for index in range(2):
        config = Config(data_dir=str(tmp_path / f"run{index}"), web_dir=WEB_DIR)
        services = build(config)
        run_sequence(services.console)
        digests.append(services.journal.view().digest())
    assert digests[0] == digests[1]


def test_uncommitted_work_is_invisible_to_the_rest_of_the_service(services):
    services.journal.open("draft")
    services.journal.append("pump/state", {"depth": 42, "tick": 0}, "draft")
    assert services.journal.read("pump/state") is None
    assert ok(services.console, "GET", "/api/journal/pending")["pending"] == ["draft"]
    services.journal.commit("draft")
    assert services.journal.read("pump/state") == {"depth": 42, "tick": 0}


def test_console_server_binds_a_local_port(console):
    server = ControlServer(("127.0.0.1", 0), console)
    try:
        host, port = server.server_address[:2]
        assert host == "127.0.0.1"
        assert port > 0
    finally:
        server.server_close()


def test_page_directory_is_delivered_from_the_configured_path(console, services):
    response = call(console, "GET", "/operations.html")
    assert response.status == 200
    assert "确认单" in response.to_bytes().decode("utf-8")
