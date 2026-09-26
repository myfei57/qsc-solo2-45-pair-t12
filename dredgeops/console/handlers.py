"""Read side of the control console."""

from typing import Any

from ..verdict import parse_filter
from .http import Request, Response, json_response
from .pages import read_page


def health(console: Any, request: Request) -> Response:
    journal = console.services.journal
    return json_response(
        {
            "status": "ok",
            "service": "control",
            "data_dir": journal.directory or "",
            "watermark": journal.watermark,
            "committed_keys": len(journal.keys()),
            "tick": console.services.clock.tick,
        }
    )


def state(console: Any, request: Request) -> Response:
    return json_response(console.services.state.view().to_dict())


def counters(console: Any, request: Request) -> Response:
    return json_response(console.services.state.counters())


def snapshot_status(console: Any, request: Request) -> Response:
    ref = console.services.state.require_snapshot(request.integer("max_age", 100))
    return json_response(ref.to_row())


def verdict_history(console: Any, request: Request) -> Response:
    subject = request.param("subject", "drag.head")
    return json_response(console.services.state.verdict_history(subject or "drag.head"))


def journal_keys(console: Any, request: Request) -> Response:
    prefix = request.param("prefix", "") or ""
    return json_response({"prefix": prefix, "keys": list(console.services.journal.keys(prefix))})


def journal_entries(console: Any, request: Request) -> Response:
    journal = console.services.journal
    record_filter = parse_filter(request.query)
    kept = [
        entry.to_row()
        for entry in journal.entries()
        if record_filter.matches(entry.as_filter_row())
    ]
    return json_response(
        {
            "filter": record_filter.describe(),
            "count": len(kept),
            "entries": kept,
            "watermark": journal.watermark,
        }
    )


def journal_pending(console: Any, request: Request) -> Response:
    journal = console.services.journal
    return json_response(
        {
            "watermark": journal.watermark,
            "pending": list(journal.pending_batches()),
            "aborted": list(journal.aborted_batches()),
        }
    )


def journal_view(console: Any, request: Request) -> Response:
    journal = console.services.journal
    watermark = request.param("watermark")
    limit = journal.watermark if watermark is None else int(watermark)
    view = journal.view(limit)
    return json_response(
        {
            "watermark": view.watermark,
            "rows": view.rows(),
            "digest": view.digest(),
        }
    )


def audit(console: Any, request: Request) -> Response:
    record_filter = parse_filter(request.query)
    records = console.services.audit.query(record_filter, request.integer("limit", 0))
    return json_response(
        {
            "filter": record_filter.describe(),
            "count": len(records),
            "records": [record.to_row() for record in records],
        }
    )


def audit_summary(console: Any, request: Request) -> Response:
    service = console.services.audit
    watermark = request.param("watermark")
    summary = service.summary(None if watermark is None else int(watermark))
    summary["sequence"] = service.sequence
    return json_response(summary)


def dens_verdict(console: Any, request: Request) -> Response:
    dens = console.services.dens
    reading = request.number("reading")
    return json_response(
        {
            "verdict": dens.verdict_of(reading),
            "efficiency": dens.efficiency(reading),
            "baseline": dens.view().baseline,
            "offset": dens.offset(),
            "generation": dens.generation(),
        }
    )


def dens_samples(console: Any, request: Request) -> Response:
    dens = console.services.dens
    return json_response(
        {"samples": list(dens.samples()), "average": dens.sample_average()}
    )


def hopper_verdict(console: Any, request: Request) -> Response:
    hopper = console.services.hopper
    level = request.number("level")
    return json_response(
        {
            "full": hopper.full_verdict(level),
            "fullness": hopper.fullness(level),
            "sustained": hopper.sustained_full(level).to_dict(),
        }
    )


def hopper_level(console: Any, request: Request) -> Response:
    hopper = console.services.hopper
    pump = console.services.pump
    speed = request.number("speed")
    level = hopper.estimate_level(pump, speed)
    return json_response(
        {
            "level": level,
            "full": hopper.full_verdict(level),
            "time_to_fill": hopper.time_to_fill(pump, speed),
        }
    )


def hopper_probes(console: Any, request: Request) -> Response:
    hopper = console.services.hopper
    return json_response({"probes": hopper.probes(), "average": hopper.average_level()})


def hopper_wash(console: Any, request: Request) -> Response:
    return json_response(console.services.hopper.wash_state())


def hopper_batches(console: Any, request: Request) -> Response:
    hopper = console.services.hopper
    return json_response(
        {
            "batches": [dict(entry) for entry in hopper.batch_entries()],
            "total": hopper.batch_total(),
        }
    )


def pump_rate(console: Any, request: Request) -> Response:
    pump = console.services.pump
    speed = request.number("speed")
    return json_response(
        {
            "rate": pump.rate(speed),
            "time_to_fill": pump.time_to_fill(speed, console.services.hopper.capacity()),
        }
    )


def pump_pressure(console: Any, request: Request) -> Response:
    pump = console.services.pump
    head = request.number("head")
    flow = request.number("flow")
    return json_response(
        {
            "pressure": pump.pressure(head, flow),
            "boost": pump.boost_pressure(pump.pressure(head, flow), 120.0),
        }
    )


def pump_power(console: Any, request: Request) -> Response:
    pump = console.services.pump
    speed = request.number("speed")
    head = request.number("head")
    power = pump.power(speed, head)
    return json_response(
        {
            "power": power,
            "factor": pump.power_factor(power, 800.0),
            "overload": pump.overload(power, 800.0),
        }
    )


def drag_line(console: Any, request: Request) -> Response:
    return json_response(console.services.drag.line_record())


def drag_head(console: Any, request: Request) -> Response:
    drag = console.services.drag
    return json_response(drag.head(console.services.dens, request.number("reading")))


def drag_winch(console: Any, request: Request) -> Response:
    state = console.services.drag.winch()
    return json_response({"winch": state, "present": state is not None})


def drag_pressure(console: Any, request: Request) -> Response:
    drag = console.services.drag
    head = drag.head_pressure(request.integer("depth"), request.number("density"))
    return json_response({"head": head, "suction": drag.suction_pressure(head)})


def jet_pressure(console: Any, request: Request) -> Response:
    jet = console.services.jet
    flow = request.number("flow")
    return json_response(
        {"pressure": jet.pressure(flow), "nozzle": jet.nozzle_state(flow)}
    )


def valve_stroke(console: Any, request: Request) -> Response:
    state = console.services.valve.stroke()
    return json_response({"stroke": state, "present": state is not None})


def overflow_flow(console: Any, request: Request) -> Response:
    overflow = console.services.overflow
    hopper = console.services.hopper
    level = request.number("level")
    capacity = overflow.capacity(hopper)
    return json_response(
        {
            "flow": overflow.flow(level, request.number("rate")),
            "spill": overflow.spill_verdict(level, capacity),
            "residual": overflow.residual(level),
            "capacity": capacity,
        }
    )


def overflow_judge(console: Any, request: Request) -> Response:
    overflow = console.services.overflow
    return json_response(
        {"full": overflow.judge_full(console.services.hopper, request.number("level"))}
    )


def pos_track(console: Any, request: Request) -> Response:
    return json_response(console.services.pos.track())


def pos_results(console: Any, request: Request) -> Response:
    return json_response({"results": [dict(row) for row in console.services.pos.results()]})


def pos_waypoint(console: Any, request: Request) -> Response:
    pos = console.services.pos
    state = pos.waypoint()
    return json_response({"waypoint": state, "present": state is not None})


def pos_geometry(console: Any, request: Request) -> Response:
    pos = console.services.pos
    lines = request.integer("lines", 5)
    spacing = request.number("spacing")
    return json_response(
        {
            "origins": pos.geometry(request.number("start"), spacing, lines),
            "origin3": pos.line_origin(3, spacing),
        }
    )


def page(console: Any, request: Request) -> Response:
    name = request.path.lstrip("/") or "index.html"
    return read_page(console.services.config.web_dir, name)
