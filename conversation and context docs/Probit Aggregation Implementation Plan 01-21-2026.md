# Probit Aggregation Implementation Plan
**Date:** January 21, 2026
**Status:** Planning

---

## Overview

Replace GPR (Gaussian Process Regression) with Probit aggregation for numeric forecast questions. The probit method fits a normal distribution to scenario data by performing linear regression in z-score space, enabling smooth extrapolation to extreme percentiles (p01, p99) without edge artifacts.

---

## Implementation Steps

### 1. Add Core Probit Functions
Add to `dre_forecasting_tools.py`:
- `pdf_normal(z)` - Standard normal PDF
- `pcntl_from_z(z)` - Integrate PDF to get percentile from z-score
- `z_from_pcntl(percentile)` - Inverse lookup via precomputed spline table

Consider precomputing the z-spline lookup table once at module load for performance.

### 2. Create `_probit_aggregate_numeric()` Function
New function that:
- Takes scenarios list and question as input
- Sorts scenarios, assigns empirical percentiles
- Transforms to z-space and performs linear regression
- Returns `NumericDistribution` with 21 percentiles
- Also returns R² for monitoring/logging

**Output Percentiles (21 total):**
```
[1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]
```

### 3. Integrate into `_aggregate_predictions()`
Modify the numeric branch in `_aggregate_predictions()` to:
- Call `_probit_aggregate_numeric()` instead of `_gpr_aggregate_numeric()`
- Log R² value for monitoring
- Keep GPR available as fallback option (configurable or automatic based on R² threshold)

### 4. Handle Edge Cases
- **Strictly increasing CDF**: Apply `_ensure_strictly_increasing_percentiles()` to ensure each percentile value increases by the minimum required increment
- **Bounds clamping**: Ensure p01/p99 values don't exceed question min/max bounds
- **Low R² flag**: If R² < threshold (e.g., 0.85), add a warning flag to the forecast summary so problematic aggregations are easy to spot
- **Small sample sizes**: Handle cases with fewer scenarios gracefully

### 5. Add Required Imports
```python
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress
```

### 6. Testing
- Test on existing scenario data files (Q41614, Q41619)
- Verify Metaculus API accepts p01/p99 in CDF submissions
- Confirm strictly increasing percentiles pass validation
- Verify scenarios and summaries are saving correctly in GitHub Actions artifacts
- Compare outputs visually with GPR results

### 7. Monitoring
- Log R² value for each numeric aggregation
- Include R² and fit quality indicator in forecast summary metadata section
- Format example in summary:
  ```
  **Aggregation Method**: Probit (R²=0.94)
  ```
  or
  ```
  **Aggregation Method**: Probit (R²=0.72 LOW FIT)
  ```

---

## Key Files

- `dre_forecasting_tools.py` - Main implementation location
- `main.py` - May need minor updates
- `jupyter/07a_Probit_Aggregation_Method_2026-01-21.ipynb` - Prototype reference

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Normal assumption invalid | Monitor R² values; flag fits below 0.85 |
| p01/p99 exceed question bounds | Clamp output values to question min/max |
| Metaculus rejects p01/p99 | Test API acceptance; fall back to p02/p98 if needed |
| Strictly increasing violation | Apply `_ensure_strictly_increasing_percentiles()` |

---

## References

- Probit method documentation: `conversation and context docs/Probit Aggregation Method for Numeric Questions 01-21-2026.md`
- GPR implementation reference: `conversation and context docs/Numeric and Discrete GPR Implementation Session 01-01-2026.md`
- Code organization: `conversation and context docs/Forecast Bot Code Reorganization and Forecast Summary Customization Session 01-04-2026.md`
