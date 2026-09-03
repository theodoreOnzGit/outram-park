"""Type stubs for `outram_park.outram_park_fork_thermochimica`, generated from the Rust API.

Physical quantities cross this boundary as `float` in SI base units.
"""

class BinaryInteraction:
    species_i: int
    species_j: int
    l_coeffs: list[float]
    def __init__(self, species_i: int, species_j: int, l_coeffs: list[float]) -> None: ...

class GemError:
    @staticmethod
    def SingularSystem() -> GemError: ...
    @staticmethod
    def NotConverged(iterations: int, max_correction: float, atom_residual: float) -> GemError: ...
    def variant(self) -> str: ...

class GemOptions:
    tol: float
    max_iter: int
    max_step: float
    mole_floor: float
    phase_floor: float
    def __init__(self, tol: float, max_iter: int, max_step: float, mole_floor: float, phase_floor: float) -> None: ...
    @staticmethod
    def default() -> GemOptions: ...

class GemResult:
    moles: list[list[float]]
    mole_fractions: list[list[float]]
    phase_totals: list[float]
    activity_coefficients: list[list[float]]
    element_potentials: list[float]
    gibbs_energy_rt: float
    gibbs_energy: float
    descent_merit_history: list[float]
    iterations: int
    converged: bool
    def __init__(self, moles: list[list[float]], mole_fractions: list[list[float]], phase_totals: list[float], activity_coefficients: list[list[float]], element_potentials: list[float], gibbs_energy_rt: float, gibbs_energy: float, descent_merit_history: list[float], iterations: int, converged: bool) -> None: ...

class GemSystem:
    def n_elements(self) -> int: ...
    def n_phases(self) -> int: ...
    def n_species(self, p: int) -> int: ...
    def element_symbols(self) -> list[str]: ...
    def species_names(self, p: int) -> list[str]: ...

class PhaseInput:
    model: SolutionModel
    species_names: list[str]
    atom_matrix: list[list[float]]
    def __init__(self, model: SolutionModel, species_names: list[str], atom_matrix: list[list[float]]) -> None: ...

class SolutionModel:
    @staticmethod
    def IdealGas() -> SolutionModel: ...
    @staticmethod
    def IdealSolution() -> SolutionModel: ...
    @staticmethod
    def RedlichKister(interactions: list[BinaryInteraction]) -> SolutionModel: ...
    def variant(self) -> str: ...

R: float
