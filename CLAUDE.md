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

~~The previous rule required every issue in both kopi-beans (`bn`) and GitHub
Issues, cross-referenced.~~ **Retired 2026-10-03 at the maintainer's request
("i just want gh issues only, to be simple")**, matching
`outram-park-backend`, which deprecated `bn` on 2026-09-21. Do not create `bn`
issues for this repo. The old `refs/heads/beads/store` ref is left in place as
history.

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

`outram-park/Cargo.toml` depends on every `outram-park-backend` crate by
path, each as an optional dependency gated behind a same-named feature (see
`outram-park/src/backend/`, one re-export module per backend crate). This
requires the root workspace's `[workspace] exclude = ["outram-park-backend"]`
(in this file's own `Cargo.toml`) — without it, Cargo's workspace-root
discovery for those path dependencies incorrectly resolves against this
repo's own `[workspace]` instead of `outram-park-backend`'s, and every
backend crate that uses `<dep>.workspace = true` inheritance (i.e. nearly
all of them) fails to build with "`workspace.dependencies` was not
defined". Don't remove that `exclude` line.

Because `outram-park`'s own `Cargo.lock` is a separate resolution from
`outram-park-backend`'s, a transitive dependency can independently resolve
to a version newer than what this environment's `rustc` supports even
though backend's own lockfile pins an older, compatible one (hit this with
`kstring` via `kovan-discovery`'s `gix` dependency). Fix with
`cargo update -p <pkg> --precise <version-from-outram-park-backend/Cargo.lock>`
rather than upgrading the toolchain.
