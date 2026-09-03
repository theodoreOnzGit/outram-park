//! Python bindings, built as a `cdylib` under the `python` feature.
//!
//! Packaged with `maturin` (see `pyproject.toml`) into a single wheel that
//! exposes the outram-park-backend simulation API to Python.
//!
//! The wheel's surface is generated rather than hand-written: for every
//! backend crate enabled by feature, `codegen/gen_bindings.py` reads that
//! crate's rustdoc JSON and emits a module under [`generated`] wrapping its
//! public types and functions. Each becomes a Python submodule, so
//! `teh-o-prke`'s API lands at `outram_park.teh_o_prke`, and so on.
//!
//! Units: the backend expresses physical quantities with `uom`. Across the
//! Python boundary each one is a plain `float` in SI base units — kelvin,
//! pascal, metre, second, watt. See [`runtime::from_si`].

pub mod generated;
pub mod runtime;

use pyo3::prelude::*;

/// The version of the `outram-park` crate this wheel was built from.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// The backend crates compiled into this wheel, as submodule names.
#[pyfunction]
fn backends() -> Vec<&'static str> {
    generated::BACKENDS.to_vec()
}

#[pymodule]
fn outram_park(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(backends, m)?)?;
    generated::register_all(py, m)?;
    Ok(())
}
