from collections.abc import Iterable
from math import cos, sin
import numpy as np
from numpy.typing import ArrayLike, NDArray

ComplexMatrix = NDArray[np.complex128]
RealVector = NDArray[np.float64]
TOLERANCE = 1e-12

IDENTITY: ComplexMatrix = np.eye(2, dtype=complex)
SIGMA_X: ComplexMatrix = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_Y: ComplexMatrix = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_Z: ComplexMatrix = np.array([[1, 0], [0, -1]], dtype=complex)

PAULI_VECTOR: NDArray[np.complex128] = np.stack([SIGMA_X, SIGMA_Y, SIGMA_Z])


def axis_from_angles(theta: float, phi: float) -> RealVector:
    """
    converts spherical radians into a Cartesian direction.
    """
    return np.array([sin(theta) * cos(phi), sin(theta) * sin(phi), cos(theta)])


def unit_vector(vector: ArrayLike) -> RealVector:
    vector = np.asarray(vector, dtype=float)
    length = np.linalg.norm(vector)
    if length <= TOLERANCE:
        raise ValueError("A direction needs a non-zero vector.")
    return vector / length


def _dot_sigma(vector: RealVector) -> ComplexMatrix:
    return np.tensordot(vector, PAULI_VECTOR, axes=1)


def pauli_along(axis: ArrayLike) -> ComplexMatrix:
    return _dot_sigma(unit_vector(axis))


def projector(axis: ArrayLike, outcome: int) -> ComplexMatrix:
    if outcome not in (+1, -1):
        raise ValueError(f"A spin-1/2 outcome must be +1 or -1, got {outcome=}.")
    return (IDENTITY + outcome * pauli_along(axis)) / 2


def density_from_bloch(bloch: ArrayLike) -> ComplexMatrix:

    bloch = np.asarray(bloch, dtype=float)
    if np.linalg.norm(bloch) > 1 + TOLERANCE:
        raise ValueError("A physical Bloch vector cannot be longer than 1.")
    return (IDENTITY + _dot_sigma(bloch)) / 2


def population(rho: ComplexMatrix) -> float:
    return max(float(np.trace(rho).real), 0.0)


def bloch_from_density(rho: ComplexMatrix) -> RealVector:
    total = population(rho)
    if total <= TOLERANCE:
        raise ValueError("A beam with zero population has no spin direction.")
    return np.trace(PAULI_VECTOR @ rho, axis1=1, axis2=2).real / total


def apply_kraus(kraus: ComplexMatrix, rho: ComplexMatrix) -> ComplexMatrix:
    return kraus @ rho @ kraus.conj().T


def is_complete_kraus_set(operators: Iterable[ComplexMatrix]) -> bool:
    total = sum(kraus.conj().T @ kraus for kraus in operators)
    return bool(np.allclose(total, IDENTITY, atol=1e-9))
