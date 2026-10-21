# Fukushima Daiichi demo simulator: plan, v1 status, and what is missing

**Status:** v1 built, 2026-10-21. **AI draft only**: not reviewed by a
person, not validated. Research, education and V&V only; never for
operation, licensing, safety decisions or emergency response.

## Scope

- **`fukushima_sim`** (metacrate binary): the Fukushima Daiichi plant only.
  v1 is **Unit 1**, a GE BWR/3 with two isolation condensers in a Mark I
  containment, following GE geometry and specifications as far as public
  sources allow (see `literature-review.md`).
- **`bwr_sim`** stays reserved for modern BWRs (BWRX-300, ABWR).
- **The backend only through the metacrate**: every backend crate is reached
  through `outram_park::backend::*` (feature `fukushima`), never named
  directly. Reused: `tampines_steam_tables` (IF97 saturation, choked flow,
  steam transport properties), `teh_o_prke` (decay heat), the digital-twin
  widget library (`PipeVisual`, `ValveVisual`, `InstrumentationVisual`,
  `TemperatureLegend`, the hot-to-cold colour map), `dhoby_ghaut::web_demo`
  (fold-away panel, zoom buttons, the page-to-worker link).
- **egui GUI**, served in the browser with `trunk`. **Not on GitHub Pages.**

## Running it

```text
cargo run --release --no-default-features --features fukushima --bin fukushima_sim
cargo run --release --no-default-features --features fukushima --bin fukushima_sim -- --headless 108000 600
cargo test --release --no-default-features --features fukushima --bin fukushima_sim
cd outram-park/web/fukushima && trunk serve --release     # http://127.0.0.1:8080
```

URL options: `?run` (start at once), `speed=<simulated s per wall s, 0 = as
fast as it goes>`, `workers=1|3`, `mode=free`.

## Architecture

| Thread / worker | Owns |
|---|---|
| page (egui) | drawing only |
| plant worker | RPV mass and energy (IF97 saturation table), isolation condensers, turbine bypass until the MSIVs close, relief and safety valves (steam-table choked flow), fire-engine injection, decay heat, the operators' sequence, pacing |
| core worker | 3 rings x 12 axial nodes: fuel and clad heat-up (implicit), Urbanic-Heidrick oxidation with steam starvation, H2, relocation, lower-plenum debris quench and dry-out, lower-head failure |
| containment worker | drywell (wall heat sink, condensation), wetwell and pool, downcomers, vacuum breakers, vent and rupture disk, head-flange leak, reactor-building H2, ex-vessel debris boiling the water on the drywell floor |

As in the CIET browser demo, the solver workers are stateless (each message
carries the part's state and the start-of-step snapshot), so 1 and 3 workers
give the same numbers bit for bit (`three_workers_are_one_worker`).

## Checks (2026-10-21)

16 tests pass (`cargo test` above): the IF97 saturation table against the
steam tables (below 3e-4), the mixture solve, the vessel's mass and energy
balance over the first hour to round-off, the core node balance (covered and
adiabatic), the oxidation law's continuity, containment pool energy, 1 vs 3
workers bit for bit, a deterministic headless trace, the committed 30 h
fixture, and physical bounds every step over 30 h. **None of these is
validation**: they check the code does what the model says.

In Chromium (headless, software WebGL): the page stays live (about 9 fps
desktop, 25 fps phone, the same paused as running, so the cost is drawing,
not physics); 30 h of the accident runs in about 25 s with 1 worker
(about 56,000 steps/s); **3 workers are about 8x slower** (about 600
steps/s), because a step's physics is about 0.1 ms and the two message round
trips per step dominate. CIET's flow solves are 13-45 ms, which is why the
split pays there and not yet here. The phone layout opens folded with
"Controls »", zoom buttons, and the plots tab.

## What the uncalibrated model gives, against the record

The recorded sequence drives the operators; nothing was tuned to the record.

Measured from `--headless 108000 1` on 2026-10-21:

| Quantity | Model (v1) | Record / published analyses [U] |
|---|---|---|
| IC auto-start | 3 s (the stored-heat surge beats the turbine bypass; the bypass gain is a placeholder and was **not** tuned to the record) | 14:52, 6 min |
| Top of fuel uncovered | 2.1 h | about 3 h (18:10) |
| Hydrogen first made (> 1 kg) | 3.0 h | |
| First relocation | 3.3 h | core damage about 4 h |
| Lower head fails | 5.4 h | about 14-15 h (MELCOR, SAND2012-6173) |
| Hydrogen made | 127 kg | several hundred kg (code estimates) |
| Peak cladding | 2142 K | |
| Drywell peak | 0.53 MPa (at 30 h) | 0.84 MPa at about 02:30 (12 h) |
| Wetwell vent | **not reached** (disk 0.549 MPa [U]) | 14:30 on 12 March |
| Reactor-building explosion | **does not happen** (flange leak needs 0.75 MPa [A]) | 15:36 on 12 March |

The model runs fast and cold in the containment: no radiation in the core,
no RPV structures to soak up heat, a collapsed (not swollen) level, a strong
placeholder drywell heat sink and no core-concrete gases. These are reported,
not fitted.

## Missing pieces, in order of what they change most

1. **Primary numbers unverified**: check every [U]/[A] in `physics/params.rs`
   against INPO 11-005 Table 7.3, SAND2012-6173 and IAEA TV1; replace the
   placeholders (IC rating, SRV throats and set points, RPV internals, drywell
   heat sinks, leak paths, reactor-building volume).
2. **RPV heat structures** (shroud, internals, vessel wall) and **radiation in
   the core** above 1200 K: both slow the heat-up and delay vessel failure.
3. **Two-phase level swell** (Zuber-Findlay or MELCOR CVH): the collapsed
   level uncovers the core early.
4. **Molten core-concrete interaction** and its gases (H2, CO, CO2) after the
   lower head fails; this, and leak paths at high drywell temperature, are what
   pressurised Unit 1's drywell to 0.84 MPa.
5. **Fission products** (CORSOR-M or Booth release, pool scrubbing, venting to
   the stack), then the plume through `sembawang` -> `changi` -> `buangkok`
   (the metacrate re-exports none of these three yet; branch
   `metacrate-crates-io-971` adds them).
6. **Units 2 and 3** (GE BWR/4): RCIC turbine-pump, HPCI, SRV
   depressurisation; MOX in Unit 3.
7. **V&V against TEPCO's measured data** (transcribed with provenance) and the
   BSAF Phase 2 code bands; record the disagreement uncalibrated.
8. **Geometry images** of the vessel's height-volume map and the core node
   layout (the drawing rule), committed with the model.
9. **Widget library**: a BWR vessel and a Mark I containment widget (both are
   painted in the app for now), worked up in `widget_studio`.
10. **Three-worker speed**: batch several steps per message or move heavier
    solves (a resolved core, a 1-D containment) to the workers so the split
    pays.
11. **Native GUI**: compiles, not run here (no display in this environment).
