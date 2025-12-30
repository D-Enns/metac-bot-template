# Memory Notes for GPR Aggregation Project

## Project: Multi-Scenario GPR Aggregation for Metaculus Spring 2026

### Core Approach
- **Goal**: Beat baseline median aggregation by using Gaussian Process Regression on multi-scenario forecasts
- **Method**: 4 LLM runs × 3 scenarios (pessimistic/baseline/optimistic) → GPR smoothed distribution
- **Development**: Jupyter notebooks first, then integrate into main.py

### Key Technical Constraints (Forecasting-Tools)
```python
# CDF constraints to enforce:
MIN_PERCENTILE_SPACING = 5e-05  # 0.005%
MAX_PMF_VALUE = 0.2             # 20% max at any point
CDF_SIZE = 201                  # Full distribution size
```

### GPR Configuration (Already Working)
```python
# From proof-of-concept notebook
smooth_kernel = C(1.0, (1e-3, 1e5)) * RBF(20.0, (1e-2, 1e2))
kernel = smooth_kernel + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))
gp_model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
```

### Critical Decisions

**1. Numeric Unit Error Handling**
```python
# Use consensus filtering (Option B)
# - Group scenarios by order of magnitude
# - Keep runs within ±0.5 orders of consensus
# - Bail if < 50% of runs agree on units
# This is an IMPORTANT FAILURE MODE - do not skip
```

**2. Question Type Priorities**
- **Binary**: Start here (40 examples available, simplest validation)
- **Numeric**: Likely biggest performance gains, but need unit error handling
- **Multiple Choice**: GPR per option + normalization
- **Discrete**: Treat as numeric, round to integers

**3. Data Locations**
- Dev notebooks: `C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter`
- Binary test data: `.../jupyter/Data/q39945 response.txt` (40 files)
- Proof of concept: `concept_002d Extract binary forecasts, automate GSR Fit plot cum dist, 10-21-2025.ipynb`

### Next Development Steps
1. Add CDF validation to GPR aggregator
2. Build unit consensus detection for numeric
3. Extract full distribution (not just p50)
4. Test on 40 binary questions
5. Acquire numeric/MC/discrete examples
6. Compare performance: GPR vs median

### Integration Notes
- Override `aggregate_predictions()` in SpringTemplateBot2026 class
- Or create standalone `gpr_aggregator.py` module
- Keep consistent with forecasting-tools framework patterns

### Performance Targets
- Beat baseline median by 5%+ on Brier/log score
- Tournament performance is the validation metric
- Cost: Same as current (3 scenarios = 1 LLM call via structured output)

---

**Last Updated**: December 29, 2025
**Status**: Planning complete, ready for Jupyter implementation
