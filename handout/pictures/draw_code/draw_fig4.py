"""Redraw fig4 moisture profiles using the final fig3 curtain style."""

from __future__ import annotations

import argparse
import hashlib
import re
import zlib
from pathlib import Path

import numpy as np

import draw_fig3

HERE = Path(__file__).resolve().parent
DATA = HERE / "fig4_profiles.csv"
ORIGINAL = draw_fig3.PATHS.ROOT / "handout" / "figures" / "fig4.pdf"
OUTPUT = HERE.parent / "fig4_waterfall.pdf"
SOURCE_SHA256 = "6b2be140ebe0e3bbee46df93b52376ab205f6f3dd45577e5fde27f94afed2aff"
TIMES_S = draw_fig3.TIMES_S
PDF_RADIUS = (43.2625, 632.007333)
PDF_MOISTURE = (61.749475, 216.739461)
MOISTURE_TICKS = (1.6, 2.6)


def extract_profiles(source: Path) -> np.ndarray:
    """Recover displayed vertices using the original PDF's labeled axis ticks."""
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Extraction requires the unmodified original fig4.pdf")
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
        if np.allclose(vertices[[0, -1], 0], PDF_RADIUS, rtol=0, atol=1e-6):
            curves.append(vertices)
    if len(curves) != len(TIMES_S):
        raise ValueError(f"Expected five source curves, found {len(curves)}")
    rows = []
    for time_s, vertices in zip(TIMES_S, curves):
        r_cm = (vertices[:, 0] - PDF_RADIUS[0]) * 2 / (
            PDF_RADIUS[1] - PDF_RADIUS[0]
        )
        C = MOISTURE_TICKS[0] + (vertices[:, 1] - PDF_MOISTURE[0]) * (
            MOISTURE_TICKS[1] - MOISTURE_TICKS[0]
        ) / (PDF_MOISTURE[1] - PDF_MOISTURE[0])
        rows.append(
            np.column_stack(
                (np.full(len(vertices), time_s), draw_fig3.UNITS.cm_to_m(r_cm), C)
            )
        )
    profiles = np.concatenate(rows)
    validate_profiles(profiles)
    return profiles


def validate_profiles(profiles: np.ndarray) -> None:
    draw_fig3.validate_profiles(profiles, field="C")


def draw(profiles: np.ndarray, output: Path) -> None:
    draw_fig3.draw(profiles, output, field="C")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-source", type=Path, help="Original, unmodified fig4.pdf")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.resolve().parent == ORIGINAL.parent.resolve():
        parser.error("Original handout/figures files must not be overwritten")
    if args.extract_source:
        profiles = extract_profiles(args.extract_source)
        np.savetxt(
            DATA,
            profiles,
            delimiter=",",
            fmt="%.17g",
            header=(
                f"source_pdf_sha256={SOURCE_SHA256}\n"
                "Source: original fig4.pdf displayed vector vertices, not full solver output.\n"
                "time_s,r_m,C_kg_per_kg"
            ),
        )
    else:
        profiles = np.loadtxt(DATA, delimiter=",")
    draw(profiles, args.output)
    print(f"Saved {args.output}; {len(TIMES_S)} curves, {len(profiles)} original PDF vertices.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
