#!/usr/bin/env python3
"""Compile the generated bindings and blacklist whatever does not build.

`gen_bindings.py` decides what to emit from rustdoc's view of the API,
which is close to but not identical to rustc's: a trait bound rustdoc does
not record, a re-export path that is not importable, an inherent name that
collides after macro expansion. Rather than trying to model all of that
statically, this compiles the result, maps each error back to the `// @item`
marker above it, records that item in `skip.json`, regenerates, and repeats
until the build is clean.

Usage: python3 repair.py [max_passes]
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CRATE = os.path.dirname(HERE)
GEN = os.path.join(CRATE, "src", "python", "generated")
SKIP_FILE = os.path.join(HERE, "skip.json")
FEATURES = "python,all-backends"


def load_skip():
    if os.path.exists(SKIP_FILE):
        return set(json.load(open(SKIP_FILE)))
    return set()


def save_skip(skip):
    with open(SKIP_FILE, "w") as f:
        json.dump(sorted(skip), f, indent=0)


def markers(path):
    """[(line_no, key)] for one generated file, ascending."""
    out = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            m = re.search(r"// @item (\S+)", line)
            if m:
                out.append((i, m.group(1)))
    return out


def regenerate():
    subprocess.run([sys.executable, os.path.join(HERE, "gen_bindings.py")],
                   check=True, stdout=subprocess.DEVNULL)


def compile_once():
    """Run cargo check, returning [(file, line, message)] for each error."""
    p = subprocess.run(
        ["cargo", "check", "--no-default-features", "--features", FEATURES,
         "--lib", "--message-format=json"],
        cwd=CRATE, capture_output=True, text=True)
    errors = []
    for line in p.stdout.splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("reason") != "compiler-message":
            continue
        m = msg["message"]
        if m.get("level") != "error":
            continue
        placed = False
        for sp in m.get("spans", []):
            if "src/python/generated/" in sp["file_name"]:
                errors.append((sp["file_name"], sp["line_start"],
                               m.get("message", "")))
                placed = True
        if not placed:
            for sp in m.get("spans", []):
                for exp in [sp.get("expansion") or {}]:
                    s = exp.get("span") or {}
                    if "src/python/generated/" in (s.get("file_name") or ""):
                        errors.append((s["file_name"], s["line_start"],
                                       m.get("message", "")))
                        placed = True
        if not placed and m.get("message"):
            errors.append((None, None, m["message"]))
    return errors


def main():
    max_passes = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    skip = load_skip()
    cache = {}
    for p in range(1, max_passes + 1):
        errors = compile_once()
        if not errors:
            print("pass %d: clean (%d items blacklisted in total)" % (p, len(skip)))
            return 0
        added, unplaced = set(), []
        for fname, line, text in errors:
            if fname is None:
                unplaced.append(text)
                continue
            # cargo reports paths relative to the workspace root, not the
            # crate, so anchor on the generated directory instead
            full = os.path.join(GEN, os.path.basename(fname))
            if full not in cache:
                cache[full] = markers(full)
            key = None
            for ln, k in cache[full]:
                if ln <= line:
                    key = k
                else:
                    break
            if key and key not in skip:
                added.add(key)
            elif key is None:
                unplaced.append("%s:%s %s" % (fname, line, text))
        with open(os.path.join(HERE, "errors-pass%d.log" % p), "w") as f:
            for fname, line, text in errors:
                f.write("%s:%s\n%s\n\n" % (fname, line, text))
        print("pass %d: %d errors -> blacklisting %d items"
              % (p, len(errors), len(added)))
        for u in unplaced[:10]:
            print("   unplaced:", u.splitlines()[0][:160])
        if not added:
            print("no further progress; %d errors remain" % len(errors))
            for fname, line, text in errors[:20]:
                print("   %s:%s %s" % (fname, line, text.splitlines()[0][:160]))
            return 1
        skip |= added
        save_skip(skip)
        cache.clear()
        regenerate()
    print("gave up after %d passes" % max_passes)
    return 1


if __name__ == "__main__":
    sys.exit(main())
