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

## Issue tracking (HARD RULE)

**Every issue/task for this repo (`outram-park`, top level) MUST be tracked
in both kopi-beans (`bn`) and GitHub Issues — never only one of the two.**
This applies to bugs, TODOs, and roadmap items alike.

- **Create in both.** When an issue is opened, open it in both trackers
  with the same title, and cross-reference them: put the GitHub issue URL
  (or `gh:#<number>`) in the `bn` issue's notes/description, and put the
  `bn` issue id (`bn:<id>`) in the GitHub issue body.
- **Close in both.** Do not close one without closing the other in the same
  pass — a `bn close` with no matching GitHub close (or vice versa) leaves
  the two trackers out of sync, which defeats the point of requiring both.
- **`bn` is installed and the store is initialized** (`cargo install
  kopi-beans`; store lives at `refs/heads/beads/store` on `origin`, same as
  `outram-park-backend`'s own store). Run `bn prime` for workflow context.
- **Known `bn init` bug on this repo:** `bn init` unconditionally tries to
  fetch `refs/heads/beads/store` from `origin` and hard-fails if that ref
  doesn't exist yet remotely — even though "ref not found" is the expected
  case for a first init, and even though the repo already had other refs
  (tags) that fetched fine. Confirmed it's not a reachability fallback
  either: pointing `origin` at an unreachable URL produces a different,
  equally fatal IO error rather than a graceful local-only path. The
  workaround used here: temporarily `git remote remove origin`, run
  `bn init` (succeeds, purely local), `git remote add origin <url>` back,
  then `git push origin refs/heads/beads/store:refs/heads/beads/store` to
  publish it. Don't re-run `bn init` here — the store already exists.
- **If `bn` is genuinely unavailable** in a given environment (no working
  build at all), state that explicitly in the hand-off and track in GitHub
  Issues alone in the meantime — this is the one accepted exception, not a
  default.
- This is independent of `outram-park-backend`'s own kopi-beans store (see
  below) — that submodule's issues are its own repo's concern, tracked per
  its own `CLAUDE.md`, not this repo's GitHub Issues.

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
