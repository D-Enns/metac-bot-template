# Plan: Numeric Prompt NV03 + Skew-T Aggregation Update

## Context

The bot's numeric forecasting pipeline currently uses a 9-scenario prompt (3 worlds × 3 estimates) with probit aggregation (linear regression in z-space, assumes normal distribution). This update:
1. Installs a vetted NV03 prompt that asks for 9 percentile values (p10-p90) with distribution shape reasoning
2. Replaces probit aggregation with Skew-T (Azzalini skew-t, method of quantiles + CvM refinement), which handles skewed distributions

Both changes are tested in notebook `012b`.

---

## Files Modified

| File | Change |
|------|--------|
| `main.py` | Replace numeric prompt text (lines 662-741) |
| `dre_forecasting_tools.py` | Replace imports, probit functions, aggregation method, metadata references |

---

## Step 1: Replace numeric prompt in `main.py`

**Location:** `_run_forecast_on_numeric()`, lines 662-741 (the `clean_indents(f"""...""")` block)

**Action:** Replace the entire prompt string with the contents of `prompts/NUMERIC_prompt_NV03_03-09-2026.md`. The new prompt file is already an f-string with the same variables (`question.question_text`, `question.background_info`, etc.).

**Key differences from old prompt:**
- Adds sections: "Consider base rates and analogs", "Common sense check", "World weighting", "Distribution shape"
- Consolidates bounds into a single "Question range information and bounds" section (with `question.lower_bound`, `question.upper_bound` shown directly alongside bound messages)
- Final answer: 9 percentile values `[p10, p20, ..., p90]` instead of 9 named world-scenarios

**Update comment** on line 662 from `# DRE 01-01-2025` to `# DRE 03-09-2026 Numeric NV03`

**No other changes in main.py** — `MultiScenarioPrediction` still parses a `list[float]`, `_numeric_prompt_to_forecast()` accumulation is unchanged, majority vote validation groups by 9 per call (still works).

---

## Step 2: Replace probit with Skew-T in `dre_forecasting_tools.py`

### 2a: Replace imports (lines 17-19)

Remove:
```python
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress
```

Add:
```python
from scipy import stats as sp_stats
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import brentq, minimize
```

Also remove the unused sklearn imports (lines 15-16) — GPR is only in `main.py`.

### 2b: Replace probit module-level functions (lines 42-70) with Skew-T functions

Remove: `_pdf_normal`, `_pcntl_from_z`, `_Z_VALUES`, `_PCNTL_VALUES`, `_Z_SPLINE`, `_z_from_pcntl`

Add (copied verbatim from `reference - 02b Skew-t...ipynb` cells 3+5, with `stats` → `sp_stats`):
- `skewt_pdf_standardized(z, alpha, nu)`
- `skewt_pdf(x, mu, sigma, alpha, nu)`
- `build_cdf_grid(alpha, nu, n_grid=2000, z_lo=-12, z_hi=12)`
- `skewt_cdf(x_arr, mu, sigma, alpha, nu, n_grid=2000)`
- `skewt_ppf(p, mu, sigma, alpha, nu, n_grid=2000)`
- `skewt_ppf_fast(p, alpha, nu, z_grid, cdf_grid)`
- `compute_robust_stats(x)`
- `fit_skewt_quantiles(x, nu, skew_target)`
- `refine_cvm(x, fit_init)`
- `compute_cvm(x, cdf_func)` — not strictly needed for aggregation but useful to keep

### 2c: Replace `_probit_aggregate_numeric()` (lines 312-402) with `_skewt_aggregate_numeric()`

Same signature: `(self, scenarios, question) -> tuple[NumericDistribution, float]`

Algorithm:
1. `validated_scenarios = self._validate_numeric_scenarios_majority_vote(scenarios)`
2. Fallback if < 9 scenarios (same as probit)
3. `x = np.array(validated_scenarios)`
4. `robust = compute_robust_stats(x)`
5. `fit = fit_skewt_quantiles(x, nu=5, skew_target=robust['bowley_skew_90'])`
6. `fit = refine_cvm(x, fit)` — wrap in try/except, use initial fit if refinement fails
7. `output_values = skewt_ppf(np.arange(1, 100) / 100, fit['mu'], fit['sigma'], fit['alpha'], fit['nu'])`
8. Clamp to question bounds (same logic as probit)
9. Create Percentile list, ensure strictly increasing
10. Store `self._last_skewt_cvm = fit['cvm']`
11. Log fit quality (CvM < 0.10 = good, >= 0.10 = warning)
12. Return `(NumericDistribution, cvm_value)`

**Edge case:** Wrap `fit_skewt_quantiles` in try/except for `ValueError('IQR ~ 0')` → fall back to `_empirical_distribution_fallback()`

### 2d: Update `_aggregate_predictions()` (lines 264-308)

- Change log tags: `[PROBIT DEBUG]` → `[SKEWT DEBUG]`
- Change method call: `self._probit_aggregate_numeric(...)` → `self._skewt_aggregate_numeric(...)`
- Change variable names: `probit_distribution, r_squared` → `skewt_distribution, cvm_value`
- Update log message on line 303

### 2e: Update metadata references

**`_get_aggregation_method_info()` (lines 601-630):**
- `_last_probit_r2` → `_last_skewt_cvm`
- Output: `"Skew-T (CvM=0.03)"` instead of `"Probit (R²=0.94)"`
- Quality: CvM < 0.10 = good, >= 0.10 = warning (lower is better, inverted from R²)

**`_save_scenario_data()` (lines 799-834), numeric branch:**
- `"aggregation_method": "probit"` → `"aggregation_method": "skew_t"`
- `probit_r_squared` → `skewt_cvm`
- Quality threshold inverted

**Class docstring (line 78):** "Probit" → "Skew-T"

---

## Verification

1. `poetry run python main.py --mode test_questions` — uncomment a numeric question URL (e.g. `questions/14333/age-of-oldest-human-as-of-2100/`) and run
2. Check that scenario JSON in `forecast_summaries/` shows `"aggregation_method": "skew_t"` with CvM value
3. Check logs for `[SKEWT DEBUG]` messages and fit parameters (mu, sigma, alpha, nu, CvM)
4. Verify the forecast submits successfully to Metaculus

---

## Risks

- **IQR near zero:** `fit_skewt_quantiles` raises `ValueError` — caught and falls back to empirical
- **CvM refinement failure:** Nelder-Mead doesn't converge — caught, uses initial quantile fit
- **Alpha saturation:** Extreme skewness clips alpha to ±10 — handled in `fit_skewt_quantiles`
- **Performance:** Grid computations during fitting take <1s per question — no concern
