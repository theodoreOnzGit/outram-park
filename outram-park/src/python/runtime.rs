//! Conversion helpers shared by every generated binding module.
//!
//! These are the only hand-written pieces of the Python bridge; everything
//! under [`super::generated`] is emitted by `codegen/gen_bindings.py` and
//! calls into here.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

use core::marker::PhantomData;
use uom::si::{Dimension, Quantity, Units};

/// Wraps a plain `f64` back into a `uom` quantity, interpreting it in the
/// SI base units of its dimension (metre, kilogram, second, kelvin, mole,
/// ampere, candela, and products thereof — so pascal for pressure, watt for
/// power, and so on).
///
/// The dimension is inferred from the call site, which is what lets the
/// generated code stay dimension-agnostic: Python speaks `float`, Rust
/// keeps its units, and the boundary is this one function.
#[inline]
pub fn from_si<D, U>(value: f64) -> Quantity<D, U, f64>
where
    D: Dimension + ?Sized,
    U: Units<f64> + ?Sized,
{
    Quantity {
        dimension: PhantomData,
        units: PhantomData,
        value,
    }
}

/// The inverse of [`from_si`]: a `uom` quantity as an `f64` in SI base units.
#[inline]
pub fn to_si<D, U>(q: Quantity<D, U, f64>) -> f64
where
    D: Dimension + ?Sized,
    U: Units<f64> + ?Sized,
{
    q.value
}

/// Turns a Rust `Result` into a `PyResult`, rendering the error with its
/// `Debug` representation. Backend error types are enums that derive
/// `Debug`, so this keeps the variant and its payload visible in Python.
#[inline]
pub fn err<T, E: core::fmt::Debug>(r: Result<T, E>) -> PyResult<T> {
    r.map_err(|e| PyRuntimeError::new_err(format!("{:?}", e)))
}
