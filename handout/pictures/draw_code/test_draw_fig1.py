"""Geometry, arrow-direction, and artifact checks for the fig1 schematic."""

import hashlib
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon
import numpy as np

import draw_fig1


class CylinderSchematicTests(unittest.TestCase):
    def test_geometry_comes_from_problem_specification(self):
        self.assertIs(draw_fig1.GEOMETRY, draw_fig1.Q1.geometry)
        angles = np.linspace(0, 2 * np.pi, 25)
        points = draw_fig1.ring_points(draw_fig1.GEOMETRY.length / 2, angles)
        np.testing.assert_allclose(
            np.linalg.norm(points[:, 1:], axis=1), draw_fig1.GEOMETRY.radius0
        )

    def test_projection_is_orthographic(self):
        basis = draw_fig1.project(np.eye(3))
        np.testing.assert_allclose(basis.T @ basis, np.eye(2), atol=1e-14)

    def test_front_is_lower_right_like_reference(self):
        length = draw_fig1.GEOMETRY.length
        rear, front = draw_fig1.project(np.array([[-length / 2, 0, 0], [length / 2, 0, 0]]))
        self.assertGreater(front[0], rear[0])
        self.assertLess(front[1], rear[1])

    def test_arrows_are_radial_with_correct_directions(self):
        for arrow in draw_fig1.radial_arrows():
            self.assertEqual(arrow.start_m[0], arrow.end_m[0])
            start_radius = np.linalg.norm(arrow.start_m[1:])
            end_radius = np.linalg.norm(arrow.end_m[1:])
            self.assertLess(max(start_radius, end_radius), draw_fig1.GEOMETRY.radius0)
            np.testing.assert_allclose(
                arrow.start_m[1:] / start_radius, arrow.end_m[1:] / end_radius
            )
            if arrow.field == "T":
                self.assertLess(end_radius, start_radius)
            else:
                self.assertEqual(arrow.field, "C")
                self.assertGreater(end_radius, start_radius)

    def test_both_colors_exist_in_section_and_interior(self):
        arrows = draw_fig1.radial_arrows()
        self.assertEqual(sum(arrow.front for arrow in arrows), 36)
        self.assertEqual(sum(not arrow.front for arrow in arrows), 108)
        for front in (True, False):
            self.assertEqual(
                {arrow.field for arrow in arrows if arrow.front == front}, {"T", "C"}
            )
        interior = [arrow for arrow in arrows if not arrow.front]
        self.assertTrue(
            all(abs(arrow.start_m[0]) < draw_fig1.GEOMETRY.length / 2 for arrow in interior)
        )

    def test_surface_and_interior_have_identical_three_ring_patterns(self):
        arrows = draw_fig1.radial_arrows()
        front = [arrow for arrow in arrows if arrow.front]
        axial_positions = sorted({arrow.start_m[0] for arrow in arrows if not arrow.front})
        self.assertEqual(len(axial_positions), 3)
        for axial_m in axial_positions:
            interior = [arrow for arrow in arrows if arrow.start_m[0] == axial_m]
            self.assertEqual(len(interior), len(front))
            for inner_arrow, front_arrow in zip(interior, front):
                self.assertEqual(inner_arrow.field, front_arrow.field)
                np.testing.assert_array_equal(inner_arrow.start_m[1:], front_arrow.start_m[1:])
                np.testing.assert_array_equal(inner_arrow.end_m[1:], front_arrow.end_m[1:])
        radii = [
            min(np.linalg.norm(arrow.start_m[1:]), np.linalg.norm(arrow.end_m[1:]))
            / draw_fig1.GEOMETRY.radius0 for arrow in front
        ]
        np.testing.assert_allclose(sorted(set(np.round(radii, 8))), (0.15, 0.43, 0.71))

    def test_arrows_are_one_third_previous_length(self):
        for arrow in draw_fig1.radial_arrows():
            self.assertAlmostEqual(
                np.linalg.norm(arrow.end_m - arrow.start_m),
                draw_fig1.GEOMETRY.radius0 * 0.54 / 3,
            )

    def test_projected_arrow_groups_do_not_overlap(self):
        arrows = draw_fig1.radial_arrows()
        positions = sorted({arrow.start_m[0] for arrow in arrows})
        previous_maximum = -np.inf
        for axial_m in positions:
            group = [arrow for arrow in arrows if arrow.start_m[0] == axial_m]
            points = np.vstack([np.array([arrow.start_m, arrow.end_m]) for arrow in group])
            along_axis = draw_fig1.project(points) @ draw_fig1.SCREEN_AXIS
            self.assertGreater(along_axis.min(), previous_maximum)
            previous_maximum = along_axis.max()

    def test_scene_has_transparent_shell_and_minimal_legend(self):
        figure = draw_fig1.build_figure()
        try:
            axes = figure.axes[0]
            self.assertFalse(axes.axison)
            self.assertEqual([text.get_text() for text in axes.texts], ["热量", "水分"])
            faces = [patch for patch in axes.patches if isinstance(patch, Polygon)]
            self.assertEqual(len(faces), 4)
            self.assertTrue(all(0 < face.get_alpha() < 0.5 for face in faces))
            arrows = [patch for patch in axes.patches if isinstance(patch, FancyArrowPatch)]
            self.assertEqual(len(arrows), 146)
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
            bounds = [text.get_window_extent(renderer) for text in axes.texts]
            self.assertFalse(bounds[0].overlaps(bounds[1]))
            self.assertTrue(all(axes.bbox.contains(*box.get_points()[0]) for box in bounds))
            self.assertTrue(all(axes.bbox.contains(*box.get_points()[1]) for box in bounds))
            self.assertTrue(all(text.get_position()[0] > 0 for text in axes.texts))
            self.assertTrue(all(text.get_position()[1] > 0 for text in axes.texts))
            self.assertLess(figure.get_figheight() / figure.get_figwidth(), 0.5)
        finally:
            plt.close(figure)

    def test_cylinder_is_more_horizontal_without_changing_geometry(self):
        self.assertAlmostEqual(np.degrees(draw_fig1.SCREEN_ANGLE), -12)
        length = draw_fig1.GEOMETRY.length
        rear, front = draw_fig1.project(np.array([[-length / 2, 0, 0], [length / 2, 0, 0]]))
        self.assertAlmostEqual(
            (front[1] - rear[1]) / (front[0] - rear[0]), np.tan(np.deg2rad(-12))
        )

    def test_reject_original_or_outside_output(self):
        for path in (draw_fig1.ORIGINAL, Path("/private/tmp/fig1.pdf")):
            with self.assertRaises(ValueError):
                draw_fig1.draw(path)
        self.assertEqual(
            hashlib.sha256(draw_fig1.ORIGINAL.read_bytes()).hexdigest(),
            draw_fig1.SOURCE_SHA256,
        )

    def test_reject_non_pdf_output(self):
        with self.assertRaises(ValueError):
            draw_fig1.draw(draw_fig1.OUTPUT.with_suffix(".png"))

    def test_writes_reproducible_vector_pdf_and_preview(self):
        with tempfile.TemporaryDirectory(dir=draw_fig1.OUTPUT.parent) as directory:
            output = Path(directory) / "fig1_3d.pdf"
            draw_fig1.draw(output)
            first = output.read_bytes()
            self.assertTrue(first.startswith(b"%PDF"))
            self.assertNotIn(b"/Subtype /Image", first)
            self.assertTrue(output.with_suffix(".png").read_bytes().startswith(b"\x89PNG"))
            draw_fig1.draw(output)
            self.assertEqual(output.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
