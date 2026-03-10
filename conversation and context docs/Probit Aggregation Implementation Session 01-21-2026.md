# Probit Aggregation Implementation Session
**Date:** January 21, 2026
**Status:** Complete - Deployed to Production

---

## Executive Summary

Successfully implemented Probit aggregation for numeric forecast questions, replacing the previous Gaussian Process Regression (GPR) method. The probit method fits a normal distribution to scenario data using linear regression in z-score space, producing smooth CDFs with natural extrapolation to extreme percentiles.

### Key Results
- **99 percentiles** output (p1-p99 at 1% increments) for smooth CDF display
- **R² fit quality monitoring** included in logs and forecast summaries
- **Validated on test question** (Q14333 - age of oldest human) - distribution looks reasonable compared to community
- **Metaculus API accepts** the new format without issues

### Items to Watch For (Potential Problems)

| Warning Sign | What It Means | Action |
|--------------|---------------|--------|
| **R² < 0.85 (LOW FIT)** | Data may not be normally distributed | Review scenarios for multimodality, skewness, or outliers |
| **R² < 0.70** | Poor fit - normal assumption likely invalid | Consider if question has natural bounds, discrete outcomes, or bimodal scenarios |
| **p1/p99 values at bounds** | Extrapolation hit question limits | Check if bounds clamping is hiding wider uncertainty |
| **Flat/identical percentiles** | Very low variance in scenarios | `_ensure_strictly_increasing_percentiles()` will add minimum spacing, but forecaster agreement may be unrealistic |
| **Scenarios clustering in groups** | Multimodal distribution | Probit will average across modes - may not represent true uncertainty well |

### Questions That May Not Fit Well
- **Bounded questions** (e.g., "days until X" can't be negative) - watch for p1 clamping at 0
- **Heavily skewed quantities** (e.g., financial losses, rare event counts) - consider log-normal in future
- **Discrete outcomes** (e.g., "number of X" where only integers make sense) - probit assumes continuous
- **Questions with natural floors/ceilings** close to expected values

---

## Problem Statement

### Issues with Previous GPR Method
1. **Edge artifacts** - GPR introduced distortions at extreme percentiles (0-20% and 80-100%)
2. **Lumpy distributions** - Randomness in individual forecasts created non-smooth CDFs
3. **Limited extrapolation** - Difficult to reliably estimate p01/p99 needed for full CDF
4. **Blocky appearance** on Metaculus even with 21 percentiles

### Desired Outcome
- Smooth CDF from p01 to p99
- Reliable extrapolation to extreme percentiles
- Simpler, more interpretable aggregation
- Visual smoothness on Metaculus display

---

## Solution: Probit Aggregation

### Core Concept
If data is normally distributed, plotting values against their percentiles in z-score (probit) space yields a straight line. We exploit this by:

1. Sorting scenario values and assigning empirical percentiles
2. Converting percentiles to z-scores using inverse normal CDF
3. Fitting linear regression: `value = slope × z + intercept`
4. Extracting any percentile by plugging in the corresponding z-score

### Mathematical Interpretation
For a normal distribution N(μ, σ):
- **Intercept** = μ (mean, equals median for normal)
- **Slope** = σ (standard deviation)
- **R²** indicates how well data fits normal assumption

---

## Implementation Details

### Files Modified
- `dre_forecasting_tools.py` - All probit implementation

### New Module-Level Functions
```python
def _pdf_normal(z: float) -> float:
    """Standard normal probability density function."""

def _pcntl_from_z(z: float) -> float:
    """Convert z-score to percentile by integrating normal PDF."""

def _z_from_pcntl(percentile: float | np.ndarray) -> float | np.ndarray:
    """Convert percentile (0-1 scale) to z-score using precomputed spline."""
```

**Performance optimization:** Z-score lookup table is precomputed at module load using spline interpolation over z-values from -7 to +7.

### New Class Methods in `SpringTemplateBotExtended`

#### `_probit_aggregate_numeric(scenarios, question)`
- Takes scenario list and question
- Returns tuple of `(NumericDistribution, r_squared)`
- Outputs 99 percentiles (p1-p99)
- Clamps values to question bounds
- Applies `_ensure_strictly_increasing_percentiles()`
- Stores R² in `self._last_probit_r2` for summary use

#### `_get_aggregation_method_info(question)`
- Returns formatted string for metadata
- Examples: `"Probit (R²=0.94)"` or `"Probit (R²=0.72 LOW FIT)"`

### Integration Points
- `_aggregate_predictions()` now calls `_probit_aggregate_numeric()` for numeric questions
- Metadata headers include `**Aggregation Method**` line
- Scenario JSON includes `probit_r_squared` and `probit_fit_quality` fields
- Condensed summary methodology line dynamically references aggregation method

### New Imports Added
```python
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress
```

---

## Output Format Evolution

### Initial Implementation (21 percentiles)
```python
output_pctls = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]
```
**Result:** Still looked blocky on Metaculus

### Final Implementation (99 percentiles)
```python
output_pctls = list(range(1, 100))  # [1, 2, 3, ..., 97, 98, 99]
```
**Result:** Smooth CDF display on Metaculus

---

## Testing and Validation

### Test Question
- **URL:** https://www.metaculus.com/questions/14333/age-of-oldest-human-as-of-2100/
- **Type:** Numeric
- **Result:** Forecast ran successfully, R² included in summary, CDF looks reasonable compared to community

### Validation Checklist
- [x] Syntax verification passed
- [x] Bot runs without errors
- [x] R² appears in forecast summary metadata
- [x] Metaculus API accepts 99-percentile CDF
- [x] Distribution visually smooth on Metaculus
- [x] Comparable to community predictions
- [x] Pushed to production (bot-dev branch)

---

## Probit Aggregation for Binary Questions

### Current State
Binary questions currently use GPR aggregation on probability scenarios (0-1 values), taking the p50 as the final prediction.

### Proposed Probit Approach
Apply the same probit methodology to binary scenarios:

1. Collect probability scenarios (e.g., 36 values between 0 and 1)
2. Sort and assign empirical percentiles
3. Transform to z-space and fit linear regression
4. Extract p50 (median) as final probability estimate
5. Optionally extract confidence interval (p25, p75) for uncertainty reporting

### Implementation Plan

#### Step 1: Create `_probit_aggregate_binary()` Function
```python
def _probit_aggregate_binary(self, scenarios: list[float]) -> tuple[float, float]:
    """
    Aggregate binary scenarios using probit regression.

    Returns:
        Tuple of (probability, r_squared)
    """
    # Sort and assign percentiles
    data_sorted = np.sort(np.array(scenarios))
    n = len(data_sorted)
    empirical_pctl = np.array(range(1, n + 1)) / (n + 1)

    # Transform to z-space and regress
    z_values = _z_from_pcntl(empirical_pctl)
    slope, intercept, r_value, _, _ = linregress(z_values, data_sorted)
    r_squared = r_value ** 2

    # p50 is at z=0, so intercept IS the median
    p50 = intercept

    # Clamp to valid probability range
    p50 = max(0.001, min(0.999, p50))

    return p50, r_squared
```

#### Step 2: Update `_aggregate_predictions()` Binary Branch
Replace GPR call with probit call in the binary question handling.

#### Step 3: Add R² Monitoring
Same pattern as numeric - store `_last_probit_r2` and include in summaries.

### Potential Benefits

| Benefit | Description |
|---------|-------------|
| **Consistency** | Same aggregation methodology across question types |
| **Fit quality metric** | R² indicates how well scenarios fit normal distribution |
| **Interpretability** | Intercept = median probability, slope = uncertainty spread |
| **Robustness to outliers** | Linear regression in z-space is less sensitive to extreme scenarios |
| **Confidence intervals** | Can extract p25/p75 for uncertainty bounds if desired |
| **Simpler code** | Remove GPR dependency for binary questions |

### Potential Concerns

| Concern | Mitigation |
|---------|------------|
| **Probabilities near 0 or 1** | Clamping already implemented; z-transform handles gracefully |
| **Non-normal scenario distributions** | Monitor R²; flag low fits |
| **Loss of GPR smoothing** | For binary (single output), smoothing is less relevant than for full CDF |
| **Different behavior than current** | A/B test on subset of questions before full rollout |

### Recommended Testing
1. Run probit binary aggregation in parallel with GPR on 10-20 questions
2. Compare outputs - should be very similar for well-behaved scenarios
3. Identify any edge cases where methods diverge significantly
4. Monitor R² distribution to understand typical fit quality

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `dre_forecasting_tools.py` | All probit implementation code |
| `main.py` | Base bot class, GPR functions still present for binary/MC |
| `jupyter/07a_Probit_Aggregation_Method_2026-01-21.ipynb` | Original prototype notebook |

---

## Commits

1. **f439345** - "Add new Probit Aggregation to main.py and dre_forecasting_tools.py"
   - Initial 21-percentile implementation

2. **[subsequent]** - "Change probit output to 99 percentiles (1% increments) for smoother CDF"
   - Final 99-percentile implementation

---

## Conclusion

The Probit Aggregation method is now deployed for numeric questions and performing well in initial production testing. The method provides:

- **Smoother CDFs** without GPR edge artifacts
- **Natural extrapolation** to extreme percentiles
- **Built-in fit quality monitoring** via R²
- **Interpretable parameters** (mean = intercept, std = slope)

The same methodology could be extended to binary questions with minimal additional work, providing consistency across question types and removing GPR dependency for simpler aggregation.

---

**Session End:** January 21, 2026
**Next Steps:** Monitor production performance, watch for low R² warnings, consider extending to binary questions
