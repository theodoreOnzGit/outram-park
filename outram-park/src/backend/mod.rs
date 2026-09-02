//! One module per `outram-park-backend` crate, each gated behind a
//! same-named Cargo feature and re-exporting that crate's full public API
//! (see the individual module files, and the matching `[dependencies]` /
//! `[features]` entries in `Cargo.toml`). None of these compile in unless
//! their feature is explicitly enabled.

// KOVAN toolchain (agent-facing tooling)
#[cfg(feature = "kovan")]
pub mod kovan;
#[cfg(feature = "kovan-codegen")]
pub mod kovan_codegen;
#[cfg(feature = "kovan-common")]
pub mod kovan_common;
#[cfg(feature = "kovan-discovery")]
pub mod kovan_discovery;
#[cfg(feature = "kovan-literature")]
pub mod kovan_literature;
#[cfg(feature = "kovan-metrics")]
pub mod kovan_metrics;
#[cfg(feature = "kovan-semantics")]
pub mod kovan_semantics;

// Core physics / coupling
#[cfg(feature = "bedok")]
pub mod bedok;
#[cfg(feature = "nee_soon")]
pub mod nee_soon;
#[cfg(feature = "tampines")]
pub mod tampines;
#[cfg(feature = "tampines-steam-tables")]
pub mod tampines_steam_tables;
#[cfg(feature = "teh-o-prke")]
pub mod teh_o_prke;
#[cfg(feature = "tuas_boussinesq_solver")]
pub mod tuas_boussinesq_solver;
#[cfg(feature = "boon-lay")]
pub mod boon_lay;
#[cfg(feature = "chem-eng-real-time-process-control-simulator")]
pub mod chem_eng_real_time_process_control_simulator;

// OpenFOAM-derived stack
#[cfg(feature = "outram-foam-basic-lib")]
pub mod outram_foam_basic_lib;
#[cfg(feature = "outram-foam-appbuilder-lib")]
pub mod outram_foam_appbuilder_lib;
#[cfg(feature = "outram-foam-mesh")]
pub mod outram_foam_mesh;
#[cfg(feature = "outram-foam-turbulence-lib")]
pub mod outram_foam_turbulence_lib;
#[cfg(feature = "outram-foam-multiphase")]
pub mod outram_foam_multiphase;
#[cfg(feature = "outram-foam-cli")]
pub mod outram_foam_cli;

// Meshing / visualization
#[cfg(feature = "outram-blender")]
pub mod outram_blender;
#[cfg(feature = "outram-park-digital-twin-engine")]
pub mod outram_park_digital_twin_engine;
#[cfg(feature = "outram-park-fork-cfmesh")]
pub mod outram_park_fork_cfmesh;

// Ported/forked external codes
#[cfg(feature = "outram-park-fork-coolprop")]
pub mod outram_park_fork_coolprop;
#[cfg(feature = "outram-park-fork-dwsim-libs")]
pub mod outram_park_fork_dwsim_libs;
#[cfg(feature = "outram-park-fork-liggghts")]
pub mod outram_park_fork_liggghts;
#[cfg(feature = "outram-park-fork-moltres")]
pub mod outram_park_fork_moltres;
#[cfg(feature = "outram-park-fork-offbeat")]
pub mod outram_park_fork_offbeat;
#[cfg(feature = "outram-park-fork-onix")]
pub mod outram_park_fork_onix;
#[cfg(feature = "outram-park-fork-pflotran")]
pub mod outram_park_fork_pflotran;
#[cfg(feature = "outram-park-fork-thermochimica")]
pub mod outram_park_fork_thermochimica;
#[cfg(feature = "njoy-outram-park-fork")]
pub mod njoy_outram_park_fork;
#[cfg(feature = "outram-mc-libs")]
pub mod outram_mc_libs;
#[cfg(feature = "outram-park-mpi")]
pub mod outram_park_mpi;

// Other
#[cfg(feature = "raffles")]
pub mod raffles;
