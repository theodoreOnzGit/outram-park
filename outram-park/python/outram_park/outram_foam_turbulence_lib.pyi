"""Type stubs for `outram_park.outram_foam_turbulence_lib`, generated from the Rust API.

Physical quantities cross this boundary as `float` in SI base units.
"""

class TurbulenceError:
    @staticmethod
    def FieldSizeMismatch(a0: str) -> TurbulenceError: ...
    @staticmethod
    def NotInitialised() -> TurbulenceError: ...
    def variant(self) -> str: ...

class KEpsilon:
    mesh: outram_foam_basic_lib.FvMesh
    k: outram_foam_basic_lib.VolScalarField
    epsilon: outram_foam_basic_lib.VolScalarField
    nu_t: outram_foam_basic_lib.VolScalarField
    u: outram_foam_basic_lib.VolVectorField
    phi: outram_foam_basic_lib.SurfaceScalarField
    nu: outram_foam_basic_lib.VolScalarField
    dt: float
    prt: float
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh) -> None: ...

class KOmega:
    mesh: outram_foam_basic_lib.FvMesh
    k: outram_foam_basic_lib.VolScalarField
    omega: outram_foam_basic_lib.VolScalarField
    nu_t: outram_foam_basic_lib.VolScalarField
    u: outram_foam_basic_lib.VolVectorField
    phi: outram_foam_basic_lib.SurfaceScalarField
    nu: outram_foam_basic_lib.VolScalarField
    dt: float
    prt: float
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh) -> None: ...

class KOmegaSST:
    mesh: outram_foam_basic_lib.FvMesh
    k: outram_foam_basic_lib.VolScalarField
    omega: outram_foam_basic_lib.VolScalarField
    nu_t: outram_foam_basic_lib.VolScalarField
    u: outram_foam_basic_lib.VolVectorField
    phi: outram_foam_basic_lib.SurfaceScalarField
    nu: outram_foam_basic_lib.VolScalarField
    dt: float
    prt: float
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh) -> None: ...

class LaminarModel:
    mesh: outram_foam_basic_lib.FvMesh
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh, nu: outram_foam_basic_lib.VolScalarField) -> None: ...

class Smagorinsky:
    mesh: outram_foam_basic_lib.FvMesh
    nu_sgs: outram_foam_basic_lib.VolScalarField
    k_sgs: outram_foam_basic_lib.VolScalarField
    u: outram_foam_basic_lib.VolVectorField
    nu: outram_foam_basic_lib.VolScalarField
    prt: float
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh) -> None: ...
    def delta(self) -> list[float]: ...

class SpalartAllmaras:
    mesh: outram_foam_basic_lib.FvMesh
    nu_tilde: outram_foam_basic_lib.VolScalarField
    nu_t: outram_foam_basic_lib.VolScalarField
    u: outram_foam_basic_lib.VolVectorField
    phi: outram_foam_basic_lib.SurfaceScalarField
    nu: outram_foam_basic_lib.VolScalarField
    dt: float
    prt: float
    def __init__(self, mesh: outram_foam_basic_lib.FvMesh) -> None: ...

def nu_t_wall(y_p: float, nu: float) -> float: ...
def y_plus(y: float, u_tau: float, nu: float) -> float: ...
def u_tau(u_wall: float, y: float, nu: float) -> float: ...
ALPHA_K: float
ALPHA_OMEGA: float
BETA: float
BETA_STAR: float
GAMMA: float
A1: float
BETA1: float
BETA2: float
BETA_STAR: float
KAPPA: float
SIGMA_K1: float
SIGMA_K2: float
SIGMA_W1: float
SIGMA_W2: float
CE: float
CK: float
CB1: float
CB2: float
CS: float
CV1: float
CW1: float
CW2: float
CW3: float
KAPPA: float
SIGMA: float
