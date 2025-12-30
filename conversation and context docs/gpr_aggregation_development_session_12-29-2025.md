# GPR Aggregation Development Session - December 29, 2025

## Session Summary
This session focused on developing a Gaussian Process Regression (GPR) based aggregation system for the Metaculus Spring 2026 forecasting bot. We reviewed the existing proof-of-concept notebook, explored forecasting-tools CDF constraints, and planned the implementation path for multi-scenario forecast aggregation.

---

## Project Context

### Goal
Improve performance in Metaculus Spring 2026 AI forecasting tournament by enhancing aggregation methods for multi-scenario forecasts across different question types (Binary, Numeric, Discrete, Multiple Choice).

### Current Approach
- **Existing method**: 5 LLM runs → median aggregation
- **New approach**: Multiple LLM runs × 3 scenarios per run (pessimistic-baseline-optimistic) → GPR smoothed aggregation

### Development Strategy
- Develop and test in Jupyter notebooks (`C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter`)
- Start with simpler parameters: Binary questions, 4 LLM runs, 3 scenarios per run
- Test and iterate before production deployment
- Tournament itself serves as validation (historical data validation not required before deployment)

---

## Key Technical Findings

### 1. Forecasting-Tools CDF Constraints

**Critical constraints identified in the forecasting-tools framework:**

| Constraint | Value | Purpose |
|-----------|-------|---------|
| Minimum percentile spacing | 5e-05 (0.005%) | Prevent degenerate CDFs |
| Minimum percentiles required | 2 | Basic distribution |
| Max PMF value | 0.2 (20%) | Prevent point masses |
| Bounds wiggle room | ±25% of range | Allow realistic distributions |
| CDF size (numeric) | 201 points | Standard Metaculus format |
| Decimal rounding | 10 places | Floating-point stability |

**Key validation checks:**
- Both percentile AND value must be strictly increasing
- Repeating values are automatically adjusted by framework
- Distributions too concentrated trigger validation errors
- At least one percentile must be within bounds ± 25%

**Source:** `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/main_with_no_framework.py` (lines 620-1109)

### 2. Proof of Concept Review

**Notebook:** `concept_002d Extract binary forecasts, automate GSR Fit plot cum dist, 10-21-2025.ipynb`

**Current GPR Implementation:**
```python
# Kernel configuration
smooth_kernel = C(1.0, (1e-3, 1e5)) * RBF(20.0, (1e-2, 1e2))
kernel = smooth_kernel + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))
gp_model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
```

**Key Design Decision: Inverted CDF Approach**
- Standard CDF: forecast value (X) → percentile (y)
- Your approach: percentile (X) → forecast value (y)
- **Advantage**: Direct query "What's the forecast at p50?" without inversion

**Workflow:**
1. Extract scenario forecasts from multiple LLM runs
2. Flatten all scenarios into single sorted list: `[25, 30, 45, 50, 65, 70, ...]`
3. Create empirical CDF (assign percentiles to each value)
4. Fit GPR model through the data points
5. Extract p50 (or other percentiles) from smooth curve
6. Handles "blockiness" from LLM's preference for round numbers (5% increments)

**Current Data:**
- 40 binary questions from Fall tournament
- Location: `C:\Users\Donni\projects\metac_bot_Spring_2026\metac-bot-template\jupyter\Data\`
- Format: Text files with 8 forecaster predictions per question
- Example: `q39945 response.txt` contains research + forecasts

---

## Technical Decisions Made

### 1. Data Source Transition
- **Current**: Regex parsing from text files
- **Production**: Structured LLM output (JSON with pessimistic/baseline/optimistic scenarios)
- **Improvement**: Prompt LLM to output only scenarios (exclude percentiles) for cleaner parsing

### 2. Numeric Unit Error Handling
**Problem**: LLMs inconsistently interpret units (10K vs 10000) - identified as important failure mode

**Solution: Consensus Filtering (Option B)**
```python
def detect_unit_consensus(scenarios_by_run):
    # Group by order of magnitude
    # Find consensus magnitude via median
    # Keep only runs within ±0.5 orders of magnitude (~3x)
    # Bail if less than half the runs are valid
```

**Rejected alternatives:**
- Option A (bail out): Too conservative, loses data
- Option C (convert outliers): Too risky, potential for errors

### 3. Full Distribution Extraction
**Goal**: Provide complete percentile distributions for numeric questions

**Implementation:**
```python
def get_full_distribution_from_gpr(gp_model, percentiles=[10, 20, 40, 60, 80, 90]):
    X = np.array(percentiles).reshape(-1, 1)
    y_pred = gp_model.predict(X)
    return {int(p): float(v) for p, v in zip(percentiles, y_pred)}
```

**Output format:**
- **Binary**: Single p50 value (0-1 scale)
- **Numeric**: Dictionary of percentiles {10: value, 20: value, ..., 90: value}
- **Validation**: Ensure minimum spacing and strictly increasing values

### 4. Question Type Extensions

**Multiple Choice:**
- Approach: GPR per option + normalization
- Collect scenarios for each option separately
- Fit individual GPR models
- Extract p50 for each option
- Normalize so probabilities sum to 1.0

**Discrete (Integer-only Numeric):**
- Examples: "How many home runs in World Series?"
- Process as numeric during GPR fitting
- Round percentile outputs to integers
- Ensure rounding preserves strict increasing order

### 5. GPR Kernel Tuning
- Current kernel parameters may need fine-tuning for optimal smoothing
- Length_scale=20.0 controls smoothness
- WhiteKernel handles noise from LLM's round-number preferences
- May adjust based on performance testing

---

## Data Availability Status

| Question Type | Status | Notes |
|--------------|--------|-------|
| Binary | ✅ 40 examples | Ready for testing |
| Numeric | ❌ Need examples | Acquire from API or tournament |
| Multiple Choice | ❌ Need examples | Acquire from API or tournament |
| Discrete | ❌ Need examples | Acquire from API or tournament |

**Data format (Binary questions):**
```
SUMMARY
Question: Will CME's market close price on 2025-09-27 be higher than its market close price on 2025-09-15?
Final Prediction: 48.0%
Forecasts
Forecaster 1: 52.0%
Forecaster 2: 48.0%
...
Forecaster 8: 46.0%
Research Summary
[News and analysis...]
```

---

## Implementation Path

### Phase 1: Enhance Binary Aggregation (Next)
1. ✅ GPR fitting already working in notebook
2. ⏳ Add CDF spacing validation
3. ⏳ Test on 40 binary questions
4. ⏳ Compare GPR p50 vs simple median performance

### Phase 2: Extend to Numeric
1. Add unit consensus detection
2. Extract full percentile distribution
3. Validate against forecasting-tools constraints
4. Test on numeric examples (need to acquire)

### Phase 3: Multiple Choice & Discrete
1. Implement GPR per option + normalization
2. Add integer rounding for discrete
3. Test on examples (need to acquire)

### Integration Decision (To Be Determined)
Options under consideration:
- **Option A**: Override `aggregate_predictions()` in SpringTemplateBot2026
- **Option B**: Create standalone `gpr_aggregator.py` module
- **Option C**: Fork forecasting-tools (most invasive)

---

## Strategic Considerations

### Efficiency Recommendations

**1. Start Even Simpler**
- Current plan: 4 LLM runs × 3 scenarios = 12 forecasts
- Consider: 1 LLM run × 3 scenarios = 3 forecasts for initial testing
- Rationale: Test aggregation logic first with minimal API costs
- Scale up runs once aggregation proven

**2. Validation Strategy**
- **Baseline**: Current median approach score (Brier/log score)
- **New approach**: GPR aggregation score
- **Test on**: Historical resolved questions (when available)
- **Goal**: 5%+ improvement over baseline

**3. Cost Management**
- 3 scenarios = 1 LLM call with structured output (not 3 separate calls)
- Lower cost than initially expected
- Example structured output:
```json
{
  "pessimistic": {"reasoning": "...", "forecast": 0.3},
  "baseline": {"reasoning": "...", "forecast": 0.5},
  "optimistic": {"reasoning": "...", "forecast": 0.7}
}
```

**4. Prompt Engineering**
- Multi-scenario approach already tested and works well
- Scenarios produce genuinely different values (not just 0.45, 0.50, 0.55)
- Reasoning for each scenario useful for explanations
- Critical: LLM must explore scenario space, not just restate same answer

**5. Binary vs Numeric Priority**
- **Binary advantages**: Simplest to validate, most common question type, consistent 0-100 scale
- **Binary challenge**: Defining what "scenarios" mean for yes/no questions
- **Numeric advantages**: Low/mid/high very natural, easier to construct distributions
- **Numeric challenge**: Unit interpretation errors (important failure mode)
- **Decision**: Start with Binary due to data availability, but Numeric may show bigger gains

### Known Risks

**1. Blockiness Problem** (Being Addressed)
- LLMs use 1% precision
- Strong bias toward 5% increments (45%, 50%, 55%)
- GPR smoothing designed to handle this

**2. CDF Constraints** (Now Understood)
- Minimum 5e-05 spacing between percentiles
- May need to add small jitter if GPR produces too-flat distributions
- Validation logic exists to catch violations

**3. Scenarios Not Meaningfully Different**
- Risk: LLM gives 0.45, 0.50, 0.55 instead of exploring uncertainty
- Mitigation: Prompt engineering already addresses this
- Validation: Check scenario spread during testing

**4. Numeric Unit Errors** (Solution Designed)
- Important failure mode in current system
- Consensus filtering approach should catch most errors
- Bail-out logic prevents bad forecasts from unit confusion

---

## Immediate Next Steps

### 1. Enhance GPR Aggregator in Jupyter
Build production-ready aggregator with:
- Unit consensus detection for numeric questions
- Full distribution extraction (not just p50)
- CDF validation against forecasting-tools constraints
- Test on 40 binary questions
- Performance comparison: GPR vs median

### 2. Acquire Additional Test Data
Need examples for:
- Numeric questions (with known resolutions if possible)
- Multiple Choice questions
- Discrete questions

**Options:**
- Query Metaculus API for historical resolved questions
- Generate synthetic test cases for development
- Collect from Spring 2026 tournament as it runs

### 3. Integration Planning
Once Jupyter proof successful:
- Decide on integration approach (A/B/C)
- Implement in main.py or separate module
- Test in tournament mode
- Monitor performance vs baseline

---

## Technical Questions Resolved

### Q: What are the forecasting-tools CDF constraints?
**A:** Minimum percentile spacing of 5e-05, max PMF 20%, strictly increasing values, bounds wiggle room ±25%

### Q: How to provide full distribution instead of just p50?
**A:** Extract multiple percentiles from GPR model, format as dictionary, let forecasting-tools interpolate to full 201-point CDF

### Q: How to handle numeric unit errors?
**A:** Use consensus filtering - group by order of magnitude, keep runs within ±0.5 orders of consensus, bail if too many outliers

### Q: What about discrete (integer-only) questions?
**A:** Treat as numeric during GPR, round outputs to integers while preserving strictly increasing order

### Q: Multiple choice aggregation approach?
**A:** GPR per option, extract p50 for each, normalize probabilities to sum to 1.0

---

## Files and Locations

**Development Environment:**
- Jupyter notebooks: `C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter`
- Proof of concept: `concept_002d Extract binary forecasts, automate GSR Fit plot cum dist, 10-21-2025.ipynb`

**Data:**
- Binary questions: `C:\Users\Donni\projects\metac_bot_Spring_2026\metac-bot-template\jupyter\Data\`
- Format: `q39945 response.txt`, `q39929 response.txt`, etc.
- 40 questions available

**Code:**
- Main bot: `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/main.py`
- No-framework version: `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/main_with_no_framework.py`
- Forecasting-tools: version 0.2.80 (via Poetry)

**Documentation:**
- Session history: `metac-bot-template/conversation and context docs/`
- Previous session: `forecast_bot_aggregation_session_12-27-2025.md`
- Project overview: `metac bot aggregator project 12-29-2025.md`

---

## Agent IDs for Resuming

If you need to resume specialized agents from this session:
- **CDF constraints exploration**: `a9a786f`
- **Claude Code guide**: `ae053f1`

---

## End of Session

**Session Date:** December 29, 2025
**Working Directory:** `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026`
**Key Topics:** GPR aggregation, CDF constraints, multi-scenario forecasting, implementation planning
**Status:** Planning complete, ready for Jupyter development

---

*This document was generated by Claude Code (Sonnet 4.5) on December 29, 2025*
