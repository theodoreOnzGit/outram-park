//! Desktop GUI frontend, built on `egui`/`eframe`.
//!
//! Gated behind the default `gui` feature — not available on Termux/Android,
//! where the [`crate::cli`] and [`crate::tui`] frontends are used instead.

pub fn run() {
    let native_options = eframe::NativeOptions::default();
    eframe::run_native(
        "outram-park",
        native_options,
        Box::new(|_cc| Ok(Box::new(App::default()))),
    )
    .expect("failed to launch the outram-park GUI");
}

#[derive(Default)]
struct App;

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("outram-park");
            ui.label("GUI frontend scaffold — reactor simulators go here.");
        });
    }
}
