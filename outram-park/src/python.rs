//! Python bindings, built as a `cdylib` under the `python` feature.
//!
//! Packaged with `maturin` (see `pyproject.toml`) into a single wheel that
//! exposes the outram-park-backend simulation API to Python.

use pyo3::prelude::*;

#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn outram_park(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
