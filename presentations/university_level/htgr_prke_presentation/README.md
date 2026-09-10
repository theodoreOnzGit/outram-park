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

Three screenshots are referenced and are **not committed**:

| macro | filename |
|---|---|
| `\htgrfull` | `htgr_sim_full.png` |
| `\htgrcontrols` | `htgr_sim_controls.png` |
| `\htgrshutdown` | `htgr_sim_shutdown.png` |

Each is wrapped in `\IfFileExists`, so the deck compiles without them and
renders a labelled placeholder box in their place. Drop the exported HTGR
Sim v1 screenshots into this directory under those names to fill them in.
`../htgrsim_presentation_short_5min/htgr_sim_v1.png` is an existing HTGR Sim
screenshot that may suit one of the three.

## Caveat carried by the deck itself

HTGR Sim v1 is an educational/research demonstrator. Plant coefficients,
controller constants and some operating assumptions are illustrative, and the
model is not validated for reactor operation, licensing, safety analysis or
operator training. The deck states this on its "Model Limitations" slide.
