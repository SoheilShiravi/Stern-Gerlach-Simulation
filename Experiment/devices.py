from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from math import degrees, pi
from typing import ClassVar, Self

import numpy as np

from Physics.spin import (
    ComplexMatrix,
    RealVector,
    axis_from_angles,
    density_from_bloch,
    projector,
)

NAMED_AXES: dict[str, tuple[float, float]] = {
    "x": (pi / 2, 0.0),
    "y": (pi / 2, pi / 2),
    "z": (0.0, 0.0),
}


def direction_label(theta: float, phi: float) -> str:
    axis = axis_from_angles(theta, phi)
    for name, angles in NAMED_AXES.items():
        if np.allclose(axis, axis_from_angles(*angles)):
            return name
    return f"θ={degrees(theta):.0f}° φ={degrees(phi):.0f}°"


class Device(ABC):
    @abstractmethod
    def kraus_operators(self) -> dict[str, ComplexMatrix]:
        pass

    @property
    @abstractmethod
    def label(self) -> str:
        """return short display text such as SG_z"""

    @property
    def output_ports(self) -> tuple[str, ...]:
        """Return the port names"""
        return tuple(self.kraus_operators())


@dataclass(frozen=True)
class SternGerlachDevice(Device):
    theta: float = 0.0
    phi: float = 0.0

    PORT_UP: ClassVar[str] = "+"
    PORT_DOWN: ClassVar[str] = "-"

    @classmethod
    def along(cls, axis_name: str) -> Self:
        """create a device along a named axis"""
        return cls(*NAMED_AXES[axis_name])

    @property
    def axis(self) -> RealVector:
        """return the unit vector n that this magnet measures along"""
        return axis_from_angles(self.theta, self.phi)

    def kraus_operators(self) -> dict[str, ComplexMatrix]:
        """return the projectors {"+": P+, "-": P-} along the magnet's axis.+"""
        return {
            self.PORT_UP: projector(self.axis, +1),
            self.PORT_DOWN: projector(self.axis, -1),
        }

    @property
    def label(self) -> str:
        """return display text such as SG_x."""
        return f"SG {direction_label(self.theta, self.phi)}"


@dataclass(frozen=True)
class Source:
    polarization: float = 0.0
    theta: float = 0.0
    phi: float = 0.0

    def __post_init__(self) -> None:
        """reject impossible polarizations when source is created"""
        if not 0.0 <= self.polarization <= 1.0:
            raise ValueError("Polarization must lie between 0 and 1")

    def density_matrix(self) -> ComplexMatrix:
        """return the normalised density matrix of the emitted beam"""
        return density_from_bloch(
            self.polarization * axis_from_angles(self.theta, self.phi)
        )

    @property
    def label(self) -> str:
        if self.polarization == 0.0:
            return "unpolarized"
        direction = direction_label(self.theta, self.phi)
        joiner = " along " if direction in NAMED_AXES else " "
        return f"{self.polarization:.0%}{joiner}{direction}"


DEVICE_CATALOG: dict[str, Callable[[], Device]] = {
    "Stern-Gerlach": SternGerlachDevice,
}
