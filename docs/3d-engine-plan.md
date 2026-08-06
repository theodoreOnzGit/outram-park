# DOVER — OUTRAM PARK 3D Engine — Plan

**DOVER** — **D**eck-based **O**pen-source **V**isualisation **E**ngine for **R**eactors.
A Singapore MRT station, matching the OUTRAM PARK / TUAS / TAMPINES / TEH-O / NEE SOON backronym convention.

**Status:** planning only. No engine code written yet.
**Date:** 2026-08-06
**Repo:** `outram-park` (presentation repo), with `outram-park-backend` as a submodule.

---

## 1. Decisions taken

| Question | Decision |
|---|---|
| Name | **DOVER** — "deck-based" names the one structural decision the engine hangs on (§5.1). |
| Relationship to 2009Scape source | **Architecture-inspired, clean Rust.** No Jagex-derived code enters the tree. |
| Where the engine lives | **Here, in `outram-park`.** Backend stays a headless physics/library repo, consumed via the submodule. |
| Relationship to `outram-blender` | **Complementary, not overlapping.** `outram-blender` authors geometry; DOVER renders it. See §2.3. |
| First milestone | **Walkable FHR plant, face colour driven by live temperature.** |

---

## 2. Provenance stance (on the record)

### 2.1 Why 2009Scape was rejected as a source

`https://github.com/Kingo64/2009Scape` was evaluated and **rejected as a source**. Findings:

- The repository carries **no license** (GitHub `licenseInfo: null`); it is a stale 2020 fork of `enderkitsune/RS-2009`. Nobody upstream held the rights to grant a licence, so nothing in it can be relicensed into this GPL-3.0 project.
- `Client/` is **343 files, ~3.5 MB** of decompiler output in package `org.runite.jagex`, with identifiers such as `Class140_Sub1_Sub1`, `aShortArray3808`, `anInt3823`. It is Jagex's proprietary client decompiled and partially renamed — not a clean-room reimplementation.
- It therefore cannot produce a derivation record meeting the standard set by `RESEARCH_INTEGRITY_AND_PROVENANCE.md` and `TRISO_ATOPS_DERIVATION.md` in the backend.

### 2.2 Why a formal clean-room procedure is *not* being used

Clean-room ("Chinese wall") reverse engineering was considered and is **deliberately not the approach**. The procedure requires a *dirty* team that examines the original and writes a purely functional specification stripped of expression, and a *clean* team that has **never seen the original** and implements solely from that spec, with records of the wall kept as evidence. It does not fit here, for three reasons:

1. **It requires two genuinely separated parties.** A solo maintainer working with an AI assistant cannot staff both sides — whoever has read the decompiled client is disqualified from implementing, and that includes the assistant.
2. **Clean room exists to achieve compatibility with the original.** Phoenix needed BIOS compatibility with IBM. DOVER needs to draw a nuclear plant. No RuneScape cache will ever be loaded and no Jagex byte format will ever be matched, so the procedure's entire purpose is absent.
3. **It defends against copying expression; it does not manufacture a licence**, nor does it address the provenance of decompiled output from a proprietary binary.

**What is used instead:** the general, published techniques these engines are built from — tile-based scene graphs, discrete height planes, painter's-algorithm scene ordering, baked HSL vertex colour, keyframe vertex-group animation. These predate RuneScape, appear in standard graphics literature, and are ideas rather than protected expression. No procedure is required to use them.

**Rule for implementers:** do not open the 2009Scape client sources while writing DOVER. If a specific algorithm is wanted (e.g. tile-shape templates), specify it from first principles or from general graphics literature, and record the source in this repo's derivation notes.

*Not legal advice.* Given the NUS affiliation and `RESEARCH_INTEGRITY_AND_PROVENANCE.md`, a real review is cheap insurance before anything is published — but the approach above is chosen specifically so that nothing turns on a close legal call.

### 2.2a Correction: a properly-licensed 2009Scape does exist

The "no licence" finding is true of **`Kingo64/2009Scape` specifically** (verified: no `LICENSE`/`COPYING` file at repo root; stale 2020 fork). It is *not* true of the project as a whole. The live project is on GitLab and is **AGPL-3.0**, split across:

| Repo | Contents | Licence |
|---|---|---|
| [`gitlab.com/2009scape/2009scape`](https://gitlab.com/2009scape/2009scape) | Server + Management Server (community-written Kotlin/Java gameplay) | AGPL-3.0 |
| [`gitlab.com/2009scape/rt4-client`](https://gitlab.com/2009scape/rt4-client) | Current client | AGPL-3.0 |
| [`gitlab.com/2009scape/legacy-client`](https://gitlab.com/2009scape/legacy-client) | Old client — **deprecated**, superseded by RT4 | — |

This changes the picture but does not change the decision, for two reasons:

1. **AGPL-3.0 into a GPL-3.0-only project is a licence decision, not a detail.** The two are combinable, but the resulting work carries AGPL obligations — `outram-park` would effectively become AGPL, and AGPL's network-service clause matters if a browser-hosted simulator is ever on the roadmap.
2. **A licence header only covers what the licensor owns.** Whether RT4-Client is a genuine rewrite or still carries decompiled Jagex lineage is **not verified here** and would need checking before relying on it. Not asserting either way.

Either way it is moot for DOVER: even a perfectly-licensed RuneScape client is a *game* client — JS5 cache, packet parsing, ISAAC, CS2 interpreter, interface system — and in Java. The overlap with "render a nuclear plant" remains near zero.

### 2.2b Precedent worth citing: OpenMW

[OpenMW](https://openmw.org/faq/) is the model for what DOVER is doing: a GPL-3.0 reimplementation of the Morrowind engine, written from scratch with the help of community-generated format documentation, shipping **no** copyrighted assets — users supply their own. It is widely regarded as legal on its face.

DOVER's shape is the same, and simpler: the engine is ours, and the "assets" are a nuclear plant authored in `outram-blender`. Unlike OpenMW, DOVER needs **no** file-format compatibility with anything, which removes the only part of OpenMW's situation that required careful documentation work.

### 2.2c Why OpenMW is a precedent, not a base

OpenMW was evaluated as an actual engine base and **rejected**. Measured: GPL-3.0 (compatible), but **15.83 MB of C++ (93% of a 107 MB repo)**, plus a native dependency stack of OpenSceneGraph (an OpenMW *fork*), Bullet, MyGUI, FFmpeg 4.4, SDL2, LuaJIT, Boost, yaml-cpp, lz4 and OpenAL-soft.

| Criterion | DOVER on wgpu | OpenMW |
|---|---|---|
| Third-party code vendored | **none** | ~16 MB C++ + forked OSG + 8 native libs |
| Language | Rust (matches the whole workspace) | C++ (needs FFI) |
| Assets required to function | none — geometry authored in `outram-blender` | designed around Morrowind's proprietary ESM/BSA/NIF |
| Per-frame cost | see §3.3 | OSG traversal + Bullet + MyGUI + LuaJIT |

The asset-provenance concern that motivates looking at OpenMW is **already fully satisfied** by DOVER: it vendors nothing, and there are no assets in the tree at all until the plant is authored locally. OpenMW would make that concern worse, not better — and it is an engine whose purpose is to consume exactly the copyrighted game data being avoided.

### 2.2d Asset policy (adopted from OpenMW's discipline)

The genuinely valuable thing to take from OpenMW is its rule, not its code:

- **The engine ships; assets do not.** No third-party game assets, meshes, textures, or data files are ever committed to or vendored into this repository.
- **Plant geometry is first-party** — authored in `outram-blender`, generated procedurally, or derived from the maintainer's own CAD.
- **Any reference geometry from outside** must have documented provenance and an open licence, recorded per `DATA_POLICY.md` and `RESEARCH_INTEGRITY_AND_PROVENANCE.md` (source, author, licence, URL/DOI, date accessed).
- **Prefer flat colour over textures** (§3.2) — this is an aesthetic choice that also removes texture-sourcing as a provenance question entirely.

### 2.3 Precedent: this problem is already solved in-tree

`outram-blender` faced the identical question and answered it. From its `lib.rs`:

> **Scaffold, not a Blender port.** Blender is millions of lines of C/C++/Python; this crate borrows its *concepts and data-structure architecture* … it does **not** port Blender's code.

…and the naming/trademark decision is already signed off in its `Cargo.toml` (DECIDED 2026-07-17). **DOVER applies the same template**, with one difference worth recording: Blender is GPLv2-or-later, so porting its code would have been permissible and architecture-only was an *elective* choice. 2009Scape is unlicensed and Jagex-derived, so for DOVER architecture-only is **mandatory**. Same output, stricter rationale — and DOVER should carry the same style of disclaimer block in its `lib.rs`.

---

## 3. Why this architecture suits OUTRAM PARK

The RS-era design is not nostalgia; it happens to match the constraints of a teaching simulator:

| Design property | Why it earns its place here |
|---|---|
| Integer tile grid, discrete height planes | A plant *is* decks and gratings on a regular grid. Integer coordinates, no float drift. |
| Per-face colour baked into the model | **Colour is the state variable.** Temperature → face colour is the entire point of the simulator. |
| Definition-driven instancing | `EquipmentDefinition` instanced from `tampines`/`nee_soon` objects, mirroring the existing 2D widget pattern. |
| Vertex-group skeletons, keyframe sequences | Control-rod travel, valve stems, pump impellers — all rigid-body, no skinning needed. |
| Tiny asset budget, low poly | Runs on a lecture-hall laptop and on the workspace's Android target. |

**Explicitly not carried over:** fixed-point software rasterisation (wgpu 29.0.3 is already a workspace dependency), JS5 cache containers, ISAAC cipher, packet parsing, the CS2 script VM, and the AWT/JOGL threading model. Those are the majority of a game client and none of it is relevant.

### 3.1 Engine base — FOSS options evaluated

| Option | Licence | Verdict |
|---|---|---|
| **wgpu directly** | MIT/Apache-2.0 | **Chosen.** Already pinned at 29.0.3 in the backend workspace; `eframe` already uses it. Zero version risk, no design-rule conflict. |
| [Bevy](https://bevy.org/) 0.18 (Mar 2026) | MIT/Apache-2.0 | Real option, real cost — see below. |
| [Fyrox](https://fyrox.rs/) | MIT | Full engine + editor; same class of objections as Bevy. |
| `rend3` | MIT/Apache-2.0 | **Maintenance mode.** Avoid. |
| `three-d` | MIT | Lightweight renderer, closer to the right altitude than Bevy, but adds a dependency for work DOVER largely has to do anyway. |
| [Luanti/Minetest](https://www.luanti.org/), [OpenRA](https://www.openra.net/) | LGPL-2.1 / GPL-3.0 | Not usable as libraries, but good reading for chunked-world streaming and tile scene organisation. |

**Why not Bevy**, stated fairly — it is a genuinely good engine and the argument is about fit, not quality:

1. **It breaks the version lock.** Bevy vendors its own `wgpu`. The plan requires handing a render target to an `egui` panel (§4.2); two `wgpu` versions in the graph makes that a type error.
2. **It conflicts with the workspace design rules.** Bevy's ECS and plugin API are built on the trait-object and `Box<dyn …>` patterns the backend `CLAUDE.md` forbids outright ("No trait objects — use enums for dispatch"; "No `Box<T>`"; "No lifetime parameters").
3. **It solves the wrong problem.** Bevy gives PBR, shadows, and a full asset pipeline — most of which DOVER would immediately switch off to get the flat-shaded look. You would fight it toward simplicity.

The counter-case is honest: **if not writing a renderer at all is worth more than the version lock**, Bevy is the answer, and the price is a separate window rather than an embedded viewport. That is a legitimate trade and worth revisiting if M1.1 proves slower than expected.

### 3.2 The "RuneScape feel", specified

The look is mostly a set of *constraints*, not a codebase. This is the spec DOVER targets — adopting it is what produces the aesthetic, regardless of engine base:

- **Integer tile grid**, 128 subunits per tile; no free-floating geometry.
- **Discrete height planes** (decks), not continuous vertical space.
- **Flat shading, per-face colour**, no smooth normals. `@interpolate(flat)` in WGSL.
- **Baked static lighting** folded into face colour at load; no runtime lights, no shadows.
- **Low triangle budget** — order 200–800 tris per equipment model.
- **Clamped orbit camera** at a fixed pitch band, snapping to deck height, plus a first-person walk mode.
- **No texture filtering / no mipmaps** where textures appear at all; prefer flat colour.
- **Fixed simulation tick** driving animation, decoupled from render framerate.

Every one of these is a decision, freely made. None requires reference to anyone's source.

### 3.3 Performance budget — "as light as OSRS"

This is a stated hard requirement, so it is recorded as a budget rather than an aspiration.

RuneScape's efficiency came from software rasterisation tuned for 2004 CPUs: small models, baked vertex colour, no dynamic lighting, tile-culled draw distance. §3.2 adopts all of it. But note that **DOVER does strictly less per-frame work than RS did** — RS re-sorted and re-rasterised the whole scene on the CPU every frame, whereas DOVER uploads geometry once at region load and re-uploads only the channel array (§5.4).

Target budget for the M1 FHR plant:

| Quantity | Budget |
|---|---|
| Equipment geometry | ~50 models × ~500 tris ≈ 25k triangles |
| Terrain | 104×104 tiles × 2 tris × visible decks ≈ 20–90k triangles |
| **Scene total** | **< 200k triangles** |
| Draw calls | 50–100, instanced per `EquipmentDefinition` |
| Per-frame CPU | one `RwLock` read + ~64 `f32` written |
| Geometry VRAM | single-digit MB |
| Per-frame uploads | the channel array only — **never** the vertex buffer |

This is idle load for a 2010-era integrated GPU. Flat shading with low overdraw and no dependent texture reads is also the ideal workload for mobile tile-based GPUs, so the Android target is helped by these choices rather than constrained by them.

**Where the real cost is.** Rendering will not be the bottleneck — `tampines`/`nee_soon` thermal-hydraulics and PRKE will dominate the frame budget by orders of magnitude. That is precisely why `app_scaffold` runs physics on a separate thread behind `SharedState`. Performance work belongs in the solvers; the renderer should stay cheap enough to ignore, and the budget above exists to keep it that way.

**Regression guard:** assert the budget in CI once M1.4 lands — fail the build if scene triangle count or per-frame upload size exceeds the table. Cheap to add, and it is the only thing that stops "as light as OSRS" quietly eroding.

---

## 4. Repo restructure

Current state: `Cargo.toml` is a single package whose `[[bin]]` paths are **broken** — it declares `src/fhr/main.rs` and `src/ipwr/main.rs`, but the files on disk are `src/fhr_sim/main.rs` and `src/ipwr/…` does not exist. `cargo check` fails today with two target-resolution errors. Fix this first; it is a prerequisite, not part of the engine.

Target layout:

```
outram-park/                          # workspace root
├── Cargo.toml                        # [workspace] + exclude = ["outram-park-backend"]
├── outram-park-backend/              # submodule (its own workspace)
├── crates/
│   └── <engine-crate>/               # the 3D engine
├── sims/                             # existing fhr_sim, bwr_sim, … bins
└── presentations/
```

Backend crates are consumed as path dependencies into the submodule:

```toml
tampines = { path = "outram-park-backend/crates/tampines" }
outram-park-digital-twin-engine = { path = "outram-park-backend/crates/outram-park-digital-twin-engine" }
```

### Two concrete gotchas to verify early

1. **Nested workspaces.** The submodule has its own `[workspace]` root. Without `exclude = ["outram-park-backend"]` in the outer workspace, Cargo will fail resolving the nested members' `edition.workspace = true` inheritance. Verify with a bare `cargo metadata` before writing any engine code.
2. **Version lock with the backend.** The engine must pin **exactly** the backend's `wgpu = "29.0.3"`, `egui = "0.34.3"`, `eframe = "0.34.3"`. A second `wgpu` in the dependency graph means incompatible device/texture types the moment the engine hands a render target to an egui panel — and that handoff is required for the milestone (3D viewport beside the existing 2D controls).

---

## 5. Engine architecture

### 5.1 Coordinate system

- **Tile = 128 integer subunits = 1.0 m** of plant. All scene coordinates are `i32`.
- **Height planes = decks.** Configurable count (RS used 4; a containment building wants ~8), each with an explicit elevation rather than a fixed step.
- Per-tile-corner heightmap for gratings, sumps, and sloped floors.

### 5.2 Scene representation

```
Region  { planes: Vec<Plane>, w, h }
Plane   { tiles: Grid<Tile>, occupants: Vec<Occupant> }
Tile    { corner_heights: [i32;4], underlay: MaterialId,
          overlay: Option<(MaterialId, TileShape, Rot)>, flags }
Occupant = Wall | WallDecoration | GroundDecoration
         | SceneObject { def: EquipmentDefId, span: (u8,u8), rot: Rot }
         | Actor
```

Occupant kinds are deliberately the RS taxonomy — walls, decorations, spanning objects — because it is a proven decomposition for dense interior scenes and it makes collision and picking fall out of the tile grid for free.

### 5.3 Model format

```
PlantModel {
    verts:      Vec<[i32;3]>,        // tile subunits
    faces:      Vec<[u16;3]>,
    face_color: Vec<Hsl16>,          // baked base colour incl. static lighting
    face_bind:  Vec<Option<ChannelId>>,   // ← the OUTRAM PARK addition
    groups:     VertexGroups,        // for keyframe animation
}
```

`face_bind` is where this departs from the source architecture, and it is the load-bearing idea:

**RS bakes face colour once at load. We bake a *base* colour at load and bind selected faces to a physics channel, resolved per frame in the shader.**

### 5.4 The physics→pixels pipeline (core contract)

```
physics thread                     render thread
──────────────                     ─────────────
SharedState<FhrState>  ──snapshot──▶  channels: [f32; N]   (normalised 0..1)
(Arc<RwLock<T>>, from                        │
 app_scaffold — already                      ▼
 exists in the backend)              small uniform buffer upload
                                             │
                                             ▼
                              fragment shader:
                                c = channel[face_bind]
                                rgb = hot_to_cold_colour_mark_1(c)   // ported to WGSL
```

Consequences worth stating plainly:

- **No vertex buffer is rewritten per frame.** The only per-frame upload is an `N`-float array, where `N` is the number of distinct physics channels (tens, not thousands). Geometry is uploaded once at region load.
- The existing `color_maps` functions (`hot_to_cold_colour_mark_1`/`mark_2`, `steam_quality_colour`) port to WGSL essentially line-for-line — they are pure `f32 → rgb` with a clamp. Keep the Rust versions as the reference and add a test asserting the WGSL output matches at sampled points, so the 2D schematic and the 3D scene can never disagree about what "hot" looks like.
- Reuses `SharedState<T>` / `spawn_physics_thread` from `outram-park-digital-twin-engine::app_scaffold` verbatim. No new threading model.

### 5.5 Rendering

- wgpu, real depth buffer. **No occluder system** — that existed only to serve a software rasteriser and is pure liability here.
- One vertex buffer per region, bump-allocated at load; instanced draws per `EquipmentDefinition`.
- Per-face colour ⇒ flat shading. Use WGSL's `@interpolate(flat)` rather than duplicating vertices.
- Static directional light + ambient folded into the HSL luminance at load time — zero runtime lighting cost, and it keeps the readable, diagram-like look that suits a teaching tool.

### 5.6 Camera

Two modes, toggleable: clamped orbit (yaw/pitch limits, follows deck height) for overview, and first-person walk for the walkthrough. Collision tests against tile occupancy flags — free, given the grid.

### 5.7 Animation

Vertex groups plus keyframe sequences of rigid transforms (origin / translate / rotate / scale). Driven by physics, not by wall-clock: impeller angular rate ∝ pump speed, rod insertion ∝ reactivity state.

### 5.8 Portability

Engine core (scene, model, animation, channel binding) stays free of `wgpu` behind a renderer trait; the wgpu backend is a gated module. This matches the workspace's Android-portability rule and keeps the core unit-testable headlessly.

### 5.9 Asset pipeline

`outram-blender` (backend, faer-based mesh authoring, already has `export.rs`, `mesh.rs`, `primitives.rs`) is the intended authoring path — it needs a `PlantModel` exporter added. **This is the long pole.** The engine is a few thousand lines of well-understood work; modelling a credible FHR plant is not. Plan asset effort separately and do not let the milestone slip on it — M1 should ship with crude placeholder geometry.

---

## 6. Milestone M1 — walkable FHR plant, colour = temperature

| Step | Deliverable | Done when |
|---|---|---|
| M1.0 | Workspace restructure; fix broken bin paths; submodule path deps resolve | `cargo check` clean at root, `cargo metadata` shows backend crates |
| M1.1 | wgpu window, depth buffer, orbit camera, hardcoded cube grid | Rotatable grid on screen |
| M1.2 | Region terrain: heightmap, underlay colours, tile shapes | A multi-deck floor plan renders |
| M1.3 | `PlantModel` format, loader, instanced scene objects | Placeholder vessel/pump/pipe geometry placed on tiles |
| M1.4 | Channel-binding colour pipeline; colour maps in WGSL + parity test | Faces respond to a hand-driven `channels` slider |
| M1.5 | Wire to `tampines` FHR state via `SharedState` | Colour tracks the live simulation |
| M1.6 | First-person mode + tile collision | You can walk the loop and watch it heat up |

M1.5 is the milestone that justifies the project; M1.1–M1.4 are de-risking.

---

## 7. Open questions

1. **Crate name.** The workspace uses Singapore place names (`tampines`, `nee_soon`, `boon-lay`, `kovan`). Suggest `dhoby-ghaut` — the interchange where everything meets — but this is your call and the naming convention is yours.
2. **Submodule weight.** 128 MB, 2728 files. Acceptable? A sparse checkout or a slimmer physics-only mirror is possible if clone time hurts presentation-repo contributors.
3. **Does the 3D viewport live inside the existing egui apps, or is it a separate binary?** Embedding gives one window with controls beside the scene, and forces the version lock in §4.2 to be exactly right. A separate binary is simpler but splits the UX.
4. **Deck count and physical scale for the FHR reference plant** — needed before M1.2 fixes the grid dimensions.
