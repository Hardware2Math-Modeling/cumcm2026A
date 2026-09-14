"""Fit an asymptotic oven temperature to attachment 1, using K and seconds.

This estimates a conditional setpoint from the four-hour record. It does not
claim that an uncontrolled oven will follow the fitted asymptote indefinitely.
Only results/validation/ambient_fit.json and data/processed/ambient_fit.csv
are written. No PDE simulation or Git operation is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.special import expit
from scipy.stats import linregress, t as student_t

from _bootstrap import setup

setup()

from common.io_excel import read_attachment  # noqa: E402
from common.paths import ROOT, attachment_path  # noqa: E402
from common.units import c_to_k, k_to_c  # noqa: E402


def candidate_models(T0):
    """Monotone heating candidates with finite asymptotes, all in SI units."""
    def exponential_free(t, S, A, tau):
        return S - A * np.exp(-t / tau)

    def exponential_fixed_initial(t, S, tau):
        return S - (S - T0) * np.exp(-t / tau)

    def logistic_fixed_initial(t, S, B, tau):
        # Algebraically: S-(S-T0)*(1+B)/(1+B*exp(t/tau)).
        # expit prevents overflow for the broad exploratory tau bounds.
        return S - (S - T0) * (1 + B) * expit(-np.log(B) - t / tau)

    def weibull_fixed_initial(t, S, tau, beta):
        return S - (S - T0) * np.exp(-(t / tau) ** beta)

    return {
        "exponential_free": {
            "function": exponential_free,
            "parameter_names": ["S_K", "A_K", "tau_s"],
            "formula": "T(t)=S-A*exp(-t/tau)",
            "initial": [T0 + 22, 22, 1800],
            "bounds": ([T0, 0, 1], [T0 + 200, 300, 144000]),
            "initial_temperature_fixed": False,
        },
        "exponential_fixed_initial": {
            "function": exponential_fixed_initial,
            "parameter_names": ["S_K", "tau_s"],
            "formula": "T(t)=S-(S-T0)*exp(-t/tau)",
            "initial": [T0 + 22, 1800],
            "bounds": ([T0, 1], [T0 + 200, 144000]),
            "initial_temperature_fixed": True,
        },
        "logistic_fixed_initial": {
            "function": logistic_fixed_initial,
            "parameter_names": ["S_K", "B_dimensionless", "tau_s"],
            "formula": "T(t)=S-(S-T0)*(1+B)/(1+B*exp(t/tau))",
            "initial": [T0 + 22, 2, 1800],
            "bounds": ([T0, 0.001, 100], [T0 + 200, 1000, 144000]),
            "initial_temperature_fixed": True,
        },
        "weibull_fixed_initial": {
            "function": weibull_fixed_initial,
            "parameter_names": ["S_K", "tau_s", "beta_dimensionless"],
            "formula": "T(t)=S-(S-T0)*exp(-(t/tau)**beta)",
            "initial": [T0 + 22, 1800, 1.1],
            "bounds": ([T0, 1, 0.25], [T0 + 200, 144000, 3]),
            "initial_temperature_fixed": True,
        },
    }


def fit_model(model, t, T, initial=None):
    with warnings.catch_warnings():
        warnings.simplefilter("error", OptimizeWarning)
        params, covariance = curve_fit(
            model["function"], t, T,
            p0=model["initial"] if initial is None else initial,
            bounds=model["bounds"], maxfev=20000,
            ftol=1e-12, xtol=1e-12, gtol=1e-12,
        )
    if not np.all(np.isfinite(params)) or not np.all(np.isfinite(covariance)):
        raise RuntimeError("Nonfinite fitted parameters or covariance")
    return params, covariance


def diagnostics(residual, parameter_count):
    residual = np.asarray(residual)
    n = residual.size
    sse = float(residual @ residual)
    aic = n * np.log(sse / n) + 2 * parameter_count
    return {
        "sample_count": n,
        "rmse_K": float(np.sqrt(sse / n)),
        "mae_K": float(np.mean(np.abs(residual))),
        "max_abs_error_K": float(np.max(np.abs(residual))),
        "mean_observed_minus_fitted_K": float(np.mean(residual)),
        "sse_K2": sse,
        "aicc": float(aic + 2 * parameter_count * (parameter_count + 1)
                      / (n - parameter_count - 1)),
        "lag1_residual_correlation": float(np.corrcoef(residual[:-1], residual[1:])[0, 1]),
        "durbin_watson": float(np.diff(residual) @ np.diff(residual) / sse),
    }


def param_mapping(model, parameters):
    return dict(zip(model["parameter_names"], map(float, parameters)))


def covariance_report(model, parameters, covariance, sample_count):
    se = np.sqrt(np.diag(covariance))
    quantile = float(student_t.ppf(0.975, sample_count - len(parameters)))
    interval = np.column_stack((parameters - quantile * se, parameters + quantile * se))
    correlation = covariance / np.outer(se, se)
    return {
        "parameter_order": model["parameter_names"],
        "covariance": covariance.tolist(),
        "parameter_correlation": correlation.tolist(),
        "standard_errors": param_mapping(model, se),
        "conditional_95pct_intervals": dict(zip(model["parameter_names"], interval.tolist())),
        "S_95pct_C": k_to_c(interval[0]).tolist(),
        "assumptions": "Local nonlinear least-squares covariance; independent constant-variance residuals; candidate and fixed T0 treated as known; not a future-temperature prediction interval.",
    }


def bootstrap_asymptote(model, t, T, parameters, count, seed, block_length):
    prediction = model["function"](t, *parameters)
    residual = T - prediction
    # The observed initial value anchors fixed-initial candidates; do not
    # resample that exactly constrained observation as independent noise.
    start = 1 if model["initial_temperature_fixed"] else 0
    pool = residual[start:] - np.mean(residual[start:])
    rng = np.random.default_rng(seed)
    samples = []
    failures = []
    for iteration in range(count):
        block_starts = rng.integers(0, len(pool), size=int(np.ceil(len(pool) / block_length)))
        indexes = (block_starts[:, None] + np.arange(block_length)) % len(pool)
        noise = pool[indexes.ravel()[:len(pool)]]
        simulated = prediction.copy()
        simulated[start:] += noise
        if start:
            simulated[0] = T[0]
        try:
            fitted, _ = fit_model(model, t, simulated, initial=parameters)
            samples.append(float(fitted[0]))
        except (RuntimeError, ValueError, OptimizeWarning) as error:
            failures.append({"iteration": iteration, "error": str(error)})
    if len(samples) < 0.95 * count:
        raise RuntimeError(f"Bootstrap failed for {len(failures)}/{count} replicates")
    return {
        "method": "circular moving-block residual bootstrap" if block_length > 1 else "iid centered residual bootstrap",
        "replicates_requested": count,
        "replicates_successful": len(samples),
        "seed": seed,
        "block_length_observations": block_length,
        "block_duration_s": float(block_length * np.median(np.diff(t))),
        "S_95pct_K": np.quantile(samples, [0.025, 0.975]).tolist(),
        "S_95pct_C": k_to_c(np.quantile(samples, [0.025, 0.975])).tolist(),
        "S_standard_deviation_K": float(np.std(samples, ddof=1)),
        "failures": failures,
        "interpretation": "Conditional parameter uncertainty with measured T0 fixed. Model choice, sensor bias, future controller changes and model-form error are not included.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    if args.bootstrap < 100:
        raise ValueError("At least 100 bootstrap replicates are required")
    raw = read_attachment(1)
    t = raw["时间"].to_numpy(dtype=float)
    T = c_to_k(raw["温度"].to_numpy(dtype=float))
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(T)) or np.any(np.diff(t) <= 0):
        raise ValueError("Attachment time and temperature must be finite and time strictly increasing")
    if t[0] != 0.0 or t[-1] != 14400.0:
        raise ValueError("Expected attachment 1 to cover 0–14400 s")
    train = t <= 10800.0
    validation = ~train
    T0 = float(T[0])
    candidates = candidate_models(T0)
    summaries = {}
    fitted = {}
    frame = {"t_s": t, "T_observed_K": T, "T_observed_C": k_to_c(T),
             "holdout_3_to_4h": validation.astype(int)}
    for name, model in candidates.items():
        p, cov = fit_model(model, t, T)
        pt, covt = fit_model(model, t[train], T[train])
        prediction = model["function"](t, *p)
        cv_prediction = model["function"](t, *pt)
        summaries[name] = {
            "formula": model["formula"],
            "parameter_count": len(p),
            "initial_temperature_fixed": model["initial_temperature_fixed"],
            "parameters": param_mapping(model, p),
            "T_asymptote_C": float(k_to_c(p[0])),
            "full_fit": diagnostics(T - prediction, len(p)),
            "holdout": diagnostics(T[validation] - cv_prediction[validation], len(p)),
            "training_fit": diagnostics(T[train] - cv_prediction[train], len(p)),
            "training_parameters": param_mapping(model, pt),
            "training_covariance": covt.tolist(),
            "parameter_bounds": [list(x) for x in model["bounds"]],
            "uncertainty": covariance_report(model, p, cov, len(t)),
        }
        fitted[name] = (p, cov)
        frame[f"T_{name}_K"] = prediction
        frame[f"residual_{name}_K"] = T - prediction
        frame[f"T_train3h_{name}_K"] = cv_prediction
        print(f"{name}: S={k_to_c(p[0]):.8f} C, RMSE={summaries[name]['full_fit']['rmse_K']:.8f} K, holdout RMSE={summaries[name]['holdout']['rmse_K']:.8f} K", flush=True)

    selected = min(summaries, key=lambda name: summaries[name]["holdout"]["rmse_K"])
    model = candidates[selected]
    parameters, covariance = fitted[selected]
    selected_prediction = model["function"](t, *parameters)
    frame["T_fitted_K"] = selected_prediction
    # Window stability and late-record slope are identifiability diagnostics,
    # not additional holdouts used to retune the selected functional form.
    window_fits = []
    for end in (7200.0, 9000.0, 10800.0, 12600.0, 14400.0):
        mask = t <= end
        p, cov = fit_model(model, t[mask], T[mask], initial=parameters)
        window_fits.append({"fit_end_s": end, "sample_count": int(mask.sum()),
                            "parameters": param_mapping(model, p), "S_C": float(k_to_c(p[0])),
                            "S_standard_error_K": float(np.sqrt(cov[0, 0]))})
    late_slope = linregress(t[validation], T[validation])
    slope_quantile = student_t.ppf(0.975, int(validation.sum()) - 2)
    lower, upper = np.asarray(model["bounds"], dtype=float)
    span = upper - lower
    scaled_distance = np.minimum((parameters - lower) / span, (upper - parameters) / span)
    iid = bootstrap_asymptote(model, t, T, parameters, args.bootstrap, 20260911, 1)
    blocked = bootstrap_asymptote(model, t, T, parameters, args.bootstrap, 20260912, 5)
    pressure_note = "The drying comparison should use this fitted constant only after the measured 4 h record, with literature RH 0.20 held independently; humidity is not fitted by this script."
    report = {
        "source": {"path": str(attachment_path(1).relative_to(ROOT)),
                   "sha256": hashlib.sha256(attachment_path(1).read_bytes()).hexdigest(),
                   "temperature_column": "温度", "input_temperature_unit": "degC",
                   "fit_temperature_unit": "K", "fit_time_unit": "s",
                   "sample_count": len(t), "time_range_s": [float(t[0]), float(t[-1])],
                   "initial_temperature_K": T0},
        "validation_protocol": {"training_range_s": [0, 10800], "training_count": int(train.sum()),
                                "holdout_range_s": [float(t[validation][0]), 14400],
                                "holdout_count": int(validation.sum()),
                                "selection_rule": "minimum last-hour holdout RMSE across four predeclared monotone asymptotic candidates, followed by refit on all data",
                                "warning": "The holdout selects the candidate and is not an untouched final test set; parameter intervals condition on the selected model."},
        "candidates": summaries,
        "selected_model": selected,
        "selected": {"model": selected, "T_inf_K": float(parameters[0]),
                     "T_inf_ci95_K": blocked["S_95pct_K"],
                     "rmse_K": summaries[selected]["full_fit"]["rmse_K"],
                     "holdout_rmse_K": summaries[selected]["holdout"]["rmse_K"],
                     "interval_method": f"{args.bootstrap}-replicate circular moving-block residual bootstrap, block length 5 observations; conditional on selected model and fixed T0",
                     "formula": model["formula"],
                     "parameters": param_mapping(model, parameters)},
        "selected_formula": model["formula"],
        "selected_parameters": param_mapping(model, parameters),
        "recommended_temperature_K": float(parameters[0]),
        "recommended_temperature_C": float(k_to_c(parameters[0])),
        "recommended_relative_humidity": 0.20,
        "relative_humidity_source": "Ju et al. 2016, doi:10.1515/ijfe-2015-0340; this script does not estimate RH",
        "full_fit_rmse_K": summaries[selected]["full_fit"]["rmse_K"],
        "holdout_rmse_K": summaries[selected]["holdout"]["rmse_K"],
        "covariance_uncertainty": covariance_report(model, parameters, covariance, len(t)),
        "bootstrap_iid": iid,
        "bootstrap_block5": blocked,
        "recommended_temperature_95pct_K": blocked["S_95pct_K"],
        "recommended_temperature_95pct_C": blocked["S_95pct_C"],
        "identifiability": {"window_fits": window_fits,
                            "scaled_distance_to_parameter_bounds": param_mapping(model, scaled_distance),
                            "asymptote_minus_fitted_4h_K": float(parameters[0] - selected_prediction[-1]),
                            "last_hour_observed_mean_K": float(np.mean(T[validation])),
                            "last_hour_observed_mean_C": float(k_to_c(np.mean(T[validation]))),
                            "last_hour_observed_slope_K_per_s": float(late_slope.slope),
                            "last_hour_observed_slope_95pct_K_per_s": [float(late_slope.slope - slope_quantile * late_slope.stderr), float(late_slope.slope + slope_quantile * late_slope.stderr)],
                            "description": "A late-record plateau, finite covariance and stability across truncated windows support a locally identifiable asymptote under the fitted model; none guarantees the unobserved long-term controller setting."},
        "decision_note": pressure_note,
        "limitations": [
            "The record covers only 4 hours and does not prove indefinite asymptotic behavior.",
            "Confidence intervals quantify conditional parameter uncertainty, not future observed temperature or material-model uncertainty.",
            "Fixed T0 treats the first reading as known; thermometer calibration error and uncertainty in T0 are excluded.",
            "The fitted approximately 50 C setpoint is an independent design comparison, not a claim of optimal medicinal quality.",
            "Neither material moisture diffusivity nor shrinkage is reidentified from temperature data.",
        ],
        "software": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "reproduction": "D:/anaconda/Scripts/conda.exe run -p D:/anaconda/envs/26A --no-capture-output python scripts/fit_ambient_temperature.py --bootstrap 500",
    }
    dest = ROOT / "results" / "validation" / "ambient_fit.json"
    csv = ROOT / "data" / "processed" / "ambient_fit.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    csv.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pd.DataFrame(frame).to_csv(csv, index=False)
    print(json.dumps({"selected_model": selected, "temperature_K": report["recommended_temperature_K"],
                      "temperature_C": report["recommended_temperature_C"],
                      "block_bootstrap_95pct_C": blocked["S_95pct_C"],
                      "holdout_rmse_K": report["holdout_rmse_K"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
