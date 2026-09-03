# codegen — the Python binding generator

Everything under `../src/python/generated/` and `../python/outram_park/` is
emitted by the scripts here. **Do not edit either tree by hand**; edit the
generator and regenerate.

## Why generated

`outram-park-backend` is roughly 1.1 M lines across 36 crates with some
16 000 public functions. Hand-written pyo3 wrappers over that would be
stale the day after they were written, and the parts that mattered would be
whichever parts someone got round to. Generating from the backend's own
rustdoc output means the Python surface tracks the Rust API by
construction, and the parts that *cannot* be exposed are counted rather
than quietly missing.

## The pipeline

```
outram-park-backend                      (the API of record)
   |  cargo +nightly doc --output-format json
   v
target/doc/<crate>.json                  (rustdoc JSON, format v60)
   |  gen_bindings.py
   v
src/python/generated/<crate>.rs          (pyo3 wrappers, one file per crate)
python/outram_park/<crate>.pyi           (type stubs, shipped in the wheel)
   |  repair.py  (cargo check -> blacklist -> regenerate -> repeat)
   v
a tree that compiles
```

`refresh.py` runs all of it:

```sh
python3 codegen/refresh.py                 # the usual case
python3 codegen/refresh.py --reset-skip    # after editing gen_bindings.py
python3 codegen/refresh.py --skip-doc      # reuse existing rustdoc JSON
python3 codegen/refresh.py --wheel         # ... and build the wheel
```

The backend crate list comes from the `all-backends` feature in
`../Cargo.toml`, so a new backend crate is wired in by editing that file —
nothing here holds a second copy of the list.

## The files

| file | role |
| --- | --- |
| `refresh.py` | drives the whole pipeline; the entry point |
| `gen_bindings.py` | rustdoc JSON → pyo3 Rust + `.pyi` stubs |
| `repair.py` | compile, blacklist what fails, regenerate, repeat |
| `crates.txt` | crate list, rewritten by `refresh.py` from `Cargo.toml` |
| `skip.json` | items the compiler rejected (generated) |
| `coverage.json` | per-crate counts of what was and was not wrapped |
| `errors-pass*.log` | raw compiler errors from the last repair run |

## How an item is mapped

A type is wrapped as an opaque `#[pyclass]` holding the Rust value. Types
that implement `Clone` can also be passed *into* Rust, so they appear in
argument position; types that do not are return-only.

| Rust | Python |
| --- | --- |
| `f64`, `i32`, `usize`, `bool`, `char` | `float`, `int`, `bool`, `str` |
| `String`, `&str`, `PathBuf`, `&Path` | `str` |
| `uom::si::f64::*` | `float`, in SI base units |
| `Vec<T>`, `&[T]`, `[T; N]` | `list[T]` |
| `Option<T>` | `T \| None` |
| `Result<T, E>` | `T`, or `RuntimeError` carrying `{:?}` of the error |
| `(A, B)` up to 4 elements | `tuple[A, B]` |
| a wrapped struct/enum | its class |

Public struct fields become properties (settable when the field type round
trips). A `new` returning `Self` becomes `__init__`; other associated
functions become static methods. A struct whose fields are *all* public and
settable and which has no `new` gets a field-wise `__init__`. Enums get one
static constructor per variant plus `.variant()`.

Skipped: generics, trait objects, closures, function pointers, `&mut`
arguments, types with lifetime parameters, and anything whose signature
contains a type not in the table above.

## Why there is a repair loop

rustdoc's view of the API and rustc's do not quite agree — a trait bound
rustdoc does not record, a `Clone` that does not hold for a field's element
type, a return value borrowing from an argument. Rather than modelling all
of that statically, `repair.py` compiles, maps each error back to the
`// @item <key>` marker above it, records the key in `skip.json`,
regenerates, and repeats until clean.

`skip.json` is therefore *evidence*, not configuration: it is only ever
added to. After fixing a generator bug, clear it (`--reset-skip`) or the
items the fix would have recovered stay excluded.

Systematic failures belong in `gen_bindings.py`, not in `skip.json`. The
first run of this pipeline produced ~3 900 errors; four root-cause fixes
(public paths rather than definition paths, cloning out of `&self`,
borrow-derived types barred from fields, exhaustive enum match arms)
brought it to 13.
