"""比较独立目录完整复算的四问数值与工作表XML内容。"""

import hashlib
import json
from zipfile import ZipFile

import numpy as np
import openpyxl
import pandas as pd

from _bootstrap import setup

setup()

from common.paths import ROOT


def xml_hashes(path):
    result = {}
    with ZipFile(path) as z:
        for name in sorted(z.namelist()):
            if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                digest = hashlib.sha256()
                with z.open(name) as f:
                    for data in iter(lambda: f.read(1024*1024), b""):
                        digest.update(data)
                result[name] = digest.hexdigest()
    return result


def main():
    independent = ROOT / "outputs" / "accuracy-reproduce"
    report = {"directory": str(independent.relative_to(ROOT)), "questions": []}
    for q in ("q1", "q2", "q3", "q4"):
        record = {"q": q}
        with np.load(ROOT / "outputs" / "cache" / f"{q}.npz") as a, np.load(
                independent / "outputs" / "cache" / f"{q}.npz") as b:
            for field in ("t", "r", "T", "C"):
                x, y = a[field], b[field]
                assert x.shape == y.shape
                difference = float(np.max(np.abs(x-y)))
                assert difference < 1e-9
                record[f"max_{field}_difference"] = difference
        filename = f"result{q[-1]}.xlsx"
        original = xml_hashes(ROOT / "results" / filename)
        replica = xml_hashes(independent / "results" / filename)
        assert original == replica, f"{q}工作表内容不同"
        record["worksheet_xml_sha256"] = original
        record["status"] = "passed"
        report["questions"].append(record)
        path = ROOT / "results" / f"{q}_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["portability_test"] = {
            "status": "passed", "report": "results/validation/accuracy-reproduction.json",
            "tolerance": 1e-9, "worksheet_xml_identical": True,
            "scope": "same environment, independent clean directory, full four-question outputs"}
        source_files = [*sorted((ROOT / "src").rglob("*.py")),
                        ROOT / "scripts" / "_runner.py"]
        manifest["code_hashes"] = {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files}
        manifest["packages"].update(pandas=pd.__version__, openpyxl=openpyxl.__version__)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(q, "independent reproduction passed", flush=True)
    (ROOT / "results" / "validation" / "accuracy-reproduction.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
