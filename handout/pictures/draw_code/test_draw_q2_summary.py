"""Check detailed Excel provenance and complete five-position curtain geometry."""

from dataclasses import replace
import hashlib
from pathlib import Path
import re
import unittest

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np
import openpyxl

import draw_q2_summary as drawing


class Q2HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = drawing.load_histories()

    def test_full_one_second_grid_and_five_positions(self):
        drawing.validate(self.data)
        self.assertEqual(len(self.data.time_s), 10801)

    def test_every_selected_cell_matches_excel(self):
        workbook = openpyxl.load_workbook(drawing.SOURCE, read_only=True, data_only=True)
        try:
            for field, sheet in drawing.SHEETS.items():
                rows = workbook[sheet].iter_rows(min_row=2, max_row=10802, values_only=True)
                expected = np.asarray([[row[index] for index in (1, 6, 11, 16, 21)]
                                       for row in rows])
                if field == "T":
                    expected = drawing.UNITS.c_to_k(expected)
                np.testing.assert_array_equal(getattr(self.data, field), expected)
        finally:
            workbook.close()

    def test_records_single_last_digit_difference_from_old_tables(self):
        differences = []
        for field in drawing.SHEETS:
            path = drawing.PATHS.ROOT / "handout" / "tables" / f"q2_{field}.tex"
            rows = re.findall(r"^(\d\.\d) & (.*?)\\\\", path.read_text(), re.M)
            self.assertEqual(len(rows), 6)
            for hours, cells in rows:
                expected = np.asarray([float(cell.strip()) for cell in cells.split("&")])
                actual = getattr(self.data, field)[int(float(hours) * 3600)]
                if field == "T":
                    actual = drawing.UNITS.k_to_c(actual)
                for index in np.flatnonzero(np.abs(actual - expected) > 1e-10):
                    differences.append(
                        (field, float(hours), index, round(float(actual[index]), 4),
                         float(expected[index]))
                    )
        self.assertEqual(differences, [("T", 1.5, 4, 47.1400, 47.1401)])

    def test_reject_missing_second(self):
        with self.assertRaises(ValueError):
            drawing.validate(replace(self.data, time_s=self.data.time_s[::2]))

    def test_reject_wrong_units_and_nonfinite_values(self):
        for values in (drawing.UNITS.k_to_c(self.data.T), self.data.T * np.nan):
            with self.assertRaises(ValueError):
                drawing.validate(replace(self.data, T=values))

    def test_surface_front_for_moisture_with_same_gap(self):
        temperature = drawing.project(0, 0, 0, field="T")
        moisture = drawing.project(0, drawing.RADIUS_M[-1], 0, field="C")
        np.testing.assert_allclose(temperature, moisture)
        self.assertGreater(temperature[0], 0)

    def test_preserves_every_vertex_and_final_style(self):
        for field in drawing.SHEETS:
            original = getattr(self.data, field).copy()
            figure = drawing.build_figure(self.data, field)
            try:
                axes = figure.axes[0]
                edges = [line for line in axes.lines if len(line.get_xdata()) > 2]
                self.assertEqual(len(edges), 5)
                self.assertEqual(len(axes.patches), 6)
                self.assertTrue(all(patch.get_alpha() == 0.10 for patch in axes.patches[1:]))
                order = range(5) if field == "C" else reversed(range(5))
                for edge, index in zip(edges, order):
                    values = getattr(self.data, field)[:, index]
                    if field == "T":
                        values = drawing.UNITS.k_to_c(values)
                    horizontal, vertical = drawing.project(
                        self.data.time_s, self.data.radius_m[index], values, field=field
                    )
                    np.testing.assert_array_equal(edge.get_xdata(), horizontal)
                    np.testing.assert_array_equal(edge.get_ydata(), vertical)
                    self.assertEqual(len(horizontal), 10801)
                    self.assertEqual(edge.get_linewidth(), 1.6)
                    np.testing.assert_allclose(edge.get_color(),
                                               np.asarray(to_rgb(drawing.COLORS[index])) * 0.88)
                figure.canvas.draw()
                renderer = figure.canvas.get_renderer()
                radius_label = next(
                    text for text in axes.texts if text.get_text() == "距中心轴的距离 / cm"
                )
                far_radius = 0 if field == "C" else drawing.RADIUS_M[-1]
                midpoint = (
                    np.asarray(drawing.project(10800, 0, 0, field=field, front=True))
                    + np.asarray(drawing.project(10800, far_radius, 0, field=field))
                ) / 2
                displacement = np.asarray(radius_label.get_position()) - midpoint
                self.assertAlmostEqual(np.dot(displacement, [1.20, 1.05]), 0)
                self.assertAlmostEqual(np.linalg.norm(displacement), 0.58)
                self.assertEqual(radius_label.get_ha(), "center")
                texts = [text for text in axes.texts
                         if text.get_text() and text.get_rotation() % 90 == 0]
                boxes = [text.get_window_extent(renderer) for text in texts]
                for index, box in enumerate(boxes):
                    self.assertTrue(all(not box.overlaps(other) for other in boxes[index + 1:]))
            finally:
                plt.close(figure)
            np.testing.assert_array_equal(getattr(self.data, field), original)

    def test_original_is_protected(self):
        with self.assertRaises(ValueError):
            drawing.draw(self.data, "T", drawing.ORIGINAL)
        self.assertEqual(
            hashlib.sha256(drawing.ORIGINAL.read_bytes()).hexdigest(),
            "ae540176c26e0f7e8ea9dcc39bac28d75d590f064c390fe4e7c0f506bebd3cb4",
        )

    def test_reject_output_outside_pictures(self):
        with self.assertRaises(ValueError):
            drawing.draw(self.data, "C", Path("/private/tmp/q2.pdf"))


if __name__ == "__main__":
    unittest.main()
