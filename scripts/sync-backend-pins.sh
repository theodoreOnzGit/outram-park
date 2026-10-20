#!/usr/bin/env bash
#
# Lockstep release, outram-park side (outram-park-backend gh:#971, #972).
# Run AFTER the backend release is live on crates.io
# (outram-park-backend/scripts/release/publish.sh).
#
#   scripts/sync-backend-pins.sh <release-tag>            # pin, check
#   scripts/sync-backend-pins.sh <release-tag> --publish  # ... and publish
#
# 1. Moves the outram-park-backend submodule to <release-tag>.
# 2. Rewrites every backend pin in outram-park/Cargo.toml to the version that
#    tag carries. Pins are crates.io versions ONLY, never paths (maintainer,
#    2026-10-20). A backend crate with no pin here is an error: wire it in
#    (feature, dependency, src/backend/ module) before releasing.
# 3. `cargo check --release --features all-backends` against crates.io.
# 4. With --publish: `cargo publish -p outram-park`. Committing and tagging
#    are left to the operator, who reviews the diff first.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

tag=${1:?usage: scripts/sync-backend-pins.sh <release-tag> [--publish]}
publish=0
[ "${2:-}" = "--publish" ] && publish=1
manifest=outram-park/Cargo.toml

git -C outram-park-backend fetch --tags --quiet origin
git -C outram-park-backend checkout --quiet "$tag"

missing=0
while IFS=$'\t' read -r name ver; do
    # The dependency key is the package name, or an alias carrying
    # `package = "<name>"` (kovan, dover).
    if grep -qE "^$name[[:space:]]*=[[:space:]]*\{" "$manifest"; then
        sed -i -E "s/^($name[[:space:]]*=[[:space:]]*\{[^}]*\bversion[[:space:]]*=[[:space:]]*\")[^\"]+\"/\1$ver\"/" "$manifest"
    elif grep -qE "package[[:space:]]*=[[:space:]]*\"$name\"" "$manifest"; then
        sed -i -E "s/(package[[:space:]]*=[[:space:]]*\"$name\"[^}]*\bversion[[:space:]]*=[[:space:]]*\")[^\"]+\"/\1$ver\"/" "$manifest"
    else
        echo "error: backend crate $name is not wired into $manifest" >&2
        missing=1
    fi
done < <(cargo metadata --no-deps --format-version 1 --manifest-path outram-park-backend/Cargo.toml \
            | jq -r '.packages[] | [.name, .version] | @tsv')
[ "$missing" = 0 ] || exit 1

if grep -qE 'path[[:space:]]*=[[:space:]]*"\.\./outram-park-backend' "$manifest"; then
    echo "error: $manifest has a path dependency on the backend; crates.io versions only" >&2
    exit 1
fi

cargo check --release -p outram-park --features all-backends
cargo test --release -p outram-park --test backend_wiring

if [ "$publish" = 1 ]; then
    cargo publish -p outram-park
fi
echo "Pins synced to $tag. Review git diff, then commit and tag."
