import itertools
from dataclasses import dataclass
from string import ascii_uppercase

from Experiment.devices import Device, Source
from Experiment.observable import Observable
from Physics.spin import is_complete_kraus_set


class ExperimentError(ValueError):
    """Raised when an edit would produce an invalid setup.

    Why a dedicated type: code building a setup can catch this one error, for example
    to show its message to a user, without also hiding genuine programming errors.
    """


@dataclass(frozen=True)
class PortRef:
    node: str
    port: str


SOURCE = "Source"
SOURCE_PORT = PortRef(SOURCE, "out")


class Experiment(Observable):
    def __init__(self, source: Source | None = None) -> None:
        """Create a setup containing only a source (unpolarized by default)."""
        super().__init__()
        self._source = source or Source()
        self._devices: dict[str, Device] = {}
        self._links: dict[PortRef, str] = {}
        self._blocked: set[PortRef] = set()

    def set_source(self, source: Source) -> None:
        self._source = source
        self._notify()

    def add_device(self, device: Device, name: str | None = None) -> str:
        self._check_is_physical(device)
        name = name or self._next_free_name()
        if name == SOURCE or name in self._devices:
            raise ExperimentError(f"The name {name!r} is already in use.")
        self._devices[name] = device
        self._notify()
        return name

    def replace_device(self, name: str, device: Device) -> None:
        self._require_device(name)
        self._check_is_physical(device)
        if device.output_ports != self._devices[name].output_ports:
            raise ExperimentError(
                "A replacement device must have the same output ports."
            )
        self._devices[name] = device
        self._notify()

    def remove_device(self, name: str) -> None:
        self._require_device(name)
        del self._devices[name]
        self._links = {
            port: target
            for port, target in self._links.items()
            if port.node != name and target != name
        }
        self._blocked = {port for port in self._blocked if port.node != name}
        self._notify()

    def connect(self, port: PortRef, target: str) -> None:
        self._require_port(port)
        self._require_device(target)
        if target not in self.connectable_targets(port):
            raise ExperimentError(
                f"{port.node} {port.port} cannot feed {target}: a device accepts "
                "one input beam and loops are not allowed."
            )
        self._links[port] = target
        self._notify()

    def disconnect(self, port: PortRef) -> None:
        self._require_port(port)
        self._links.pop(port, None)
        self._notify()

    def set_blocked(self, port: PortRef, blocked: bool) -> None:
        self._require_port(port)
        if blocked:
            self._blocked.add(port)
        else:
            self._blocked.discard(port)
        self._notify()

    @property
    def source(self) -> Source:
        return self._source

    @property
    def device_names(self) -> tuple[str, ...]:
        return tuple(self._devices)

    def device(self, name: str) -> Device:
        self._require_device(name)
        return self._devices[name]

    def output_ports(self, node: str) -> tuple[str, ...]:
        if node == SOURCE:
            return (SOURCE_PORT.port,)
        return self.device(node).output_ports

    def target_of(self, port: PortRef) -> str | None:
        return self._links.get(port)

    def input_of(self, name: str) -> PortRef | None:
        return next(
            (port for port, target in self._links.items() if target == name), None
        )

    def is_blocked(self, port: PortRef) -> bool:
        return port in self._blocked

    def connectable_targets(self, port: PortRef) -> list[str]:
        upstream = self._upstream_nodes(port.node)
        return [
            name
            for name in self._devices
            if name not in upstream and self.input_of(name) in (None, port)
        ]

    def _upstream_nodes(self, node: str) -> set[str]:
        upstream = {node}
        while (incoming := self.input_of(node)) is not None:
            node = incoming.node
            upstream.add(node)
        return upstream

    def _next_free_name(self) -> str:
        lengths = itertools.count(1)
        letter_groups = itertools.chain.from_iterable(
            itertools.product(ascii_uppercase, repeat=length) for length in lengths
        )
        return next(
            name for name in map("".join, letter_groups) if name not in self._devices
        )

    def _require_device(self, name: str) -> None:
        if name not in self._devices:
            raise ExperimentError(f"There is no device called {name!r}.")

    def _require_port(self, port: PortRef) -> None:
        if port.port not in self.output_ports(port.node):
            raise ExperimentError(f"{port.node} has no output port {port.port!r}.")

    @staticmethod
    def _check_is_physical(device: Device) -> None:
        if not is_complete_kraus_set(device.kraus_operators().values()):
            raise ExperimentError(
                f"{type(device).__name__} is not physical: its Kraus operators "
                "must satisfy Σ K†K = I."
            )
