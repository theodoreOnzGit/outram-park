# outram-park (frontend crate)

Frontend crate for the [outram-park-backend](https://github.com/theodoreOnzGit/outram-park-backend)
reactor simulation engine. One crate, three faces:

1. **Desktop GUI** — egui/eframe, gated behind the default `gui` feature.
2. **CLI + TUI** — always compiled in, pure-Rust, Android/Termux compatible.
3. **Python bindings** — built as a `cdylib` under the `python` feature and
   packaged with [maturin](https://www.maturin.rs/) into a single wheel that
   exposes the outram-park-backend API to Python.

## The Python API

The wheel is not a hand-written façade over a few chosen entry points: it
wraps the public API of **every** backend crate, one Python submodule per
crate — currently 2 137 classes, 3 873 methods, 1 739 functions and 485
constants across 36 crates.

```python
import outram_park as op
op.version()        # '0.1.0'
op.backends()       # ['bedok', 'boon_lay', ..., 'tuas_boussinesq_solver']

from outram_park import teh_o_prke as prke

nuclide = prke.FissioningNuclide.U235Thermal()
decay   = prke.DecayHeat.new_at_equilibrium(nuclide, 10e6)   # 10 MW, saturated
decay.total_decay_heat_power()                               # 6.59e5 W

for _ in range(100):
    decay.advance_timestep(0.0, 1.0)     # 100 s of shutdown, 1 s steps
decay.total_decay_heat_power()           # 3.10e5 W
```

### Units

The backend expresses physical quantities with [`uom`](https://docs.rs/uom).
Across the Python boundary **every quantity is a plain `float` in SI base
units** — kelvin, pascal, metre, second, watt, kilogram, and products
thereof. There are no unit objects to construct and none to unwrap; the
conversion happens in `src/python/runtime.rs`.

Worth stating twice, because the numbers look wrong otherwise:
`total_decay_energy_per_fission()` reads 13.183 MeV/fission in the Rust
docs and returns `2.11e-12` here — the same quantity, in joules.

### What is exposed, and what is not

Each backend crate's public types become Python classes holding the Rust
value, with their public fields as properties and their inherent methods as
methods. A `new` returning `Self` becomes `__init__`. Enums additionally
get one static constructor per variant plus a `.variant()` returning the
variant name. Free functions and scalar constants land at submodule level.
Rust doc comments come across as Python docstrings.

An item is only wrapped when every type in its signature has an
unambiguous Python representation: scalars, `bool`, `str`, `Vec`/slices,
`Option`, `Result` (raised as `RuntimeError`), tuples, `uom` quantities,
and other wrapped types. Generic functions, trait objects, closures,
`&mut` arguments and types with lifetime parameters are skipped — see
`codegen/coverage.json` for per-crate counts, and `codegen/skip.json` for
the handful of items the compiler rejected.

Type stubs (`.pyi`) for the whole surface ship inside the wheel, so
`dir()`, editors and type checkers see the API without the Rust source.

## Building the wheel

This is a runbook: follow it top to bottom and you get the wheel. No step
needs anything beyond the tools listed, and no step needs an AI assistant.

### 0. Prerequisites

| dependency | why | install |
| --- | --- | --- |
| Rust stable | builds the crate and the wheel | `rustup toolchain install stable` |
| Rust **nightly** | rustdoc JSON is nightly-only; used to read the backend API | `rustup toolchain install nightly` |
| Python 3.9+ with `venv` | runs the pipeline scripts and the build venv | Debian/Ubuntu also need `apt install python3-venv` |
| git | the backend is a submodule | — |
| ~15 GB free disk | Rust build artefacts for ~1.1 M lines of backend | — |
| network, first run only | fetches crates and `maturin[zig]` | — |

Nothing else. In particular you do **not** need a system-wide maturin,
docker, or zig — the pipeline creates what it needs.

### 1. Get the source, including the backend

`outram-park-backend` is a git submodule. A clone without it will fail in
step 2 with "no rustdoc JSON for ...":

```sh
git clone https://github.com/theodoreOnzGit/outram-park.git
cd outram-park
git submodule update --init --recursive
```

In an existing clone, `git submodule status` should print a line for
`outram-park-backend` with no leading `-`. If it has one, run the
`submodule update` above.

### 2. Build the wheel

One command:

```sh
python3 outram-park/codegen/refresh.py --wheel
```

It can be run from anywhere; it resolves its own paths. It prints each
stage as it goes and finishes with the path to the wheel:

```
36 backend crates
$ cargo +nightly doc --no-deps -p kovan ...
$ python3 .../gen_bindings.py
bedok                        types=36    methods=17     fns=43    consts=11
...                                              (one line per backend crate)
$ python3 .../repair.py 25
pass 1: clean (56 items blacklisted in total)

2137 classes, 3873 methods, 1739 functions, 485 constants across 36 crates
2182 items unmappable, 56 dropped by the compiler
done in 33s
$ .../.build-venv/bin/maturin build --release --zig --compatibility manylinux2014

wheel: .../target/wheels/outram_park-0.1.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (36.5 MB)
```

**Timing.** On a warm build tree the binding stage takes about 30 seconds
and the release wheel two to four minutes. The *first* run on a fresh
clone is far longer — tens of minutes — because it compiles the whole
backend twice over (once for rustdoc, once for the wheel). That is a
one-off; afterwards cargo's cache carries it.

If the backend API has changed, the repair loop will report something like
`pass 1: 100 errors -> blacklisting 52 items` before converging. That is
normal output, not a failure — see "Why there is a repair loop" in
`codegen/README.md`. What matters is that the last pass says `clean`.

### 3. Verify it

Never ship a wheel you have not imported. In a throwaway venv:

```sh
python3 -m venv /tmp/check
/tmp/check/bin/pip install target/wheels/outram_park-*.whl
/tmp/check/bin/python -c "
import outram_park as op
from outram_park import teh_o_prke as prke
print(len(op.backends()), 'backends')
n = prke.FissioningNuclide.U235Thermal()
d = prke.DecayHeat.new_at_equilibrium(n, 10e6)
print(f'{d.total_decay_heat_power():.4g} W')
"
```

Expected: `36 backends` and `6.591e+05 W` — decay heat is ~6.6 % of a
10 MW fission power at saturation, so a wildly different number means
something is wrong.

### 4. Ship it

`target/wheels/` holds exactly one wheel per successful run, but the
pipeline never deletes old ones. If you have built more than once, check
the directory and take the newest — or clear it first with
`rm target/wheels/*.whl`. Upload that single `.whl` on its own; the type
stubs and every backend module are inside it.

The wheel is `abi3` and `manylinux_2_17`: one file covers CPython 3.9
through 3.14+ on any x86-64 Linux with glibc ≥ 2.17. It does **not** cover
macOS, Windows, or ARM — those need their own build on that platform.

### The other modes

```sh
python3 codegen/refresh.py                  # regenerate + compile, no wheel
python3 codegen/refresh.py --only-wheel      # wheel only, skip regeneration
python3 codegen/refresh.py --skip-doc        # reuse existing rustdoc JSON (fast)
python3 codegen/refresh.py --reset-skip      # after editing codegen/gen_bindings.py
python3 codegen/refresh.py --wheel-native    # link against host glibc (faster, not portable)
```

`--skip-doc` skips the rustdoc pass, which is most of the regeneration
time, and is safe whenever the backend source has not changed since the
last run.

### Running the stages by hand

`refresh.py` is a wrapper around four ordinary commands. If it breaks, or
you want to inspect an intermediate, run them yourself from the
`outram-park/` directory (the one holding `pyproject.toml`):

```sh
# 1. read the backend's public API into rustdoc JSON (nightly only).
#    One -p per crate; the list is the `all-backends` feature in Cargo.toml.
cd ../outram-park-backend
RUSTDOCFLAGS="-Z unstable-options --output-format json" \
  cargo +nightly doc --no-deps -p teh-o-prke -p tampines -p ...
#    -> outram-park-backend/target/doc/<crate>.json
cd ../outram-park

# 2. rustdoc JSON -> pyo3 wrappers + type stubs
python3 codegen/gen_bindings.py
#    -> src/python/generated/*.rs, python/outram_park/*.pyi

# 3. compile, drop whatever does not build, repeat until clean
python3 codegen/repair.py
#    -> updates codegen/skip.json

# 4. build the wheel (see "Driving maturin by hand" below)
maturin build --release
```

Step 2 can be limited to one crate for a quick look —
`python3 codegen/gen_bindings.py teh-o-prke` — but that skips rewriting
`src/python/generated/mod.rs`, so do a full run before compiling.

### Troubleshooting

**`no rustdoc JSON for <crates>`** — the submodule is not checked out, or
step 1 failed. Run `git submodule update --init --recursive`.

**`rustdoc JSON format_version N, but this generator was written for 60`**
— your nightly is newer than the generator. rustdoc JSON is explicitly
unstable and its schema changes. Either install an older nightly, or
update `codegen/gen_bindings.py` for the new shape; the error names the
file to change.

**`error: the configured Python interpreter version (3.x) is newer than
PyO3's maximum supported version`** — this should not happen any more; the
build is `abi3-py39`, which is version-independent. If you see it, the
`python` feature in `Cargo.toml` has lost its `pyo3/abi3-py39` entry.

**`Failed to find zig`** — only when driving maturin yourself. See
"Distributable Linux wheels" below; `refresh.py --wheel` handles it.

**`bindings do not compile cleanly`** — the repair loop could not converge.
The raw compiler errors are in `codegen/errors-pass*.log`. This normally
means a backend change hit a case the generator does not model; see
`codegen/README.md`.

**`warning: unused ...` by the thousand** — expected. The generated code is
machine-written and noisy; only `error:` lines matter.

### Regenerating after a backend change

The tree under `src/python/generated/` and the stubs under
`python/outram_park/` are a pure function of the backend's public API.
**Do not edit either by hand** — run `refresh.py` and commit what it
produces. The backend crate list comes from the `all-backends` feature in
`Cargo.toml`, so wiring in a new backend crate means editing `Cargo.toml`
and re-running; nothing else holds a copy of the list.

`codegen/README.md` explains how the pipeline works and how to extend the
type mapping.

## Driving maturin by hand

`refresh.py --wheel` covers the normal case; this section is for when you
want to drive maturin yourself.

`pyproject.toml` is already wired for it: it selects the `python` and
`all-backends` features, disables default features (so the wheel does
**not** pull in the desktop GUI's windowing deps), and points maturin at
this crate's `Cargo.toml`.

### Installing maturin

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install maturin        # or: pip install maturin
# or, from source:            cargo install maturin --locked
```

on Arch Linux

```sh
sudo pacman -S python-pipx
pipx install maturin
```

maturin ≥ 1.7, < 2.0 (matches `[build-system] requires` in `pyproject.toml`).

### A plain build

Run from this directory (`outram-park/`, where `pyproject.toml` lives):

```sh
maturin build --release
```

The build is `abi3-py39`, so it produces **one** wheel that works on
CPython 3.9 and every later version — including versions newer than the
pyo3 release it was built against. There is no need to pass
`--interpreter`, and no `PYO3_USE_ABI3_FORWARD_COMPATIBILITY` workaround.

Install it with:

```sh
pip install ../target/wheels/outram_park-*.whl
```

### Iterating locally

With a virtualenv active, this compiles and installs into it in one step:

```sh
maturin develop --release
```

Then `python -c "import outram_park; print(outram_park.backends())"`.

### Distributable Linux wheels (manylinux)

A plain `maturin build` links against the build host's glibc. On a
rolling-release distro that is far newer than anything the wheel will be
opened on, and maturin falls back to the unportable `linux_x86_64` tag —
which installs fine and then fails at import on an older system. For a
wheel that runs anywhere, link against an old glibc with zig:

```sh
python3 -m venv /tmp/mvenv
/tmp/mvenv/bin/pip install 'maturin[zig]'
PATH="$(echo /tmp/mvenv/lib/python3*/site-packages/ziglang):$PATH" \
  /tmp/mvenv/bin/maturin build --release --zig --compatibility manylinux2014
```

Two things bite here, and `refresh.py --wheel` handles both: maturin needs
`ziglang` importable by its *own* interpreter (so injecting it next to a
pipx-installed maturin does not work), **and** it needs a `zig` binary on
`PATH` — the one shipped inside the `ziglang` package.

The container route works too, if you have one:

```sh
docker run --rm -v "$(pwd)/..":/io -w /io/outram-park \
  ghcr.io/pyo3/maturin build --release
```

### Source distribution

```sh
maturin sdist        # -> ../target/wheels/outram_park-0.1.0.tar.gz
```

### Publishing

```sh
maturin publish --release        # builds + uploads to PyPI (twine creds)
```
