//! **Fukushima Daiichi Unit 1 station-blackout demo** (AI draft, 2026-10-21).
//!
//! A GE BWR/3 with isolation condensers in a Mark I containment, from the
//! earthquake's scram through the station blackout, core damage, hydrogen,
//! venting and the reactor-building explosion, after the recorded sequence or
//! the reader's own actions. `bwr_sim` is kept for modern BWRs (BWRX-300,
//! ABWR); this binary is the Fukushima plant only.
//!
//! **Built against the `outram-park` metacrate only**: every backend crate is
//! reached through `outram_park::backend::*` (feature `fukushima`).
//!
//! ```text
//! cargo run --release --no-default-features --features fukushima --bin fukushima_sim
//! cargo run --release --no-default-features --features fukushima --bin fukushima_sim -- --headless 108000 600
//! cd outram-park/web/fukushima && trunk serve --release      # the browser demo
//! ```
//!
//! Research, education and V&V only. Not validated; not for operation,
//! licensing, safety decisions or emergency response. See `physics::params`
//! for the provenance of every number, and each physics module for what it
//! leaves out.

#![cfg_attr(target_arch = "wasm32", allow(dead_code))]

mod app;
mod engine;
mod physics;

/// Natively: the egui app with the engine on a thread, or `--headless
/// [steps] [every]` for a CSV trace with no window.
#[cfg(not(target_arch = "wasm32"))]
fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if let Some(i) = args.iter().position(|a| a == "--headless") {
        let steps = args.get(i + 1).and_then(|s| s.parse().ok()).unwrap_or(3600);
        let every = args.get(i + 2).and_then(|s| s.parse().ok()).unwrap_or(60);
        print!("{}", physics::headless_csv(steps, every));
        return Ok(());
    }
    eframe::run_native(
        "Fukushima Daiichi Unit 1",
        eframe::NativeOptions::default(),
        Box::new(|cc| {
            let ctx = cc.egui_ctx.clone();
            let link = outram_park::backend::dhoby_ghaut::web_demo::link::start_native(engine::Runner::default(), move || ctx.request_repaint());
            Ok(Box::new(app::App::new(link)))
        }),
    )
    .map_err(|e| e.to_string())
}

/// In the browser the same module starts four times: on the page (the egui
/// app), and in three workers told apart by their name: the plant worker
/// (unnamed) and the `core` and `containment` solver workers it starts.
#[cfg(target_arch = "wasm32")]
fn main() {
    use eframe::wasm_bindgen::JsCast as _;
    eframe::WebLogger::init(log::LevelFilter::Info).ok();
    if let Some(scope) = js_sys::global().dyn_ref::<web_sys::DedicatedWorkerGlobalScope>() {
        match scope.name().as_str() {
            "core" => engine::web::solver_main(0),
            "containment" => engine::web::solver_main(1),
            _ => outram_park::backend::dhoby_ghaut::web_demo::link::worker_main::<engine::Runner>(),
        }
        return;
    }
    let web_options = eframe::WebOptions { renderer: eframe::Renderer::Glow, ..Default::default() };
    wasm_bindgen_futures::spawn_local(async move {
        let document = web_sys::window().expect("no window").document().expect("no document");
        let canvas = document
            .get_element_by_id("fukushima_canvas")
            .expect("no #fukushima_canvas")
            .dyn_into::<web_sys::HtmlCanvasElement>()
            .expect("#fukushima_canvas is not a canvas");
        let started = eframe::WebRunner::new()
            .start(
                canvas,
                web_options,
                Box::new(|cc| {
                    let link = outram_park::backend::dhoby_ghaut::web_demo::link::start_web(cc.egui_ctx.clone(), engine::web::WORKER_JS, engine::Event::Error)?;
                    Ok(Box::new(app::App::new(link)))
                }),
            )
            .await;
        if let Some(el) = document.get_element_by_id("loading") {
            match started {
                Ok(()) => el.remove(),
                Err(e) => el.set_inner_html(&format!("<p>Failed to start: {e:?}</p>")),
            }
        }
    });
}
