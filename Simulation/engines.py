from abc import ABC, abstractmethod
from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray

from Experiment import SOURCE_PORT, Experiment, PortRef
from Physics.spin import (
    TOLERANCE,
    ComplexMatrix,
    apply_kraus,
    bloch_from_density,
    population,
)
from Simulation.results import Beam, BeamFate, SimulationResult


def _fate_of(experiment: Experiment, port: PortRef) -> BeamFate:
    if experiment.is_blocked(port):
        return BeamFate.BLOCKED
    if experiment.target_of(port) is None:
        return BeamFate.EXITS
    return BeamFate.ENTERS_DEVICE


def _spin_of(rho: ComplexMatrix) -> tuple[float, float, float] | None:
    if population(rho) <= TOLERANCE:
        return None
    x, y, z = bloch_from_density(rho)
    return float(x), float(y), float(z)


def _branch_probabilities(outputs: Iterable[ComplexMatrix]) -> NDArray[np.float64]:
    populations = np.array([population(rho) for rho in outputs])
    total = populations.sum()
    return populations / total if total > TOLERANCE else np.zeros_like(populations)


class SimulationEngine(ABC):
    total_particles: int | None = None

    def run(self, experiment: Experiment) -> SimulationResult:
        beams: list[Beam] = []
        self._follow_beam(
            experiment,
            SOURCE_PORT,
            experiment.source.density_matrix(),
            (),
            self.total_particles,
            beams,
        )
        return SimulationResult(tuple(beams), self.total_particles)

    def _follow_beam(
        self,
        experiment: Experiment,
        port: PortRef,
        rho: ComplexMatrix,
        earlier_path: tuple[PortRef, ...],
        count: int | None,
        beams: list[Beam],
    ) -> None:
        path = (*earlier_path, port)
        fate = _fate_of(experiment, port)
        beams.append(Beam(port, path, fate, population(rho), _spin_of(rho), count))
        if fate is not BeamFate.ENTERS_DEVICE:
            return

        next_node = experiment.target_of(port)
        outputs = {
            port_name: apply_kraus(kraus, rho)
            for port_name, kraus in experiment.device(next_node)
            .kraus_operators()
            .items()
        }
        counts = self._split_particles(count, _branch_probabilities(outputs.values()))
        for (port_name, rho_out), count_out in zip(outputs.items(), counts):
            self._follow_beam(
                experiment,
                PortRef(next_node, port_name),
                rho_out,
                path,
                count_out,
                beams,
            )

    @abstractmethod
    def _split_particles(
        self, count: int | None, probabilities: NDArray[np.float64]
    ) -> list[int | None]:
        ...


class ExactEngine(SimulationEngine):
    def _split_particles(
        self, count: int | None, probabilities: NDArray[np.float64]
    ) -> list[int | None]:
        return [None] * len(probabilities)


class MonteCarloEngine(SimulationEngine):
    def __init__(self, total_particles: int = 10_000, seed: int = 0) -> None:
        if total_particles <= 0:
            raise ValueError("The number of particles must be positive.")
        self.total_particles = total_particles
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def run(self, experiment: Experiment) -> SimulationResult:
        self._rng = np.random.default_rng(self.seed)
        return super().run(experiment)

    def _split_particles(
        self, count: int | None, probabilities: NDArray[np.float64]
    ) -> list[int | None]:
        if not count or probabilities.sum() == 0:
            return [0] * len(probabilities)
        return [int(n) for n in self._rng.multinomial(count, probabilities)]
