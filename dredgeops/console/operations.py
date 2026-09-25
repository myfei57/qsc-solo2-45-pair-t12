"""Write side of the control console."""

from typing import Any

from .http import Request, Response, json_response


def confirmation_issue(console: Any, request: Request) -> Response:
    body = request.body()
    confirmation = console.services.confirmations.issue(
        body["name"],
        body["subject"],
        int(body.get("ttl_ticks", 10)),
    )
    return json_response(confirmation.to_row())


def journal_advance_tick(console: Any, request: Request) -> Response:
    body = request.body()
    tick = console.services.clock.advance(int(body.get("steps", 1)))
    return json_response({"tick": tick})


def journal_maintenance(console: Any, request: Request) -> Response:
    body = request.body()
    console.services.journal.set_read_only(bool(body.get("on", False)))
    return json_response({"read_only": console.services.journal.read_only})


def journal_commit(console: Any, request: Request) -> Response:
    batch_id = request.body()["batch_id"]
    watermark = console.services.journal.commit(batch_id)
    return json_response({"batch_id": batch_id, "watermark": watermark})


def journal_discard(console: Any, request: Request) -> Response:
    batch_id = request.body()["batch_id"]
    dropped = console.services.journal.discard(batch_id)
    return json_response({"batch_id": batch_id, "dropped": dropped})


def journal_rollback(console: Any, request: Request) -> Response:
    body = request.body()
    batch_id = body["batch_id"]
    restored = console.services.journal.rollback(batch_id, body.get("reason", "operator rollback"))
    return json_response({"batch_id": batch_id, "keys_restored": restored})


def drag_lower(console: Any, request: Request) -> Response:
    pump = console.services.pump
    depth = request.body().get("depth")
    if depth is not None:
        pump.set_depth(int(depth))
    depth = console.services.drag.lower(pump)
    return json_response({"lowered": True, "depth": depth})


def drag_lift(console: Any, request: Request) -> Response:
    return json_response({"lifted": console.services.drag.lift()})


def drag_restart(console: Any, request: Request) -> Response:
    depth = console.services.drag.restart(console.services.pump)
    return json_response({"lowered": True, "depth": depth})


def drag_winch(console: Any, request: Request) -> Response:
    body = request.body()
    return json_response(
        console.services.drag.set_winch(body["cable_out"], body["angle"])
    )


def jet_open(console: Any, request: Request) -> Response:
    return json_response({"open": True, "tick": console.services.jet.open_jet()})


def jet_close(console: Any, request: Request) -> Response:
    return json_response({"open": False, "tick": console.services.jet.close()})


def pump_persist(console: Any, request: Request) -> Response:
    return json_response({"persisted": True, "tick": console.services.pump.persist()})


def pump_start(console: Any, request: Request) -> Response:
    tick = console.services.pump.start(console.services.jet)
    return json_response({"running": True, "tick": tick})


def pump_stop(console: Any, request: Request) -> Response:
    tick = console.services.pump.stop(console.services.overflow)
    return json_response({"running": False, "tick": tick})


def pump_emergency(console: Any, request: Request) -> Response:
    tick = console.services.pump.emergency_stop()
    return json_response({"running": False, "emergency": True, "tick": tick})


def pump_shutdown(console: Any, request: Request) -> Response:
    return json_response(
        console.services.pump.shutdown(console.services.drag, console.services.overflow)
    )


def pump_curve(console: Any, request: Request) -> Response:
    body = request.body()
    row = console.services.pump.recalibrate_curve(
        body["slope"],
        body["base"],
        body["confirmation_id"],
    )
    return json_response(row)


def hopper_gate(console: Any, request: Request) -> Response:
    return json_response({"gate_open": True, "tick": console.services.hopper.open_gate()})


def hopper_gate_close(console: Any, request: Request) -> Response:
    return json_response({"gate_open": False, "tick": console.services.hopper.close_gate()})


def hopper_rebuild(console: Any, request: Request) -> Response:
    body = request.body()
    row = console.services.hopper.rebuild(
        {str(name): float(volume) for name, volume in body["compartments"].items()},
        body["confirmation_id"],
    )
    return json_response(row)


def hopper_probe(console: Any, request: Request) -> Response:
    body = request.body()
    return json_response(console.services.hopper.set_probe(body["name"], body["level"]))


def hopper_batch(console: Any, request: Request) -> Response:
    body = request.body()
    row = console.services.hopper.record_batch(
        body["batch_id"],
        body["compartment"],
        body["volume"],
    )
    return json_response(row)


def hopper_wash_start(console: Any, request: Request) -> Response:
    return json_response({"running": True, "tick": console.services.hopper.start_wash()})


def hopper_wash_stop(console: Any, request: Request) -> Response:
    return json_response({"running": False, "tick": console.services.hopper.stop_wash()})


def valve_sea(console: Any, request: Request) -> Response:
    return json_response(console.services.valve.open_sea(console.services.hopper))


def valve_alarm(console: Any, request: Request) -> Response:
    body = request.body()
    if body.get("on", True):
        row = console.services.valve.set_alarm(console.services.hopper)
    else:
        row = console.services.valve.clear_alarm(console.services.hopper)
    row["discharge_ready"] = console.services.valve.discharge_ready(console.services.hopper)
    return json_response(row)


def valve_stroke(console: Any, request: Request) -> Response:
    body = request.body()
    return json_response(console.services.valve.set_stroke(body["position"], body["target"]))


def overflow_close(console: Any, request: Request) -> Response:
    return json_response({"closed": True, "tick": console.services.overflow.close()})


def overflow_open(console: Any, request: Request) -> Response:
    return json_response({"closed": False, "tick": console.services.overflow.open_gate()})


def dens_calibrate(console: Any, request: Request) -> Response:
    body = request.body()
    return json_response(
        console.services.dens.calibrate(body["baseline"], body["confirmation_id"])
    )


def dens_probe_replace(console: Any, request: Request) -> Response:
    return json_response({"generation": console.services.dens.replace_probe()})


def dens_sample(console: Any, request: Request) -> Response:
    return json_response(console.services.dens.add_sample(request.body()["reading"]))


def pos_line_next(console: Any, request: Request) -> Response:
    body = request.body()
    row = console.services.drag.next_line(console.services.pos, body["id"])
    return json_response({"line": row["line_id"], "latch": console.services.pos.latch()})


def pos_line_done(console: Any, request: Request) -> Response:
    return json_response(console.services.pos.line_done(request.body()["length"]))


def pos_waypoint(console: Any, request: Request) -> Response:
    body = request.body()
    console.services.pos.set_waypoint(body["name"], body["lat"], body["lon"])
    return json_response(console.services.pos.distance_to(body["lat"], body["lon"]))


def state_snapshot(console: Any, request: Request) -> Response:
    return json_response(console.services.state.snapshot())


def audit_clear(console: Any, request: Request) -> Response:
    return json_response({"cleared": console.services.audit.clear()})
