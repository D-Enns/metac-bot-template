# Probit Aggregation Method for Numeric Questions

**Date:** January 21, 2026
**Status:** Prototype Complete, Ready for Integration Testing

---

## Executive Summary

Developed and validated an alternate aggregation method for numeric forecasts using probit (normal) regression instead of Gaussian Process Regression (GPR). The method fits a normal distribution to scenario data by performing linear regression in z-score (probit) space, enabling smooth extrapolation to extreme percentiles (p01, p99) without edge artifacts.

Initial testing on two numeric questions (Q41614, Q41619) shows excellent fit quality with high R² values.

---

## Problem Statement

### Issues with Current GPR Method

1. **Edge artifacts** - GPR introduces distortions at extreme percentiles (0-20% and 80-100%)
2. **Lumpy distributions** - Randomness in individual forecasts creates non-smooth CDFs
3. **Limited extrapolation** - Difficult to reliably estimate p01/p99 needed for full CDF

### Desired Outcome

- Smooth CDF from p01 to p99
- Reliable extrapolation to extreme percentiles
- Simpler, more interpretable aggregation

---

## Probit Method Overview

### Core Insight

If data is normally distributed, plotting values against their percentiles in z-score (probit) space yields a straight line. We exploit this by:

1. Sorting scenario values and assigning empirical percentiles
2. Converting percentiles to z-scores
3. Fitting linear regression: `value = slope × z + intercept`
4. Extracting any percentile by plugging in the corresponding z-score

### Mathematical Basis

For a normal distribution N(μ, σ):
- **Intercept** = μ (mean, equals median for normal)
- **Slope** = σ (standard deviation)
- **R²** indicates how well data fits normal assumption

### Key Functions

```python
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress

# Normal PDF
def pdf_normal(z):
    return (1 / ((2 * np.pi))**0.5) * np.exp(-0.5 * (z**2))

# Percentile from z-score (integrate PDF from -inf to z)
def pcntl_from_z(z):
    return quad(pdf_normal, -np.inf, z)[0]

# Z-score from percentile (inverse via spline interpolation)
def z_from_pcntl(percentile):
    x = [pcntl_from_z(z) for z in np.arange(-7, 7.01, 0.01)]
    z = list(np.arange(-7, 7.01, 0.01))
    zspline = splrep(x, z)
    return splev(percentile, zspline)
```

### Aggregation Function

```python
def probit_aggregate_numeric(scenarios, output_pctls=[1,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,99]):
    # Sort and assign empirical percentiles
    data_sorted = np.sort(scenarios)
    n = len(data_sorted)
    pctl = np.array(range(1, n + 1)) / (n + 1)  # 0-1 scale

    # Transform to z-space and regress
    ztile = z_from_pcntl(pctl)
    slope, intercept, r_value, _, _ = linregress(ztile, data_sorted)

    # Generate output distribution
    output_z = z_from_pcntl(np.array(output_pctls) / 100)
    output_values = [z * slope + intercept for z in output_z]

    return output_pctls, output_values, r_value**2
```

---

## Test Results

### Questions Tested

| Question ID | Description | Scenarios | Range | R² |
|-------------|-------------|-----------|-------|-----|
| 41614 | ICE BofA Single-A Corporate Index Yield | 36 | 4.25 - 5.30 | High |
| 41619 | 30-Year Treasury Yield | 36 | 4.25 - 5.55 | High |

### Observations

- Both questions showed excellent fit to normal distribution
- Probit produces smooth CDF without GPR edge artifacts
- Extrapolation to p01/p99 is natural and well-behaved
- Method is simpler and more interpretable than GPR

---

## Implementation Plan

### Step 1: Add Core Functions to main.py

Add the probit transformation functions:
- `pdf_normal(z)`
- `pcntl_from_z(z)`
- `z_from_pcntl(percentile)`

Consider precomputing the z-spline lookup table for performance.

### Step 2: Create Probit Aggregation Function

```python
def _probit_aggregate_numeric(scenarios, question):
    # ... implementation ...

    # Output percentiles including p01 and p99
    output_pctls = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]

    # Build and return NumericDistribution
    percentile_list = [Percentile(percentile=p/100, value=v) for p, v in zip(output_pctls, output_values)]
    return NumericDistribution.from_question(percentile_list, question)
```

### Step 3: Update CDF Output to Include p01 and p99

- **Current GPR output:** 19 percentiles (p05, p10, p15, ..., p90, p95)
- **New probit output:** 21 percentiles (p01, p05, p10, ..., p90, p95, p99)
- Verify Metaculus API accepts p01/p99 in CDF submissions

### Step 4: Add Required Imports

```python
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress
```

### Step 5: Replace or Augment GPR

Options:
1. **Replace entirely** - Remove GPR, use probit only
2. **Keep as fallback** - Use probit primary, GPR if R² < threshold (e.g., 0.85)
3. **Make configurable** - Add parameter to choose method

---

## Concerns and Risks

| Concern | Risk Level | Mitigation |
|---------|------------|------------|
| **Normal assumption invalid** | Medium | Monitor R² values; flag fits with R² < 0.9 |
| **Skewed distributions** | Medium | Consider log-normal transform for strictly positive quantities; segmented fit for asymmetric data |
| **Bounded questions** | Medium | Clamp output values to question bounds after fitting |
| **Multimodal scenarios** | Low | R² will be low; could fallback to GPR or empirical CDF |
| **p01/p99 API compatibility** | Low | Test API submission; may need p02/p98 if rejected |
| **Extrapolation beyond bounds** | Medium | p01/p99 could exceed question min/max; must clamp |

### When Probit May Not Work Well

- Questions with natural floors (e.g., "days until X" can't be negative)
- Highly skewed quantities (e.g., financial losses, extreme events)
- Multimodal forecasts (scenarios cluster in distinct groups)
- Very small sample sizes (< 20 scenarios)

---

## Validation Checklist

- [x] Prototype in Jupyter notebook
- [x] Test on 2 numeric questions
- [ ] Test on 5+ additional numeric questions with varying characteristics
- [ ] Verify R² > 0.9 for typical questions
- [ ] Confirm p01/p99 values stay within question bounds
- [ ] Test Metaculus API accepts 21-percentile CDF
- [ ] Compare submitted distributions visually with GPR output
- [ ] Add logging for slope, intercept, R² for production monitoring
- [ ] Implement bound clamping for output values
- [ ] Consider fallback strategy for low R² fits

---

## Key Files and References

### Jupyter Notebooks

- **Probit aggregation prototype:**
  `jupyter/07a_Probit_Aggregation_Method_2026-01-21.ipynb`

- **Original probit reference notebook:**
  `jupyter/07 Normal Cumulative Probability Plot and Fit (2024).ipynb`

### Documentation

- **Project objectives:**
  `conversation and context docs/Alternate Numeric and Discrete Aggregation Objectives 01-21-2026.txt`

- **GPR implementation reference:**
  `conversation and context docs/Numeric and Discrete GPR Implementation Session 01-01-2026.md`

- **Data download recipe:**
  `conversation and context docs/Recipe - Downloading Forecast Summaries from GitHub.md`

### Test Data

- **Numeric scenario files:**
  `all_forecast_summaries/41614_unknown_scenarios_1.json`
  `all_forecast_summaries/41619_unknown_scenarios_1.json`

### Production Code

- **Main bot with current GPR:**
  `main.py` (see `_gpr_aggregate_numeric()` function)

---

## Next Steps

1. **Gather more test data** - Run bot on additional numeric questions to build test corpus
2. **Test edge cases** - Find questions with skewed or bounded distributions
3. **Implement in main.py** - Add probit aggregation alongside or replacing GPR
4. **API testing** - Verify Metaculus accepts p01/p99 in submissions
5. **Production monitoring** - Log R² values to track fit quality over time

---

## Conclusion

The probit aggregation method offers a simpler, more interpretable alternative to GPR for numeric forecast aggregation. Initial testing shows excellent results on financial yield questions. The method naturally handles extrapolation to extreme percentiles (p01, p99) without edge artifacts.

Key advantages:
- **Smooth CDFs** without GPR edge artifacts
- **Natural extrapolation** to p01/p99
- **Interpretable parameters** (mean = intercept, std = slope)
- **Simpler implementation** than GPR

Recommended approach: Implement probit as primary method with R² monitoring, keeping GPR as fallback for edge cases.

---

**Session End:** January 21, 2026
