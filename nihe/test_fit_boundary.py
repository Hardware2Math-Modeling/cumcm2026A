"""Independent checks; generated ideal curves below are tests, not observations."""

import hashlib
import unittest

import numpy as np

from fit_boundary import (
    MODELS,
    SOURCE,
    Curve,
    FittedBoundary,
    bootstrap_plateau,
    compare_models,
    fit_curve,
    read_attachment,
    remaining,
)


class AttachmentTests(unittest.TestCase):
    def test_original_structure_units_and_read_only(self):
        before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        time_s, fields, metadata = read_attachment()
        self.assertEqual(metadata["count"], 241)
        self.assertEqual(metadata["range"], "A1:C242")
        np.testing.assert_array_equal(time_s, np.arange(0, 14401, 60))
        self.assertAlmostEqual(fields["T_amb"][0], 301.15)
        self.assertAlmostEqual(fields["C_amb"][0], 0.01963)
        self.assertEqual(before, metadata["sha256"])
        self.assertEqual(before, hashlib.sha256(SOURCE.read_bytes()).hexdigest())


class CurveTests(unittest.TestCase):
    def test_all_models_start_monotone_and_converge(self):
        time_s = np.r_[0, np.geomspace(1e-5, 1e8, 500)]
        for model in MODELS:
            with self.subTest(model=model):
                fraction = remaining(model, time_s, 1200.0, 1.3)
                self.assertAlmostEqual(fraction[0], 1.0)
                self.assertTrue(np.all(np.isfinite(fraction)))
                self.assertTrue(np.all(np.diff(fraction) <= 1e-14))
                self.assertTrue(np.all((fraction >= 0) & (fraction <= 1)))
                self.assertLess(fraction[-1], 1e-10)

    def test_extreme_horizon_is_finite(self):
        for model in MODELS:
            self.assertEqual(float(remaining(model, 1e300, 1200.0, 1.3)), 0.0)

    def test_reject_invalid_prediction_inputs(self):
        for invalid in (-1, np.nan, np.inf, [1, -1]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                remaining("exponential", invalid, 1000)
        with self.assertRaises(ValueError):
            remaining("unknown", 0, 1000)
        with self.assertRaises(ValueError):
            remaining("exponential", 0, 0)
        with self.assertRaises(ValueError):
            remaining("quadratic", 0, 1000, -1)

    def test_exponential_settling_time_matches_closed_form(self):
        curve = Curve("exponential", np.array([323.15, 22.0, 1200.0]), 0, 0, 0, (), 0)
        for fraction in (0.01, 0.001):
            self.assertAlmostEqual(curve.settling_time(fraction), -1200 * np.log(fraction))
        with self.assertRaises(ValueError):
            curve.settling_time(0)

    def test_recovery_from_ideal_curves_not_measurements(self):
        time_s = np.arange(0, 14401, 120, dtype=float)
        for model in MODELS:
            with self.subTest(model=model):
                parameters = [323.15, 22.0, 2200.0]
                if model != "exponential":
                    parameters += [0.8 if model == "quadratic" else 1.4]
                ideal = Curve(model, np.array(parameters), 0, 0, 0, (), 0)
                observations = ideal.predict(time_s)
                recovered = fit_curve(model, time_s, observations)
                np.testing.assert_allclose(recovered.predict(time_s), observations, atol=1e-5)
                self.assertAlmostEqual(recovered.plateau, ideal.plateau, places=5)
                self.assertEqual(recovered.failed_starts, 0)

    def test_temperature_translation_invariance(self):
        time_s, fields, _ = read_attachment()
        kelvin = fit_curve("logistic", time_s, fields["T_amb"])
        translated = fit_curve("logistic", time_s, fields["T_amb"] - 273.15)
        self.assertAlmostEqual(kelvin.plateau - translated.plateau, 273.15, places=6)
        self.assertAlmostEqual(kelvin.rmse, translated.rmse, places=7)

    def test_reject_invalid_training_series(self):
        time_s = np.arange(20, dtype=float)
        for invalid in (np.ones(20), np.full(20, np.nan), np.arange(19)):
            with self.assertRaises(ValueError):
                fit_curve("exponential", time_s, invalid)
        with self.assertRaises(ValueError):
            fit_curve("exponential", time_s[::-1], time_s)


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.time_s, cls.fields, _ = read_attachment()

    def test_final_holdout_cannot_change_selection_score(self):
        comparisons, selected = compare_models(self.time_s, self.fields["C_amb"])
        perturbed = self.fields["C_amb"].copy()
        perturbed[self.time_s > 0.875 * self.time_s[-1]] += 0.002
        alternative, selected_alternative = compare_models(self.time_s, perturbed)
        self.assertEqual(selected, selected_alternative)
        for index, original in enumerate(comparisons):
            changed = alternative[index]
            self.assertEqual(original["cv_rmse"], changed["cv_rmse"])
        expected = min(comparisons, key=lambda entry: entry["cv_rmse"])
        self.assertEqual(expected["model"], selected)

    def test_bootstrap_reproducible_and_audited(self):
        curve = fit_curve("logistic", self.time_s, self.fields["T_amb"])
        settings = dict(repetitions=20, block_length=6, seed=17)
        first = bootstrap_plateau(curve, self.time_s, self.fields["T_amb"], **settings)
        second = bootstrap_plateau(curve, self.time_s, self.fields["T_amb"], **settings)
        np.testing.assert_array_equal(first["interval"], second["interval"])
        self.assertEqual(first["success"] + len(first["failures"]), 20)
        self.assertLess(first["interval"][0], first["interval"][1])
        with self.assertRaises(ValueError):
            bootstrap_plateau(
                curve, self.time_s, self.fields["T_amb"], repetitions=2, block_length=6, seed=17
            )

    def test_boundary_returns_si_scalar_and_vector(self):
        curves = {
            field: fit_curve("logistic", self.time_s, observations)
            for field, observations in self.fields.items()
        }
        boundary = FittedBoundary(**curves)
        temperature, concentration = boundary.ambient([0, 14400, 259200])
        self.assertEqual(temperature.shape, (3,))
        self.assertTrue(np.all(temperature > 273.15))
        self.assertTrue(np.all(concentration > 0))
        scalar_temperature, scalar_concentration = boundary.ambient(259200)
        self.assertAlmostEqual(scalar_temperature, curves["T_amb"].plateau)
        self.assertAlmostEqual(scalar_concentration, curves["C_amb"].plateau)


if __name__ == "__main__":
    unittest.main()
