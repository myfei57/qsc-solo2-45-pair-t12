"""Service wiring for the control console."""

from dataclasses import dataclass
from typing import Any

from .audit import AuditLog, AuditService
from .clock import IdSequence, LogicalClock
from .config import Config
from .console.router import Console
from .dens import DensService
from .drag import DragService
from .event import EventBus
from .hopper import HopperService
from .jet import JetService
from .overflow import OverflowService
from .pos import PosService
from .pump import PumpService
from .state import StateService
from .store import Journal
from .valve import ValveService
from .verdict import BatchRegistry
from .version import Artifacts, Confirmations, Generations


@dataclass
class Services:
    """Every subsystem wired together, with the console in front of them."""

    config: Config
    journal: Journal
    bus: EventBus
    clock: LogicalClock
    generations: Generations
    confirmations: Confirmations
    artifacts: Artifacts
    batches: BatchRegistry
    pump: PumpService
    jet: JetService
    drag: DragService
    hopper: HopperService
    overflow: OverflowService
    valve: ValveService
    pos: PosService
    dens: DensService
    audit: AuditService
    state: StateService
    console: Any = None

    def reload(self) -> None:
        """Restore every subsystem from the committed part of the stream."""
        self.pump.reload()
        self.jet.reload()
        self.drag.reload()
        self.hopper.reload()
        self.overflow.reload()
        self.valve.reload()
        self.pos.reload()
        self.dens.reload()


def build_services(config: Config) -> Services:
    """Wire the whole service from a configuration."""
    journal = Journal(config.data_dir)
    bus = EventBus()
    clock = LogicalClock()
    generations = Generations(journal)
    confirmations = Confirmations(journal, clock, IdSequence("cfm"), generations)
    artifacts = Artifacts(journal, clock)
    batches = BatchRegistry(journal)

    pump = PumpService(journal, bus, clock, generations, confirmations)
    jet = JetService(journal, bus, clock)
    drag = DragService(journal, bus, clock)
    hopper = HopperService(journal, bus, clock, generations, confirmations, batches)
    overflow = OverflowService(journal, bus, clock)
    valve = ValveService(journal, bus, clock)
    pos = PosService(journal, bus, clock)
    dens = DensService(journal, bus, clock, generations, confirmations)
    audit = AuditService(AuditLog(config.data_dir), bus, clock)
    state = StateService(
        journal,
        bus,
        clock,
        generations,
        artifacts,
        subsystems={
            "pump": pump,
            "jet": jet,
            "drag": drag,
            "hopper": hopper,
            "overflow": overflow,
            "valve": valve,
            "pos": pos,
            "dens": dens,
        },
        histories={
            "drag.head": drag.history(),
            "dens.efficiency": dens.history(),
            "hopper.fullness": hopper.history(),
        },
    )

    services = Services(
        config=config,
        journal=journal,
        bus=bus,
        clock=clock,
        generations=generations,
        confirmations=confirmations,
        artifacts=artifacts,
        batches=batches,
        pump=pump,
        jet=jet,
        drag=drag,
        hopper=hopper,
        overflow=overflow,
        valve=valve,
        pos=pos,
        dens=dens,
        audit=audit,
        state=state,
    )
    services.reload()
    hopper.wire()
    overflow.wire()
    audit.wire()
    state.wire()
    services.console = Console(services)
    return services
