"""Console routing, status mapping and page delivery."""

from dredgeops.console.pages import page_names
from dredgeops.console.router import ROUTES

from support import call, call_raw, ok, refused


def test_health_endpoint_reports_ok(console):
    body = ok(console, "GET", "/healthz")
    assert body["status"] == "ok"
    assert body["service"] == "control"
    assert body["watermark"] == 0
    assert body["tick"] == 0


def test_route_table_declares_each_method_and_path_once(console):
    routes = console.routes()
    assert len(routes) == len(ROUTES)
    assert len(set(routes)) == len(routes)
    assert ("GET", "/healthz") in routes
    assert ("POST", "/api/pump/start") in routes


def test_unknown_route_returns_not_found(console):
    response = refused(console, "GET", "/api/does-not-exist")
    assert response.status == 404
    assert "no route" in response.body["error"]


def test_state_endpoint_returns_every_subsystem(console):
    body = ok(console, "GET", "/api/state")
    assert len(body["subsystems"]) == 8
    assert body["subsystems"]["drag"]["lowered"] is False


def test_pre_gate_error_maps_to_conflict(console):
    response = refused(console, "POST", "/api/pump/start", {})
    assert response.status == 409
    assert "flush water" in response.body["error"]


def test_latch_error_maps_to_conflict(console):
    ok(console, "POST", "/api/pos/line/next", {"id": "L-1"})
    response = refused(console, "POST", "/api/pos/line/next", {"id": "L-2"})
    assert response.status == 409
    assert "latched" in response.body["error"]


def test_out_of_range_error_maps_to_unprocessable(console):
    confirmation_id = ok(
        console,
        "POST",
        "/api/confirmation",
        {"name": "dens.baseline", "subject": "dens", "ttl_ticks": 5},
    )["confirmation_id"]
    response = refused(
        console,
        "POST",
        "/api/dens/calibrate",
        {"baseline": 400.0, "confirmation_id": confirmation_id},
    )
    assert response.status == 422


def test_missing_confirmation_maps_to_not_found(console):
    response = refused(
        console,
        "POST",
        "/api/dens/calibrate",
        {"baseline": 1000.0, "confirmation_id": "cfm-000900"},
    )
    assert response.status == 404


def test_duplicate_batch_maps_to_conflict(console):
    ok(console, "POST", "/api/hopper/batch", {"batch_id": "D-1", "compartment": "bow", "volume": 3.0})
    response = refused(
        console,
        "POST",
        "/api/hopper/batch",
        {"batch_id": "D-1", "compartment": "mid", "volume": 4.0},
    )
    assert response.status == 409


def test_maintenance_mode_maps_to_unavailable(console):
    ok(console, "POST", "/api/journal/maintenance", {"on": True})
    response = refused(console, "POST", "/api/jet/open", {})
    assert response.status == 503
    ok(console, "POST", "/api/journal/maintenance", {"on": False})


def test_page_routes_serve_html(console):
    for name in page_names():
        path = "/" if name == "index.html" else f"/{name}"
        response = call(console, "GET", path)
        assert response.status == 200
        assert response.content_type.startswith("text/html")
        assert b"<html" in response.to_bytes()


def test_malformed_json_body_is_rejected(console):
    response = call_raw(console, "POST", "/api/clock/advance", "{not json")
    assert response.status == 400
    assert "malformed request" in response.body["error"]


def test_missing_body_field_is_rejected(console):
    response = call(console, "POST", "/api/hopper/probe", {"level": 3.0})
    assert response.status == 400
    assert "malformed request" in response.body["error"]


def test_journal_entry_filter_endpoint(console):
    ok(console, "POST", "/api/pump/persist", {})
    ok(console, "POST", "/api/jet/open", {})
    body = ok(console, "GET", "/api/journal/entries?key_prefix=pump/")
    assert body["count"] == 1
    assert body["entries"][0]["key"] == "pump/state"
    assert body["filter"]["key_prefix"] == "pump/"


def test_journal_keys_endpoint_lists_committed_keys(console):
    ok(console, "POST", "/api/hopper/gate", {})
    body = ok(console, "GET", "/api/journal/keys?prefix=hopper/")
    assert body["keys"] == ["hopper/gate"]


def test_journal_view_endpoint_can_freeze_at_a_watermark(console):
    ok(console, "POST", "/api/pump/persist", {})
    fresh = ok(console, "GET", "/api/journal/view")
    earlier = ok(console, "GET", "/api/journal/view?watermark=0")
    assert "pump/state" in fresh["rows"]
    assert earlier["rows"] == {}
    assert earlier["watermark"] == 0


def test_rollback_endpoint_restores_history(console):
    ok(console, "POST", "/api/pump/persist", {})
    entries = ok(console, "GET", "/api/journal/entries")["entries"]
    batch_id = entries[0]["batch_id"]
    body = ok(console, "POST", "/api/journal/rollback", {"batch_id": batch_id})
    assert body["keys_restored"] >= 1
    assert ok(console, "GET", "/api/journal/keys")["keys"] == []
