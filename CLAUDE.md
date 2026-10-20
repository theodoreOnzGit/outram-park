# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in the
`outram-park` workspace (this top-level repository).

## Branch / push conventions

- **This repo (`outram-park`, top level):** push to `develop`, not `main`.
- **`outram-park-backend` (git submodule):** push to `develop`, never
  `main`, when committing changes inside that submodule's own tree.

Session-specific exceptions to the above (granted directly by the user in
conversation, not written policy for future sessions) do not change this
file — they apply only for the duration of the session they were granted
in.

## Issue tracking: GitHub Issues only

**Track every issue and task for this repo (`outram-park`, top level) in
GitHub Issues on `theodoreOnzGit/outram-park`, and nowhere else.** Bugs, TODOs
and roadmap items alike, via `gh issue create / comment / list`.

`outram-park-backend`'s issues are that repo's own concern, tracked in its own
GitHub Issues per its own `CLAUDE.md`.

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

### Consuming its crates from the `outram-park` crate

**`outram-park/Cargo.toml` depends on `outram-park-backend` crates ONLY as
published crates.io versions — never by local path (maintainer, 2026-10-20).**
Each is an optional dependency gated behind a same-named feature, with one
re-export module per crate in `outram-park/src/backend/`, and `all-backends`
turns them all on. Every backend crate is wired in; when the backend gains a
crate, add it here in the same release.

~~`outram-park/Cargo.toml` depends on every `outram-park-backend` crate by
path~~ **CORRECTED 2026-10-20**: path dependencies were removed. The backend
and `outram-park` are **published in lockstep**: the backend release goes to
crates.io first (`cargo publish --workspace` in the backend), then the pins
here move to the versions just published, and `outram-park` is published
after them. Until a version is live on crates.io, a build that enables its
feature cannot resolve it; that is expected, not a defect to patch with a
path dependency.

The root `Cargo.toml` keeps `[workspace] exclude = ["outram-park-backend"]` so
Cargo never mistakes the submodule's own workspace for a member of this one.
