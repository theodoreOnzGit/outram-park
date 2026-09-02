//! CLI frontend: scriptable, machine-readable output.
//!
//! Always compiled in and Android/Termux compatible (no windowing
//! dependencies) — usable by agents (scripted, one-shot invocations) and
//! humans alike. See [`crate::tui`] for the interactive counterpart.

use clap::{Args, ValueEnum};

#[derive(Args, Debug)]
pub struct CliArgs {
    /// Which reactor simulator to run.
    #[arg(value_enum)]
    pub simulator: Simulator,
}

#[derive(ValueEnum, Clone, Debug)]
pub enum Simulator {
    Fhr,
    Ipwr,
    Bwr,
    Htgr,
    Gen3,
    Fukushima,
}

pub fn run(args: CliArgs) {
    println!(
        "outram-park cli: {:?} simulator scaffold not yet implemented",
        args.simulator
    );
}
