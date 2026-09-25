"""Keys used by the control state stream."""

PUMP_STATE = "pump/state"
PUMP_RUNNING = "pump/running"
PUMP_CURVE = "pump/curve"

JET_OPEN = "jet/open"

DRAG_LOWER = "drag/lower"
DRAG_LIFT = "drag/lift"
DRAG_LINE = "drag/line"
DRAG_WINCH = "drag/winch"

HOPPER_GATE = "hopper/gate"
HOPPER_MAP = "hopper/map"
HOPPER_RELEASE = "hopper/release"
HOPPER_PROBES = "hopper/probes"
HOPPER_WASH = "hopper/wash"

OVERFLOW_GATE = "overflow/gate"

VALVE_SEA = "valve/sea"
VALVE_ALARM = "valve/alarm"
VALVE_STROKE = "valve/stroke"

POS_LATCH = "pos/latch"
POS_LINE = "pos/line"
POS_LINE_RESULT = "pos/line-result"
POS_WAYPOINT = "pos/waypoint"

DENS_BASELINE = "dens/baseline"
DENS_SAMPLES = "dens/samples"

VERSION_PREFIX = "version/"
CONFIRMATION_PREFIX = "confirmation/"
ARTIFACT_PREFIX = "artifact/"
BATCH_PREFIX = "batch/"


def version_key(name: str) -> str:
    return VERSION_PREFIX + name


def confirmation_key(confirmation_id: str) -> str:
    return CONFIRMATION_PREFIX + confirmation_id


def artifact_key(kind: str, name: str) -> str:
    return f"{ARTIFACT_PREFIX}{kind}/{name}"


def batch_key(batch_id: str) -> str:
    return BATCH_PREFIX + batch_id
