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

`refresh.py` runs all of it, from anywhere -- it resolves its own paths:

```sh
python3 codegen/refresh.py                 # the usual case
python3 codegen/refresh.py --wheel         # ... and build a portable wheel
python3 codegen/refresh.py --only-wheel    # wheel only, no regeneration
python3 codegen/refresh.py --reset-skip    # after editing gen_bindings.py
python3 codegen/refresh.py --skip-doc      # reuse existing rustdoc JSON
```

For the step-by-step build procedure, prerequisites and troubleshooting,
see "Building the wheel" in `../README.md`. This file is about how the
generator works.

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
| `blocked.md` | *why* items were dropped: unmapped type shapes, ranked |
| `../rustfmt.toml` | pins the formatting the generated tree is written in |
| `errors-pass*.log` | raw compiler errors from the last repair run (gitignored) |
| `.build-venv/` | `maturin[zig]`, created on first `--wheel` (gitignored) |

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

## rustdoc JSON is unstable

The schema is nightly-only and versioned, and it does change. The version
this generator was written against is `FORMAT_VERSION` in
`gen_bindings.py`; a mismatch aborts with a message naming the file to
update, rather than generating quiet nonsense from a shape it misreads.

## The generated tree is formatted

`gen_bindings.py` runs `cargo fmt` over `src/python/generated/` as its last
step, so the checked-in result is what `cargo fmt --check` expects and a
regeneration that changes nothing produces no diff.

Two details that are easy to get wrong and were:

- It is `cargo fmt`, not a bare `rustfmt`. Cargo resolves the edition and the
  crate's `rustfmt.toml`; a bare invocation guessing `--edition 2021` against
  a 2024 crate disagrees about where a lone `) -> T` belongs, and leaves a
  tree that `cargo fmt --check` rejects however many times rustfmt has just
  run over it.
- It runs **twice**. rustfmt is not idempotent on some of the nested blocks
  emitted here -- a `let` followed by an `if` inside a struct literal
  collapses only on the second pass.

`../rustfmt.toml` pins `reorder_modules = false` for the same reason the
backend does: `src/backend/mod.rs` groups its modules under explanatory
comments, and a comment binds to the item below it, so alphabetising across
those boundaries reattaches a heading to the wrong set.

## Reading `blocked.md`

`coverage.json` says how much was dropped; `blocked.md` says why, ranked by
how many items each unmapped type shape costs, with examples. That
distinction is the difference between knowing there is a gap and knowing
where to push.

Every binding gap found so far was a handful of type shapes blocking dozens
of items each -- `&Geometry` on the Monte Carlo runners, `&Tape` on RECONR,
`Option<&mut Tally>`, the `uom` aliases, `Result<T>` as a crate-local generic
alias. All of them were obvious the moment the shapes were *counted*, and
all of them were originally found the expensive way, by using the wheel and
noticing something missing.

A row is fixed in one of two places, and the report cannot tell you which:

- **In the generator**, when the shape has a faithful Python representation
  and simply is not mapped yet. `&T` through `PyRef`, `Option<&mut T>`, alias
  following.
- **In the backend**, when it does not. `&[T]` needs `T: Clone`, because a
  slice of owned values cannot be built from borrows; a generic
  `fn read<R: Read>` needs a concrete seam beside it, because a type
  parameter cannot be monomorphised from outside the crate. A generator can
  neither add a derive nor pick an instantiation.

Some rows are neither, and should stay: `&mut [f64]` on an in-place numeric
kernel, a `dyn Trait`, a closure parameter. Exposing those would mean
inventing semantics rather than binding existing ones.

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
