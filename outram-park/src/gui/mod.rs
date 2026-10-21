//! Desktop GUI frontend, built on `egui`/`eframe`.
//!
//! Gated behind the default `gui` feature — not available on Termux/Android,
//! where the [`crate::cli`] and [`crate::tui`] frontends are used instead.

/// Launch the desktop GUI. GUI glue: needs a window, so no test reaches it.
#[cfg(not(target_arch = "wasm32"))]
pub fn run() {
    let native_options = eframe::NativeOptions::default();
    eframe::run_native(
        "outram-park",
        native_options,
        Box::new(|_cc| Ok(Box::new(App))),
    )
    .expect("failed to launch the outram-park GUI");
}

#[cfg(not(target_arch = "wasm32"))]
#[derive(Default)]
struct App;

#[cfg(not(target_arch = "wasm32"))]
impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ui, |ui| {
            ui.heading("outram-park");
            ui.label("GUI frontend scaffold — reactor simulators go here.");
        });
    }
}
