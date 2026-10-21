# Fukushima Daiichi demo simulator: literature review (open sources first)

**Status:** AI-assisted draft, 2026-10-21, not yet reviewed by a person.
The search could read search-result excerpts but **not the primary PDFs**
(the fetch tool could not resolve the hosts), so every number below is
**[U] unverified** until checked against the document it is attributed to.
Research, education and V&V only.

## 1. Open-source codes

| Code | Licence | Language | Physics | Use for us |
|---|---|---|---|---|
| ORNL TRANSFORM (github.com/ORNL-Modelica/TRANSFORM-Library) | Apache-2.0 | Modelica | 0-D/1-D thermal hydraulics, two-phase volumes, point kinetics, decay heat | **Best port candidate** for component equations (keep notices) |
| MOOSE + Thermal Hydraulics Module | LGPL-2.1 | C++ | 1-D single-phase flow channels, junctions, heat structures | Architecture ideas; single-phase V&V cases. Open THM has no two-phase |
| GeN-Foam, OFFBEAT (gitlab foam-for-nuclear) | GPL-3.0 [U] | C++ | Porous two-phase TH, point kinetics to SN; fuel performance | Closures; OUTRAM PARK already ports both |
| pyrk | BSD-3 [U] | Python | Point kinetics with lumped thermal feedback | Cross-check |
| OpenMC | MIT | C++/Python | Monte Carlo, depletion | Offline void/Doppler coefficients, decay heat |
| CoolProp, IAPWS-IF97, Cantera | MIT / BSD | | Properties; H2 combustion (AICC) | Dependencies or data |
| RELAP-7, SAM, Pronghorn | Not openly released (NCRC) [U] | | | **Avoid** |
| MELCOR, MAAP, ASTEC, SAMPSON | Proprietary or restricted | | Full severe accident | **No code.** MELCOR's public reference manuals (SAND reports) are an equation reference |
| FRAPCON / FRAPTRAN | NRC agreement [U] | Fortran | Fuel performance | Correlations from the public NUREG manuals only |
| IAEA BWR PC-based simulators | Closed, gated, no severe accident | Windows | Normal operation, design-basis transients | UX inspiration only |

GitHub searches for Fukushima simulation, station blackout, isolation
condenser, zircaloy oxidation, suppression pool and hydrogen deflagration
found **no substantive open-source severe-accident or Fukushima code**, only
small hobby BWR simulators. The closest browser competitor is TH462/Reactor-Dynamics
(AGPL-3.0, JavaScript, PWR/BWR/RBMK scenarios, fidelity unverified).

**The gap:** no open, browser-runnable simulator ties BWR/3 IC and BWR/4
RCIC/HPCI station-blackout physics (Mark I pressurisation, Zr oxidation and
H2, release) to the public TEPCO measurements and the BSAF code-spread
envelopes.

## 2. Open data for Fukushima

- **OECD/NEA BSAF Phase 1 summary**, NEA/CSNI/R(2015)18, public PDF. The
  BSAF **specification and plant data package are restricted** (NEA Data
  Bank) and are **not used**. Phase 2 results are in open-access journal
  papers (HAL-IRSN, Polimi, VTT): code-ensemble bands for cross-checks.
- **ARC-F** (2019-2022) and **FACE** (2022-): hydrogen explosion analyses;
  final report not found openly [U].
- **TEPCO plant parameter PDFs** (RPV pressure and level, drywell and wetwell
  pressure, CAMS) for Units 1-3: public, to be transcribed. **The primary V&V
  target**, with TEPCO's own warnings about instrument reliability.
- **SAND2012-6173** (Gauntt et al., Sandia, unlimited release, OSTI 1055601):
  MELCOR models of Units 1-3 and their plant tables. Follow-ups
  SAND2013-9956 (Unit 2 RCIC), SAND2017-10811R.
- **INPO 11-005** (2011, ML11347A454): minute-level timeline; Tables 7.3-1/7.3-2
  "Fukushima Daiichi Unit Information".
- **IAEA, *The Fukushima Daiichi Accident*, Technical Volume 1** (design
  description); the Japanese government's June 2011 report to the IAEA,
  attachment 4.
- **JAEA-Data/Code 2012-018** (Nishihara et al.): ORIGEN2 core inventories and
  decay heat for Units 1-4.
- **Decay heat:** ANS-5.1-2014 is paywalled. OUTRAM PARK's `teh-o-prke`
  carries the 1978 draft ANS fit (Tobias), used here.
- **Source term (Cs-137):** about 35-37 PBq (Stohl 2012), about 8.8 PBq
  (Terada 2012), about 12-14 PBq [U] (Katata 2015). I-131 about 100-200 PBq [U].

## 3. Reduced-order models and their open references

| Model | Reference |
|---|---|
| Point kinetics, void/Doppler feedback | TRANSFORM, pyrk, textbooks; OUTRAM PARK `teh-o-prke` |
| RPV mixture level and swell | MELCOR CVH pool/atmosphere (SAND manual); Zuber-Findlay drift flux; RELAP5 manuals (NUREG/CR-5535) |
| Isolation condenser (Unit 1) | TEPCO operation-record analysis; JNES-EV-2011-9011. Per-train rating **not found** |
| RCIC / HPCI turbine pumps | SAND2013-9956; RCIC about 95 t/h (Unit 2) [U] |
| Relief valves | TEPCO (Unit 2: 8 SRVs, relief 7.44-7.58 MPa gauge) |
| Suppression pool and Mark I pressurisation | NRC Mark I training chapters (ML14140A181); BSAF papers |
| Core uncovery and heat-up | MELCOR COR package documentation |
| Zr-steam oxidation | Urbanic-Heidrick (MELCOR default), Cathcart-Pawel, Baker-Just, Prater-Courtright: ORNL/NUREG-17 |
| H2 and deflagration | Shapiro diagram (4 % lean limit); AICC via Cantera |
| Fission-product release | CORSOR, CORSOR-M (NUREG/CR-4173), CORSOR-Booth (MELCOR FP report) |

## 4. GE BWR/3 and BWR/4 Mark I design data (public)

- **NRC R-304B GE BWR/4 Technology Systems Manual** (ML023040368, chapters
  ML11258A231) and **R-504B Advanced Technology**, including the Fukushima
  chapter 7.1 (ML14140A185). US government works: the best open GE design
  description.
- **NUREG-1433** BWR/4 Standard Technical Specifications (set points context).
- Reference UFSARs in ADAMS: Browns Ferry, Peach Bottom, Hatch, Vermont Yankee
  (BWR/4 Mark I); Dresden 2/3, Millstone 1 (BWR/3 with ICs) [U, not retrieved].

| Parameter | Unit 1 (BWR/3, IC) | Units 2-3 (BWR/4, RCIC + HPCI) |
|---|---|---|
| Power | 460 MWe / 1380 MWt | 784 MWe / 2381 MWt |
| Assemblies | 400 | 548 (U3: 516 UO2 + 32 MOX) |
| Control rods | 97 [U] | 137 |
| RPV ID / height | about 4.8 m / 20 m [U] | about 5.6 m / 22 m [U] |
| Steam dome | about 7 MPa | about 7 MPa |
| Drywell free volume | about 3410 m3 [U] | 4240 m3 (U3) |
| Wetwell gas / pool | 2620 m3 / 1750 m3 | 3160 m3 / 2980 m3 (U3) |
| Containment design | 0.43 MPa gauge | about 0.38 MPa gauge [U] |
| Emergency cooling | 2 IC trains; HPCI | RCIC about 95 t/h; HPCI |

GE-Hitachi's current designs (ABWR, ESBWR, BWRX-300) are context only; they
belong to `bwr_sim`, not to this demo. The BWRX-300's isolation condensers
descend from Unit 1's, a teaching tie-in.
