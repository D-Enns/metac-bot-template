# Notebook 012b — Skew-T Aggregation Testbed Session 03-10-2026

## Goal

Create notebook 012b that adds skew-T aggregation as an alternative to probit, using the same validated scenarios. Both methods produce p1-p99 percentile pairs and 201-point CDFs for direct comparison.

## What Was Done

### 1. Fixed majority vote threshold in 012a (carried into 012b)
- `N_RUNS = 2` caused `ValueError` because the hard-coded `< 3` threshold required 3 agreeing calls
- Fix: `min_required = min(3, num_calls)` — scales threshold for small N_RUNS

### 2. Created `jupyter/012b_Metaculus_Bot_Testbed_NUMERIC_NV03_03-10-2026.ipynb`
- Based on 012a (all 13 cells copied)
- 5 new cells inserted after probit visualization, before LLM reasoning text
- Skew-T math copied from `reference - 02b Skew-t Cumulative Probability Plot and Fit, with Comparisons (2026).ipynb`

### 3. Visualization axis fixes
- **Subplot 3 (both probit and skew-T)**: Z-score on y-axis, forecast value on x-axis
- **Subplot 2 (both)**: Scenario rug marks at y=0.1 (cosmetic)
- **Skew-T subplot 3**: Shows both probit and skew-T model curves in z-space for direct comparison

## New Cells in 012b (after probit visualization, before LLM reasoning)

| Cell | Type | Content |
|------|------|---------|
| Markdown | header | Skew-T Aggregation section description |
| Code | core functions | `skewt_pdf_standardized`, `skewt_pdf`, `skewt_build_cdf_grid`, `skewt_cdf`, `skewt_ppf`, `skewt_ppf_fast` |
| Code | fitting functions | `compute_robust_stats`, `fit_skewt_quantiles`, `refine_cvm` |
| Code | aggregation | Fits skew-T (nu=5, CvM refinement), generates p1-p99, clamps to bounds, builds 201-point CDF via NumericDistribution |
| Code | visualization | 3 subplots (skew-T CDF, histogram+PDF overlay, z-score comparison) + percentile comparison table |

## Key Design Decisions

- **`build_cdf_grid` renamed to `skewt_build_cdf_grid`** to avoid future name collisions
- **`scipy.stats` imported as `sp_stats`** to avoid shadowing variable names
- **nu=5 fixed** — small samples (18-54 scenarios) can't reliably estimate degrees of freedom
- **Bowley skew target uses 90th-10th percentile variant** (`bowley_skew_90`)
- **CvM refinement enabled** — jointly re-optimizes (sigma, alpha) via Nelder-Mead, median hard-constrained
- **Same NumericDistribution pipeline** for both probit and skew-T → identical 201-point CDF output format
- **Z-score comparison plot** (skew-T subplot 3) shows both models in z-space with empirical points, making divergence at tails visible

## Import Changes (cell 2)

Added to existing scipy imports:
```python
from scipy import stats as sp_stats
from scipy.integrate import cumulative_trapezoid  # (quad already present)
from scipy.optimize import brentq, minimize
```

## Files

- **Created**: `jupyter/012b_Metaculus_Bot_Testbed_NUMERIC_NV03_03-10-2026.ipynb`
- **Modified**: `jupyter/012a_Metaculus_Bot_Testbed_NUMERIC_NV03_03-09-2026.ipynb` (majority vote fix only)
- **Reference**: `jupyter/reference - 02b Skew-t Cumulative Probability Plot and Fit, with Comparisons (2026).ipynb`

## Status

Notebook created, not yet run end-to-end. Ready for testing.
