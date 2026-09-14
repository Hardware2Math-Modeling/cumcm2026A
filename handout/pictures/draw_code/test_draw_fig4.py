"""Check original moisture vertices and the shared curtain renderer."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

import draw_fig3
import draw_fig4


class FigureMoistureTests(unittest.TestCase):
    def setUp(self):
        self.profiles = np.loadtxt(draw_fig4.DATA, delimiter=",")

    def test_saved_vertices_match_original(self):
        np.testing.assert_array_equal(
            draw_fig4.extract_profiles(draw_fig4.ORIGINAL), self.profiles
        )
        self.assertEqual(len(self.profiles), 179)

    def test_pdf_calibration_at_curve_endpoints(self):
        first_curve = self.profiles[self.profiles[:, 0] == 100]
        self.assertAlmostEqual(first_curve[0, 2], 2.55, places=7)
        last_curve = self.profiles[self.profiles[:, 0] == 1800]
        recovered_pdf_height = 61.749475 + (last_curve[-1, 2] - 1.6) * (
            216.739461 - 61.749475
        )
        self.assertAlmostEqual(recovered_pdf_height, 47.836762, places=6)

    def test_reject_wrong_source(self):
        with self.assertRaises(ValueError):
            draw_fig4.extract_profiles(draw_fig4.ORIGINAL.with_name("fig3.pdf"))

    def test_reject_nonfinite_values(self):
        self.profiles[0, 2] = np.nan
        with self.assertRaises(ValueError):
            draw_fig4.validate_profiles(self.profiles)

    def test_reject_missing_time(self):
        with self.assertRaises(ValueError):
            draw_fig4.validate_profiles(self.profiles[self.profiles[:, 0] != 300])

    def test_reject_incorrect_units(self):
        self.profiles[:, 1] *= 100
        with self.assertRaises(ValueError):
            draw_fig4.validate_profiles(self.profiles)

    def test_reject_values_outside_plot_range(self):
        self.profiles[0, 2] = 0.1
        with self.assertRaises(ValueError):
            draw_fig4.validate_profiles(self.profiles)

    def test_protect_original_pdf(self):
        with self.assertRaises(ValueError):
            draw_fig4.draw(self.profiles, draw_fig4.ORIGINAL)
        self.assertEqual(
            hashlib.sha256(draw_fig4.ORIGINAL.read_bytes()).hexdigest(),
            draw_fig4.SOURCE_SHA256,
        )

    def test_draw_preserves_data_and_style(self):
        original = self.profiles.copy()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / draw_fig4.OUTPUT.name
            with patch.object(plt, "close"):
                draw_fig4.draw(self.profiles, output)
                figure = plt.gcf()
            self.assertTrue(output.read_bytes().startswith(b"%PDF"))
            axes = figure.axes[0]
            self.assertEqual(len(axes.patches), 6)
            for curtain in axes.patches[1:]:
                self.assertEqual(curtain.get_alpha(), 0.10)
            top_edges = [
                line for line in axes.lines
                if len(line.get_xdata()) > 2
            ]
            self.assertEqual(len(top_edges), 5)
            for edge, time_s, color in zip(top_edges, draw_fig4.TIMES_S, draw_fig3.COLORS):
                self.assertEqual(edge.get_linewidth(), 1.6)
                np.testing.assert_allclose(
                    edge.get_color(), np.asarray(to_rgb(color)) * 0.88
                )
                curve = self.profiles[self.profiles[:, 0] == time_s]
                depth = (
                    (1900 - time_s) / draw_fig4.TIMES_S[-1] + draw_fig3.TIME_INSET
                )
                r_cm = draw_fig3.UNITS.m_to_cm(curve[:, 1])
                np.testing.assert_array_equal(edge.get_xdata(), r_cm + 1.20 * depth)
                np.testing.assert_array_equal(
                    edge.get_ydata(),
                    0.40 + 0.70 * (0.28 + 3.4 * (curve[:, 2] - 1.4) - 0.40)
                    + 1.05 * depth - 0.24 * r_cm,
                )
            figure.canvas.draw()
            labels = [
                text for text in axes.texts
                if text.get_text() and text.get_rotation() % 90 == 0
            ]
            boxes = [
                text.get_window_extent(figure.canvas.get_renderer()) for text in labels
            ]
            for index, box in enumerate(boxes):
                for other in boxes[index + 1:]:
                    self.assertFalse(box.overlaps(other), "Overlapping axis labels")
            plt.close(figure)
        np.testing.assert_array_equal(self.profiles, original)

    def test_reverse_time_preserves_gap_and_intervals(self):
        times = np.asarray(draw_fig4.TIMES_S)
        depths = draw_fig3.time_depth(times, reverse=True)
        self.assertAlmostEqual(depths[-1], draw_fig3.time_depth(times[0]))
        np.testing.assert_allclose(np.diff(depths), -np.diff(times) / times[-1])
        self.assertTrue(np.all(np.diff(depths) < 0))

    def test_fig3_render_matches_saved_output(self):
        profiles = np.loadtxt(draw_fig3.DATA, delimiter=",")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fig3.pdf"
            draw_fig3.draw(profiles, output)
            self.assertEqual(output.read_bytes(), draw_fig3.OUTPUT.read_bytes())


if __name__ == "__main__":
    unittest.main()
