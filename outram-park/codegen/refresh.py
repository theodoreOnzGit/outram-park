#!/usr/bin/env python3
"""Regenerate the Python bindings from the current backend API.

Run this whenever `outram-park-backend` changes -- a new crate, a new type,
a changed signature. It drives the whole pipeline end to end:

  1. read the backend crate list from `Cargo.toml`'s `all-backends` feature
  2. `cargo +nightly doc --output-format json` for each of those crates
  3. `gen_bindings.py` -- rustdoc JSON -> `src/python/generated/*.rs` + stubs
  4. `repair.py` -- compile, blacklist what does not build, repeat
  5. print a coverage summary
  6. with `--wheel`, build a portable wheel to hand to someone else

Nothing here is incremental by design: the generated tree is a pure function
of the backend's public API plus `skip.json`, so a full regeneration is the
only way to notice that something was *removed*.

    python3 codegen/refresh.py                # regenerate, steps 1-5
    python3 codegen/refresh.py --wheel        # ... and build a portable wheel
    python3 codegen/refresh.py --only-wheel   # just the wheel, no regeneration
    python3 codegen/refresh.py --skip-doc     # reuse existing rustdoc JSON
    python3 codegen/refresh.py --reset-skip   # re-test blacklisted items

`--reset-skip` is the one to use after changing `gen_bindings.py`: entries
in `skip.json` are only ever added, so items that a generator fix would now
handle stay excluded until the blacklist is cleared.

Requires: a nightly toolchain for rustdoc JSON (`rustup toolchain install
nightly`), and for `--wheel`, network access the first time so it can
create `codegen/.build-venv` with `maturin[zig]`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CRATE = os.path.dirname(HERE)
BACKEND = os.path.join(os.path.dirname(CRATE), "outram-park-backend")
DOC_DIR = os.path.join(BACKEND, "target", "doc")


def run(cmd, cwd=None, env=None, quiet=False):
    print("$ " + " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(cmd, cwd=cwd, env=e,
                       stdout=subprocess.DEVNULL if quiet else None)
    return p.returncode


def backend_crates():
    """The crate list, taken from the `all-backends` feature so that
    `Cargo.toml` stays the single place a backend crate is registered."""
    src = open(os.path.join(CRATE, "Cargo.toml")).read()
    m = re.search(r"^all-backends = \[(.*?)^\]", src, re.S | re.M)
    if not m:
        sys.exit("Cargo.toml: no `all-backends` feature found")
    return re.findall(r'"([^"]+)"', m.group(1))


BUILD_VENV = os.path.join(HERE, ".build-venv")


def maturin_env():
    """A venv holding `maturin[zig]`, created on first use.

    `--zig` is what makes the wheel portable: it links against an old glibc
    instead of the build host's, which on a rolling-release distro is far
    newer than anything the wheel will be opened on. maturin needs `ziglang`
    importable by its *own* interpreter and a `zig` binary on PATH, so both
    have to live in one environment -- injecting `ziglang` alongside a
    pipx-installed maturin does not work.
    """
    mat = os.path.join(BUILD_VENV, "bin", "maturin")
    if not os.path.exists(mat):
        print("bootstrapping %s (maturin[zig])" % BUILD_VENV)
        if run([sys.executable, "-m", "venv", BUILD_VENV]) != 0:
            sys.exit("could not create the build venv")
        if run([os.path.join(BUILD_VENV, "bin", "pip"), "install", "-q",
                "maturin[zig]"]) != 0:
            sys.exit("could not install maturin[zig]")
    zig = None
    for root, dirs, files in os.walk(os.path.join(BUILD_VENV, "lib")):
        if "zig" in files and os.path.basename(root) == "ziglang":
            zig = root
            break
    if zig is None:
        sys.exit("ziglang not found in %s" % BUILD_VENV)
    return mat, zig


def build_wheel(portable):
    if not portable:
        return run(["maturin", "build", "--release"], cwd=CRATE)
    mat, zig = maturin_env()
    rc = run([mat, "build", "--release", "--zig",
              "--compatibility", "manylinux2014"], cwd=CRATE,
             env={"PATH": zig + os.pathsep + os.environ["PATH"]})
    if rc == 0:
        wheels = os.path.join(os.path.dirname(CRATE), "target", "wheels")
        newest = max((os.path.join(wheels, f) for f in os.listdir(wheels)
                      if f.endswith(".whl")), key=os.path.getmtime)
        print("\nwheel: %s (%.1f MB)"
              % (newest, os.path.getsize(newest) / 1e6))
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-doc", action="store_true",
                    help="reuse the rustdoc JSON already in the backend's target/doc")
    ap.add_argument("--reset-skip", action="store_true",
                    help="clear skip.json first, re-testing every previously dropped item")
    ap.add_argument("--wheel", action="store_true",
                    help="build a portable manylinux2014 wheel once the bindings compile")
    ap.add_argument("--wheel-native", action="store_true",
                    help="build against the host's glibc instead (faster, not portable)")
    ap.add_argument("--only-wheel", action="store_true",
                    help="skip regeneration and just build the wheel")
    ap.add_argument("--passes", type=int, default=25,
                    help="maximum compile-repair passes (default 25)")
    args = ap.parse_args()

    t0 = time.time()
    if args.only_wheel:
        return build_wheel(portable=not args.wheel_native)

    crates = backend_crates()
    with open(os.path.join(HERE, "crates.txt"), "w") as f:
        f.write("\n".join(crates) + "\n")
    print("%d backend crates" % len(crates))

    if not args.skip_doc:
        # rustdoc JSON is nightly-only; the emitted format is versioned, so
        # gen_bindings.py checks the version it was written against.
        cmd = ["cargo", "+nightly", "doc", "--no-deps"]
        for c in crates:
            cmd += ["-p", c]
        rc = run(cmd, cwd=BACKEND, quiet=True,
                 env={"RUSTDOCFLAGS": "-Z unstable-options --output-format json"})
        if rc != 0:
            return rc
    missing = [c for c in crates
               if not os.path.exists(os.path.join(DOC_DIR, c.replace("-", "_") + ".json"))]
    if missing:
        sys.exit("no rustdoc JSON for: %s (drop --skip-doc?)" % ", ".join(missing))

    if args.reset_skip:
        with open(os.path.join(HERE, "skip.json"), "w") as f:
            f.write("[]")
        print("skip.json reset")

    if run([sys.executable, os.path.join(HERE, "gen_bindings.py")]) != 0:
        return 1
    rc = run([sys.executable, os.path.join(HERE, "repair.py"), str(args.passes)])
    if rc != 0:
        print("bindings do not compile cleanly; see codegen/errors-pass*.log")
        return rc

    cov = json.load(open(os.path.join(HERE, "coverage.json")))
    tot = {k: sum(c.get(k, 0) for c in cov.values())
           for k in ("types", "methods", "fns", "consts",
                     "methods_skipped", "fns_skipped")}
    skipped = len(json.load(open(os.path.join(HERE, "skip.json"))))
    print("\n%d classes, %d methods, %d functions, %d constants across %d crates"
          % (tot["types"], tot["methods"], tot["fns"], tot["consts"], len(cov)))
    print("%d items unmappable, %d dropped by the compiler"
          % (tot["methods_skipped"] + tot["fns_skipped"], skipped))
    print("done in %.0fs" % (time.time() - t0))

    if args.wheel or args.wheel_native:
        return build_wheel(portable=not args.wheel_native)
    return 0


if __name__ == "__main__":
    sys.exit(main())
