"""把数值解写成题目附件 3 的四个 Excel 文件。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from .model import RADIUS0_M, Result

TIME_HEADER = "时间\\到药材中心的距离"
SURFACE_HEADER = "药材表面"
DISTANCE_CM = np.arange(0.0, 2.01, 0.1)


def _cell(sheet, value):
    cell = WriteOnlyCell(sheet, value=None if value is None else float(value))
    cell.number_format = "0.0000"
    return cell


def _field_rows(result: Result, field: str):
    values = result.T if field == "T" else result.C
    for i, t_s in enumerate(result.t):
        row = [int(round(t_s))]
        if result.question == "q4":
            radius = result.R[i]
            physical_r = result.xi * radius
            for d_cm in DISTANCE_CM[:-1]:
                target = d_cm * 0.01
                row.append(np.interp(target, physical_r, values[i]) if target <= radius + 1e-12 else None)
            row.append(values[i, -1])
        else:
            targets = DISTANCE_CM * 0.01 / RADIUS0_M
            row.extend(np.interp(targets, result.xi, values[i]))
        if field == "T":
            row[1:] = [None if x is None else float(x) - 273.15 for x in row[1:]]
        yield row


def _write_sheet(book, name: str, result: Result, field: str):
    sheet = book.create_sheet(name)
    headers = [TIME_HEADER, *[f"{x:g}" for x in DISTANCE_CM[:-1]]]
    headers.append(SURFACE_HEADER if result.question == "q4" else "2")
    sheet.append(headers)
    for row in _field_rows(result, field):
        sheet.append([row[0], *[_cell(sheet, x) for x in row[1:]]])


def write_result(result: Result, out_dir: Path) -> Path:
    """写出 result1~4.xlsx；时间列为秒，数值显示四位小数。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    book = Workbook(write_only=True)
    if result.question in ("q1", "q2"):
        _write_sheet(book, "温度", result, "T")
        _write_sheet(book, "水分浓度", result, "C")
    else:
        _write_sheet(book, "Sheet1", result, "C")
    path = out_dir / f"result{result.question[-1]}.xlsx"
    book.save(path)
    return path
