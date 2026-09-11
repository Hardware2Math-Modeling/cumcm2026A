"""流式回读全部交付单元格，与未舍入求解缓存核验。"""

import hashlib
import json
import sys

import numpy as np
import openpyxl

from _bootstrap import setup

setup()

from common.io_excel import layout
from common.paths import ROOT
from common.units import cm_to_m, k_to_c


def main():
    questions = sys.argv[1:] or ["q1", "q2", "q3", "q4"]
    if any(q not in {"q1", "q2", "q3", "q4"} for q in questions):
        raise ValueError("参数只能是q1/q2/q3/q4")
    dest = ROOT / "results" / "validation" / "accuracy-output-check.json"
    report = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {"files": []}
    report["files"] = [x for x in report["files"] if x["q"] not in questions]
    cached = {}
    for question in questions:
        path = ROOT / "results" / f"result{question[-1]}.xlsx"
        with np.load(ROOT / "outputs" / "cache" / f"{question}.npz") as f:
            t, r, T, C = f["t"], f["r"], f["T"], f["C"]
            meta = json.loads(str(f["meta"]))
        if question in {"q2", "q3"}:
            cached[question] = (t, C)
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        expected_layout = layout(question)
        assert book.sheetnames == list(expected_layout.sheet_names)
        sheet_records = []
        for name, field in expected_layout.sheets:
            rows = book[name].iter_rows(values_only=True)
            assert list(next(rows)) == expected_layout.expected_columns()
            if question == "q4":
                targets = cm_to_m(np.array([float(x) for x in expected_layout.distance_headers()[:-1]]))
                expected = np.empty((len(t), 21))
                for i, R in enumerate(meta["R"]):
                    expected[i, :-1] = np.interp(targets, r/r[-1]*R, C[i], right=np.nan)
                    expected[i, -1] = C[i, -1]
                expected = np.round(expected, 4)
            else:
                expected = np.round(k_to_c(T) if field == "T" else C, 4)
            count = 0
            for i, row in enumerate(rows):
                if i >= len(t):
                    raise AssertionError("输出行数过多")
                assert len(row) == 22 and row[0] == t[i]
                values = np.asarray(row[1:], dtype=float)
                if not np.array_equal(np.isnan(values), np.isnan(expected[i])) or not np.allclose(
                        values, expected[i], rtol=0, atol=1e-11, equal_nan=True):
                    raise AssertionError(f"{question}/{name}/row {i+2} 数值不一致")
                count += 1
            assert count == len(t)
            assert np.all(np.diff(t) == expected_layout.dt_s)
            sheet_records.append({"sheet": name, "data_rows": count, "columns": 22})
            print(question, name, count, "rows verified", flush=True)
        book.close()
        report["files"].append({"q": question, "sheets": sheet_records,
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        manifest_path = ROOT / "results" / f"{question}_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "computed_and_readback_verified"
        manifest["readback"] = "results/validation/accuracy-output-check.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if "q2" in cached and "q3" in cached:
        t2, c2 = cached["q2"]
        t3, c3 = cached["q3"]
        mask = t3 <= t2[-1]
        indices = np.searchsorted(t2, t3[mask])
        assert np.array_equal(t2[indices], t3[mask])
        delta = float(np.max(np.abs(c2[indices]-c3[mask])))
        assert delta < 1e-8
        report["q2_q3_common_time_max_C_difference"] = delta
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Requested output cells verified:", questions, flush=True)


if __name__ == "__main__":
    main()
