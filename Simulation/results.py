from dataclasses import dataclass
from enum import Enum

from Experiment import SOURCE, PortRef


class BeamFate(Enum):
    ENTERS_DEVICE = "enters a device"
    EXITS = "exits the apparatus"
    BLOCKED = "is blocked"


@dataclass(frozen=True)
class Beam:
    port: PortRef
    path: tuple[PortRef, ...]
    fate: BeamFate
    probability: float
    spin: tuple[float, float, float] | None
    count: int | None = None

    @property
    def label(self) -> str:
        hops = [f"{hop.node}{hop.port}" for hop in self.path if hop.node != SOURCE]
        return " ".join(hops) or SOURCE


@dataclass(frozen=True)
class SimulationResult:
    beams: tuple[Beam, ...]
    total_particles: int | None = None

    @property
    def is_sampled(self) -> bool:
        return self.total_particles is not None

    @property
    def exits(self) -> tuple[Beam, ...]:
        return tuple(beam for beam in self.beams if beam.fate is BeamFate.EXITS)

    @property
    def blocked(self) -> tuple[Beam, ...]:
        return tuple(beam for beam in self.beams if beam.fate is BeamFate.BLOCKED)

    def beam_at(self, port: PortRef) -> Beam | None:
        return next((beam for beam in self.beams if beam.port == port), None)

    def fraction_of(self, beam: Beam) -> float:
        if beam.count is None or self.total_particles is None:
            return beam.probability
        return beam.count / self.total_particles
