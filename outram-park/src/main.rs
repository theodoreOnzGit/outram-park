use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "outram-park",
    about = "Open-source TRAnsient Multi-Phase Advanced Reactor simulator Kit"
)]
struct Args {
    #[command(subcommand)]
    mode: Option<Mode>,
}

#[derive(Subcommand)]
enum Mode {
    /// Launch the desktop GUI.
    #[cfg(feature = "gui")]
    Gui,
    /// Run a one-shot, scriptable command (for agents and shell use).
    Cli(outram_park::cli::CliArgs),
    /// Launch the interactive terminal UI.
    Tui,
}

fn main() {
    let args = Args::parse();
    match args.mode {
        #[cfg(feature = "gui")]
        Some(Mode::Gui) => outram_park::gui::run(),
        Some(Mode::Cli(cli_args)) => outram_park::cli::run(cli_args),
        Some(Mode::Tui) => outram_park::tui::run(),
        None => default_mode(),
    }
}

#[cfg(feature = "gui")]
fn default_mode() {
    outram_park::gui::run();
}

#[cfg(not(feature = "gui"))]
fn default_mode() {
    outram_park::tui::run();
}
