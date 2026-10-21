# Fukushima Daiichi demo simulator: plan and scope

**Status:** AI-assisted draft, 2026-10-21. The maintainer asked for an AI
draft to be built first; this records what was built and what comes next.
Research, education and V&V only.

## Scope

- **`fukushima_sim`** (metacrate binary): the Fukushima Daiichi plant only,
  GE BWR/3 (Unit 1, isolation condensers) first, then GE BWR/4 (Units 2-3,
  RCIC and HPCI), all in Mark I containment. Follows GE geometry and
  specifications as far as public sources allow (see the literature review).
- **`bwr_sim`** stays reserved for modern BWRs (BWRX-300, ABWR).
- **Built against the metacrate only**: every backend crate is reached through
  `outram_park::backend::*`; nothing in `outram-park-backend` is changed.
- **egui GUI**, drawn with the digital-twin engine's widget library and
  dhoby-ghaut's web-demo framework (fold-away panel, zoom buttons, worker
  link): mobile-first, never lagging.
- **wasm demo served with `trunk`** (`outram-park/web/fukushima/`), with the
  CIET browser demo's parallelism. **Not published on GitHub Pages** until the
  maintainer says so.

## Architecture (built, draft 1)

| Thread / worker | Owns |
|---|---|
| page (egui) | drawing only |
| plant worker | RPV mass and energy (IF97 saturation table), isolation condensers, relief/safety valves (steam-table choked flow), fire-engine injection, decay heat (`teh-o-prke`), the operators' sequence, pacing |
| core worker | 3 rings x 12 axial nodes: fuel and clad heat-up, Urbanic-Heidrick oxidation, H2, steam starvation, relocation, debris, lower-head failure |
| containment worker | drywell (with wall heat sink and condensation), wetwell and pool, downcomers, vacuum breakers, vent, head-flange leak, reactor building H2 |

The solver workers are stateless, as CIET's flow workers are: each message
carries the part's state plus the start-of-step snapshot, so 1 and 3 workers
give the same numbers **bit for bit** (`three_workers_are_one_worker`).

## Gaps, in order of what they change most

1. **Primary numbers unverified**: check every [U]/[A] in `physics/params.rs`
   against INPO 11-005 Table 7.3, SAND2012-6173 and IAEA TV1; replace
   placeholders (IC rating, SRV throats, RPV internals, heat sinks).
2. **Two-phase level swell** (Zuber-Findlay / MELCOR CVH): the collapsed
   level uncovers the core early.
3. **Radiation in the core** (rod-to-rod, to the shroud) above 1200 K.
4. **Temperature-dependent UO2/Zircaloy properties** from the OFFBEAT port.
5. **Fission products** (CORSOR-M / Booth), pool scrubbing, release to the
   environment, then `sembawang` -> `changi` -> `buangkok` for the plume
   (the HTGR simulator's chain).
6. **Units 2 and 3**: RCIC turbine-pump, HPCI, SRV-driven depressurisation,
   MOX in Unit 3.
7. **V&V against TEPCO's measured data** (transcribed, with provenance), and
   against BSAF Phase 2 code bands; record the disagreement uncalibrated.
8. **Geometry images** of the lumped vessel map and the core node layout
   (the drawing rule), committed with the model.
9. **Widget library**: a BWR vessel and a Mark I containment widget, worked
   up in `widget_studio` (backend change; needs the maintainer).
