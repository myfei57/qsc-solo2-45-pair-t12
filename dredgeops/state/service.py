"""Consolidated read model and the expiring control snapshot."""

from typing import Any, Mapping, Protocol

from ..clock import LogicalClock
from ..errors import StaleArtifactError
from ..event import Event, EventBus, topics
from ..store import Journal
from ..verdict import VerdictHistory
from ..version import ArtifactRef, Artifacts, Generations
from .counters import counters
from .view import ControlState

SNAPSHOT_NAME = "control.snapshot"


class Readable(Protocol):
    """Anything that can render a read model."""

    def view(self) -> Any: ...


class StateService:
    """Aggregates subsystem views and freezes them into expiring snapshots."""

    def __init__(
        self,
        journal: Journal,
        bus: EventBus,
        clock: LogicalClock,
        generations: Generations,
        artifacts: Artifacts,
        subsystems: Mapping[str, Readable],
        histories: Mapping[str, VerdictHistory],
    ) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._generations = generations
        self._artifacts = artifacts
        self._subsystems = dict(subsystems)
        self._histories = dict(histories)

    def view(self) -> ControlState:
        return ControlState(
            tick=self._clock.tick,
            committed_keys=len(self._journal.keys()),
            events=self._bus.sequence,
            watermark=self._journal.watermark,
            subsystems={
                name: subsystem.view().to_dict()
                for name, subsystem in self._subsystems.items()
            },
        )
    def counters(self) -> dict[str, int]:
        return counters(self._bus)

    def snapshot(self) -> dict[str, Any]:
        """Freeze the committed stream and record its digest."""
        frozen = self._journal.snapshot()
        generation = self._generations.advance(SNAPSHOT_NAME, "state-snapshot")
        ref = self._artifacts.record(
            "snapshot",
            SNAPSHOT_NAME,
            generation,
            frozen.digest,
            watermark=frozen.watermark,
        )
        self._bus.publish(topics.TOPIC_SNAPSHOT, frozen.watermark)
        return {"snapshot": frozen.to_dict(), "artifact": ref.to_row()}

    def require_snapshot(self, max_age_ticks: int = 100) -> ArtifactRef:
        """Return the latest snapshot while it is not superseded or too old."""
        ref = self._artifacts.get("snapshot", SNAPSHOT_NAME)
        if ref is None:
            raise StaleArtifactError("no snapshot recorded as " + SNAPSHOT_NAME)
        self._generations.require_current(
            SNAPSHOT_NAME, ref.generation, f"snapshot {SNAPSHOT_NAME}"
        )
        if self._clock.tick - ref.tick > max_age_ticks:
            raise StaleArtifactError("snapshot is too old")
        return ref
    def verdict_history(self, subject: str) -> dict[str, Any]:
        history = self._histories.get(subject)
        if history is None:
            return {"subject": subject, "current": "unknown", "points": []}
        return history.to_dict()

    def wire(self) -> None:
        """A parameter generation moving on invalidates any snapshot in force."""
        for topic in (
            topics.TOPIC_BASELINE_INVALIDATED,
            topics.TOPIC_BASELINE_SET,
            topics.TOPIC_CURVE_SET,
            topics.TOPIC_MAP_REBUILT,
        ):
            self._bus.subscribe(topic, self._expire_snapshot)

    def _expire_snapshot(self, event: Event) -> None:
        self._generations.advance(SNAPSHOT_NAME, "state-snapshot-expire")
