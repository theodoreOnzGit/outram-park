//! Every `outram-park-backend` crate is wired into this metacrate
//! (outram-park-backend gh:#971, #972; maintainer, 2026-10-20).
//!
//! Reads the backend's member manifests from the `outram-park-backend`
//! submodule and checks that each one has, in `outram-park/Cargo.toml`, a
//! crates.io dependency (never a path), a same-named feature, a place in
//! `all-backends`, and a re-export module in `src/backend/`. A backend crate
//! added without wiring it in here fails this test.
//!
//! Needs the submodule checked out (`git submodule update --init`); it is
//! excluded from the crates.io package, where the submodule does not exist.

use std::fs;
use std::path::Path;

/// `(package name, dependency key)` for every backend member crate.
fn backend_members(backend: &Path) -> Vec<(String, String)> {
    let mut out = Vec::new();
    for entry in fs::read_dir(backend.join("crates")).expect("backend crates/ readable") {
        let manifest = entry.unwrap().path().join("Cargo.toml");
        let Ok(text) = fs::read_to_string(&manifest) else { continue };
        let name = text
            .lines()
            .find_map(|l| l.strip_prefix("name = \"").and_then(|r| r.strip_suffix('"')))
            .unwrap_or_else(|| panic!("no package name in {}", manifest.display()))
            .to_string();
        out.push((name.clone(), name));
    }
    out.sort();
    out
}

#[test]
fn every_backend_crate_is_wired_in() {
    let here = Path::new(env!("CARGO_MANIFEST_DIR"));
    let backend = here.join("../outram-park-backend");
    assert!(
        backend.join("crates").is_dir(),
        "the outram-park-backend submodule is not checked out: git submodule update --init"
    );
    let manifest = fs::read_to_string(here.join("Cargo.toml")).unwrap();
    let all_backends = manifest
        .split("all-backends = [")
        .nth(1)
        .and_then(|r| r.split(']').next())
        .expect("all-backends feature present");

    let mut problems = Vec::new();
    for (package, _) in backend_members(&backend) {
        // The dependency line: keyed by the package name, or an alias with
        // `package = "<name>"`.
        let dep = manifest.lines().find(|l| {
            l.starts_with(&format!("{package} = {{"))
                || l.contains(&format!("package = \"{package}\""))
        });
        let Some(dep) = dep else {
            problems.push(format!("{package}: no dependency"));
            continue;
        };
        let key = dep.split(" = ").next().unwrap().trim().to_string();
        if dep.contains("path =") {
            problems.push(format!("{package}: path dependency (crates.io only)"));
        }
        if !dep.contains("version =") {
            problems.push(format!("{package}: no version"));
        }
        if !manifest.contains(&format!("\n{key} = [\"dep:{key}\"]")) {
            problems.push(format!("{package}: no `{key}` feature"));
        }
        if !all_backends.contains(&format!("\"{key}\"")) {
            problems.push(format!("{package}: not in all-backends"));
        }
        let module = here.join("src/backend").join(format!("{}.rs", key.replace('-', "_")));
        if !module.is_file() {
            problems.push(format!("{package}: no {}", module.display()));
        }
    }
    assert!(problems.is_empty(), "backend wiring gaps:\n{}", problems.join("\n"));
}
