# Bot Update for Numeric Prompt NV03 and Skew-T Aggregation Session 03-10-2026

## Goal

Replace the bot's numeric forecasting pipeline: install the NV03 prompt and replace probit aggregation with Skew-T aggregation.

## What Was Done

### 1. Planning Phase
- Read project spec, new prompt file (`prompts/NUMERIC_prompt_NV03_03-09-2026.md`), reference notebook (`reference - 02b Skew-t...ipynb`), testbed notebook (`012b`), and both `main.py` and `dre_forecasting_tools.py`
- Wrote implementation plan to `conversation and context docs/Plan - Bot Update for Numeric Prompt NV03 and Skew-T Aggregation, 03-10-2026.md`

### 2. Prompt Replacement (main.py)
- Replaced NV02 prompt in `_run_forecast_on_numeric()` with NV03
- Key changes: adds base rates, common sense check, world weighting, distribution shape reasoning
- Output format changed from 9 named world-scenarios to 9 percentile values (p10-p90)
- Same f-string variables, no other code changes needed

### 3. Skew-T Aggregation (dre_forecasting_tools.py)
- **Imports**: Replaced `scipy.integrate.quad`, `scipy.interpolate`, `scipy.stats.linregress`, sklearn with `scipy.stats`, `scipy.integrate.cumulative_trapezoid`, `scipy.optimize.brentq/minimize`
- **Module-level functions**: Replaced 4 probit functions + z-spline precomputation with 10 Skew-T functions copied from reference notebook (with `stats` → `sp_stats`)
- **Aggregation method**: `_probit_aggregate_numeric()` → `_skewt_aggregate_numeric()` using method-of-quantiles fitting + CvM refinement, with fallbacks for IQR~0 and refinement failure
- **Metadata**: All probit references updated to skew-t (R² → CvM, quality threshold inverted: lower CvM = better, threshold 0.10)
- Updated `_aggregate_predictions()`, `_get_aggregation_method_info()`, `_save_scenario_data()`, class docstring

### 4. CLAUDE.md Updated
- Probit aggregation description replaced with Skew-T description

### 5. Bug Fixes During Testing (two GitHub Actions test runs failed)

**Fix 1: Majority vote threshold for small N_RUNS**
- Error: `Insufficient agreement: only 2/2 calls consistent. Refusing to submit unreliable forecast.`
- Cause: Hard-coded `< 3` threshold in `_validate_numeric_scenarios_majority_vote()` meant 2/2 agreeing calls still failed
- Fix: `min_required = min(3, num_calls)` — scales threshold for small runs (same fix from notebook 012a/012b)

**Fix 2: Parser extracting world weights instead of percentile values**
- Error: `Sampled outputs are not the same: scenarios=[30.0, 55.0, 15.0] vs scenarios=[0.3, 0.55, 0.15]`
- Cause: NV03 prompt includes world weight numbers (e.g. 35%, 50%, 15%) in the reasoning, and `structure_output` parser sometimes extracted those 3-element lists instead of the final 9 percentile values
- Fix: Changed `MultiScenarioPrediction.scenarios` from `min_length=1` to `min_length=9`, updated description to match NV03 output format

## Commits

| Commit | Description |
|--------|-------------|
| `50b4f29` | Add accumulated project files (notebooks, docs, tools, data products) |
| `49e838f` | Replace probit with Skew-T aggregation, install NV03 numeric prompt |
| `74f60a0` | Fix majority vote threshold for small N_RUNS |
| `69849b0` | Fix parser extracting world weights instead of percentile values |

## Files Modified

| File | Changes |
|------|---------|
| `main.py` | NV03 prompt, majority vote threshold fix, MultiScenarioPrediction min_length=9 |
| `dre_forecasting_tools.py` | Skew-T imports, functions, aggregation method, all metadata references |
| `CLAUDE.md` | Probit → Skew-T description |
| `prompts/NUMERIC_prompt_NV03_03-09-2026.md` | New prompt file (added to repo) |

## Status

Deployed and verified via GitHub Actions test run. Monitoring over the next few days for production performance.
