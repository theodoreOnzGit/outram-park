//! `outram-park`: frontend crate for outram-park-backend.
//!
//! Houses three things:
//! 1. A desktop GUI ([`gui`]), gated behind the default `gui` feature.
//! 2. A CLI and TUI ([`cli`], [`tui`]), always compiled in and
//!    Android/Termux compatible, for agents and humans alike.
//! 3. Python bindings ([`python`]), built as a `cdylib` under the `python`
//!    feature and packaged with `maturin` into a single wheel that exposes
//!    the outram-park-backend API -- generated from each backend crate's
//!    rustdoc JSON by `codegen/gen_bindings.py`.

#[cfg(feature = "gui")]
pub mod gui;

pub mod cli;
pub mod tui;

pub mod backend;

#[cfg(feature = "python")]
pub mod python;
