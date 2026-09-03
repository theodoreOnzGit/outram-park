"""Type stubs for `outram_park.outram_park_fork_moltres`, generated from the Rust API.

Physical quantities cross this boundary as `float` in SI base units.
"""

class CirculatingFuelSolver:
    k_eff: float
    def solve(self) -> EigenReport: ...
    def xs(self) -> XsFields: ...
    def beta_total(self) -> float: ...

class EigenReport:
    k_eff: float
    outer_iterations: int
    k_residual: float
    flux_residual: float
    converged: bool
    def __init__(self, k_eff: float, outer_iterations: int, k_residual: float, flux_residual: float, converged: bool) -> None: ...

class EigenSettings:
    k_tolerance: float
    flux_tolerance: float
    max_outer_iterations: int
    @staticmethod
    def default() -> EigenSettings: ...

class StaticDiffusion:
    k_eff: float
    def solve(self) -> EigenReport: ...
    def xs(self) -> XsFields: ...

class MoltresError:
    @staticmethod
    def InvalidMaterial(a0: str) -> MoltresError: ...
    @staticmethod
    def NoFissionSource() -> MoltresError: ...
    @staticmethod
    def NotConverged(outer_iterations: int, k_residual: float, flux_residual: float) -> MoltresError: ...
    @staticmethod
    def LinearSolveFailed(field: str, residual: float, iterations: int) -> MoltresError: ...
    def variant(self) -> str: ...

class DelayedFamily:
    beta: float
    @staticmethod
    def keepin_u235() -> list[DelayedFamily]: ...
    @staticmethod
    def total_beta(families: list[DelayedFamily]) -> float: ...

class MsrMaterial:
    name: str
    diffusion: list[float]
    sigma_removal: list[float]
    nu_sigma_f: list[float]
    chi_prompt: list[float]
    chi_delayed: list[float]
    scattering: list[list[float]]
    sigma_power: list[float]
    d_sigma_removal_d_temp: list[float]
    def __init__(self, name: str, diffusion: list[float], sigma_removal: list[float], nu_sigma_f: list[float], chi_prompt: list[float], chi_delayed: list[float], scattering: list[list[float]], sigma_power: list[float], d_sigma_removal_d_temp: list[float]) -> None: ...

class XsFields:
    energy_groups: int

class PrecursorDrift:
    families: list[DelayedFamily]
    diffusion: float

class RingMesh:
    circumference: float
    flow_area: float
    n_cells: int
    dx: float
    def __init__(self, circumference: float, flow_area: float, n_cells: int) -> None: ...
    def arc_centre(self, cell: int) -> float: ...
    def two_zone_map(self, core_length: float) -> list[int]: ...

class CoupledMsrSolver:
    neutronics: CirculatingFuelSolver
    thermal: SaltThermalModel
    target_power: float
    t_ref: float
    relaxation: float
    max_picard_iterations: int
    temperature_tolerance: float
    def solve(self) -> CoupledReport: ...

class CoupledReport:
    eigen: EigenReport
    picard_iterations: int
    temperature_residual: float

class SaltThermalConfig:
    rho_cp: float
    conductivity: float
    hx_conductance: float
    hx_temperature: float
    hx_mask: list[bool]

def reactivity(k_eff: float) -> float: ...
