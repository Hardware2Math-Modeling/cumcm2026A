"""Draw five radial histories from the detailed Q2 Excel workbook."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import openpyxl

from draw_fig3 import (
    COLORS, PATHS, PLOTTING, TOP_DARKEN, TOP_LINEWIDTH, UNITS, field_height, time_depth,
)

SOURCE = PATHS.ROOT / "results" / "result2.xlsx"
ORIGINAL = PATHS.ROOT / "handout" / "figures" / "q2_summary.pdf"
OUTPUT_DIR = PATHS.ROOT / "handout" / "pictures"
RADIUS_M = UNITS.cm_to_m(np.array([0.0, 0.5, 1.0, 1.5, 2.0]))
END_TIME_S = 10800
SHEETS = {"T": "温度", "C": "水分浓度"}


@dataclass(frozen=True)
class Histories:
    time_s: np.ndarray
    radius_m: np.ndarray
    T: np.ndarray
    C: np.ndarray


def validate(data: Histories) -> None:
    if not np.array_equal(data.time_s, np.arange(END_TIME_S + 1)):
        raise ValueError("Expected every second from 0 through 10800; no interpolation allowed")
    if not np.array_equal(data.radius_m, RADIUS_M):
        raise ValueError("Expected radii 0, 0.5, 1, 1.5, 2 cm")
    for field in SHEETS:
        values = getattr(data, field)
        if values.shape != (END_TIME_S + 1, 5) or not np.isfinite(values).all():
            raise ValueError(f"{field}: incomplete or nonfinite Excel data")
    if np.any((data.T < UNITS.c_to_k(27)) | (data.T > UNITS.c_to_k(52))):
        raise ValueError("Temperature must be kelvin within the displayed range")
    if np.any((data.C < 0.8) | (data.C > 2.6)):
        raise ValueError("Moisture data outside the displayed 0.8–2.6 kg/kg range")


def load_histories(source: Path = SOURCE) -> Histories:
    """Read original Excel cells by radial headers; keep all one-second samples."""
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    fields = {}
    times = {}
    try:
        for field, sheet_name in SHEETS.items():
            if sheet_name not in workbook.sheetnames:
                raise ValueError(f"Missing worksheet: {sheet_name}")
            rows = workbook[sheet_name].iter_rows(values_only=True)
            header = next(rows)
            try:
                radial_header = UNITS.cm_to_m(np.asarray(header[1:], dtype=float))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{sheet_name}: invalid radial headers") from error
            columns = []
            for radius in RADIUS_M:
                matches = np.flatnonzero(np.isclose(radial_header, radius, rtol=0, atol=1e-12))
                if len(matches) != 1:
                    raise ValueError(f"{sheet_name}: missing or duplicate radius {radius} m")
                columns.append(int(matches[0]) + 1)
            selected = []
            for row in rows:
                if not isinstance(row[0], (int, float)):
                    raise ValueError(f"{sheet_name}: nonnumeric time")
                if row[0] > END_TIME_S:
                    break
                selected.append([row[0], *(row[column] for column in columns)])
            array = np.asarray(selected, dtype=float)
            times[field] = array[:, 0]
            fields[field] = UNITS.c_to_k(array[:, 1:]) if field == "T" else array[:, 1:]
    finally:
        workbook.close()
    if not np.array_equal(times["T"], times["C"]):
        raise ValueError("Temperature and moisture time grids differ")
    data = Histories(times["T"], RADIUS_M.copy(), fields["T"], fields["C"])
    validate(data)
    return data


def project(time_s, radius_m, value, *, field, front=False):
    """Display time horizontally, radius in depth, and field value vertically."""
    depth = (
        0.0 if front else time_depth(100)
        + ((RADIUS_M[-1] - np.asarray(radius_m)) if field == "C" else np.asarray(radius_m))
        / RADIUS_M[-1]
    )
    along = UNITS.s_to_h(np.asarray(time_s)) * 0.85
    lower, scale = (27.0, 0.18) if field == "T" else (0.8, 2.4)
    height = field_height(value, lower, scale)
    return along + 1.20 * depth, height + 1.05 * depth - 0.24 * along


def build_figure(data: Histories, field: str):
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Polygon

    if field not in SHEETS:
        raise ValueError("Field must be T or C")
    validate(data)
    PLOTTING.apply_style()
    plt.rcParams.update(
        {"font.sans-serif": ["Arial Unicode MS", "Songti SC", "DejaVu Sans"],
         "font.size": 11, "path.simplify": False}
    )
    figure, axes = plt.subplots(figsize=(7.0, 5.4))
    figure.subplots_adjust(left=0.11, right=0.97, bottom=0.10, top=0.97)
    axes.set_aspect("equal")
    axes.axis("off")
    axis_color = "#293647"
    far_radius = RADIUS_M[0] if field == "C" else RADIUS_M[-1]

    def position(time_s, radius_m, value=0, *, front=False):
        return project(time_s, radius_m, value, field=field, front=front)

    def line(start, end, **kwargs):
        axes.plot([start[0], end[0]], [start[1], end[1]], **kwargs)

    origin = position(0, 0, front=True)
    time_end = position(END_TIME_S, 0, front=True)
    far_end = position(END_TIME_S, far_radius)
    axes.add_patch(
        Polygon([origin, time_end, far_end, position(0, far_radius)],
                facecolor="#F5F6FA", edgecolor="none", zorder=0)
    )
    for time_s in np.arange(0, END_TIME_S + 1, 1800):
        line(position(time_s, 0, front=True), position(time_s, far_radius),
             color="#DDE1E9", linewidth=0.65, zorder=1)
    for radius in RADIUS_M:
        line(position(0, radius), position(END_TIME_S, radius),
             color="#C8CFDA", linewidth=0.8, linestyle=(0, (3, 4)), zorder=1)
    order = range(5) if field == "C" else reversed(range(5))
    for layer, index in enumerate(order):
        radius, color = RADIUS_M[index], COLORS[index]
        values = UNITS.k_to_c(data.T[:, index]) if field == "T" else data.C[:, index]
        horizontal, vertical = position(data.time_s, radius, values)
        left, right = position(data.time_s[0], radius), position(data.time_s[-1], radius)
        zorder = 4 + layer
        axes.add_patch(
            Polygon([left, *zip(horizontal, vertical), right],
                    facecolor=color, edgecolor="none", alpha=0.10, zorder=zorder)
        )
        axes.plot(
            horizontal, vertical, color=tuple(channel * TOP_DARKEN for channel in to_rgb(color)),
            linewidth=TOP_LINEWIDTH, zorder=zorder + 0.1,
        )
        for bottom, top in ((left, (horizontal[0], vertical[0])),
                            (right, (horizontal[-1], vertical[-1]))):
            line(bottom, top, color=color, linewidth=1, zorder=zorder)
        line(left, right, color=color, linewidth=1, alpha=0.65, zorder=zorder)
    upper = 52.5 if field == "T" else 2.68
    radius_arrow = (
        (position(END_TIME_S, -0.002), time_end) if field == "C"
        else (time_end, position(END_TIME_S, 0.022))
    )
    for start, end in ((origin, position(11400, 0, front=True)), radius_arrow,
                       (origin, position(0, 0, upper, front=True))):
        axes.annotate("", xy=end, xytext=start,
                      arrowprops={"arrowstyle": "-|>", "color": axis_color, "lw": 1.2},
                      zorder=12)
    line((0, 0.22), (0, 0.40), color="white", linewidth=4, zorder=13)
    for height in (0.265, 0.355):
        line((-0.052, height - 0.03), (0.052, height + 0.03),
             color=axis_color, linewidth=1, zorder=14)
    for time_s in np.arange(0, END_TIME_S + 1, 1800):
        horizontal, vertical = position(time_s, 0, front=True)
        line((horizontal, vertical), (horizontal, vertical - 0.045),
             color=axis_color, linewidth=0.8)
        axes.text(horizontal, vertical - 0.12, f"{UNITS.s_to_h(time_s):.1f}",
                  ha="center", va="top", fontsize=10)
    for radius, color in zip(RADIUS_M, COLORS):
        horizontal, vertical = position(END_TIME_S, radius)
        line((horizontal, vertical), (horizontal + 0.04, vertical - 0.035),
             color=axis_color, linewidth=0.8)
        axes.text(horizontal + 0.08, vertical - 0.04, f"{UNITS.m_to_cm(radius):.1f}",
                  color=color, ha="left", va="center", fontsize=10, fontweight="bold")
    ticks = (0, 28, 32, 36, 40, 44, 48, 52) if field == "T" else (0, 1.0, 1.4, 1.8, 2.2, 2.6)
    for value in ticks:
        horizontal, vertical = position(0, 0, value, front=True)
        line((horizontal, vertical), (horizontal - 0.045, vertical),
             color=axis_color, linewidth=0.8)
        axes.text(horizontal - 0.10, vertical, str(value), ha="right", va="center")
    axes.text(1.25, -0.80, "时间 / h", ha="center", va="center", fontsize=12,
              rotation=np.degrees(np.arctan2(-0.24, 1)), rotation_mode="anchor")
    radius_midpoint = (np.asarray(time_end) + np.asarray(far_end)) / 2
    label_offset = 0.58 * np.array([1.05, -1.20]) / np.hypot(1.05, 1.20)
    radius_label = radius_midpoint + label_offset
    axes.text(*radius_label, "距中心轴的距离 / cm", ha="center", va="center", fontsize=11,
              rotation=np.degrees(np.arctan2(1.05, 1.20)), rotation_mode="anchor")
    axes.text(-0.52, 1.78, "温度 / °C" if field == "T" else "干基含水率 / (kg/kg)",
              ha="center", va="center", rotation=90, fontsize=12)
    axes.set_xlim(-0.64, 4.95)
    axes.set_ylim(-1.05, 4.60)
    return figure


def draw(data: Histories, field: str, output: Path) -> None:
    import matplotlib.pyplot as plt

    if OUTPUT_DIR.resolve() not in output.resolve().parents or output.suffix.lower() != ".pdf":
        raise ValueError("Output must be a PDF under handout/pictures")
    figure = build_figure(data, field)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, bbox_inches="tight", pad_inches=0.08,
                       metadata={"CreationDate": None, "ModDate": None})
        figure.savefig(output.with_suffix(".png"), dpi=240, bbox_inches="tight", pad_inches=0.08)
    finally:
        plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    data = load_histories(args.source)
    for field, name in (("T", "temperature"), ("C", "moisture")):
        output = OUTPUT_DIR / f"q2_{name}_waterfall.pdf"
        draw(data, field, output)
        print(f"Saved {output}: 5 curves, {len(data.time_s)} Excel points each")
    manifest = {
        "source": str(args.source.resolve().relative_to(PATHS.ROOT)),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "original_pdf_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        "sheets": SHEETS, "time_range_s": [0, END_TIME_S], "time_step_s": 1,
        "points_per_curve": len(data.time_s), "radius_m": RADIUS_M.tolist(),
        "internal_units": {"time": "s", "radius": "m", "T": "K", "C": "kg/kg"},
        "resampling": False, "smoothing": False,
    }
    (OUTPUT_DIR / "draw_code" / "q2_summary_source.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
