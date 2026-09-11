"""Create and verify deterministic local review ZIPs using the standard library.

Run only after both scenarios, validation and the final manuscript are complete.
This script never modifies problem/, installs dependencies or publishes files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "outputs" / "delivery"
FIXED_ZIP_TIME = (2026, 9, 11, 0, 0, 0)
LIMIT_BYTES = 20_000_000
MANIFEST_NAME = "PACKAGE_MANIFEST.json"
BUFFER_SIZE = 1024 * 1024
EXCLUDED_COMPONENTS = {
    ".git", ".github", ".agents", ".codex", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".ipynb_checkpoints", ".devtools",
    "node_modules", "build", "interim", "outputs",
}
LEGACY_FILES = {
    "scripts/make_accuracy_report.py",
    "scripts/validate_numerics.py",
    "scripts/validate_q4_accuracy.py",
    "scripts/verify_accuracy_reproduction.py",
    "results/validation/accuracy.json",
    "results/validation/accuracy-q4.json",
    "results/validation/accuracy-reproduction.json",
    "results/validation/accuracy-methods.md",
    "results/validation/numerics.json",
    "paper/figs/fig1-accuracy.pdf",
    "paper/figs/fig1-C-history.pdf",
    "paper/tab/q1_validation.tex",
    "paper/tab/q1_values.tex",
}
TEMPORARY_SUFFIXES = {
    ".pyc", ".pyo", ".aux", ".log", ".out", ".fls", ".fdb_latexmk",
    ".synctex", ".toc", ".nav", ".snm", ".vrb", ".tmp", ".bak",
    ".bbl", ".blg", ".bcf", ".dvi", ".xdv",
}
ROOT_FILES = (
    "AGENTS.md", "README.md", "Makefile", "environment.yml", "pyproject.toml",
    ".gitignore", ".gitattributes", "REPRODUCE.md", "run_all.py",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path):
    return path.relative_to(ROOT).as_posix()


def excluded(path):
    rel = path.relative_to(ROOT)
    if path.is_symlink() or any(part in EXCLUDED_COMPONENTS for part in rel.parts):
        return True
    if path.name.startswith(("~$", ".#")) or path.name in {".DS_Store", "Thumbs.db", "desktop.ini"}:
        return True
    if path.suffix.lower() in TEMPORARY_SUFFIXES or ".synctex" in path.name:
        return True
    if relative(path) in LEGACY_FILES:
        return True
    return False


def collect(directory):
    parent = ROOT / directory
    if not parent.is_dir():
        raise FileNotFoundError(f"Required directory is missing: {directory}")
    return [path for path in parent.rglob("*") if path.is_file() and not excluded(path)]


def unique_sorted(paths):
    return sorted(set(paths), key=relative)


def audit_entrypoint_dependencies(planned_files):
    """AST-check local imports and literal Python script calls, without runs.

    External package imports are left to environment.yml. Dynamic qN solver
    imports are covered by retaining all of src/. This audit follows the main
    entrypoints and current tests, including historical helper modules still
    used by current tests; filenames alone never determine historical status.
    """
    planned = {path.resolve() for path in planned_files}
    seeds = [ROOT / "run_all.py", ROOT / "scripts/run_pipeline.py",
             ROOT / "tests/test_accuracy.py", ROOT / "tests/test_numerics.py"]
    visited = set()
    edges = []
    pending = list(seeds)

    def resolve_module(module, caller, level=0):
        if not module:
            return []
        if level:
            base = caller.parent
            for _ in range(level - 1):
                base = base.parent
            bases = [base]
        else:
            bases = [caller.parent, ROOT, ROOT / "scripts", ROOT / "src"]
        module_path = Path(*module.split("."))
        for base in bases:
            options = [base / module_path.with_suffix(".py"), base / module_path / "__init__.py"]
            for option in options:
                if option.is_file() and option.resolve().is_relative_to(ROOT.resolve()):
                    return [option.resolve()]
        return []

    while pending:
        path = pending.pop().resolve()
        if path in visited:
            continue
        if not path.is_file() or path not in planned:
            raise RuntimeError("Entrypoint dependency is absent from ZIP plan: " + relative(path))
        visited.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        dependencies = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies += resolve_module(alias.name, path)
            elif isinstance(node, ast.ImportFrom):
                dependencies += resolve_module(node.module, path, node.level)
                for alias in node.names:
                    if alias.name != "*":
                        child = f"{node.module}.{alias.name}" if node.module else alias.name
                        dependencies += resolve_module(child, path, node.level)
            elif isinstance(node, ast.Call):
                function_name = (node.func.id if isinstance(node.func, ast.Name)
                                 else node.func.attr if isinstance(node.func, ast.Attribute) else "")
                if function_name not in {"python", "run_path", "run", "Popen", "check_call", "check_output"}:
                    continue
                script_literals = [value.value for argument in node.args for value in ast.walk(argument)
                                   if isinstance(value, ast.Constant) and isinstance(value.value, str)
                                   and value.value.endswith(".py")]
                for script in script_literals:
                    raw = Path(script)
                    if raw.is_absolute() or "\n" in script:
                        continue
                    for base in (ROOT, path.parent, ROOT / "scripts", ROOT / "tests"):
                        candidate = base / raw
                        if candidate.is_file():
                            dependencies.append(candidate.resolve())
                            break
                    else:
                        raise RuntimeError(f"Called script does not exist: {relative(path)} -> {script}")
        for dependency in set(dependencies):
            if dependency not in planned:
                raise RuntimeError(f"ZIP would break local dependency: {relative(path)} -> {relative(dependency)}")
            edges.append({"caller": relative(path), "dependency": relative(dependency)})
            pending.append(dependency)
    return {"method": "AST local import and literal .py path dependency closure",
            "entrypoints": [relative(path) for path in seeds],
            "checked_python_files": sorted(relative(path) for path in visited),
            "dependencies": sorted(edges, key=lambda row: (row["caller"], row["dependency"])),
            "status": "all resolved local dependencies are present in ZIP source plan"}


def require_files(paths):
    missing = [relative(path) for path in paths if not path.is_file()]
    empty = [relative(path) for path in paths if path.is_file() and path.stat().st_size == 0]
    if missing or empty:
        raise RuntimeError(f"Delivery is unfinished. Missing: {missing}; empty: {empty}")


def verify_workbook_manifest(directory, q):
    file = directory / f"result{q}.xlsx"
    manifest_file = directory / f"q{q}_manifest.json"
    summary_file = directory / f"q{q}_summary.json"
    require_files([file, manifest_file, summary_file])
    manifest, summary = load_json(manifest_file), load_json(summary_file)
    if manifest.get("model_version") != "latent-v2" or manifest.get("latent_heat") is not True:
        raise RuntimeError(f"Historical or non-latent result is not deliverable: {relative(file)}")
    if summary.get("latent_heat") is not True:
        raise RuntimeError(f"Summary does not confirm latent heat: {relative(summary_file)}")
    if sha256_file(file) != manifest.get("submission_sha256"):
        raise RuntimeError(f"Workbook does not match its result manifest: {relative(file)}")
    input_hashes = {name.replace("\\", "/"): digest
                    for name, digest in manifest.get("input_hashes", {}).items()}
    for name, digest in input_hashes.items():
        if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest:
            raise RuntimeError(f"Original input does not match the run manifest: {name}")
    if q != 1 and (summary.get("event_time_s") is None
                   or summary.get("max_C_final_internal", 1.0) >= 0.15):
        raise RuntimeError(f"Strict drying threshold is not confirmed: {relative(summary_file)}")
    with zipfile.ZipFile(file) as workbook:
        bad = workbook.testzip()
        if bad is not None:
            raise RuntimeError(f"Damaged XLSX member: {relative(file)} :: {bad}")
    # Flag any final code drift instead of presenting unverifiable provenance.
    recorded = {name.replace("\\", "/"): digest
                for name, digest in manifest.get("source_hashes", {}).items()}
    if not recorded:
        raise RuntimeError(f"Missing source hashes: {relative(manifest_file)}")
    changed = [name for name, digest in recorded.items()
               if not (ROOT / name).is_file() or sha256_file(ROOT / name) != digest]
    changed += [relative(path) + " (new source file)"
                for path in sorted((ROOT / "src").rglob("*.py"))
                if relative(path) not in recorded]
    return {"result": relative(file), "bytes": file.stat().st_size,
            "submission_sha256": manifest["submission_sha256"],
            "source_hashes_differ_from_current": changed}


def preflight():
    required = [ROOT / name for name in ROOT_FILES]
    required += [ROOT / name for name in (
        "problem/A题.pdf", "problem/附件/附件1.xlsx", "problem/附件/附件2.xlsx",
        "paper/main.tex", "paper/preamble.tex", "paper/refs.bib", "paper/build/main.pdf",
        "paper/tab/all_values.tex", "paper/tab/temperature_scenarios.tex",
        "results/validation/latent.json", "results/validation/ambient_fit.json",
        "results/validation/fitted_numerics.json",
        "data/processed/ambient_fit.csv", "scripts/README_delivery.md",
        "results/scenarios/fitted_temperature/comparison.json",
    )]
    require_files(required)
    validation = load_json(ROOT / "results/validation/latent.json")
    if validation.get("model_version") != "latent-v2" or not validation.get("settings"):
        raise RuntimeError("Latent-heat validation is missing or still being written")
    if not all(validation.get(name) for name in ("grid", "time", "sensitivity", "ablation")):
        raise RuntimeError("Latent validation does not contain every required analysis")
    for q in ("q1", "q3", "q4"):
        if not any(row.get("q") == q and row.get("n") == 2561 for row in validation["grid"]):
            raise RuntimeError(f"Finest validation grid is missing for {q}")
    fitted = ROOT / "results/scenarios/fitted_temperature"
    comparison = load_json(fitted / "comparison.json")
    if not all(q in comparison for q in ("q2", "q3", "q4")):
        raise RuntimeError("Fitted-temperature scenario has not finished all three questions")
    records = [verify_workbook_manifest(ROOT / "results", q) for q in (1, 2, 3, 4)]
    records += [verify_workbook_manifest(fitted, q) for q in (2, 3, 4)]
    return records


def zip_info(name, readonly=False):
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info._compresslevel = 9  # ZipInfo streaming compression setting on Python 3.12.
    info.create_system = 3
    info.external_attr = ((0o100444 if readonly else 0o100644) << 16)
    if readonly:
        info.external_attr |= 0x01  # DOS read-only flag; source filesystem is untouched.
    return info


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC check failed: {path.name} :: {bad}")
        manifest = json.loads(archive.read(MANIFEST_NAME))
        expected = {row["path"] for row in manifest["files"]} | {MANIFEST_NAME}
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise RuntimeError(f"ZIP membership mismatch: {path.name}")
        for row in manifest["files"]:
            digest = hashlib.sha256()
            count = 0
            with archive.open(row["path"]) as handle:
                for chunk in iter(lambda: handle.read(BUFFER_SIZE), b""):
                    digest.update(chunk)
                    count += len(chunk)
            if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
                raise RuntimeError(f"ZIP member hash mismatch: {path.name} :: {row['path']}")
    size = path.stat().st_size
    return {"path": relative(path), "bytes": size, "MB_decimal": size / 1_000_000,
            "MiB_binary": size / 1024**2, "limit_20MB_bytes": LIMIT_BYTES,
            "exceeds_20MB": size > LIMIT_BYTES, "sha256": sha256_file(path),
            "member_count": len(names), "verified": "CRC plus every member SHA-256 and byte count"}


def write_archive(name, files, purpose, provenance_warnings):
    target = DELIVERY / name
    temporary = target.with_suffix(".zip.tmp")
    records = [{"path": relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
               for path in files]
    manifest = {
        "format_version": 1, "purpose": purpose,
        "local_review_only": True, "files": records,
        "provenance_warnings": provenance_warnings,
        "excluded_historical_files": sorted(LEGACY_FILES),
        "exclusions": "Repository metadata, output caches, temporary files, compiled LaTeX files, and explicitly enumerated historical reports; main.pdf is separate. Current accuracy-output-check.json and imported validate_accuracy.py helpers are retained. Original problem PDFs and current figure PDFs remain for source reproducibility.",
        "reproducibility": "Sorted members, fixed ZIP timestamps and permissions, DEFLATE level 9. Identical input bytes and the same Python/zlib runtime produce identical archive bytes.",
    }
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as archive:
        for path in files:
            info = zip_info(relative(path), readonly=path.relative_to(ROOT).parts[0] == "problem")
            with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as destination:
                shutil.copyfileobj(source, destination, BUFFER_SIZE)
        archive.writestr(zip_info(MANIFEST_NAME),
                         json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
    # Verify before replacing a previously completed package. Any source file
    # changed while packaging is caught because hashes were computed first.
    verify_archive(temporary)
    os.replace(temporary, target)
    result = verify_archive(target)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify existing delivery ZIPs without rebuilding")
    parser.add_argument("--allow-source-drift", action="store_true",
                        help="Explicitly preserve and report source-hash differences; never suppress them")
    args = parser.parse_args()
    if args.verify_only:
        archives = sorted(DELIVERY.glob("*.zip"))
        if not archives:
            raise FileNotFoundError("No delivery ZIPs exist")
        for archive in archives:
            print(json.dumps(verify_archive(archive), ensure_ascii=False), flush=True)
        return 0
    provenance = preflight()
    drift = [row for row in provenance if row["source_hashes_differ_from_current"]]
    if drift and not args.allow_source_drift:
        raise RuntimeError("Result source hashes differ from current files. Resolve the discrepancy or explicitly retain it with --allow-source-drift; no archive was created. "
                           + json.dumps(drift, ensure_ascii=False))
    source_files = [ROOT / name for name in ROOT_FILES]
    for directory in ("problem", "src", "scripts", "tests", "docs", "data", "paper"):
        source_files += collect(directory)
    source_files = unique_sorted(source_files)
    dependency_audit = audit_entrypoint_dependencies(source_files)
    main_results = unique_sorted(path for path in collect("results")
                                 if "scenarios" not in path.relative_to(ROOT).parts)
    fitted_files = collect("results/scenarios/fitted_temperature")
    fitted_files += [ROOT / name for name in (
        "results/validation/ambient_fit.json", "results/validation/latent.json",
        "results/validation/fitted_numerics.json", "results/validation/README.md",
        "data/processed/ambient_fit.csv", "scripts/README_delivery.md",
        "scripts/fit_ambient_temperature.py", "scripts/validate_fitted_scenario.py",
        "docs/model/environment-fit.md",
    )]
    # Additional final verification reports (for example full-cell workbook
    # readback) are retained with the scenario too; only individually named
    # historical reports are excluded by collect().
    fitted_files += collect("results/validation")
    require_files(fitted_files)
    fitted_files = unique_sorted(fitted_files)
    DELIVERY.mkdir(parents=True, exist_ok=True)
    packages = [write_archive("cumcm2026A_support.zip", unique_sorted(source_files + main_results),
                              "Main 60 C / 20% RH scenario: source, frozen problem copies, validation, results and LaTeX sources", drift),
                write_archive("fitted_temperature_results.zip", fitted_files,
                              "Additional fitted-temperature / 20% RH scenario; use alongside the main support/source ZIP", drift)]
    if packages[0]["exceeds_20MB"]:
        print("NOTICE: Main support ZIP exceeds 20 MB; preserving it and additionally creating source/results ZIPs. No results are omitted.", flush=True)
        packages += [write_archive("cumcm2026A_source.zip", source_files,
                                   "Source-only companion; combine with main_results ZIP at the same extracted directory", drift),
                     write_archive("cumcm2026A_main_results.zip", main_results,
                                   "Complete main result files and current validation; may itself exceed 20 MB", drift)]
    pdf = ROOT / "paper/build/main.pdf"
    report = {"local_review_only": True, "submission_performed": False,
              "size_limit_interpretation": "Conservatively 20,000,000 bytes, with MiB also reported; over-limit files are preserved and disclosed, not silently truncated or split internally.",
              "packages": packages, "workbook_provenance": provenance,
              "source_dependency_audit": dependency_audit,
              "separate_final_pdf": {"path": relative(pdf), "bytes": pdf.stat().st_size,
                                     "sha256": sha256_file(pdf),
                                     "exceeds_20MB": pdf.stat().st_size > LIMIT_BYTES},
              "all_packages_within_20MB": all(not row["exceeds_20MB"] for row in packages)}
    (DELIVERY / "package_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    over = [row["path"] for row in packages if row["exceeds_20MB"]]
    if report["separate_final_pdf"]["exceeds_20MB"]:
        over.append(relative(pdf))
    if over:
        print("OVER 20 MB; local review artifacts remain complete: " + ", ".join(over), flush=True)
    print("Package report: " + relative(DELIVERY / "package_report.json"), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"Delivery packaging failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
