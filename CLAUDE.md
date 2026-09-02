# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in the
`outram-park` workspace (this top-level repository).

## Branch / push conventions

- **This repo (`outram-park`, top level):** push directly to `main`.
- **`outram-park-backend` (git submodule):** push to `develop`, never
  `main`, when committing changes inside that submodule's own tree.

## The `outram-park-backend` submodule

`outram-park-backend/` is a git submodule (see `.gitmodules`), pointing at
`https://github.com/theodoreOnzGit/outram-park-backend.git` and tracking
its `develop` branch.

That submodule carries its own `CLAUDE.md` (and crate-level `CLAUDE.md`
files under `outram-park-backend/crates/*/`), which governs that
repository tree exclusively. Its own scope-boundary rule states that it
never applies to a parent project — so none of it is inherited here, and
none of this file applies inside it either.

When working inside `outram-park-backend/`, follow `outram-park-backend/CLAUDE.md`
directly rather than anything written in this file. When working anywhere
else in `outram-park` (this top-level repo), this file governs instead.
