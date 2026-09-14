"""Draw a translucent 3D cylinder with radial heat and moisture arrows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from draw_fig3 import PATHS, PLOTTING
from common.problem_spec import Q1

ORIGINAL = PATHS.ROOT / "handout" / "figures" / "fig1.pdf"
OUTPUT = PATHS.ROOT / "handout" / "pictures" / "fig1_3d.pdf"
SOURCE_SHA256 = "5cfab32654003e3b08cd1aebb1a8d2191ccb03b77ba69f8d5c90ac30ff2ce6b2"
GEOMETRY = Q1.geometry
HEAT_COLOR = "#B6504B"
MOISTURE_COLOR = "#327FA5"
OUTLINE_COLOR = "#707579"
VIEW_ANGLE = np.deg2rad(27.0)
SCREEN_ANGLE = np.deg2rad(-12.0)
SCREEN_AXIS = np.array([np.cos(SCREEN_ANGLE), np.sin(SCREEN_ANGLE)])
SCREEN_UP = np.array([-np.sin(SCREEN_ANGLE), np.cos(SCREEN_ANGLE)])
RADIAL_BANDS = ((0.15, 0.33), (0.43, 0.61), (0.71, 0.89))
ARROWS_PER_RING = 12
AXIAL_FRACTIONS = (-0.46, -0.14, 0.18, 0.50)


@dataclass(frozen=True)
class RadialArrow:
    field: str
    start_m: np.ndarray
    end_m: np.ndarray
    front: bool


def project(points_m: np.ndarray) -> np.ndarray:
    """Orthographically project a physical 3D cylinder, without rescaling its axes."""
    points = np.asarray(points_m, dtype=float)
    along = np.sin(VIEW_ANGLE) * points[..., 0] + np.cos(VIEW_ANGLE) * points[..., 1]
    return along[..., None] * SCREEN_AXIS + points[..., 2, None] * SCREEN_UP


def ring_points(axial_m: float, angles: np.ndarray) -> np.ndarray:
    """Return a circular section in meters, with the cylinder along coordinate 0."""
    return np.column_stack(
        (
            np.full(len(angles), axial_m),
            GEOMETRY.radius0 * np.cos(angles),
            GEOMETRY.radius0 * np.sin(angles),
        )
    )


def radial_arrows() -> list[RadialArrow]:
    """Arrow lengths indicate direction only, not computed flux magnitudes."""
    arrows = []
    for axial_fraction in AXIAL_FRACTIONS:
        axial_m = axial_fraction * GEOMETRY.length
        front = axial_fraction == 0.50
        for inner, outer in RADIAL_BANDS:
            for index in range(ARROWS_PER_RING):
                angle = np.deg2rad(12.0 + 360.0 * index / ARROWS_PER_RING)
                field = "T" if index % 2 == 0 else "C"
                radial_start, radial_end = (outer, inner) if field == "T" else (inner, outer)
                start = np.array(
                    [axial_m, radial_start * GEOMETRY.radius0 * np.cos(angle),
                     radial_start * GEOMETRY.radius0 * np.sin(angle)]
                )
                end = np.array(
                    [axial_m, radial_end * GEOMETRY.radius0 * np.cos(angle),
                     radial_end * GEOMETRY.radius0 * np.sin(angle)]
                )
                arrows.append(RadialArrow(field, start, end, front))
    return arrows


def build_figure():
    """Compose projected vector surfaces from back to front, keeping arrows visible."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Polygon

    PLOTTING.apply_style()
    plt.rcParams.update(
        {
            "font.sans-serif": ["Arial Unicode MS", "Songti SC", "DejaVu Sans"],
            "font.size": 12,
            "path.simplify": False,
        }
    )
    figure, axes = plt.subplots(figsize=(8.0, 3.8))
    figure.subplots_adjust(left=0.025, right=0.975, bottom=0.025, top=0.975)
    axes.set_aspect("equal")
    axes.axis("off")
    rear_m, front_m = -GEOMETRY.length / 2, GEOMETRY.length / 2
    full_angles = np.linspace(0, 2 * np.pi, 361)

    def face(axial_m, alpha, zorder):
        axes.add_patch(
            Polygon(
                project(ring_points(axial_m, full_angles)),
                facecolor="#A1A5A8", edgecolor="none", alpha=alpha, zorder=zorder,
            )
        )

    def shell(start_angle, end_angle, alpha, zorder):
        angles = np.linspace(start_angle, end_angle, 181)
        vertices = project(
            np.vstack((ring_points(rear_m, angles), ring_points(front_m, angles[::-1])))
        )
        axes.add_patch(
            Polygon(
                vertices, facecolor="#A1A5A8", edgecolor="none",
                alpha=alpha, zorder=zorder,
            )
        )

    def outline(axial_m, angles, *, alpha=1.0, linestyle="-", zorder=6):
        points = project(ring_points(axial_m, angles))
        axes.plot(
            points[:, 0], points[:, 1], color=OUTLINE_COLOR,
            linewidth=1.1, alpha=alpha, linestyle=linestyle, zorder=zorder,
        )

    def arrow(geometry):
        start, end = project(np.array([geometry.start_m, geometry.end_m]))
        axes.add_patch(
            FancyArrowPatch(
                start, end, arrowstyle="-|>", mutation_scale=8,
                linewidth=1.1, color=HEAT_COLOR if geometry.field == "T" else MOISTURE_COLOR,
                shrinkA=0, shrinkB=0, alpha=1.0 if geometry.front else 0.83,
                zorder=9 if geometry.front else 3,
            )
        )

    face(rear_m, 0.12, 0)
    shell(-np.pi / 2, np.pi / 2, 0.12, 1)
    outline(
        rear_m, np.linspace(-np.pi / 2, np.pi / 2, 181),
        alpha=0.5, linestyle=(0, (4, 4)), zorder=2,
    )
    for geometry in radial_arrows():
        if not geometry.front:
            arrow(geometry)
    shell(np.pi / 2, 3 * np.pi / 2, 0.24, 4)
    outline(rear_m, np.linspace(np.pi / 2, 3 * np.pi / 2, 181), alpha=0.85)
    for angle in (-np.pi / 2, np.pi / 2):
        endpoints = project(
            np.vstack(
                (ring_points(rear_m, np.array([angle])),
                 ring_points(front_m, np.array([angle])))
            )
        )
        axes.plot(
            endpoints[:, 0], endpoints[:, 1],
            color=OUTLINE_COLOR, linewidth=1.2, zorder=6,
        )
    face(front_m, 0.24, 7)
    outline(front_m, full_angles, zorder=8)
    for geometry in radial_arrows():
        if geometry.front:
            arrow(geometry)

    boundary = project(
        np.vstack((ring_points(rear_m, full_angles), ring_points(front_m, full_angles)))
    )
    lower = boundary.min(axis=0)
    upper = boundary.max(axis=0)
    margin = GEOMETRY.radius0 * 0.33
    legend_height = upper[1] - GEOMETRY.radius0 * 0.10
    legend_left = upper[0] - GEOMETRY.radius0 * 2.70
    for offset, color, label in (
        (0.0, HEAT_COLOR, "热量"),
        (1.40, MOISTURE_COLOR, "水分"),
    ):
        start = (legend_left + offset * GEOMETRY.radius0, legend_height)
        end = (start[0] + 0.53 * GEOMETRY.radius0, legend_height)
        axes.add_patch(
            FancyArrowPatch(
                start, end, arrowstyle="-|>", color=color, mutation_scale=13,
                linewidth=1.6, shrinkA=0, shrinkB=0, zorder=10,
            )
        )
        axes.text(
            end[0] + 0.15 * GEOMETRY.radius0, legend_height, label,
            color=color, ha="left", va="center", fontsize=12,
        )
    axes.set_xlim(lower[0] - margin, upper[0] + margin)
    axes.set_ylim(lower[1] - margin, upper[1] + margin)
    return figure


def draw(output: Path) -> None:
    import matplotlib.pyplot as plt

    output = output.resolve()
    pictures = OUTPUT.parent.resolve()
    if pictures not in output.parents:
        raise ValueError("New figures must stay under handout/pictures")
    if output.suffix.lower() != ".pdf":
        raise ValueError("Output must be a vector PDF")
    figure = build_figure()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            output, bbox_inches="tight", pad_inches=0.06,
            metadata={"CreationDate": None, "ModDate": None},
        )
        figure.savefig(
            output.with_suffix(".png"), dpi=240, bbox_inches="tight", pad_inches=0.06,
        )
    finally:
        plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    draw(args.output)
    print(f"Saved {args.output} and PNG preview; original fig1.pdf preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
