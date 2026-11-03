from Experiment import Experiment, Observable
from Simulation.engines import SimulationEngine
from Simulation.results import SimulationResult


class LiveSimulation(Observable):
    def __init__(self, experiment: Experiment, engine: SimulationEngine) -> None:
        super().__init__()
        self._experiment = experiment
        self._engine = engine
        self._stop_watching = experiment.subscribe(self._recompute)
        self._result = engine.run(experiment)

    @property
    def experiment(self) -> Experiment:
        return self._experiment

    @property
    def result(self) -> SimulationResult:
        return self._result

    def load_experiment(self, experiment: Experiment) -> None:
        self._stop_watching()
        self._experiment = experiment
        self._stop_watching = experiment.subscribe(self._recompute)
        self._recompute()

    def set_engine(self, engine: SimulationEngine) -> None:
        self._engine = engine
        self._recompute()

    def _recompute(self) -> None:
        self._result = self._engine.run(self._experiment)
        self._notify()
