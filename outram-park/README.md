# outram-park (frontend crate)

Frontend crate for the [outram-park-backend](https://github.com/theodoreOnzGit/outram-park-backend)
reactor simulation engine. One crate, three faces:

1. **Desktop GUI** — egui/eframe, gated behind the default `gui` feature.
2. **CLI + TUI** — always compiled in, pure-Rust, Android/Termux compatible.
3. **Python bindings** — built as a `cdylib` under the `python` feature and
   packaged with [maturin](https://www.maturin.rs/) into a single wheel that
   exposes the outram-park-backend API to Python.

## Building the Python wheel with maturin

`pyproject.toml` is already wired for this: it selects the `python` feature,
disables default features (so the wheel does **not** pull in the desktop
GUI's windowing deps), and points maturin at this crate's `Cargo.toml`.

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
pipx install maturin        # or: pip install maturin
# or, from source:            cargo install maturin --locked
```


maturin ≥ 1.7, < 2.0 (matches `[build-system] requires` in `pyproject.toml`).

### 2. Build

Run from this directory (`outram-park/`, where `pyproject.toml` lives):

```sh
maturin build --release
```

For Arch Linux

```sh 
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin build --release
```

The wheel is written to `../target/wheels/` (the workspace `target/` dir),
e.g. `outram_park-0.1.0-cp312-cp312-linux_x86_64.whl`. Install it with:

```sh
pip install ../target/wheels/outram_park-*.whl
```

### 3. Iterate locally

With a virtualenv active, this compiles and installs into it in one step:

```sh
maturin develop --release
```

Then `python -c "import outram_park; print(outram_park.version())"`.

### Targeting specific interpreters

By default maturin builds for the Python on `PATH`. Build for others with
`-i` (they must be installed):

```sh
maturin build --release -i python3.9 -i python3.10 -i python3.11 -i python3.12
```

The wheel is currently interpreter-specific (one wheel per Python minor
version). To emit a single wheel that works across 3.9+ instead, enable an
abi3 build by adding `abi3-py39` to the pyo3 feature in `Cargo.toml`'s
`python` feature.

### Distributable Linux wheels (manylinux)

Local builds are tagged `linux_x86_64` and won't upload to PyPI. For
portable `manylinux` wheels, build in the maturin container:

```sh
docker run --rm -v "$(pwd)/..":/io -w /io/outram-park \
  ghcr.io/pyo3/maturin build --release
```

or use `--zig` for cross-friendly glibc targeting:

```sh
maturin build --release --zig
```

### Source distribution

```sh
maturin sdist        # -> ../target/wheels/outram_park-0.1.0.tar.gz
```

### Publishing

```sh
maturin publish --release        # builds + uploads to PyPI (twine creds)
```
