"""Topic names carried on the control event bus."""

TOPIC_DRAG_LOWERED = "drag.lowered"
TOPIC_DRAG_LIFTED = "drag.lifted"
TOPIC_LINE_STARTED = "drag.line.started"
TOPIC_PUMP_STARTED = "pump.started"
TOPIC_PUMP_STOPPED = "pump.stopped"
TOPIC_PUMP_PERSISTED = "pump.persisted"
TOPIC_JET_OPENED = "jet.opened"
TOPIC_JET_CLOSED = "jet.closed"
TOPIC_GATE_OPENED = "hopper.gate.opened"
TOPIC_GATE_CLOSED = "hopper.gate.closed"
TOPIC_SEA_OPENED = "valve.sea.opened"
TOPIC_OVERFLOW_CLOSED = "overflow.closed"
TOPIC_OVERFLOW_OPENED = "overflow.opened"
TOPIC_LINE_DONE = "pos.line.done"
TOPIC_BASELINE_SET = "dens.baseline.set"
TOPIC_BASELINE_INVALIDATED = "dens.baseline.invalidated"
TOPIC_CURVE_SET = "pump.curve.set"
TOPIC_MAP_REBUILT = "hopper.map.rebuilt"
TOPIC_DISCHARGE_LOCKED = "hopper.discharge.locked"
TOPIC_DISCHARGE_FREED = "hopper.discharge.freed"
TOPIC_VALVE_ALARM = "valve.alarm.changed"
TOPIC_HOPPER_BATCH = "hopper.batch.recorded"
TOPIC_SNAPSHOT = "state.snapshot"

ALL_TOPICS: tuple[str, ...] = (
    TOPIC_DRAG_LOWERED,
    TOPIC_DRAG_LIFTED,
    TOPIC_LINE_STARTED,
    TOPIC_PUMP_STARTED,
    TOPIC_PUMP_STOPPED,
    TOPIC_PUMP_PERSISTED,
    TOPIC_JET_OPENED,
    TOPIC_JET_CLOSED,
    TOPIC_GATE_OPENED,
    TOPIC_GATE_CLOSED,
    TOPIC_SEA_OPENED,
    TOPIC_OVERFLOW_CLOSED,
    TOPIC_OVERFLOW_OPENED,
    TOPIC_LINE_DONE,
    TOPIC_BASELINE_SET,
    TOPIC_BASELINE_INVALIDATED,
    TOPIC_CURVE_SET,
    TOPIC_MAP_REBUILT,
    TOPIC_DISCHARGE_LOCKED,
    TOPIC_DISCHARGE_FREED,
    TOPIC_VALVE_ALARM,
    TOPIC_HOPPER_BATCH,
    TOPIC_SNAPSHOT,
)
