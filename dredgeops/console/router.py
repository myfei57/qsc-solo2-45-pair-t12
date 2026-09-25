"""Request routing for the control console."""

from typing import Any, Callable

from ..errors import (
    BatchNotPendingError,
    CommitOrderError,
    ConfirmationMismatchError,
    ContractError,
    DuplicateBatchError,
    DuplicateStageError,
    LatchClearError,
    LatchSetError,
    MaintenanceError,
    OutOfRangeError,
    OutOfSequenceError,
    PreGateError,
    RollbackError,
    StaleArtifactError,
    UnknownBatchError,
    UnknownConfirmationError,
    UnknownKeyError,
    UnknownStageError,
)
from . import handlers, operations
from .http import Request, Response, error_response

Handler = Callable[["Console", Request], Response]

CONFLICT = (
    PreGateError,
    LatchSetError,
    LatchClearError,
    OutOfSequenceError,
    DuplicateStageError,
    DuplicateBatchError,
    StaleArtifactError,
    RollbackError,
    CommitOrderError,
)
MALFORMED = (OutOfRangeError, UnknownStageError, ConfirmationMismatchError)
MISSING = (UnknownKeyError, UnknownConfirmationError, UnknownBatchError, BatchNotPendingError)

ROUTES: tuple[tuple[str, str, Handler], ...] = (
    ("GET", "/healthz", handlers.health),
    ("GET", "/api/state", handlers.state),
    ("GET", "/api/state/counters", handlers.counters),
    ("GET", "/api/state/snapshot", handlers.snapshot_status),
    ("POST", "/api/state/snapshot", operations.state_snapshot),
    ("GET", "/api/verdict/history", handlers.verdict_history),
    ("GET", "/api/journal/keys", handlers.journal_keys),
    ("GET", "/api/journal/entries", handlers.journal_entries),
    ("GET", "/api/journal/pending", handlers.journal_pending),
    ("GET", "/api/journal/view", handlers.journal_view),
    ("POST", "/api/journal/commit", operations.journal_commit),
    ("POST", "/api/journal/discard", operations.journal_discard),
    ("POST", "/api/journal/rollback", operations.journal_rollback),
    ("POST", "/api/journal/maintenance", operations.journal_maintenance),
    ("POST", "/api/clock/advance", operations.journal_advance_tick),
    ("POST", "/api/confirmation", operations.confirmation_issue),
    ("GET", "/api/audit", handlers.audit),
    ("GET", "/api/audit/summary", handlers.audit_summary),
    ("POST", "/api/audit/clear", operations.audit_clear),
    ("GET", "/api/dens/verdict", handlers.dens_verdict),
    ("GET", "/api/dens/samples", handlers.dens_samples),
    ("POST", "/api/dens/calibrate", operations.dens_calibrate),
    ("POST", "/api/dens/probe/replace", operations.dens_probe_replace),
    ("POST", "/api/dens/sample", operations.dens_sample),
    ("GET", "/api/hopper/verdict", handlers.hopper_verdict),
    ("GET", "/api/hopper/level", handlers.hopper_level),
    ("GET", "/api/hopper/probes", handlers.hopper_probes),
    ("GET", "/api/hopper/wash", handlers.hopper_wash),
    ("GET", "/api/hopper/batches", handlers.hopper_batches),
    ("POST", "/api/hopper/gate", operations.hopper_gate),
    ("POST", "/api/hopper/gate/close", operations.hopper_gate_close),
    ("POST", "/api/hopper/rebuild", operations.hopper_rebuild),
    ("POST", "/api/hopper/probe", operations.hopper_probe),
    ("POST", "/api/hopper/batch", operations.hopper_batch),
    ("POST", "/api/hopper/wash/start", operations.hopper_wash_start),
    ("POST", "/api/hopper/wash/stop", operations.hopper_wash_stop),
    ("GET", "/api/pump/rate", handlers.pump_rate),
    ("GET", "/api/pump/pressure", handlers.pump_pressure),
    ("GET", "/api/pump/power", handlers.pump_power),
    ("POST", "/api/pump/persist", operations.pump_persist),
    ("POST", "/api/pump/start", operations.pump_start),
    ("POST", "/api/pump/stop", operations.pump_stop),
    ("POST", "/api/pump/emergency", operations.pump_emergency),
    ("POST", "/api/pump/shutdown", operations.pump_shutdown),
    ("POST", "/api/pump/curve", operations.pump_curve),
    ("GET", "/api/drag/line", handlers.drag_line),
    ("GET", "/api/drag/head", handlers.drag_head),
    ("GET", "/api/drag/winch", handlers.drag_winch),
    ("GET", "/api/drag/pressure", handlers.drag_pressure),
    ("POST", "/api/drag/lower", operations.drag_lower),
    ("POST", "/api/drag/lift", operations.drag_lift),
    ("POST", "/api/drag/restart", operations.drag_restart),
    ("POST", "/api/drag/winch", operations.drag_winch),
    ("GET", "/api/jet/pressure", handlers.jet_pressure),
    ("POST", "/api/jet/open", operations.jet_open),
    ("POST", "/api/jet/close", operations.jet_close),
    ("GET", "/api/valve/stroke", handlers.valve_stroke),
    ("POST", "/api/valve/sea", operations.valve_sea),
    ("POST", "/api/valve/alarm", operations.valve_alarm),
    ("POST", "/api/valve/stroke", operations.valve_stroke),
    ("GET", "/api/overflow/flow", handlers.overflow_flow),
    ("GET", "/api/overflow/judge", handlers.overflow_judge),
    ("POST", "/api/overflow/close", operations.overflow_close),
    ("POST", "/api/overflow/open", operations.overflow_open),
    ("GET", "/api/pos/track", handlers.pos_track),
    ("GET", "/api/pos/results", handlers.pos_results),
    ("GET", "/api/pos/waypoint", handlers.pos_waypoint),
    ("GET", "/api/pos/geometry", handlers.pos_geometry),
    ("POST", "/api/pos/line/next", operations.pos_line_next),
    ("POST", "/api/pos/line/done", operations.pos_line_done),
    ("POST", "/api/pos/waypoint", operations.pos_waypoint),
    ("GET", "/", handlers.page),
    ("GET", "/index.html", handlers.page),
    ("GET", "/operations.html", handlers.page),
    ("GET", "/lines.html", handlers.page),
    ("GET", "/audit.html", handlers.page),
)


def status_for(error: ContractError) -> int:
    """Map a contract violation onto a response status."""
    if isinstance(error, CONFLICT):
        return 409
    if isinstance(error, MALFORMED):
        return 422
    if isinstance(error, MISSING):
        return 404
    if isinstance(error, MaintenanceError):
        return 503
    return 400


class Console:
    """Routes requests onto subsystem operations and renders the status pages."""

    def __init__(self, services: Any) -> None:
        self.services = services
        self._routes: dict[tuple[str, str], Handler] = {
            (method, path): handler for method, path, handler in ROUTES
        }

    def routes(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._routes))

    def handle(self, request: Request) -> Response:
        handler = self._routes.get((request.method, request.path))
        if handler is None:
            return error_response(
                f"no route for {request.method} {request.path}",
                status=404,
            )
        try:
            return handler(self, request)
        except ContractError as error:
            return error_response(str(error), status=status_for(error))
        except (KeyError, ValueError, TypeError) as error:
            return error_response(f"malformed request: {error}", status=400)
