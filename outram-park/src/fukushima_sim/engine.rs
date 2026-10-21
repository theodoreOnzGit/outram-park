//! The physics engine, off the UI thread (the "no lagging" rule): natively a
//! thread, in the browser a Web Worker running the same wasm module, both
//! through `dhoby_ghaut::web_demo::link`. The page only draws.
//!
//! ## Parallelism, after the CIET Educational Simulator's browser demo
//!
//! | CIET demo | this demo |
//! |---|---|
//! | page draws (plain JS) | page draws (egui) |
//! | plant worker: heat transfer, real-time pacing | plant worker: the vessel, isolation condensers, relief valves, operators' sequence, pacing |
//! | DRACS-flow worker, primary-flow worker, solving from a start-of-step snapshot | core worker (fuel heat-up, oxidation, relocation) and containment worker (drywell, wetwell, building), stepping from a start-of-step snapshot |
//!
//! As in CIET, the solver workers are **stateless**: each message carries the
//! part's whole state and the step's snapshot, and the reply carries the new
//! state and the result. So the run can switch between one worker (both
//! parts stepped inline in the plant worker) and three at any time, and the
//! two give the same numbers bit for bit (`physics::tests::three_workers_are_one_worker`).
//! The plant worker sends the core's and the containment's messages, and the
//! two workers step **at the same time**; it finishes the step when both
//! replies are in.
//!
//! ## Pacing
//!
//! The page sends a [`Request::Tick`] when it is ready for news (one
//! outstanding at a time); the engine steps until the simulated clock
//! reaches `speed x` the wall time since the run was (re)started, or for at
//! most [`TICK_BUDGET_MS`], then answers with a frame.

use crate::physics::containment::{Containment, ContainmentResult, ContainmentSnapshot};
use crate::physics::core::{Core, CoreResult, CoreSnapshot};
use crate::physics::wire::{Reader, Writer};
use crate::physics::{Frame, Mode, Plant};
use outram_park::backend::dhoby_ghaut::web_demo::link::Floats;
use outram_park::backend::dhoby_ghaut::web_demo::platform::now_s;

/// Longest a tick steps before answering, ms (a frame's worth, so the page
/// hears often even when the physics cannot keep up).
pub const TICK_BUDGET_MS: f64 = 30.0;
/// Simulated seconds between history samples.
pub const SAMPLE_EVERY_S: f64 = 60.0;
/// Numbers per history sample (see [`Runner::sample`]).
pub const SAMPLE_LEN: usize = 10;

/// Operator controls the page can set.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Control {
    IcA,
    IcB,
    DcPower,
    ReliefHeldOpen,
    Injection,
    Vent,
}

impl Control {
    pub const ALL: [Control; 6] = [Control::IcA, Control::IcB, Control::DcPower, Control::ReliefHeldOpen, Control::Injection, Control::Vent];
    fn index(self) -> usize {
        Self::ALL.iter().position(|c| *c == self).unwrap_or(0)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum Request {
    Tick,
    Run(bool),
    /// Simulated seconds per wall second; 0 = as fast as it goes.
    Speed(f64),
    /// 1 or 3 workers.
    Workers(u8),
    Mode(Mode),
    Set(Control, bool),
    Reset,
}

#[derive(Clone)]
pub enum Event {
    /// The plant now, the history samples since the last frame, and
    /// `[steps per wall second, ms per step, behind the clock (s), workers]`.
    Frame { frame: Floats, history: Floats, stats: [f64; 4] },
    /// Natively the engine thread cannot fail this way; a worker can.
    #[cfg_attr(not(target_arch = "wasm32"), allow(dead_code))]
    Error(String),
}

/// The engine's state: the three parts, the clock, the history.
pub struct Runner {
    pub plant: Plant,
    pub core: Core,
    pub containment: Containment,
    pub running: bool,
    pub speed: f64,
    pub workers: u8,
    /// (wall s, sim s) at the last (re)start or speed change.
    anchor: (f64, f64),
    next_sample: f64,
    history: Vec<f64>,
    tick_start: f64,
    steps_this_tick: u32,
    behind_s: f64,
    #[cfg(target_arch = "wasm32")]
    web: web::Solvers,
}

impl Default for Runner {
    fn default() -> Self {
        let plant = Plant::new(Mode::Historical);
        let (core, containment) = plant.parts();
        let mut r = Self {
            plant,
            core,
            containment,
            running: false,
            speed: 600.0,
            workers: 3,
            anchor: (now_s(), 0.0),
            next_sample: 0.0,
            history: Vec::new(),
            tick_start: 0.0,
            steps_this_tick: 0,
            behind_s: 0.0,
            #[cfg(target_arch = "wasm32")]
            web: web::Solvers::default(),
        };
        r.sample();
        r
    }
}

impl Runner {
    fn reanchor(&mut self) {
        self.anchor = (now_s(), self.plant.time_s());
    }

    /// Apply a request other than `Tick`.
    pub fn apply(&mut self, r: Request) {
        match r {
            Request::Tick => {}
            Request::Run(on) => {
                self.running = on;
                self.reanchor();
            }
            Request::Speed(s) => {
                self.speed = s.max(0.0);
                self.reanchor();
            }
            Request::Workers(n) => self.workers = if n >= 3 { 3 } else { 1 },
            Request::Mode(m) => self.plant.mode = m,
            Request::Set(c, on) => {
                let k = &mut self.plant.controls;
                match c {
                    Control::IcA => k.ic_open[0] = on,
                    Control::IcB => k.ic_open[1] = on,
                    Control::DcPower => k.dc_power = on,
                    Control::ReliefHeldOpen => k.relief_held_open = on,
                    Control::Injection => k.injection = on,
                    Control::Vent => k.vent_ordered = on,
                }
                let _ = c.index();
            }
            Request::Reset => {
                let mode = self.plant.mode;
                self.plant = Plant::new(mode);
                (self.core, self.containment) = self.plant.parts();
                self.history.clear();
                self.next_sample = 0.0;
                self.sample();
                self.reanchor();
            }
        }
    }

    /// Start a tick's budget.
    pub fn start_tick(&mut self) {
        self.tick_start = now_s();
        self.steps_this_tick = 0;
    }

    /// Whether to take another step in this tick.
    pub fn should_step(&mut self) -> bool {
        if !self.running || self.plant.time_s() >= crate::physics::SCENARIO_END_S {
            return false;
        }
        let now = now_s();
        if (now - self.tick_start) * 1e3 >= TICK_BUDGET_MS {
            return false;
        }
        if self.speed > 0.0 {
            let target = self.anchor.1 + self.speed * (now - self.anchor.0);
            let behind = target - self.plant.time_s();
            self.behind_s = behind.max(0.0);
            // More than a minute behind: give up catching up (re-anchor),
            // and report it.
            if behind > 60.0 * self.speed.max(1.0) {
                self.reanchor();
            }
            return behind > 0.0;
        }
        self.behind_s = 0.0;
        true
    }

    /// After a finished step: count it and sample the history.
    pub fn after_step(&mut self) {
        self.steps_this_tick += 1;
        if self.plant.time_s() >= self.next_sample {
            self.sample();
        }
    }

    fn sample(&mut self) {
        let f = self.plant.frame();
        self.history.extend_from_slice(&[
            f.t_s,
            f.vessel.p_pa / 1e6,
            f.vessel.level_m,
            f.core.peak_clad_k.max(f.vessel.sat.t_k),
            f.containment.p_dw_pa / 1e6,
            f.containment.p_ww_pa / 1e6,
            f.core.h2_total_kg,
            f.decay_w / 1e6,
            f.containment.t_pool_k,
            f.containment.rb_h2_fraction,
        ]);
        self.next_sample = f.t_s + SAMPLE_EVERY_S;
    }

    /// The frame event that ends a tick.
    pub fn frame_event(&mut self) -> Event {
        let mut w = Writer::default();
        self.plant.frame().write(&mut w);
        let elapsed = (now_s() - self.tick_start).max(1e-9);
        let ms_per_step = if self.steps_this_tick > 0 { elapsed * 1e3 / self.steps_this_tick as f64 } else { 0.0 };
        let stats = [self.steps_this_tick as f64 / elapsed, ms_per_step, self.behind_s, self.workers as f64];
        Event::Frame { frame: Floats::from_vec(w.0), history: Floats::from_vec(std::mem::take(&mut self.history)), stats }
    }

    /// Step inline until the tick is spent (one-worker mode, and natively).
    pub fn run_inline(&mut self) {
        while self.should_step() {
            self.plant.step_inline(&mut self.core, &mut self.containment);
            self.after_step();
        }
    }
}

#[cfg_attr(not(target_arch = "wasm32"), allow(dead_code))] // used by the browser's solver workers (and the tests)
/// A solver worker's whole job: read the state and the snapshot, step, write
/// the new state and the result. `role` 0 = core, 1 = containment.
pub fn solve(role: u8, msg: &[f64]) -> Vec<f64> {
    let mut r = Reader::new(msg);
    let mut w = Writer::default();
    if role == 0 {
        let mut c = Core::read_state(&mut r);
        let s = CoreSnapshot::read(&mut r);
        let res = c.step(&s);
        c.write_state(&mut w);
        res.write(&mut w);
    } else {
        let mut c = Containment::read_state(&mut r);
        let s = ContainmentSnapshot::read(&mut r);
        let res = c.step(&s);
        c.write_state(&mut w);
        res.write(&mut w);
    }
    w.0
}

/// Read a solver worker's reply into the part and its result.
#[cfg_attr(not(target_arch = "wasm32"), allow(dead_code))] // used by the browser's solver workers (and the tests)
pub fn read_core_reply(v: &[f64]) -> (Core, CoreResult) {
    let mut r = Reader::new(v);
    (Core::read_state(&mut r), CoreResult::read(&mut r))
}
#[cfg_attr(not(target_arch = "wasm32"), allow(dead_code))] // used by the browser's solver workers (and the tests)
pub fn read_containment_reply(v: &[f64]) -> (Containment, ContainmentResult) {
    let mut r = Reader::new(v);
    (Containment::read_state(&mut r), ContainmentResult::read(&mut r))
}

/// Decode a frame on the page.
pub fn decode_frame(v: &[f64]) -> Frame {
    Frame::read(&mut Reader::new(v))
}

// ─── Natively: one engine thread, the parts stepped inline ────────────────

#[cfg(not(target_arch = "wasm32"))]
impl outram_park::backend::dhoby_ghaut::web_demo::link::NativeEngine for Runner {
    type Req = Request;
    type Ev = Event;
    fn handle(&mut self, req: Request, post: &mut impl FnMut(Event)) {
        if req == Request::Tick {
            self.start_tick();
            self.run_inline();
            post(self.frame_event());
        } else {
            self.apply(req);
        }
    }
}

// ─── In the browser: the plant worker and its two solver workers ──────────

#[cfg(target_arch = "wasm32")]
pub mod web {
    use super::*;
    use outram_park::backend::dhoby_ghaut::web_demo::link::{js, Message, Poster, WorkerEngine};
    use std::sync::{Arc, RwLock};
    use wasm_bindgen::closure::Closure;
    use wasm_bindgen::{JsCast as _, JsValue};

    /// The script every worker starts from (it inits the same module).
    pub const WORKER_JS: &str = "./fukushima_worker.js";

    /// The plant worker's two solver workers and the step in flight.
    #[derive(Default)]
    pub struct Solvers {
        workers: Option<[web_sys::Worker; 2]>,
        /// Solver workers that have said they are listening (a worker's
        /// handler is set only once its module has loaded, so messages sent
        /// earlier would be lost: the same hello handshake as the link's).
        ready: u8,
        /// A tick is waiting for the solvers to be ready.
        waiting: bool,
        busy: bool,
        core: Option<Vec<f64>>,
        containment: Option<Vec<f64>>,
    }

    fn mode_name(m: Mode) -> &'static str {
        match m {
            Mode::Historical => "historical",
            Mode::FreePlay => "free",
        }
    }

    impl Message for Request {
        fn to_js(&self) -> JsValue {
            let o = js::object();
            let (kind, a, b) = match *self {
                Request::Tick => ("tick", 0.0, 0.0),
                Request::Run(on) => ("run", on as u8 as f64, 0.0),
                Request::Speed(s) => ("speed", s, 0.0),
                Request::Workers(n) => ("workers", n as f64, 0.0),
                Request::Mode(m) => ("mode", if m == Mode::FreePlay { 1.0 } else { 0.0 }, 0.0),
                Request::Set(c, on) => ("set", c.index() as f64, on as u8 as f64),
                Request::Reset => ("reset", 0.0, 0.0),
            };
            js::set(&o, "kind", kind);
            js::set(&o, "a", a);
            js::set(&o, "b", b);
            let _ = mode_name;
            o.into()
        }
        fn from_js(v: &JsValue) -> Result<Self, String> {
            let a = js::get_f64(v, "a").unwrap_or(0.0);
            let b = js::get_f64(v, "b").unwrap_or(0.0);
            Ok(match js::get_str(v, "kind").as_str() {
                "tick" => Request::Tick,
                "run" => Request::Run(a != 0.0),
                "speed" => Request::Speed(a),
                "workers" => Request::Workers(a as u8),
                "mode" => Request::Mode(if a != 0.0 { Mode::FreePlay } else { Mode::Historical }),
                "set" => Request::Set(*Control::ALL.get(a as usize).ok_or("bad control")?, b != 0.0),
                "reset" => Request::Reset,
                k => return Err(format!("unknown request '{k}'")),
            })
        }
    }

    impl Message for Event {
        fn to_js(&self) -> JsValue {
            let o = js::object();
            match self {
                Event::Frame { frame, history, stats } => {
                    js::set(&o, "kind", "frame");
                    js::set(&o, "frame", frame.js());
                    js::set(&o, "history", history.js());
                    js::set(&o, "stats", js::f64s(stats));
                }
                Event::Error(m) => {
                    js::set(&o, "kind", "error");
                    js::set(&o, "message", m.as_str());
                }
            }
            o.into()
        }
        fn from_js(v: &JsValue) -> Result<Self, String> {
            match js::get_str(v, "kind").as_str() {
                "frame" => {
                    let s = js::get_f64s(v, "stats");
                    Ok(Event::Frame {
                        frame: Floats::get(v, "frame").ok_or("no frame")?,
                        history: Floats::get(v, "history").ok_or("no history")?,
                        stats: [s.first().copied().unwrap_or(0.0), s.get(1).copied().unwrap_or(0.0), s.get(2).copied().unwrap_or(0.0), s.get(3).copied().unwrap_or(0.0)],
                    })
                }
                "error" => Ok(Event::Error(js::get_str(v, "message"))),
                k => Err(format!("unknown event '{k}'")),
            }
        }
    }

    impl WorkerEngine for Runner {
        type Req = Request;
        type Ev = Event;
        fn handle(state: &Arc<RwLock<Self>>, req: Request, post: Poster<Event>) {
            if req != Request::Tick {
                if let Ok(mut r) = state.write() {
                    r.apply(req);
                }
                return;
            }
            let three = state.read().map(|r| r.workers == 3).unwrap_or(false);
            if three {
                if state.read().map(|r| r.web.busy).unwrap_or(true) {
                    return;
                }
                if let Err(e) = ensure_solvers(state, post) {
                    post.post(Event::Error(e));
                    return;
                }
                let ready = {
                    let Ok(mut r) = state.write() else { return };
                    r.start_tick();
                    if r.web.ready < 2 {
                        r.web.waiting = true;
                        r.web.busy = true;
                    }
                    r.web.ready >= 2
                };
                if ready {
                    next_step(state, post);
                }
            } else if let Ok(mut r) = state.write() {
                r.start_tick();
                r.run_inline();
                let ev = r.frame_event();
                drop(r);
                post.post(ev);
            }
        }
        fn error(message: String) -> Event {
            Event::Error(message)
        }
    }

    /// Start the core and containment workers once.
    fn ensure_solvers(state: &Arc<RwLock<Runner>>, post: Poster<Event>) -> Result<(), String> {
        if state.read().map(|r| r.web.workers.is_some()).unwrap_or(true) {
            return Ok(());
        }
        let make = |name: &str, role: u8| -> Result<web_sys::Worker, String> {
            let opts = web_sys::WorkerOptions::new();
            opts.set_type(web_sys::WorkerType::Module);
            opts.set_name(name);
            let w = web_sys::Worker::new_with_options(WORKER_JS, &opts).map_err(|e| format!("{e:?}"))?;
            let st = state.clone();
            // `Closure<dyn FnMut>` is wasm-bindgen's only callback type: a
            // framework boundary, as in dhoby-ghaut's link.
            let on_msg = Closure::<dyn FnMut(web_sys::MessageEvent)>::new(move |ev: web_sys::MessageEvent| {
                if ev.data().is_string() {
                    let go = st.write().map(|mut r| {
                        r.web.ready += 1;
                        let go = r.web.ready >= 2 && r.web.waiting;
                        if go {
                            r.web.waiting = false;
                            r.start_tick();
                        }
                        go
                    });
                    if go.unwrap_or(false) {
                        next_step(&st, post);
                    }
                    return;
                }
                let v = js_sys::Float64Array::new(&ev.data()).to_vec();
                if let Ok(mut r) = st.write() {
                    if role == 0 {
                        r.web.core = Some(v);
                    } else {
                        r.web.containment = Some(v);
                    }
                }
                try_finish(&st, post);
            });
            w.set_onmessage(Some(on_msg.as_ref().unchecked_ref()));
            on_msg.forget();
            let on_err = Closure::<dyn FnMut(web_sys::ErrorEvent)>::new(move |ev: web_sys::ErrorEvent| {
                post.post(Event::Error(format!("solver worker: {}", ev.message())));
            });
            w.set_onerror(Some(on_err.as_ref().unchecked_ref()));
            on_err.forget();
            Ok(w)
        };
        let core = make("core", 0)?;
        let containment = make("containment", 1)?;
        if let Ok(mut r) = state.write() {
            r.web.workers = Some([core, containment]);
        }
        Ok(())
    }

    /// Send the next step to the solver workers, or end the tick.
    fn next_step(state: &Arc<RwLock<Runner>>, post: Poster<Event>) {
        let Ok(mut r) = state.write() else { return };
        if !r.should_step() {
            r.web.busy = false;
            let ev = r.frame_event();
            drop(r);
            post.post(ev);
            return;
        }
        let s = r.plant.begin();
        let mut wc = Writer::default();
        r.core.write_state(&mut wc);
        s.core.write(&mut wc);
        let mut wk = Writer::default();
        r.containment.write_state(&mut wk);
        s.containment.write(&mut wk);
        r.web.busy = true;
        r.web.core = None;
        r.web.containment = None;
        if let Some([c, k]) = &r.web.workers {
            let _ = c.post_message(&js::f64s(&wc.0));
            let _ = k.post_message(&js::f64s(&wk.0));
        }
    }

    /// Both replies in: finish the step and go on.
    fn try_finish(state: &Arc<RwLock<Runner>>, post: Poster<Event>) {
        {
            let Ok(mut r) = state.write() else { return };
            if r.web.core.is_none() || r.web.containment.is_none() {
                return;
            }
            let (Some(cv), Some(kv)) = (r.web.core.take(), r.web.containment.take()) else { return };
            let (core, core_res) = read_core_reply(&cv);
            let (cont, cont_res) = read_containment_reply(&kv);
            r.core = core;
            r.containment = cont;
            r.plant.finish(core_res, cont_res);
            r.after_step();
        }
        next_step(state, post);
    }

    /// A solver worker's main: answer each message with its step.
    pub fn solver_main(role: u8) {
        let scope: web_sys::DedicatedWorkerGlobalScope = js_sys::global().unchecked_into();
        let s2 = scope.clone();
        let on_msg = Closure::<dyn FnMut(web_sys::MessageEvent)>::new(move |ev: web_sys::MessageEvent| {
            let msg = js_sys::Float64Array::new(&ev.data()).to_vec();
            let out = solve(role, &msg);
            let _ = s2.post_message(&js::f64s(&out));
        });
        scope.set_onmessage(Some(on_msg.as_ref().unchecked_ref()));
        on_msg.forget();
        let _ = scope.post_message(&JsValue::from_str("ready"));
    }
}
