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

**Known mismatch.** The Mission Briefing slide states the plant starts at its
rated 10 MWth, but `htgr_sim_full.png` was captured at 6.7 MWth and
`htgr_sim_controls.png` at 7.4 MWth. Either recapture both at 10 MWth or change
the figure in the deck; as it stands the slide and its own screenshot disagree.

## Caveat carried by the deck itself

HTGR Sim v1 is an educational/research demonstrator. Plant coefficients,
controller constants and some operating assumptions are illustrative, and the
model is not validated for reactor operation, licensing, safety analysis or
operator training. The deck states this on its "Model Limitations" slide.
