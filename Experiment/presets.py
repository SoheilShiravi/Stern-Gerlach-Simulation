from collections.abc import Callable
from math import radians

from Experiment.devices import Device, SternGerlachDevice
from Experiment.experiment import SOURCE_PORT, Experiment, PortRef

_PLUS = SternGerlachDevice.PORT_UP
_MINUS = SternGerlachDevice.PORT_DOWN


def _filter_chain(*devices: Device) -> Experiment:
    experiment = Experiment()
    previous_port = SOURCE_PORT
    for device in devices:
        name = experiment.add_device(device)
        experiment.connect(previous_port, name)
        if previous_port != SOURCE_PORT:
            experiment.set_blocked(PortRef(previous_port.node, _MINUS), True)
        previous_port = PortRef(name, _PLUS)
    return experiment


def single_device() -> Experiment:
    return _filter_chain(SternGerlachDevice.along("z"))


def repeated_measurement() -> Experiment:
    return _filter_chain(SternGerlachDevice.along("z"), SternGerlachDevice.along("z"))


def incompatible_axes() -> Experiment:
    return _filter_chain(
        SternGerlachDevice.along("z"),
        SternGerlachDevice.along("x"),
        SternGerlachDevice.along("z"),
    )


def tilted_axis() -> Experiment:
    return _filter_chain(
        SternGerlachDevice.along("z"),
        SternGerlachDevice(theta=radians(60)),
    )


def both_branches() -> Experiment:
    experiment = Experiment()
    first = experiment.add_device(SternGerlachDevice.along("z"))
    experiment.connect(SOURCE_PORT, first)
    for port_name in (_PLUS, _MINUS):
        branch = experiment.add_device(SternGerlachDevice.along("x"))
        experiment.connect(PortRef(first, port_name), branch)
    return experiment


PRESETS: dict[str, Callable[[], Experiment]] = {
    "Empty setup": Experiment,
    "Single magnet (z)": single_device,
    "Repeated measurement (z → z)": repeated_measurement,
    "Incompatible axes (z → x → z)": incompatible_axes,
    "Tilted magnet (z → θ=60°)": tilted_axis,
    "Both branches (z → x, x)": both_branches,
}

DEFAULT_PRESET = "Incompatible axes (z → x → z)"
