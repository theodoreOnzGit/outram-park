#!/usr/bin/env python3
"""Generate pyo3 bindings for the outram-park-backend crates from rustdoc JSON.

Reads one rustdoc JSON file per backend crate (produced by
`codegen/run.sh`) and emits, under `src/python/generated/`, one Rust file
per crate wrapping that crate's public API as a Python submodule.

The mapping is deliberately conservative -- an item is only emitted when
every type in its signature has an unambiguous Python representation (see
`Ty` and `map_type`). Anything else is skipped and counted in the coverage
report. `skip.json`, maintained by the compile-repair loop in `repair.py`,
drops the residue that type-checks in rustdoc's view but not in rustc's.
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CRATE_ROOT = os.path.dirname(HERE)
DOC_DIR = os.path.join(CRATE_ROOT, "..", "outram-park-backend", "target", "doc")
OUT_DIR = os.path.join(CRATE_ROOT, "src", "python", "generated")
STUB_DIR = os.path.join(CRATE_ROOT, "python", "outram_park")
SKIP_FILE = os.path.join(HERE, "skip.json")

RUST_KEYWORDS = {
    "as", "break", "const", "continue", "crate", "dyn", "else", "enum",
    "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop",
    "match", "mod", "move", "mut", "pub", "ref", "return", "self", "Self",
    "static", "struct", "super", "trait", "true", "type", "unsafe", "use",
    "where", "while", "async", "await", "gen", "try", "abstract", "become",
    "box", "do", "final", "macro", "override", "priv", "typeof", "unsized",
    "virtual", "yield",
}

PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "match", "case", "type",
}

INT_PRIMS = {
    "i8": "i8", "i16": "i16", "i32": "i32", "i64": "i64", "i128": "i128",
    "isize": "isize", "u8": "u8", "u16": "u16", "u32": "u32", "u64": "u64",
    "u128": "u128", "usize": "usize",
}
FLOAT_PRIMS = {"f32": "f32", "f64": "f64"}


class Ty:
    """A Rust type that has a Python representation.

    `py` is the Rust type written into the pyo3 signature; `into_rust` and
    `from_rust` are expression templates (`$V` is the value) bridging the
    two sides.
    """

    def __init__(self, py, pyi, into_rust="$V", from_rust="$V", owned=True,
                 param_prefix="", fallible=False):
        self.py = py
        self.pyi = pyi
        self.param_prefix = param_prefix
        # True when `into_rust` can fail and uses `?`, which forces the
        # generated function to return a `PyResult`.
        self.fallible = fallible
        self._into = into_rust
        self._from = from_rust
        self.owned = owned

    def into_rust(self, e):
        return self._into.replace("$V", e)

    def from_rust(self, e):
        return self._from.replace("$V", e)


def scalar(rust, pyi):
    return Ty(rust, pyi)


def describe_type(t, paths):
    """A short human-readable rendering of a rustdoc type, for reporting."""
    if not isinstance(t, dict):
        return str(t)
    k = next(iter(t), "?")
    v = t[k]
    if k == "primitive":
        return v
    if k == "generic":
        return v
    if k == "resolved_path":
        p = paths.get(str(v["id"]))
        name = p["path"][-1] if p else v.get("path", "?")
        args = angle_args(v)
        if args:
            return "%s<%s>" % (name, ", ".join(describe_type(a, paths) for a in args))
        return name
    if k == "borrowed_ref":
        return ("&mut " if v.get("is_mutable") else "&") + describe_type(v["type"], paths)
    if k == "slice":
        return "[%s]" % describe_type(v, paths)
    if k == "array":
        return "[%s; N]" % describe_type(v["type"], paths)
    if k == "tuple":
        return "(%s)" % ", ".join(describe_type(x, paths) for x in v)
    if k == "impl_trait":
        return "impl Trait"
    if k == "dyn_trait":
        return "dyn Trait"
    if k == "qualified_path":
        return "<assoc path>"
    if k == "function_pointer":
        return "fn pointer"
    if k == "raw_pointer":
        return "raw pointer"
    return k


def _has_generic(t):
    """True if a rustdoc type mentions a type parameter anywhere."""
    if isinstance(t, dict):
        if "generic" in t:
            return True
        return any(_has_generic(x) for x in t.values())
    if isinstance(t, list):
        return any(_has_generic(x) for x in t)
    return False


def _tykey(args):
    return json.dumps(args, sort_keys=True)


def angle_args(v):
    """The concrete type arguments of a `resolved_path`, if any."""
    a = v.get("args")
    if not a or "angle_bracketed" not in a:
        return []
    return [x["type"] for x in a["angle_bracketed"]["args"] if "type" in x]


def esc_path(segments):
    """Raw-escape any path segment that is a Rust keyword.

    Crates really do have modules named `gen` and `type`; without `r#`
    the emitted path does not even parse.
    """
    return [("r#" + x if x in RUST_KEYWORDS else x) for x in segments]


def rustdoc_str(docs, limit):
    """Escape rustdoc prose for a `#[doc = "..."]` attribute.

    Truncation happens before escaping so a cut can never land in the
    middle of an escape sequence.
    """
    d = (docs or "")[:limit]
    return d.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# The rustdoc JSON schema this generator was written against. rustdoc bumps
# it whenever the shape changes, and it is nightly-only and explicitly
# unstable, so a newer toolchain can and will emit something this code
# misreads. Failing loudly beats generating quiet nonsense.
FORMAT_VERSION = 60


class CrateModel:
    """The subset of one crate's rustdoc JSON that the emitter needs."""

    def __init__(self, path):
        with open(path) as f:
            d = json.load(f)
        got = d.get("format_version")
        if got != FORMAT_VERSION:
            sys.exit(
                "%s: rustdoc JSON format_version %s, but this generator was\n"
                "written for %s. Your nightly toolchain emits a different\n"
                "schema. Either pin an older nightly, or read the rustdoc-types\n"
                "changelog and update gen_bindings.py for the new shape."
                % (os.path.basename(path), got, FORMAT_VERSION))
        self.index = d["index"]
        self.paths = d["paths"]
        self.crate_name = d["index"][str(d["root"])]["name"]
        self.types = {}          # id -> type record
        self.generic_types = {}  # id -> local generic struct/enum record
        self.impl_records = defaultdict(list)  # type id -> [(for_args, [fn ids])]
        self.alias_by_inst = {}  # (target id, args key) -> alias id
        self.alias_target = {}   # alias id -> the type it stands for
        self.generic_alias = {}  # alias id -> ([param names], target type)
        self.by_pyname = {}
        self.traits = defaultdict(set)   # type id -> trait names
        self.inherent = defaultdict(list)  # type id -> [fn item ids]
        self.free_fns = []
        self.consts = []
        self.stats = defaultdict(int)
        self.public = self._public_paths()
        self._scan()

    # -- scanning -----------------------------------------------------

    def _is_public(self, item):
        if item.get("visibility") != "public":
            return False
        for a in item.get("attrs", []):
            s = a if isinstance(a, str) else a.get("other", "")
            if "doc(hidden)" in s or "doc = hidden" in s:
                return False
        return True

    def _generic_free(self, generics):
        """True if nothing here needs monomorphising.

        Lifetimes are irrelevant, and an argument-position `impl Trait`
        shows up as a *synthetic* type parameter -- rejecting those would
        throw away every `fn zeros(name: impl Into<String>, ..)`, which is
        how most constructors in this workspace are written. They are
        handled in `Emitter._map_impl_trait` instead.
        """
        for p in generics.get("params", []):
            kind = p.get("kind", {})
            if kind == "lifetime" or "lifetime" in kind:
                continue
            if isinstance(kind, dict) and kind.get("type", {}).get("is_synthetic"):
                continue
            return False
        return True

    def rust_path(self, item_id):
        """The shortest *importable* path to an item, or None.

        `self.paths` records definition sites, and a crate that defines a
        type in a private module and re-exports it has a definition path
        that does not compile. `_public_paths` walks the module tree, so
        what comes back here is a path a dependent crate can name.
        """
        return self.public.get(str(item_id))

    def _scan_aliases(self):
        """Wrap type aliases that pin a generic type to concrete arguments.

        `pub type VolScalarField = VolField<f64>` is the shape that matters:
        the generic `VolField<T>` cannot be a `#[pyclass]`, but each alias of
        it names one concrete instantiation that can. The alias is wrapped
        under its own name and path, and the target's fields and inherent
        impls are emitted with `T` substituted.
        """
        for k, v in self.index.items():
            if v.get("crate_id") != 0 or "type_alias" not in v["inner"]:
                continue
            if not self._is_public(v):
                continue
            ta = v["inner"]["type_alias"]
            alias_params = [
                pp["name"] for pp in ta.get("generics", {}).get("params", [])
            ]
            if alias_params:
                # A *generic* alias cannot be wrapped as a class, but it can
                # still be seen through. `pub type Result<T> = Result<T, Error>`
                # is the one that matters: it hides every fallible function in
                # a crate behind a shape the Result mapping does not recognise.
                self.generic_alias[k] = (alias_params, ta["type"])
                continue        # the alias is itself generic; nothing pinned
            # Aliases that merely rename an existing type -- above all the
            # `uom` ones this workspace uses everywhere (`pub type
            # MolarFlowRate = CatalyticActivity`) -- are followed through
            # rather than wrapped. Without this, every signature spelled with
            # a named quantity is dropped.
            self.alias_target[k] = ta["type"]
            rp = ta["type"].get("resolved_path") if isinstance(ta["type"], dict) else None
            if not rp:
                continue
            tgt = str(rp["id"])
            g = self.generic_types.get(tgt)
            if not g:
                continue
            args = angle_args(rp)
            if len(args) != len(g["params"]) or any(_has_generic(a) for a in args):
                continue
            path = self.rust_path(k)
            if not path:
                continue
            self.types[k] = {
                "id": k, "name": v["name"], "kind": g["kind"], "path": path,
                "docs": v.get("docs") or g["docs"], "inner": g["inner"],
                "target": tgt, "args": args,
            }
            self.alias_by_inst.setdefault((tgt, _tykey(args)), k)
            self.stats["types_from_alias"] += 1

    def _public_paths(self):
        """item id -> shortest publicly reachable `a::b::C` path."""
        best = {}
        root = None
        for k, v in self.index.items():
            m = v["inner"].get("module")
            if m and m.get("is_crate"):
                root = k
                break
        if root is None:
            return best
        # (module id, prefix); breadth-first so the first path found for an
        # item is also the shortest
        queue = [(root, [self.index[root]["name"]])]
        seen_mod = set()
        while queue:
            mid, prefix = queue.pop(0)
            if (mid, tuple(prefix)) in seen_mod:
                continue
            seen_mod.add((mid, tuple(prefix)))
            mod = self.index.get(mid, {}).get("inner", {}).get("module")
            if not mod:
                continue
            for cid in mod["items"]:
                ci = self.index.get(str(cid))
                if not ci or ci.get("visibility") not in ("public", "default"):
                    continue
                kind = next(iter(ci["inner"]))
                if kind == "use":
                    u = ci["inner"]["use"]
                    tgt = str(u["id"])
                    if u.get("is_glob"):
                        tmod = self.index.get(tgt, {}).get("inner", {}).get("module")
                        if tmod:
                            queue.append((tgt, prefix))
                        continue
                    if tgt in self.index and "module" in self.index[tgt]["inner"]:
                        queue.append((tgt, prefix + [u["name"]]))
                    elif tgt not in best:
                        best[tgt] = "::".join(esc_path(prefix + [u["name"]]))
                    continue
                name = ci.get("name")
                if not name:
                    continue
                if kind == "module":
                    queue.append((str(cid), prefix + [name]))
                elif str(cid) not in best:
                    best[str(cid)] = "::".join(esc_path(prefix + [name]))
        return best

    def _scan(self):
        idx = self.index
        for k, v in idx.items():
            if v.get("crate_id") != 0:
                continue
            inner = v["inner"]
            kind = next(iter(inner))
            if kind in ("struct", "enum"):
                if not self._is_public(v):
                    continue
                body = inner[kind]
                if not self._generic_free(body.get("generics", {})):
                    # A generic type cannot be wrapped directly, but a type
                    # alias may pin it to concrete arguments -- see
                    # `_scan_aliases`. `VolScalarField = VolField<f64>` is
                    # the case that matters: without it none of the field
                    # types exist in Python at all.
                    path = self.rust_path(k)
                    if path:
                        self.generic_types[k] = {
                            "id": k, "name": v["name"], "kind": kind,
                            "path": path, "docs": v.get("docs") or "",
                            "inner": body,
                            "params": [pp["name"] for pp
                                       in body.get("generics", {}).get("params", [])],
                        }
                    self.stats["types_generic_skipped"] += 1
                    continue
                if body.get("generics", {}).get("params"):
                    # only lifetimes are left, and a borrowed type cannot be
                    # owned by a `#[pyclass]` wrapper
                    self.stats["types_lifetime_skipped"] += 1
                    continue
                path = self.rust_path(k)
                if not path:
                    continue
                self.types[k] = {
                    "id": k, "name": v["name"], "kind": kind, "path": path,
                    "docs": v.get("docs") or "", "inner": body,
                }
            elif kind == "function":
                # module-level functions only; impl items are reached via impls
                pass
            elif kind == "constant":
                if self._is_public(v) and self.rust_path(k):
                    self.consts.append(k)

        # free functions: those whose paths entry is a function
        for k, v in idx.items():
            if v.get("crate_id") != 0 or "function" not in v["inner"]:
                continue
            p = self.paths.get(str(k))
            if p and p["kind"] == "function" and self._is_public(v):
                self.free_fns.append(k)

        self._scan_aliases()

        # impls
        for k, v in idx.items():
            impl = v["inner"].get("impl")
            if not impl or impl.get("blanket_impl") or impl.get("is_synthetic"):
                continue
            forty = impl.get("for", {})
            rp = forty.get("resolved_path")
            if not rp:
                continue
            tid = str(rp["id"])
            if tid not in self.types and tid not in self.generic_types:
                continue
            tr = impl.get("trait")
            if tr:
                self.traits[tid].add(tr["path"].split("::")[-1])
                continue
            fns = [str(it) for it in impl.get("items", [])
                   if self.index.get(str(it))
                   and "function" in self.index[str(it)]["inner"]]
            if not fns:
                continue
            self.impl_records[tid].append((angle_args(rp), fns))
            if tid in self.types and self._generic_free(impl.get("generics", {})):
                self.inherent[tid].extend(fns)


class Emitter:
    def __init__(self, model, skip, registry=None, feature=None):
        self.m = model
        self.skip = skip
        # path -> wrapper for types defined in *other* backend crates. Each
        # crate's bindings are generated separately, so without this a
        # `VolScalarField` in a `outram-foam-appbuilder-lib` signature is
        # unmappable and every solver stays undrivable.
        self.registry = registry if registry is not None else {}
        self.feature = feature
        self.needed = set()   # features the item being emitted depends on
        self.blocked = []     # (item, position, rendered type) that did not map
        self.wrapped = {}   # type id -> (rust_ident, py_name)
        self.self_tid = None   # type id `Self` resolves to, while in an impl
        self.cloneable = set()  # wrapped types that can also be arguments
        self.subst = {}         # type-param name -> concrete rustdoc type
        self.lines = []
        self.markers = []   # (line_no, item_key)
        self.registrations = []
        self.pyi = []
        self.stats = model.stats

    # -- naming -------------------------------------------------------

    def _ident(self, s):
        return re.sub(r"[^A-Za-z0-9_]", "_", s)

    @staticmethod
    def rust_ident(name):
        """A Rust-legal identifier for `name`."""
        return name + "_" if name in RUST_KEYWORDS else name

    def plan_types(self):
        """Choose which types get a `#[pyclass]` wrapper, and their names."""
        used = {}
        # Shallowest path first, so when two distinct types share a name the
        # more canonical one keeps the unprefixed Python name: `Sphere` should
        # be `prelude::Sphere`, the CSG surface, not
        # `pebble_beds::sphere_packing::Sphere`. Alphabetical order alone gave
        # the plain name to whichever sorted first, which is arbitrary.
        for tid, t in sorted(
            self.m.types.items(),
            key=lambda kv: (kv[1]["path"].count("::"), kv[1]["path"]),
        ):
            if "type:" + t["path"] in self.skip:
                continue
            tr = self.m.traits[t.get("target", tid)]
            if "Clone" in tr:
                self.cloneable.add(tid)
            else:
                # Without Clone the wrapper cannot hand the value back to
                # Rust by value, so the class is return-only: methods on it
                # work, but it can never appear as an argument.
                self.stats["types_no_clone"] += 1
            name = t["name"]
            if name in used:
                segs = t["path"].split("::")
                name = (segs[-2] + "_" + name) if len(segs) > 1 else name + "_"
                if name in used:
                    self.stats["types_name_collision"] += 1
                    continue
            used[name] = tid
            self.wrapped[tid] = ("Py_" + self._ident(t["path"]), name)

    # -- type mapping -------------------------------------------------

    def map_type(self, t, arg_position):
        """Map a rustdoc type to a `Ty`, or None when unrepresentable."""
        if not isinstance(t, dict):
            return None
        kind = next(iter(t))
        v = t[kind]

        if kind == "primitive":
            if v in FLOAT_PRIMS:
                return scalar(v, "float")
            if v in INT_PRIMS:
                return scalar(v, "int")
            if v == "bool":
                return scalar("bool", "bool")
            if v == "char":
                return Ty("char", "str")
            if v == "str":
                return Ty("String", "str", into_rust="&$V", from_rust="$V.to_string()")
            if v == "unit":
                return Ty("()", "None")
            return None

        if kind == "borrowed_ref":
            # `&T` / `&mut T` where T is a wrapped type: borrow the pyclass
            # rather than cloning it. A pyclass *is* the owner of its Rust
            # value, so a shared or exclusive borrow through PyRef/PyRefMut
            # reaches the caller's own object -- and it does not require T:
            # Clone, which is what previously made every `&Geometry`,
            # `&Material`, `&Tape` argument unmappable and so hid every
            # general runner in the MC and NJOY crates behind their data model.
            if arg_position:
                borrowed = self._borrowed_wrapper(v)
                if borrowed is not None:
                    return borrowed
            if v.get("is_mutable"):
                # `&mut Self` in return position is the chaining half of a
                # builder. Python does not need the chain -- the wrapper is
                # mutable in place -- so the method is kept and its return
                # value dropped. A `&mut T` *argument* stays unmappable:
                # writes through it could not reach the caller's object.
                if (not arg_position and isinstance(v.get("type"), dict)
                        and v["type"].get("generic") == "Self"):
                    return Ty("()", "None", from_rust="{ let _ = $V; }")
                return None
            inner = self.map_type(v["type"], arg_position)
            if inner is None:
                return None
            if not arg_position:
                # returning a reference: hand back an owned clone
                return Ty(inner.py, inner.pyi,
                          from_rust=inner.from_rust("$V.clone()"))
            if inner.py == "String":
                return Ty(inner.py, inner.pyi, into_rust=inner.into_rust("$V"),
                          owned=False)
            if inner.owned:
                return Ty(inner.py, inner.pyi,
                          into_rust="&" + inner.into_rust("$V"), owned=False)
            return None

        if kind == "slice":
            inner = self.map_type(v, arg_position)
            if inner is None or inner.py == "()":
                return None
            return Ty("Vec<%s>" % inner.py, "list[%s]" % inner.pyi,
                      into_rust="$V.into_iter().map(|e| %s).collect::<Vec<_>>()"
                                % inner.into_rust("e"),
                      from_rust="$V.iter().cloned().map(|e| %s).collect::<Vec<_>>()"
                                % inner.from_rust("e"))

        if kind == "array":
            inner = self.map_type(v["type"], arg_position)
            if inner is None or inner.py == "()":
                return None
            if arg_position:
                # Deliberately not supported. A fixed-size array argument needs
                # a fallible length check, and `?` cannot appear inside the
                # closures the Vec/Option/tuple mappings generate, nor in a
                # setter or a field-wise constructor, which have nowhere to
                # return an error to. `[T; N]` arguments therefore stay in
                # `blocked.md` rather than being half-supported.
                return None
            return Ty("Vec<%s>" % inner.py, "list[%s]" % inner.pyi,
                      from_rust="$V.into_iter().map(|e| %s).collect::<Vec<_>>()"
                                % inner.from_rust("e"))

        if kind == "tuple":
            if not v:
                return Ty("()", "None")
            if len(v) > 4:
                return None
            parts = [self.map_type(x, arg_position) for x in v]
            if any(p is None for p in parts):
                return None
            py = "(%s)" % ", ".join(p.py for p in parts)
            pyi = "tuple[%s]" % ", ".join(p.pyi for p in parts)
            names = ["e%d" % i for i in range(len(parts))]
            frm = "{ let (%s) = $V; (%s) }" % (
                ", ".join(names),
                ", ".join(p.from_rust(n) for p, n in zip(parts, names)))
            into = "{ let (%s) = $V; (%s) }" % (
                ", ".join(names),
                ", ".join(p.into_rust(n) for p, n in zip(parts, names)))
            return Ty(py, pyi, into_rust=into, from_rust=frm)

        if kind == "impl_trait":
            return self._map_impl_trait(v, arg_position)

        if kind == "resolved_path":
            return self._map_path(v, arg_position)

        if kind == "generic":
            if v == "Self" and self.self_tid is not None:
                return self._wrapper_ty(self.self_tid, arg_position)
            if v in self.subst:
                return self.map_type(self.subst[v], arg_position)

        return None

    def _subst_type(self, t):
        """Apply the active type-parameter substitution to a rustdoc type."""
        if isinstance(t, dict):
            if set(t) == {"generic"} and t["generic"] in self.subst:
                return self.subst[t["generic"]]
            return {k: self._subst_type(x) for k, x in t.items()}
        if isinstance(t, list):
            return [self._subst_type(x) for x in t]
        return t

    def _map_impl_trait(self, bounds, arg_position):
        """`impl Into<String>` and friends, in argument position.

        Argument-position `impl Trait` is pervasive in this workspace --
        `VolField::zeros(name: impl Into<String>, ..)` is the shape that
        blocks every field constructor. Only conversion traits with a
        concrete target are handled, and only as arguments: `impl Trait` in
        return position names an unnameable type.
        """
        if not arg_position:
            return None
        traits = [b["trait_bound"]["trait"] for b in bounds
                  if isinstance(b, dict) and "trait_bound" in b]
        if len(traits) != 1:
            return None
        tr = traits[0]
        name = tr["path"].split("::")[-1]
        args = angle_args(tr)
        if name == "Into" and len(args) == 1:
            # `T: Into<T>` holds reflexively, so passing the target type
            # straight through always satisfies the bound.
            return self.map_type(args[0], True)
        if name == "AsRef" and len(args) == 1:
            a = args[0]
            if a == {"primitive": "str"}:
                return Ty("String", "str")
            p = self.m.paths.get(str(a.get("resolved_path", {}).get("id"))) \
                if isinstance(a, dict) and "resolved_path" in a else None
            if p and "::".join(p["path"]) == "std::path::Path":
                return Ty("String", "str",
                          into_rust="std::path::PathBuf::from($V)")
        return None

    def _borrowed_wrapper(self, ref):
        """`&T`/`&mut T` for a wrapped type, as a PyRef/PyRefMut parameter."""
        inner = ref.get("type")
        if not isinstance(inner, dict):
            return None
        ident = None
        if "resolved_path" in inner:
            rp = inner["resolved_path"]
            tid = str(rp["id"])
            if tid not in self.wrapped:
                alias = self.m.alias_by_inst.get(
                    (tid, _tykey([self._subst_type(a) for a in angle_args(rp)]))
                )
                if alias is not None:
                    tid = alias
            if tid in self.wrapped:
                ident = self.wrapped[tid][0]
                pyi = self.wrapped[tid][1]
            else:
                p = self.m.paths.get(str(rp["id"]))
                full = "::".join(p["path"]) if p else None
                g = self.registry.get(full) if full else None
                if g is not None and g["feature"] != self.feature:
                    self.needed.add(g["feature"])
                    ident = "crate::python::generated::%s::%s" % (g["crate"], g["ident"])
                    pyi = "%s.%s" % (g["crate"], g["pyname"])
        elif inner.get("generic") == "Self" and self.self_tid is not None:
            ident, pyi = self.wrapped[self.self_tid]
        if ident is None:
            return None
        if ref.get("is_mutable"):
            return Ty(
                "PyRefMut<'_, %s>" % ident, pyi,
                into_rust="&mut $V.inner", owned=False, param_prefix="mut ",
            )
        return Ty("PyRef<'_, %s>" % ident, pyi, into_rust="&$V.inner", owned=False)

    def _wrapper_ty(self, tid, arg_position=False):
        if tid not in self.wrapped:
            return None
        if arg_position and tid not in self.cloneable:
            return None
        ident, pyname = self.wrapped[tid]
        return Ty(ident, pyname,
                  into_rust="$V.inner",
                  from_rust="%s { inner: $V }" % ident)

    def _map_path(self, v, arg_position):
        p = self.m.paths.get(str(v["id"]))
        full = "::".join(p["path"]) if p else None
        if full is None:
            return None
        segs = p["path"]
        last = segs[-1]

        # uom quantities: represented as f64 in SI base units
        if len(segs) >= 3 and segs[0] == "uom" and segs[1] == "si" and segs[2] == "f64":
            return Ty("f64", "float",
                      into_rust="from_si($V)", from_rust="to_si($V)")

        if full in ("alloc::string::String", "std::string::String"):
            return Ty("String", "str")
        if full in ("std::path::PathBuf",):
            return Ty("String", "str",
                      into_rust="std::path::PathBuf::from($V)",
                      from_rust="$V.to_string_lossy().into_owned()")
        if full in ("std::path::Path",):
            return Ty("String", "str",
                      into_rust="std::path::Path::new(&$V)",
                      from_rust="$V.to_string_lossy().into_owned()", owned=False)

        if full in ("core::option::Option", "std::option::Option"):
            args = angle_args(v)
            if len(args) != 1:
                return None
            inner = self.map_type(args[0], arg_position)
            if inner is None:
                return None
            # `Option<&mut T>` / `Option<&T>` over a wrapped type. The borrow
            # has to be taken from inside the Option, which needs a binding
            # rather than an expression -- hence the block. This is the shape
            # of an optional out-parameter (`tally: Option<&mut Tally>`), and
            # without it every runner carrying one stays invisible.
            if arg_position and inner.py.startswith(("PyRefMut<", "PyRef<")):
                # The borrow must outlive the call, so it is taken from the
                # parameter itself rather than from a `let` inside a block --
                # a block-local binding is dropped at the closing brace, while
                # the borrow is still live in the enclosing call.
                mutable = inner.py.startswith("PyRefMut<")
                return Ty(
                    "Option<%s>" % inner.py, "%s | None" % inner.pyi,
                    into_rust=("$V.as_mut().map(|r| &mut r.inner)" if mutable
                               else "$V.as_ref().map(|r| &r.inner)"),
                    owned=False, param_prefix="mut " if mutable else "",
                )
            if not inner.owned or inner.py == "()":
                return None
            return Ty("Option<%s>" % inner.py, "%s | None" % inner.pyi,
                      into_rust="$V.map(|e| %s)" % inner.into_rust("e"),
                      from_rust="$V.map(|e| %s)" % inner.from_rust("e"))

        if full in ("alloc::vec::Vec", "std::vec::Vec"):
            args = angle_args(v)
            if len(args) != 1:
                return None
            inner = self.map_type(args[0], arg_position)
            if inner is None or not inner.owned or inner.py == "()":
                return None
            return Ty("Vec<%s>" % inner.py, "list[%s]" % inner.pyi,
                      into_rust="$V.into_iter().map(|e| %s).collect::<Vec<_>>()"
                                % inner.into_rust("e"),
                      from_rust="$V.into_iter().map(|e| %s).collect::<Vec<_>>()"
                                % inner.from_rust("e"))

        if full in ("alloc::sync::Arc", "std::sync::Arc",
                    "alloc::rc::Rc", "std::rc::Rc"):
            args = angle_args(v)
            if len(args) != 1:
                return None
            inner = self.map_type(args[0], arg_position)
            if inner is None or not inner.owned:
                return None
            # Python has no shared-ownership handle to hand back, so the
            # value is cloned into a fresh Arc on the way in and out of the
            # refcount on the way out. For a large mesh that is a real copy.
            ctor = "Arc" if "Arc" in full else "Rc"
            return Ty(inner.py, inner.pyi,
                      into_rust="std::sync::%s::new(%s)"
                                % (ctor, inner.into_rust("$V"))
                                if ctor == "Arc" else
                                "std::rc::Rc::new(%s)" % inner.into_rust("$V"),
                      from_rust=inner.from_rust("(*$V).clone()"))

        if full in ("core::result::Result", "std::result::Result"):
            if arg_position:
                return None
            args = angle_args(v)
            ok = self.map_type(args[0], False) if args else Ty("()", "None")
            if ok is None:
                return None
            return Ty("PyResult<%s>" % ok.py, ok.pyi,
                      from_rust="err($V).map(|v| %s)" % ok.from_rust("v"))

        # a local type with a wrapper
        tid = str(v["id"])
        if tid not in self.wrapped:
            # Resolve type parameters first: inside `VolField<T>` the field
            # `internal: Field<T>` must be looked up as `Field<f64>` for the
            # `ScalarField` alias to match.
            key = _tykey([self._subst_type(a) for a in angle_args(v)])
            alias = self.m.alias_by_inst.get((tid, key))
            if alias is not None:
                tid = alias
        local = self._wrapper_ty(tid, arg_position)
        if local is not None:
            return local
        if tid in self.m.alias_target and tid not in self.wrapped:
            return self.map_type(self.m.alias_target[tid], arg_position)
        if tid in self.m.generic_alias and tid not in self.wrapped:
            names, target = self.m.generic_alias[tid]
            supplied = angle_args(v)
            saved = self.subst
            self.subst = dict(saved)
            self.subst.update(dict(zip(names, supplied)))
            try:
                return self.map_type(target, arg_position)
            finally:
                self.subst = saved
        if p["crate_id"] != 0:
            return self._foreign_ty(full, arg_position)
        return None

    def _foreign_ty(self, full, arg_position):
        """A type wrapped by another crate's generated module."""
        g = self.registry.get(full)
        if g is None or g["feature"] == self.feature:
            return None
        if arg_position and not g["cloneable"]:
            return None
        self.needed.add(g["feature"])
        rust = "crate::python::generated::%s::%s" % (g["crate"], g["ident"])
        return Ty(rust, "%s.%s" % (g["crate"], g["pyname"]),
                  into_rust="$V.inner",
                  from_rust="%s { inner: $V }" % rust)

    def _cfg(self):
        """A `#[cfg]` gating the current item on the crates it borrows types
        from, so a partial feature selection still compiles."""
        if not self.needed:
            return None
        feats = sorted(self.needed)
        if len(feats) == 1:
            return '#[cfg(feature = "%s")]' % feats[0]
        return "#[cfg(all(%s))]" % ", ".join('feature = "%s"' % f for f in feats)

    # -- emission -----------------------------------------------------

    def mark(self, key):
        self.markers.append((len(self.lines), key))
        self.lines.append("    // @item %s" % key)

    def w(self, s=""):
        self.lines.append(s)

    def _fn_sig(self, item_id, self_kind_allowed):
        """Return (receiver, params, body_args, ret) or None if unmappable."""
        it = self.m.index[item_id]
        self._reporting_item = "%s::%s" % (
            self.m.crate_name, it.get("name") or "?"
        )
        fn = it["inner"]["function"]
        if not self.m._generic_free(fn.get("generics", {})):
            return None
        if fn["header"].get("is_unsafe") or fn["header"].get("is_async"):
            return None
        if fn["header"].get("abi") not in ("Rust", None):
            return None
        sig = fn["sig"]
        if sig.get("is_c_variadic"):
            return None

        receiver = None
        fallible_args = False
        params, call_args, pyi_args = [], [], []
        for i, (aname, aty) in enumerate(sig["inputs"]):
            if i == 0 and aname == "self":
                k = next(iter(aty)) if isinstance(aty, dict) else None
                if k == "borrowed_ref":
                    receiver = "&mut self" if aty[k].get("is_mutable") else "&self"
                    recv_expr = "&mut self.inner" if aty[k].get("is_mutable") else "&self.inner"
                elif k == "generic" and aty[k] == "Self":
                    if self.self_tid not in self.cloneable:
                        return None
                    receiver, recv_expr = "&self", "self.inner.clone()"
                else:
                    return None
                if not self_kind_allowed:
                    return None
                continue
            ty = self.map_type(aty, True)
            if ty is None:
                self.blocked.append(
                    (self._reporting_item, aname, describe_type(aty, self.m.paths))
                )
                return None
            pname = aname if aname not in PY_KEYWORDS else aname + "_"
            pname = self.rust_ident(self._ident(pname)) or "arg%d" % i
            params.append("%s%s: %s" % (ty.param_prefix, pname, ty.py))
            if ty.fallible:
                fallible_args = True
            call_args.append(ty.into_rust(pname))
            pyi_args.append("%s: %s" % (pname, ty.pyi))

        out = sig.get("output")
        if out is None:
            ret = Ty("()", "None")
        else:
            ret = self.map_type(out, False)
            if ret is None:
                self.blocked.append(
                    (self._reporting_item, "-> return",
                     describe_type(out, self.m.paths))
                )
                return None
        if fallible_args and not ret.py.startswith("PyResult<"):
            # An argument conversion that can fail needs somewhere to fail to.
            ret = Ty("PyResult<%s>" % ret.py, ret.pyi,
                     from_rust="Ok(%s)" % ret.from_rust("$V"))
        return receiver, locals().get("recv_expr"), params, call_args, pyi_args, ret

    def emit_type(self, tid):
        t = self.m.types[tid]
        ident, pyname = self.wrapped[tid]
        tr = self.m.traits[t.get("target", tid)]
        self.self_tid = tid
        self.mark("type:" + t["path"])
        self.w('#[doc = "%s"]' % rustdoc_str(t["docs"], 1500))
        self.w('#[pyclass(name = "%s", module = "outram_park.%s")]'
               % (pyname, self.m.crate_name))
        if tid in self.cloneable:
            self.w("#[derive(Clone)]")
        self.w("pub struct %s { pub inner: ::%s }" % (ident, t["path"]))
        self.w("#[pymethods]")
        self.w("impl %s {" % ident)

        base = self.m.generic_types.get(t.get("target"))
        self.subst = dict(zip(base["params"], t["args"])) if base else {}

        seen = set()        # Python-visible names already taken
        rust_names = set()  # Rust fn idents in this impl block, which must
                            # not collide with the get_/set_ field accessors
        have_new = False
        field_ctor = []     # None once any field is unusable as a ctor arg
        ctor_needed = set() # features the field-wise constructor depends on
        # public fields -> getters/setters
        if t["kind"] == "struct":
            plain = t["inner"]["kind"].get("plain") if isinstance(t["inner"]["kind"], dict) else None
            if (plain or {}).get("has_stripped_fields"):
                field_ctor = None
            for fid in (plain or {}).get("fields", []):
                fi = self.m.index.get(str(fid))
                if not fi or fi.get("visibility") != "public":
                    field_ctor = None
                    continue
                fname = fi["name"]
                self.needed = set()
                if "field:%s::%s" % (t["path"], fname) in self.skip:
                    field_ctor = None
                    continue
                fty = self.map_type(fi["inner"]["struct_field"], False)
                fty_in = self.map_type(fi["inner"]["struct_field"], True)
                usable = (fty is not None and not fty.py.startswith("PyResult")
                          and fname not in PY_KEYWORDS and fname not in seen)
                settable = usable and fty_in is not None and fty_in.owned
                if not settable:
                    # a field the constructor cannot supply means the struct
                    # cannot be built literally at all
                    field_ctor = None
                if not usable:
                    continue
                seen.add(fname)
                rust_names.add("get_" + fname)
                self.mark("field:%s::%s" % (t["path"], fname))
                cfg = self._cfg()
                if cfg:
                    self.w("    " + cfg)
                self.w('    #[getter(%s)]' % fname)
                self.w("    pub fn get_%s(&self) -> %s { let v = self.inner.%s.clone(); %s }"
                       % (fname, fty.py, fname, fty.from_rust("v")))
                if settable:
                    rust_names.add("set_" + fname)
                    if cfg:
                        self.w("    " + cfg)
                    self.w('    #[setter(%s)]' % fname)
                    self.w("    pub fn set_%s(&mut self, v: %s) { self.inner.%s = %s; }"
                           % (fname, fty_in.py, fname, fty_in.into_rust("v")))
                    if field_ctor is not None:
                        field_ctor.append((fname, fty_in))
                        ctor_needed |= self.needed
                self.pyi.append(("    %s: %s" % (fname, fty.pyi), pyname))

        for item_id, msubst in self._methods_for(t, tid):
            self.subst = msubst
            it = self.m.index[item_id]
            name = it["name"]
            key = "method:%s::%s" % (t["path"], name)
            if key in self.skip or name in seen or name in rust_names:
                continue
            if name in PY_KEYWORDS or name.startswith("__"):
                continue
            self.needed = set()
            got = self._fn_sig(item_id, True)
            if got is None:
                self.stats["methods_skipped"] += 1
                continue
            receiver, recv_expr, params, call_args, pyi_args, ret = got
            seen.add(name)
            rust_names.add(name)
            self.stats["methods"] += 1
            self.mark(key)
            cfg = self._cfg()
            if cfg:
                self.w("    " + cfg)
            self.w('    #[doc = "%s"]' % rustdoc_str(it.get("docs"), 1200))
            if receiver is None:
                # `new` returning Self (or Result<Self, _>) becomes the
                # Python constructor, so `Foo(...)` works as it reads;
                # every other associated function stays a staticmethod.
                is_ctor = (name == "new" and not have_new
                           and ret.py in (ident, "PyResult<%s>" % ident))
                if is_ctor:
                    self.w("    #[new]")
                    have_new = True
                else:
                    self.w("    #[staticmethod]")
                call = "::%s::%s(%s)" % (t["path"], name, ", ".join(call_args))
                sigparams = params
                pyi_sig = pyi_args
            else:
                is_ctor = False
                call = "::%s::%s(%s)" % (t["path"], name,
                                         ", ".join([recv_expr] + call_args))
                sigparams = [receiver] + params
                pyi_sig = ["self"] + pyi_args
            rname = self.rust_ident(name)
            if rname != name:
                self.w('    #[pyo3(name = "%s")]' % name)
            self.w("    pub fn %s(%s) -> %s { %s }"
                   % (rname, ", ".join(sigparams), ret.py, ret.from_rust(call)))
            if is_ctor:
                stub = "    def __init__(self, %s) -> None: ..." % ", ".join(pyi_args)
            elif receiver is None:
                stub = ("    @staticmethod\n    def %s(%s) -> %s: ..."
                        % (name, ", ".join(pyi_sig), ret.pyi))
            else:
                stub = ("    def %s(%s) -> %s: ..."
                        % (name, ", ".join(pyi_sig), ret.pyi))
            self.pyi.append((stub, pyname))

        if t["kind"] == "enum":
            self.emit_variants(t, ident, seen)
        elif not have_new and field_ctor and ("ctor:" + t["path"]) not in self.skip:
            # an all-public-fields struct with no `new`: build it literally,
            # so the Python constructor mirrors the struct definition
            self.mark("ctor:" + t["path"])
            self.needed = set(ctor_needed)
            have_new = True
            cfg = self._cfg()
            if cfg:
                self.w("    " + cfg)
            self.w("    #[new]")
            if "Default" in tr:
                # The type has a Default, so every field is optional and
                # `Foo()` means "all defaults" while `Foo(delta_t=1e-4)`
                # overrides one. Requiring all thirteen fields of a
                # ControlDict positionally would make the class unusable.
                self.w("    #[pyo3(signature = (%s))]"
                       % ", ".join("%s=None" % n for n, _ in field_ctor))
                # A field that is *already* `Option<T>` is passed at one
                # level, not two: `Option<Option<T>>` leaves pyo3 unable to
                # tell which layer the `None` default belongs to. Omitting
                # such an argument means "keep the default"; setting it to
                # `None` explicitly is what the field's setter is for.
                self.w("    pub fn __new__(%s) -> Self {"
                       % ", ".join(
                           "%s: %s" % (n, ty.py if ty.py.startswith("Option<")
                                       else "Option<%s>" % ty.py)
                           for n, ty in field_ctor))
                self.w("        let d = <::%s as Default>::default();" % t["path"])
                self.w("        Self { inner: ::%s {" % t["path"])
                for n, ty in field_ctor:
                    if ty.py.startswith("Option<"):
                        self.w("            %s: { let v = %s; "
                               "if v.is_some() { v } else { d.%s } },"
                               % (n, ty.into_rust(n), n))
                    else:
                        self.w("            %s: %s.map(|v| %s).unwrap_or(d.%s),"
                               % (n, n, ty.into_rust("v"), n))
                self.w("        } }")
                self.w("    }")
                self.pyi.append(("    def __init__(self, %s) -> None: ..."
                                 % ", ".join(
                                     "%s: %s = None"
                                     % (n, ty.pyi if ty.pyi.endswith("| None")
                                        else "%s | None" % ty.pyi)
                                     for n, ty in field_ctor), pyname))
            else:
                self.w("    pub fn __new__(%s) -> Self { Self { inner: ::%s { %s } } }"
                       % (", ".join("%s: %s" % (n, ty.py) for n, ty in field_ctor),
                          t["path"],
                          ", ".join("%s: %s" % (n, ty.into_rust(n))
                                    for n, ty in field_ctor)))
                self.pyi.append(("    def __init__(self, %s) -> None: ..."
                                 % ", ".join("%s: %s" % (n, ty.pyi)
                                             for n, ty in field_ctor), pyname))

        if not have_new and "Default" in tr and t["kind"] == "struct":
            # A type whose fields cannot all be exposed still deserves a
            # constructor if it has a Default -- otherwise `FvSolution()` is
            # a TypeError and the caller has to know to say
            # `FvSolution.default()`.
            self.mark("defaultctor:" + t["path"])
            self.needed = set()
            have_new = True
            self.w("    #[new]")
            self.w("    pub fn __new__() -> Self { Self { inner: Default::default() } }")
            self.pyi.append(("    def __init__(self) -> None: ...", pyname))

        if "Debug" in tr and "__repr__" not in seen:
            self.w('    pub fn __repr__(&self) -> String { format!("{:?}", self.inner) }')
        if "Display" in tr and "__str__" not in seen:
            self.w('    pub fn __str__(&self) -> String { format!("{}", self.inner) }')
        if "PartialEq" in tr:
            self.w("    pub fn __eq__(&self, other: &Self) -> bool { self.inner == other.inner }")
        if "Default" in tr and "default" not in seen:
            self.w("    #[staticmethod]")
            self.w("    pub fn default() -> Self { Self { inner: Default::default() } }")
            self.pyi.append(("    @staticmethod\n    def default() -> %s: ..." % pyname, pyname))
        self.w("}")
        self.w()
        self.registrations.append("    m.add_class::<%s>()?;" % ident)
        self.stats["types"] += 1
        self.self_tid = None
        self.subst = {}

    def _methods_for(self, t, tid):
        """[(fn id, substitution)] for one wrapped type.

        A plain type has no substitution. An alias contributes the target's
        inherent impls, each matched against the alias's concrete arguments:
        `impl<T: Clone> VolField<T>` under `VolField<f64>` yields `T -> f64`,
        while `impl VolField<Vector3>` is skipped for that alias.
        """
        target = t.get("target")
        if target is None:
            return [(i, {}) for i in self.m.inherent[tid]]
        out = []
        for for_args, fns in self.m.impl_records[target]:
            sub = self._match_args(for_args, t["args"])
            if sub is None:
                continue
            out.extend((f, sub) for f in fns)
        return out

    @staticmethod
    def _match_args(for_args, alias_args):
        """Unify an impl's `for` arguments with an alias's concrete ones."""
        if len(for_args) != len(alias_args):
            return None
        sub = {}
        for fa, aa in zip(for_args, alias_args):
            if isinstance(fa, dict) and set(fa) == {"generic"}:
                name = fa["generic"]
                if sub.get(name, aa) != aa:
                    return None
                sub[name] = aa
            elif fa != aa:
                return None
        return sub

    def emit_variants(self, t, ident, seen):
        """Give an enum a constructor per variant, plus `variant()`.

        Without this an enum wrapper is unreachable from Python: nothing
        else in the generated surface can produce one. The match arm for a
        variant is emitted whether or not its constructor is -- a skipped
        arm makes `variant()` non-exhaustive and fails the whole crate.
        """
        pyname = self.wrapped[t["id"]][1]
        arms = []
        for vid in t["inner"].get("variants", []):
            vi = self.m.index.get(str(vid))
            if not vi:
                continue
            vname = vi["name"]
            vk = vi["inner"]["variant"]["kind"]
            vpath = "::%s::%s" % (t["path"], vname)

            if vk == "plain":
                arms.append('%s => "%s"' % (vpath, vname))
                fields = []
            elif isinstance(vk, dict) and "tuple" in vk:
                arms.append('%s(..) => "%s"' % (vpath, vname))
                fields = self._variant_fields(
                    [(None, f) for f in vk["tuple"]], vk)
            elif isinstance(vk, dict) and "struct" in vk:
                arms.append('%s { .. } => "%s"' % (vpath, vname))
                fields = self._variant_fields(
                    [(True, f) for f in vk["struct"].get("fields", [])], vk["struct"])
            else:
                continue

            if fields is None or (
                    "variant:%s::%s" % (t["path"], vname)) in self.skip:
                continue
            # `None`, `True`, `type` ... are legal Rust variant names but not
            # legal Python attribute names, so the constructor gets a
            # trailing underscore rather than being dropped.
            py_ctor = vname + "_" if vname in PY_KEYWORDS else vname
            if py_ctor in seen:
                continue
            seen.add(py_ctor)
            self.mark("variant:%s::%s" % (t["path"], vname))
            self.w("    #[staticmethod]")
            self.w('    #[pyo3(name = "%s")]' % py_ctor)
            named = isinstance(vk, dict) and "struct" in vk
            if not fields:
                build = vpath
            elif named:
                build = "%s { %s }" % (
                    vpath, ", ".join("%s: %s" % (n, ty.into_rust(self.rust_ident(n)))
                                     for n, ty in fields))
            else:
                build = "%s(%s)" % (
                    vpath, ", ".join(ty.into_rust(self.rust_ident(n))
                                     for n, ty in fields))
            self.w("    pub fn v_%s(%s) -> Self { Self { inner: %s } }"
                   % (self._ident(vname),
                      ", ".join("%s: %s" % (self.rust_ident(n), ty.py)
                                for n, ty in fields),
                      build))
            self.pyi.append(("    @staticmethod\n    def %s(%s) -> %s: ..."
                             % (py_ctor,
                                ", ".join("%s: %s" % (n, ty.pyi) for n, ty in fields),
                                pyname), pyname))

        if arms and "variant" not in seen:
            self.w("    /// The name of the enum variant this value holds.")
            self.w("    pub fn variant(&self) -> &'static str {")
            self.w('        match &self.inner { %s, _ => "unknown" }' % ", ".join(arms))
            self.w("    }")
            self.pyi.append(("    def variant(self) -> str: ...", pyname))

    def _variant_fields(self, entries, container):
        """[(name, Ty)] for a variant's payload, or None if any field is
        unusable -- a partially-built variant is not constructible."""
        if container.get("has_stripped_fields"):
            return None
        out = []
        for i, (named, fid) in enumerate(entries):
            fi = self.m.index.get(str(fid))
            if not fi:
                return None
            ty = self.map_type(fi["inner"]["struct_field"], True)
            if ty is None or not ty.owned:
                return None
            out.append((fi["name"] if named else "a%d" % i, ty))
        return out

    def emit_free_fn(self, item_id):
        it = self.m.index[item_id]
        path = self.m.rust_path(item_id)
        key = "fn:" + path
        if key in self.skip:
            return
        self.needed = set()
        got = self._fn_sig(item_id, False)
        if got is None:
            self.stats["fns_skipped"] += 1
            return
        _, _, params, call_args, pyi_args, ret = got
        ident = "fn_" + self._ident(path)
        ident = self.rust_ident(ident)
        self.mark(key)
        cfg = self._cfg()
        if cfg:
            self.w(cfg)
        self.w('#[doc = "%s"]' % rustdoc_str(it.get("docs"), 1200))
        self.w('#[pyfunction(name = "%s")]' % it["name"])
        self.w("pub fn %s(%s) -> %s { %s }"
               % (ident, ", ".join(params), ret.py,
                  ret.from_rust("::%s(%s)" % (path, ", ".join(call_args)))))
        self.w()
        self.registrations.append(
            ("    %s\n" % cfg if cfg else "")
            + "    m.add_function(wrap_pyfunction!(%s, m)?)?;" % ident)
        self.pyi.append(("def %s(%s) -> %s: ..."
                         % (it["name"], ", ".join(pyi_args), ret.pyi), None))
        self.stats["fns"] += 1

    def emit_const(self, item_id):
        it = self.m.index[item_id]
        path = self.m.rust_path(item_id)
        key = "const:" + path
        if key in self.skip:
            return
        ty = self.map_type(it["inner"]["constant"]["type"], False)
        if ty is None or ty.py not in ("f64", "f32", "bool", "String") and ty.py not in INT_PRIMS:
            return
        self.mark(key)
        self.registrations.append(
            '    m.add("%s", %s)?;' % (it["name"], ty.from_rust("::" + path)))
        self.pyi.append(("%s: %s" % (it["name"], ty.pyi), None))
        self.stats["consts"] += 1

    def run(self):
        self.w("// @generated by codegen/gen_bindings.py from rustdoc JSON -- DO NOT EDIT.")
        self.w("//! Python bindings for the `%s` backend crate." % self.m.crate_name)
        self.w("#![allow(non_snake_case, non_camel_case_types, unused_imports,")
        self.w("         unreachable_patterns, clippy::all)]")
        self.w("use pyo3::prelude::*;")
        self.w("use crate::python::runtime::{err, from_si, to_si};")
        self.w()
        for tid in sorted(self.wrapped, key=lambda t: self.m.types[t]["path"]):
            self.emit_type(tid)
        for fid in sorted(self.m.free_fns, key=lambda i: self.m.rust_path(i) or ""):
            self.emit_free_fn(fid)
        for cid in sorted(self.m.consts, key=lambda i: self.m.rust_path(i) or ""):
            self.emit_const(cid)
        self.w("pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {")
        self.lines.extend(self.registrations)
        self.w("    Ok(())")
        self.w("}")
        return "\n".join(self.lines) + "\n"


def crate_files():
    out = {}
    feats = open(os.path.join(HERE, "crates.txt")).read().split()
    for f in feats:
        snake = f.replace("-", "_")
        p = os.path.join(DOC_DIR, snake + ".json")
        if os.path.exists(p):
            out[f] = (snake, p)
        else:
            print("warning: no rustdoc JSON for %s" % f, file=sys.stderr)
    return out


def write_stub(path, snake, em):
    """Write the `.pyi` for one backend submodule.

    Shipped in the wheel next to the extension module, so an editor -- or a
    model reading the package -- can see the whole surface without the Rust
    source.
    """
    classes, module_level = [], []
    for line, owner in em.pyi:
        if owner is None:
            module_level.append(line)
        else:
            if not classes or classes[-1][0] != owner:
                classes.append((owner, []))
            classes[-1][1].append(line)
    with open(path, "w") as f:
        f.write('"""Type stubs for `outram_park.%s`, generated from the '
                'Rust API.\n\nPhysical quantities cross this boundary as '
                '`float` in SI base units.\n"""\n' % snake)
        for name, members in classes:
            f.write("\nclass %s:\n" % name)
            if not members:
                f.write("    ...\n")
            for m in members:
                f.write(m + "\n")
        if module_level:
            f.write("\n")
            for m in module_level:
                f.write(m + "\n")


def rustfmt(_directory):
    """Format the crate, as the last step of generation.

    The emitter writes one statement per line with no regard for width, which
    is fine for a machine and unreadable when a signature has to be inspected
    -- and it leaves `cargo fmt --check` permanently red on the workspace.

    Deliberately `cargo fmt` rather than a bare `rustfmt`: cargo resolves the
    edition and the workspace `rustfmt.toml` for us, and a bare invocation
    guessing at `--edition` disagrees with the very command CI runs (2021 puts
    a lone `) -> T` on its own line, 2024 does not). Two passes because
    rustfmt is not idempotent on some of the nested blocks emitted here.

    Not fatal on failure: unformatted bindings still compile, and a missing or
    unhappy rustfmt should not fail a generation run.
    """
    for _ in range(2):
        r = subprocess.run(["cargo", "fmt", "-p", "outram-park"],
                           cwd=CRATE_ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print("warning: `cargo fmt` on the generated tree failed:\n%s"
                  % r.stderr.strip()[:500], file=sys.stderr)
            return


def write_blocked_report(blocked):
    """Write `blocked.md`: which unmapped types cost the most API surface.

    Coverage counts say *how much* was dropped; this says *why*, ranked, with
    examples. The distinction matters. Every binding gap found by dogfooding
    the wheel so far -- `&Geometry` on the MC runners, `&Tape` on RECONR,
    `Option<&mut Tally>`, the `uom` aliases -- was a handful of type shapes
    blocking dozens of items, and each was obvious the moment the shapes were
    counted rather than hunted for one function at a time.
    """
    from collections import Counter, defaultdict

    counts = Counter(ty for _f, _i, _w, ty in blocked)
    examples = defaultdict(list)
    crates = defaultdict(set)
    for feat, item, where, ty in blocked:
        crates[ty].add(feat)
        if len(examples[ty]) < 4:
            examples[ty].append("%s (%s)" % (item, where))

    with open(os.path.join(HERE, "blocked.md"), "w") as f:
        f.write("# What the bindings could not express\n\n")
        f.write("Generated by `codegen/gen_bindings.py`; regenerated on every "
                "full run.\n\nEach row is a Rust type shape that stopped at "
                "least one item from reaching Python, ranked by how many. Fixing "
                "the top of this list is the cheapest way to widen the API.\n\n")
        f.write("A shape is fixed in one of two places, and the report cannot "
                "tell you which:\n\n")
        f.write("- **In the generator**, when the shape *has* a faithful Python "
                "representation and simply is not mapped yet (`&T` via `PyRef`, "
                "`Option<&mut T>`, `uom` aliases).\n")
        f.write("- **In the backend**, when it does not (`&[T]` needs `T: Clone`; "
                "a generic `fn f<R: Read>` needs a concrete seam beside it). The "
                "generator cannot add a derive or monomorphise a type parameter.\n\n")
        f.write("| items | type | crates | examples |\n|---:|---|---:|---|\n")
        for ty, n in counts.most_common(60):
            f.write("| %d | `%s` | %d | %s |\n"
                    % (n, ty.replace("|", "\\|"), len(crates[ty]),
                       "; ".join(examples[ty])))
        f.write("\nTotal blocked signatures: %d, over %d distinct type shapes.\n"
                % (len(blocked), len(counts)))


def write_package(mods):
    """Write the Python package that carries the extension module."""
    init = os.path.join(STUB_DIR, "__init__.py")
    with open(init, "w") as f:
        f.write('"""outram-park: the outram-park-backend simulation API, in Python.\n\n'
                'One submodule per backend crate -- see `backends()` for the list\n'
                'compiled into this build. Physical quantities are plain `float`s in\n'
                'SI base units (kelvin, pascal, metre, second, watt, kilogram).\n"""\n\n')
        f.write("from .outram_park import *  # noqa: F401,F403\n")
        f.write("from .outram_park import backends, version  # noqa: F401\n\n")
        f.write("__all__ = [\"backends\", \"version\"] + list(backends())\n")
    open(os.path.join(STUB_DIR, "py.typed"), "w").close()
    with open(os.path.join(STUB_DIR, "__init__.pyi"), "w") as f:
        f.write('"""Type stubs for the `outram_park` package."""\n\n')
        for _, snake in mods:
            f.write("from . import %s as %s\n" % (snake, snake))
        f.write("\ndef version() -> str: ...\n")
        f.write("def backends() -> list[str]: ...\n")


def main():
    skip = set()
    if os.path.exists(SKIP_FILE):
        skip = set(json.load(open(SKIP_FILE)))
    only = sys.argv[1:] or None
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(STUB_DIR, exist_ok=True)
    crates = crate_files()

    # Pass 1: plan every crate, so each one's emitter can resolve types that
    # live in a sibling crate. Solver signatures are full of them --
    # `PimpleFoam::new(mesh: Arc<FvMesh>, ..)` names a type from
    # outram-foam-basic-lib -- and without a shared registry they are simply
    # dropped, which is what left the solvers undrivable from Python.
    planned, registry = {}, {}
    for feat, (snake, path) in sorted(crates.items()):
        model = CrateModel(path)
        em = Emitter(model, skip, registry, feat)
        em.plan_types()
        planned[feat] = (snake, model, em)
        for tid, (ident, pyname) in em.wrapped.items():
            entry = {
                "crate": snake, "feature": feat, "ident": ident,
                "pyname": pyname, "cloneable": tid in em.cloneable,
            }
            # Register under both the re-exported path this crate documents
            # and rustdoc's definition path: a consuming crate resolves the
            # type through its own `paths` table, which records where the
            # type was *defined*, not where it is re-exported.
            keys = {model.types[tid]["path"]}
            defn = model.paths.get(str(tid))
            if defn:
                keys.add("::".join(defn["path"]))
            for key in keys:
                registry.setdefault(key, entry)

    mods, report, blocked = [], {}, []
    for feat, (snake, model, em) in sorted(planned.items()):
        if only and feat not in only:
            continue
        src = em.run()
        with open(os.path.join(OUT_DIR, snake + ".rs"), "w") as f:
            f.write(src)
        mods.append((feat, snake))
        report[feat] = dict(em.stats)
        blocked.extend((feat, item, where, ty) for item, where, ty in em.blocked)
        write_stub(os.path.join(STUB_DIR, snake + ".pyi"), snake, em)
        print("%-45s types=%-5d methods=%-6d fns=%-5d consts=%d"
              % (feat, em.stats["types"], em.stats["methods"],
                 em.stats["fns"], em.stats["consts"]))

    if not only:
        # a single-crate run would otherwise truncate the report to that
        # one crate, and the stale file reads as a real coverage collapse
        with open(os.path.join(HERE, "coverage.json"), "w") as f:
            json.dump(report, f, indent=1, sort_keys=True)
        write_blocked_report(blocked)
        write_package(mods)
        with open(os.path.join(OUT_DIR, "mod.rs"), "w") as f:
            f.write("// @generated by codegen/gen_bindings.py -- DO NOT EDIT.\n")
            f.write("//! One module per backend crate, each gated on that crate's feature.\n\n")
            for feat, snake in mods:
                f.write('#[cfg(feature = "%s")]\npub mod %s;\n' % (feat, snake))
            f.write("\nuse pyo3::prelude::*;\n\n")
            f.write("/// The backend crates compiled into this build, as submodule names.\n")
            f.write("pub const BACKENDS: &[&str] = &[\n")
            for feat, snake in mods:
                f.write('    #[cfg(feature = "%s")]\n    "%s",\n' % (feat, snake))
            f.write("];\n\n")
            f.write("/// Registers one Python submodule per enabled backend crate.\n")
            f.write("pub fn register_all(py: Python<'_>, root: &Bound<'_, PyModule>) -> PyResult<()> {\n")
            f.write("    let sys = py.import(\"sys\")?;\n")
            f.write("    let sysmods = sys.getattr(\"modules\")?;\n")
            for feat, snake in mods:
                f.write('    #[cfg(feature = "%s")] {\n' % feat)
                f.write('        let sub = PyModule::new(py, "%s")?;\n' % snake)
                f.write('        %s::register(&sub)?;\n' % snake)
                f.write('        root.add_submodule(&sub)?;\n')
                f.write('        sysmods.set_item("outram_park.%s", &sub)?;\n' % snake)
                f.write("    }\n")
            f.write("    Ok(())\n}\n")
        # Last, so `mod.rs` above is formatted along with everything else.
        rustfmt(OUT_DIR)


if __name__ == "__main__":
    main()
