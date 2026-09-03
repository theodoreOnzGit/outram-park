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

One script does everything — regenerate the bindings from the current
backend API, compile them, and produce a wheel you can hand to someone
else:

```sh
cd outram-park                       # the directory holding pyproject.toml
python3 codegen/refresh.py --wheel
```

That writes
`../target/wheels/outram_park-0.1.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
— one wheel, ~39 MB, good for CPython 3.9 and every later version on any
x86-64 Linux with glibc ≥ 2.17. It is the only file to hand over; the type
stubs are inside it.

### What it needs

| dependency | why | install |
| --- | --- | --- |
| Rust stable | builds the crate | `rustup toolchain install stable` |
| Rust **nightly** | rustdoc JSON is nightly-only | `rustup toolchain install nightly` |
| Python 3.9+ | runs the pipeline scripts | any |
| network, first run only | fetches `maturin[zig]` into `codegen/.build-venv` | — |

`codegen/.build-venv` is created automatically on the first `--wheel` run
and reused afterwards; it is gitignored. No system-wide maturin, docker or
zig installation is required.

### The other modes

```sh
python3 codegen/refresh.py                  # regenerate + compile, no wheel
python3 codegen/refresh.py --only-wheel      # wheel only, skip regeneration
python3 codegen/refresh.py --skip-doc        # reuse existing rustdoc JSON (fast)
python3 codegen/refresh.py --reset-skip      # after editing codegen/gen_bindings.py
python3 codegen/refresh.py --wheel-native    # link against host glibc (faster, not portable)
```

A full run takes roughly 3 minutes for the bindings and another 4 for the
release wheel. `--skip-doc` skips the rustdoc pass, which is most of the
first figure, and is safe whenever the backend source has not changed.

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

### 1. Install maturin

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

### 2. Build

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

### 3. Iterate locally

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
