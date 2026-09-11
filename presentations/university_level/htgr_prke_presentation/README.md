# PRKE with HTGR Sim v1

Teaching deck: **Point Reactor Kinetics Equations (PRKE) with HTGR Simulator**,
the HTGR counterpart of `../fhr_prke_presentation/prke.tex`.

Source: [issue #4](https://github.com/theodoreOnzGit/outram-park/issues/4).

## Build

```bash
lualatex htgr-prke.tex
biber    htgr-prke
lualatex htgr-prke.tex
lualatex htgr-prke.tex
```

Self-contained, matching the convention of the sibling presentation folders:
`beamerthememidcenturymodern.sty` and `demo.bib` are copied in rather than
shared, so the deck builds from this directory alone.

## Screenshots

Four screenshots are referenced and **are committed** alongside the deck, so it
builds fully from this directory with no extra files:

| macro | filename | slide |
|---|---|---|
| `\htgrfull` | `htgr_sim_full.png` | Mission Briefing |
| `\htgrcontrols` | `htgr_sim_controls.png` | Your Interface |
| `\htgrshutdown` | `htgr_sim_shutdown.png` | Shutdown Demonstration |
| `\htgrshutdownplot` | `htgr_sim_shutdown_plot.png` | Shutdown: What the Time History Shows |

All four are captured from HTGR Sim v1, built from the
`outram-park-digital-twin-engine` example of the same name.

Each is still wrapped in `\IfFileExists`, so the deck also compiles if one is
removed, rendering a labelled placeholder box in its place.

**Why the deck says "about 10 MWth".** HTR-10's rated thermal power is 10 MWth,
but the screenshots were captured while the simulator was still being explored,
and show 6.7 MWth (`htgr_sim_full.png`) and 7.4 MWth (`htgr_sim_controls.png`).
The deck therefore says *about* 10 MWth rather than naming an exact figure its
own screenshots contradict. If the shots are ever recaptured with the plant
settled at rated power, the wording can be tightened again.

## Caveat carried by the deck itself

HTGR Sim v1 is an educational/research demonstrator. Plant coefficients,
controller constants and some operating assumptions are illustrative, and the
model is not validated for reactor operation, licensing, safety analysis or
operator training. The deck states this on its "Model Limitations" slide.
