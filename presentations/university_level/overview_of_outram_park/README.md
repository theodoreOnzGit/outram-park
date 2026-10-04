# Map of Outram Park 

This python code illustrates what outram park does.

```bash 
python ./digital_twin_four_layer_update_paths_standalone.py
```

## Status deck: Where OUTRAM PARK Stands

`outram-park-overview.tex` — a 34-slide Beamer review of the workspace
organised **by physics module**, with the built PDF committed alongside it.

```bash
lualatex outram-park-overview.tex
biber    outram-park-overview
lualatex outram-park-overview.tex
lualatex outram-park-overview.tex
```

Needs `lualatex` (the theme uses `fontspec`) and `biber`.

### Where its numbers come from

Every figure is measured, not estimated, and the deck says which kind each is:

- **kLOC and test counts** — measured from the workspace on 2026-09-15 at
  `outram-park-backend` `develop` @ `2e7368612`. Test counts are *declared*
  test functions (`#[test]` attributes) counted statically — an inventory,
  not a record of a passing run. The deck states this on its own slide.
- **Maturity** — the roster declared 2026-09-13 in
  `outram-park-backend/CLAUDE.md` (11 of 38 crates), including its caveats.
- **The one measured run quoted** — `cargo check --workspace --lib --tests`
  clean, and 1,111 tests passing across the three most recently merged
  crates, both run on 2026-09-15.

If the workspace moves, re-measure before reusing the numbers.
