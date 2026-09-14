"""Redraw fig3 as time-slice curtains without rerunning the physical model."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zlib
from pathlib import Path

import numpy as np


def project_modules():
    """Locate the shared path and unit contracts from any working directory."""
    for directory in Path(__file__).resolve().parents:
        if (directory / "src" / "common" / "paths.py").is_file():
            sys.path.insert(0, str(directory / "src"))
            from common import paths, plotting, units

            return paths, plotting, units
    raise FileNotFoundError("Cannot locate src/common/paths.py")


PATHS, PLOTTING, UNITS = project_modules()
HERE = Path(__file__).resolve().parent
DATA = HERE / "fig3_profiles.csv"
OUTPUT = PATHS.ROOT / "handout" / "pictures" / "fig3_waterfall.pdf"
SOURCE_SHA256 = "54ff16c46bb7ace2e3309560ea063336013d7ed6d3183f3927d493a4bc75f93e"
TIMES_S = (100, 300, 600, 1200, 1800)
COLORS = ("#4B9568", "#93AC67", "#C9AA5B", "#CF885E", "#C36961")
TIME_INSET = (0.24 - TIMES_S[0] / TIMES_S[-1]) / 2
TOP_LINEWIDTH = 1.6
TOP_DARKEN = 0.88
UPPER_HEIGHT_RATIO = 0.70


def field_height(value, lower, scale):
    """Compress the upper field axis about the fixed top of its break."""
    uncompressed = 0.28 + scale * (np.asarray(value) - lower)
    return np.where(
        np.asarray(value) == 0, 0,
        0.40 + UPPER_HEIGHT_RATIO * (uncompressed - 0.40),
    )


def time_depth(time_s, *, reverse: bool = False):
    """Reverse time without changing the nearest curtain gap or time scale."""
    projected_time = (
        TIMES_S[-1] + TIMES_S[0] - np.asarray(time_s)
        if reverse else np.asarray(time_s)
    )
    return projected_time / TIMES_S[-1] + TIME_INSET


def extract_profiles(source: Path) -> np.ndarray:
    """Recover the exact displayed polyline vertices, not the missing solver data."""
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Extraction requires the unmodified original fig3.pdf")
    streams = [
        zlib.decompress(match.group(1)).decode("latin1")
        for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S)
        if match.group(1).startswith(b"x")
    ]
    content = next(stream for stream in streams if " RG" in stream)
    number = r"[-+]?(?:\d*\.)?\d+"
    pattern = (
        rf"1\.8 w\s+{number}\s+{number}\s+{number}\s+RG"
        rf"\s+/DeviceRGB\s+cs\s+((?:{number}\s+{number}\s+[ml]\s+)+)S"
    )
    curves = []
    for match in re.finditer(pattern, content):
        vertices = np.array(
            re.findall(rf"({number})\s+({number})\s+[ml]", match.group(1)),
            dtype=float,
        )
        if np.isclose(vertices[:, 0].min(), 40.874805) and np.isclose(
            vertices[:, 0].max(), 632.007333
        ):
            curves.append(vertices)
    if len(curves) != len(TIMES_S):
        raise ValueError(f"Expected five source curves, found {len(curves)}")
    rows = []
    for time_s, vertices in zip(TIMES_S, curves):
        r_cm = (vertices[:, 0] - 40.874805) * 2.0 / (632.007333 - 40.874805)
        T_celsius = 28.0 + (vertices[:, 1] - 48.006304) * 8.0 / (
            197.856751 - 48.006304
        )
        rows.append(
            np.column_stack(
                (
                    np.full(len(vertices), time_s),
                    UNITS.cm_to_m(r_cm),
                    UNITS.c_to_k(T_celsius),
                )
            )
        )
    return np.concatenate(rows)


def validate_profiles(profiles: np.ndarray, *, field: str = "T") -> None:
    """Reject incomplete, nonfinite, or reordered source curves."""
    if field not in ("T", "C"):
        raise ValueError("Field must be T or C")
    if profiles.ndim != 2 or profiles.shape[1] != 3 or not np.isfinite(profiles).all():
        raise ValueError("Profiles must be finite (time_s, r_m, field_value) rows")
    if not np.array_equal(np.unique(profiles[:, 0]), TIMES_S):
        raise ValueError("The five original times must be preserved")
    for time_s in TIMES_S:
        curve = profiles[profiles[:, 0] == time_s]
        if len(curve) < 3 or np.any(np.diff(curve[:, 1]) < 0):
            raise ValueError(f"Invalid radial coordinates at {time_s} s")
        if not np.allclose(curve[[0, -1], 1], (0, UNITS.cm_to_m(2.0)), atol=1e-12):
            raise ValueError(f"Incomplete radial coverage at {time_s} s")
        if field == "T" and np.any(curve[:, 2] <= 200):
            raise ValueError("Temperature data must use kelvin")
        if field == "C" and np.any((curve[:, 2] < 1.4) | (curve[:, 2] > 2.6)):
            raise ValueError("Moisture data must fit the original 1.4–2.6 kg/kg range")


def draw(profiles: np.ndarray, output: Path, *, field: str = "T") -> None:
    """Use an oblique projection with physical, linearly scaled time coordinates."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Polygon

    validate_profiles(profiles, field=field)
    if output.resolve().parent == (PATHS.ROOT / "handout" / "figures").resolve():
        raise ValueError("Original handout/figures files must not be overwritten")
    PLOTTING.apply_style()
    plt.rcParams.update(
        {
            "font.sans-serif": ["Arial Unicode MS", "Songti SC", "DejaVu Sans"],
            "font.size": 11,
            "axes.labelsize": 12,
            "lines.linewidth": 1.0,
            "path.simplify": False,
        }
    )
    figure, axes = plt.subplots(figsize=(7.0, 5.4))
    figure.subplots_adjust(left=0.11, right=0.97, bottom=0.10, top=0.97)
    axes.set_aspect("equal")
    axes.axis("off")
    baseline = 0.0
    lower_value, vertical_scale, upper_value = (
        (27.0, 0.42, 38.3) if field == "T" else (1.4, 3.4, 2.66)
    )
    vertical_ticks = (
        (0, 28, 30, 32, 34, 36, 38)
        if field == "T"
        else (0, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6)
    )
    reverse_time = field == "C"
    far_time = TIMES_S[0] if reverse_time else TIMES_S[-1]

    def project(r_cm, time_s, value, *, front=False):
        depth = 0.0 if front else time_depth(time_s, reverse=reverse_time)
        horizontal = np.asarray(r_cm) + 1.20 * depth
        value_height = field_height(value, lower_value, vertical_scale)
        vertical = value_height + 1.05 * depth - 0.24 * np.asarray(r_cm)
        return horizontal, vertical

    def line(start, end, **kwargs):
        axes.plot(
            [start[0], end[0]], [start[1], end[1]], solid_capstyle="round", **kwargs
        )

    origin = project(0, 0, baseline, front=True)
    radius_end = project(2.0, 0, baseline, front=True)
    far_end = project(2.0, far_time, baseline)
    floor = [
        origin,
        radius_end,
        far_end,
        project(0, far_time, baseline),
    ]
    axes.add_patch(Polygon(floor, facecolor="#F5F6FA", edgecolor="none", zorder=0))
    for r_cm in np.linspace(0, 2, 5):
        line(
            project(r_cm, 0, baseline, front=True),
            project(r_cm, far_time, baseline),
            color="#DDE1E9",
            linewidth=0.65,
            zorder=1,
        )
    for time_s in TIMES_S:
        line(
            project(0, time_s, baseline),
            project(2, time_s, baseline),
            color="#C8CFDA",
            linewidth=0.8,
            linestyle=(0, (3, 4)),
            zorder=1,
        )
    draw_order = range(len(TIMES_S)) if reverse_time else reversed(range(len(TIMES_S)))
    for layer, order in enumerate(draw_order):
        time_s, color = TIMES_S[order], COLORS[order]
        curve = profiles[profiles[:, 0] == time_s]
        r_cm = UNITS.m_to_cm(curve[:, 1])
        values = UNITS.k_to_c(curve[:, 2]) if field == "T" else curve[:, 2]
        horizontal, vertical = project(r_cm, time_s, values)
        left = project(r_cm[0], time_s, baseline)
        right = project(r_cm[-1], time_s, baseline)
        vertices = [left, *zip(horizontal, vertical), right]
        zorder = 4 + layer
        axes.add_patch(
            Polygon(
                vertices,
                facecolor=color,
                edgecolor="none",
                alpha=0.10,
                zorder=zorder,
            )
        )
        top_color = tuple(channel * TOP_DARKEN for channel in to_rgb(color))
        axes.plot(
            horizontal, vertical, color=top_color,
            linewidth=TOP_LINEWIDTH, zorder=zorder + 0.1,
        )
        for bottom, top in (
            (left, (horizontal[0], vertical[0])),
            (right, (horizontal[-1], vertical[-1])),
        ):
            line(bottom, top, color=color, linewidth=1.0, zorder=zorder)
        line(left, right, color=color, linewidth=1.0, alpha=0.65, zorder=zorder)

    axis_color = "#293647"
    time_axis = (
        (project(2.0, TIMES_S[0] - 180, baseline), radius_end)
        if reverse_time else (radius_end, project(2.0, 1980, baseline))
    )
    for start, end in (
        (origin, project(2.17, 0, baseline, front=True)),
        time_axis,
        (origin, project(0, 0, upper_value, front=True)),
    ):
        axes.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={"arrowstyle": "-|>", "color": axis_color, "lw": 1.2},
            zorder=12,
        )
    line((0, 0.22), (0, 0.40), color="white", linewidth=4.0, zorder=13)
    for height in (0.265, 0.355):
        line(
            (-0.052, height - 0.03),
            (0.052, height + 0.03),
            color=axis_color,
            linewidth=1.0,
            zorder=14,
        )
    for r_cm in np.linspace(0, 2, 5):
        position = project(r_cm, 0, baseline, front=True)
        line(position, (position[0], position[1] - 0.045), color=axis_color, linewidth=0.8)
        axes.text(
            position[0], position[1] - 0.12, f"{r_cm:.1f}", ha="center", va="top"
        )
    for time_s, color in zip(TIMES_S, COLORS):
        position = project(2, time_s, baseline)
        label_shift = {100: 0.01, 300: -0.025}.get(time_s, 0) if reverse_time else 0
        line(
            position,
            (position[0] + 0.04, position[1] - 0.035),
            color=axis_color,
            linewidth=0.8,
        )
        axes.text(
            position[0] + 0.08,
            position[1] - 0.04 + label_shift,
            str(time_s),
            color=color,
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
        )
    for value in vertical_ticks:
        position = project(0, 0, value, front=True)
        line(position, (position[0] - 0.045, position[1]), color=axis_color, linewidth=0.8)
        axes.text(
            position[0] - 0.10, position[1], str(value), ha="right", va="center"
        )
    axes.text(
        0.98,
        -0.68,
        "距中心轴的距离 / cm",
        ha="center",
        va="center",
        rotation=np.degrees(np.arctan2(-0.24, 1.0)),
        rotation_mode="anchor",
        fontsize=12,
    )
    axes.text(
        3.48,
        -0.12,
        "时间 / s",
        ha="left",
        va="bottom",
        rotation=np.degrees(np.arctan2(1.05, 1.20)),
        rotation_mode="anchor",
        fontsize=11,
    )
    if field == "T":
        axes.text(-0.42, 1.78, "温度 / °C", ha="center", va="center", rotation=90, fontsize=12)
    else:
        axes.text(
            -0.52, 1.78, "干基含水率 / (kg/kg)",
            ha="center", va="center", rotation=90, fontsize=12,
        )
    axes.set_xlim(-0.50 if field == "T" else -0.64, 4.50)
    axes.set_ylim(-1.00, 4.25)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        output,
        bbox_inches="tight",
        pad_inches=0.08,
        metadata={"CreationDate": None, "ModDate": None},
    )
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-source", type=Path, help="Original, unmodified fig3.pdf")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() == (PATHS.ROOT / "handout" / "figures" / "fig3.pdf").resolve():
        parser.error("The original handout/figures/fig3.pdf must not be overwritten")
    if args.extract_source:
        profiles = extract_profiles(args.extract_source)
        validate_profiles(profiles)
        np.savetxt(
            DATA,
            profiles,
            delimiter=",",
            fmt="%.17g",
            header=(
                f"source_pdf_sha256={SOURCE_SHA256}\n"
                "Source: original fig3.pdf displayed vector vertices, not full solver output.\n"
                "time_s,r_m,T_K"
            ),
        )
    else:
        profiles = np.loadtxt(DATA, delimiter=",")
    draw(profiles, args.output)
    print(f"Saved {args.output}; {len(TIMES_S)} curves, {len(profiles)} original PDF vertices.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
