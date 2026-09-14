"""Data-preservation checks for the handout-only plotting program."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

import draw_fig3


class FigureDataTests(unittest.TestCase):
    def test_upper_axis_compression_preserves_zero_and_break(self):
        for lower, scale in ((27, 0.42), (1.4, 3.4), (27, 0.18), (0.8, 2.4)):
            self.assertEqual(draw_fig3.field_height(0, lower, scale), 0)
            break_value = lower + (0.40 - 0.28) / scale
            self.assertAlmostEqual(draw_fig3.field_height(break_value, lower, scale), 0.40)
            self.assertAlmostEqual(
                draw_fig3.field_height(lower + 2, lower, scale)
                - draw_fig3.field_height(lower + 1, lower, scale),
                scale * 0.70,
            )

    def setUp(self):
        self.profiles = np.loadtxt(draw_fig3.DATA, delimiter=",")

    def test_original_times_and_radial_coverage(self):
        draw_fig3.validate_profiles(self.profiles)

    def test_saved_vertices_match_preserved_original(self):
        original = draw_fig3.PATHS.ROOT / "handout" / "figures" / "fig3.pdf"
        np.testing.assert_array_equal(draw_fig3.extract_profiles(original), self.profiles)

    def test_output_is_separate_from_original(self):
        self.assertEqual(draw_fig3.OUTPUT.parent.name, "pictures")
        self.assertEqual(draw_fig3.OUTPUT.name, "fig3_waterfall.pdf")

    def test_first_slice_gap_is_halved(self):
        first_time_depth = draw_fig3.TIMES_S[0] / draw_fig3.TIMES_S[-1]
        previous_gap = first_time_depth + 0.24
        current_gap = first_time_depth + draw_fig3.TIME_INSET
        self.assertAlmostEqual(current_gap, previous_gap / 2)

    def test_reject_nonfinite_data(self):
        self.profiles[0, 2] = np.nan
        with self.assertRaises(ValueError):
            draw_fig3.validate_profiles(self.profiles)

    def test_reject_missing_time(self):
        with self.assertRaises(ValueError):
            draw_fig3.validate_profiles(self.profiles[self.profiles[:, 0] != 300])

    def test_reject_celsius_as_internal_temperature(self):
        self.profiles[:, 2] = draw_fig3.UNITS.k_to_c(self.profiles[:, 2])
        with self.assertRaises(ValueError):
            draw_fig3.validate_profiles(self.profiles)

    def test_draw_preserves_input(self):
        original = self.profiles.copy()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fig3.pdf"
            draw_fig3.draw(self.profiles, output)
            self.assertTrue(output.read_bytes().startswith(b"%PDF"))
        np.testing.assert_array_equal(self.profiles, original)

    def test_only_top_edges_are_emphasized(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(plt, "close"):
                draw_fig3.draw(self.profiles, Path(directory) / "fig3.pdf")
                figure = plt.gcf()
            top_edges = [
                line for line in figure.axes[0].lines if len(line.get_xdata()) > 2
            ]
            self.assertEqual(len(top_edges), 5)
            for edge, time_s, color in zip(
                top_edges, reversed(draw_fig3.TIMES_S), reversed(draw_fig3.COLORS)
            ):
                self.assertEqual(edge.get_linewidth(), 1.6)
                np.testing.assert_allclose(
                    edge.get_color(), np.asarray(to_rgb(color)) * 0.88
                )
                curve = self.profiles[self.profiles[:, 0] == time_s]
                np.testing.assert_array_equal(
                    edge.get_xdata(),
                    draw_fig3.UNITS.m_to_cm(curve[:, 1])
                    + 1.20 * draw_fig3.time_depth(time_s),
                )
            side_edges = [
                line for line in figure.axes[0].lines
                if isinstance(line.get_color(), str) and line.get_color() in draw_fig3.COLORS
            ]
            self.assertEqual(len(side_edges), 15)
            self.assertTrue(all(edge.get_linewidth() == 1.0 for edge in side_edges))
            plt.close(figure)


if __name__ == "__main__":
    unittest.main()
