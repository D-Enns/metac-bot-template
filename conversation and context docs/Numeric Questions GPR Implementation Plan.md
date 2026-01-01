# Numeric Questions - GPR Implementation Plan

**Date:** December 31, 2025
**Status:** 📋 Planning - Ready to implement
**Prerequisites:** Binary GPR implementation complete and tested

---

## Quick Reference

### What's Already Done
✅ **Binary Questions:** GPR multi-scenario aggregation working
- Framework: Flexible `MultiScenarioPrediction` model
- Architecture: Override `_aggregate_predictions()` for GPR
- Tested: 4 calls × 3 scenarios = 12 total → GPR p50
- Scalable: Works with any scenario count (3, 9, 72...)

### Relevant Documents
- `Binary GPR Aggregation Debug and Enhancement Session 12-31-2025.md` - Implementation details
- `Forecast Summary and Comment System.md` - How summaries are generated
- `GPR_Binary_Implementation_Summary_12-30-2025.md` - Original implementation

---

## Numeric Questions Overview

### What Are Numeric Questions?

**Example:** "What will the global average temperature anomaly be in 2030?"

**Answer Format:** Full probability distribution over a range
- Not a single number
- Not a binary probability
- A **CDF (Cumulative Distribution Function)** with percentiles

**Metaculus Expects:**
```python
{
    "10th percentile": 1.2,  # 10% chance value is below this
    "20th percentile": 1.4,
    "40th percentile": 1.6,
    "60th percentile": 1.9,
    "80th percentile": 2.1,
    "90th percentile": 2.3
}
```

---

## Key Challenges for Numeric Questions

### Challenge 1: Unit Interpretation Errors

**Problem:** LLMs inconsistent with units

**Example:**
```
Question: "How many people will die in 2030 from X?"
Expected unit: thousands
LLM call 1: "5000" (means 5,000 people)
LLM call 2: "5000" (means 5,000 thousands = 5 million people)
LLM call 3: "5" (means 5 thousand people)
```

**Impact:** Scenarios span orders of magnitude → GPR fails

**Solution Approach:**
1. Detect outliers (values >10× different from others)
2. Attempt unit normalization
3. Reject calls that are ±0.5 orders of magnitude from consensus
4. Log warnings and potentially retry

### Challenge 2: Percentile Output Format

**Problem:** Must return multiple percentiles, not single value

**Binary Return:**
```python
return 0.0651  # Single probability
```

**Numeric Must Return:**
```python
return NumericDistribution(
    percentiles={
        10: 1.2,
        20: 1.4,
        40: 1.6,
        60: 1.9,
        80: 2.1,
        90: 2.3
    }
)
```

**How GPR Fits:**
- Binary: GPR produces p50 directly
- Numeric: GPR produces **full CDF** → extract all needed percentiles

### Challenge 3: Unbounded Ranges

**Problem:** Some numeric questions have very wide ranges

**Example:** "World population in 2100?"
- Reasonable range: 5 billion to 15 billion
- LLM might suggest: 100 million to 100 billion

**Solution:**
- Use question's stated bounds when available
- Clip extreme scenarios
- Log when scenarios exceed reasonable bounds

### Challenge 4: Distribution Shape

**Problem:** Numeric distributions can be skewed/asymmetric

**Binary distributions:**
- Symmetric around p50
- Simple bell curve

**Numeric distributions:**
- Can be highly skewed (e.g., economic questions)
- Fat tails (rare but extreme outcomes)
- Multimodal (multiple peaks)

**GPR Advantage:** Handles these naturally via flexible kernel

---

## Proposed Architecture

### Similar to Binary, But Extended

**Binary Flow:**
```
4 calls → parse 3 scenarios each → 12 values
       ↓
    GPR fit
       ↓
   Extract p50
       ↓
  Return float
```

**Numeric Flow:**
```
8 calls → parse 9 percentile estimates each → 72 values
       ↓
    GPR fit on empirical CDF
       ↓
   Extract p10, p20, p40, p60, p80, p90
       ↓
  Return NumericDistribution
```

### Key Differences

| Aspect | Binary | Numeric |
|--------|--------|---------|
| Scenarios per call | 3 (Low, Mid, High) | 9 (p10, p20, ..., p90) |
| Total scenarios | 12 (4×3) | 72 (8×9) |
| LLM calls | 4 | 8 |
| GPR output | Single p50 | Full CDF with 6 percentiles |
| Return type | `float` | `NumericDistribution` |
| Main challenge | Consistency | Unit interpretation |

---

## Implementation Plan

### Phase 1: Data Model and Parsing

**Task:** Extend `MultiScenarioPrediction` to handle percentile scenarios

**Option A:** Same model, different prompt
```python
# Can reuse existing MultiScenarioPrediction
# Prompt asks for 9 values representing percentiles
# Parse as: scenarios = [p10_value, p20_value, ..., p90_value]
```

**Option B:** New specialized model
```python
class NumericScenarioPrediction(BaseModel):
    """Percentile estimates for numeric questions"""
    percentiles: dict[int, float] = Field(
        ...,
        description="Percentile estimates mapping percentile to value"
    )
    # Example: {10: 1.2, 20: 1.4, 30: 1.6, ..., 90: 2.3}
```

**Recommendation:** Option A (reuse existing model)
- Simpler: one model for all question types
- Flexible: works with any count
- Prompt-driven: easy to change percentile count

### Phase 2: Prompt Design

**Request format:**
```
You will provide 9 estimates at different confidence levels:
- 10th percentile: You're 90% confident the value will be ABOVE this
- 20th percentile: You're 80% confident the value will be ABOVE this
- 30th percentile: You're 70% confident the value will be ABOVE this
- 40th percentile: You're 60% confident the value will be ABOVE this
- 50th percentile: Your best guess (median)
- 60th percentile: You're 60% confident the value will be BELOW this
- 70th percentile: You're 70% confident the value will be BELOW this
- 80th percentile: You're 80% confident the value will be BELOW this
- 90th percentile: You're 90% confident the value will be BELOW this

CRITICAL: Pay close attention to the units: {question.unit_of_measure}

The last thing you write is your answer in this exact format:
[p10, p20, p30, p40, p50, p60, p70, p80, p90]
Example: [5.2, 6.8, 8.1, 9.2, 10.5, 12.1, 14.3, 17.8, 22.4]
```

**Key additions for numeric:**
- Emphasis on units
- Clear percentile explanations
- Request 9 values for better distribution coverage

### Phase 3: Parsing and Storage

**Similar to binary:**
```python
async def _numeric_prompt_to_forecast(
    self,
    question: NumericQuestion,
    prompt: str,
) -> ReasonedPrediction[NumericDistribution]:
    # Clear storage if new question
    if self._current_question_id != question.page_url:
        self._numeric_scenarios = []  # New storage for numeric
        self._current_question_id = question.page_url

    reasoning = await self.get_llm("default", "llm").invoke(prompt)

    # Parse scenarios
    scenario_prediction: MultiScenarioPrediction = await structure_output(
        reasoning, MultiScenarioPrediction, ...
    )

    # Validate scenario count
    if len(scenario_prediction.scenarios) != 9:
        logger.warning(f"Expected 9 scenarios, got {len(scenario_prediction.scenarios)}")

    # Store all scenarios
    self._numeric_scenarios.extend(scenario_prediction.scenarios)

    # Check for unit interpretation issues
    if self._detect_unit_inconsistency(scenario_prediction.scenarios):
        logger.error("Possible unit interpretation error detected!")
        # Could raise exception to trigger retry, or flag for review

    # Return median as placeholder (framework will aggregate later)
    median_value = float(np.median(scenario_prediction.scenarios))

    # Return as NumericDistribution (temporary - will be replaced by GPR)
    return ReasonedPrediction(
        prediction_value=self._create_temp_distribution(scenario_prediction.scenarios),
        reasoning=reasoning
    )
```

### Phase 4: Unit Consistency Detection

**Method:**
```python
def _detect_unit_inconsistency(self, scenarios: list[float]) -> bool:
    """
    Detect if scenarios suggest unit interpretation errors.

    Returns True if scenarios span >2 orders of magnitude,
    suggesting some forecaster interpreted units differently.
    """
    if len(scenarios) < 3:
        return False

    sorted_scenarios = sorted(scenarios)
    min_val = sorted_scenarios[0]
    max_val = sorted_scenarios[-1]

    if min_val <= 0:
        return False  # Can't check ratio with negative/zero

    ratio = max_val / min_val

    # If max is >100× min, likely unit confusion
    if ratio > 100:
        logger.warning(
            f"Scenarios span {ratio:.1f}× range: {min_val} to {max_val}. "
            f"Possible unit interpretation error."
        )
        return True

    return False
```

**Enhancement:** Track scenarios by call and identify outlier calls
```python
def _identify_outlier_calls(self) -> list[int]:
    """
    Identify which calls have scenarios that are outliers.
    Returns list of call numbers (0-indexed) that are outliers.
    """
    # Group scenarios by call (9 scenarios per call)
    calls = [
        self._numeric_scenarios[i:i+9]
        for i in range(0, len(self._numeric_scenarios), 9)
    ]

    # Get median value from each call
    call_medians = [np.median(call) for call in calls]

    # Find outliers (>3× from median of medians)
    overall_median = np.median(call_medians)
    outliers = []

    for i, call_median in enumerate(call_medians):
        if abs(np.log10(call_median) - np.log10(overall_median)) > 0.5:
            # More than 0.5 orders of magnitude different
            outliers.append(i)
            logger.warning(
                f"Call {i+1} appears to have unit interpretation error: "
                f"median={call_median}, expected~{overall_median}"
            )

    return outliers
```

### Phase 5: GPR Aggregation for Numeric

**Override `_aggregate_predictions()` for numeric questions:**
```python
async def _aggregate_predictions(
    self,
    predictions: list,
    question: MetaculusQuestion,
) -> float | NumericDistribution:
    from forecasting_tools.data_models.questions import BinaryQuestion, NumericQuestion

    # Binary questions (existing code)
    if isinstance(question, BinaryQuestion) and len(self._binary_scenarios) >= 3:
        # ... existing binary GPR code ...
        return gpr_result

    # Numeric questions (NEW)
    elif isinstance(question, NumericQuestion) and len(self._numeric_scenarios) >= 9:
        logger.info(f"Using GPR aggregation on {len(self._numeric_scenarios)} numeric scenarios")

        # Check for outliers and potentially remove
        outliers = self._identify_outlier_calls()
        if outliers:
            logger.warning(f"Removing {len(outliers)} outlier calls due to unit errors")
            # Filter out outlier scenarios
            # ... implementation ...

        # Apply GPR to create full CDF
        gpr_distribution = self._gpr_aggregate_numeric(self._numeric_scenarios)

        # Clear scenarios
        self._numeric_scenarios = []
        self._current_question_id = None

        return gpr_distribution

    # Default aggregation for other types or insufficient data
    else:
        return await super()._aggregate_predictions(predictions, question)
```

### Phase 6: GPR Numeric Aggregation

**Core GPR method:**
```python
def _gpr_aggregate_numeric(self, scenarios: list[float]) -> NumericDistribution:
    """
    Aggregate numeric scenarios using GPR to create full CDF.

    Args:
        scenarios: List of numeric values from multiple percentile estimates

    Returns:
        NumericDistribution with smoothed percentiles
    """
    # Sort scenarios to create empirical CDF
    sorted_scenarios = sorted(scenarios)

    # Create percentiles for each scenario
    n = len(sorted_scenarios)
    empirical_percentiles = [100 * i / (n + 1) for i in range(1, n + 1)]

    # Fit GPR model (same as binary)
    X = np.array(empirical_percentiles).reshape(-1, 1)
    y = np.array(sorted_scenarios)

    kernel = C(1.0, (1e-3, 1e5)) * RBF(20.0, (1e-2, 1e2)) + WhiteKernel(1.0, (1e-5, 1e2))
    gpr_model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
    gpr_model.fit(X, y)

    # Extract required percentiles (Metaculus format)
    target_percentiles = [10, 20, 40, 60, 80, 90]
    percentile_values = {}

    for p in target_percentiles:
        value = gpr_model.predict(np.array([[p]]))[0]
        percentile_values[p] = float(value)

    logger.info(f"GPR numeric aggregation: {len(scenarios)} scenarios → 6 percentiles")
    logger.info(f"Distribution: p10={percentile_values[10]:.2f}, p50={(percentile_values[40]+percentile_values[60])/2:.2f}, p90={percentile_values[90]:.2f}")

    # Create NumericDistribution
    from forecasting_tools.data_models.numeric_report import NumericDistribution

    return NumericDistribution(
        percentiles=percentile_values
    )
```

---

## Testing Strategy

### Test Questions

**Simple numeric (for initial testing):**
- "Age of oldest living human in 2030" (bounded, single unit)
- Easy to validate, clear units

**Complex numeric (for validation):**
- "Global temperature anomaly in 2040" (small range, precision matters)
- Economic questions (large range, potential unit confusion)

### Test Phases

**Phase 1: Unit Tests**
- Test `_gpr_aggregate_numeric()` with dummy data
- Verify percentile extraction
- Test outlier detection

**Phase 2: Integration Tests**
- Single question with mock LLM responses
- Verify full flow: prompt → parse → store → aggregate
- Test with intentional unit errors

**Phase 3: Live Tests**
- Test question via GitHub Actions
- Monitor for unit interpretation issues
- Verify posted distribution makes sense

### Success Criteria

- ✅ 8 calls complete successfully
- ✅ 72 scenarios stored (8 × 9)
- ✅ No major unit interpretation errors (or handled gracefully)
- ✅ GPR produces sensible distribution (monotonically increasing percentiles)
- ✅ Distribution posted to Metaculus successfully
- ✅ Percentiles are reasonable given the question

---

## Edge Cases to Handle

### 1. Negative Values
**Question:** "GDP growth rate in 2030?" (can be negative)

**Handling:**
- GPR works fine with negative values
- Just ensure percentiles are monotonic

### 2. Zero-Crossing Distributions
**Question:** "Net migration to country X" (positive or negative)

**Challenge:** Distribution crosses zero

**Handling:**
- GPR handles this naturally
- May need wider kernel to smooth appropriately

### 3. Extremely Wide Ranges
**Question:** "Number of deaths from pandemic X in 2030?"

**Range:** Could be 0 to millions

**Handling:**
- Consider log-scale GPR for very wide ranges
- Might need different kernel parameters
- Test with real data to see if standard approach works

### 4. Very Narrow Ranges
**Question:** "Average global temperature in 2030?"

**Range:** Maybe 1.4°C to 1.8°C (very narrow)

**Handling:**
- Standard GPR should work fine
- Might see scenarios very close together
- GPR smoothing particularly valuable here

---

## Configuration

### Recommended Settings

**Testing (smaller, faster):**
```python
predictions_per_research_report=4  # 4 calls
# Prompt: 9 scenarios per call
# Total: 4 × 9 = 36 scenarios
```

**Production:**
```python
predictions_per_research_report=8  # 8 calls
# Prompt: 9 scenarios per call
# Total: 8 × 9 = 72 scenarios
```

### Why 9 Scenarios Per Call?

**Covers the full distribution:**
- p10, p20, p30, p40, p50, p60, p70, p80, p90
- Enough to capture shape (skewness, tails)
- Not too many to overwhelm LLM

**Alternative: 7 scenarios**
- p10, p25, p40, p50, p60, p75, p90
- Slightly fewer, still good coverage
- User preference

---

## Known Risks

### Risk 1: Unit Interpretation Errors
**Probability:** Medium-High
**Impact:** High (could make distribution nonsensical)
**Mitigation:** Detection algorithm, logging, potential retry logic

### Risk 2: LLM Percentile Understanding
**Probability:** Medium
**Impact:** Medium (scenarios might not reflect proper confidence intervals)
**Mitigation:** Clear prompt instructions, validation of monotonicity

### Risk 3: GPR Overfitting/Underfitting
**Probability:** Low
**Impact:** Medium (distribution too smooth or too jagged)
**Mitigation:** Tune kernel parameters if needed, test on multiple questions

### Risk 4: Metaculus API Format
**Probability:** Low
**Impact:** High (forecast rejected)
**Mitigation:** Test with staging API first, validate format against spec

---

## Code Structure

### New Methods to Add

```python
class SpringTemplateBot2026(ForecastBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Existing binary storage
        self._binary_scenarios = []
        # NEW: Numeric storage
        self._numeric_scenarios = []
        self._current_question_id = None

    # Existing: Binary methods
    # _run_forecast_on_binary()
    # _binary_prompt_to_forecast()
    # _gpr_aggregate_binary()

    # NEW: Numeric methods
    async def _run_forecast_on_numeric(
        self, question: NumericQuestion, research: str
    ) -> ReasonedPrediction[NumericDistribution]:
        """Main forecast function for numeric questions"""
        pass

    async def _numeric_prompt_to_forecast(
        self, question: NumericQuestion, prompt: str
    ) -> ReasonedPrediction[NumericDistribution]:
        """Parse and store numeric scenarios"""
        pass

    def _gpr_aggregate_numeric(
        self, scenarios: list[float]
    ) -> NumericDistribution:
        """Apply GPR to create full distribution"""
        pass

    def _detect_unit_inconsistency(
        self, scenarios: list[float]
    ) -> bool:
        """Check for unit interpretation errors"""
        pass

    def _identify_outlier_calls(self) -> list[int]:
        """Find calls with outlier scenarios"""
        pass

    # MODIFIED: Extend aggregation
    async def _aggregate_predictions(
        self, predictions: list, question: MetaculusQuestion
    ):
        """Handle both binary and numeric aggregation"""
        # Add numeric case to existing binary case
        pass
```

### File Locations

**Main implementation:** `main.py`
- Add numeric methods after binary methods (around line 450-500)
- Extend `_aggregate_predictions()` (around line 385)
- Add numeric storage to `__init__()` (around line 139)

**Tests:** `tests/test_numeric_aggregation.py` (new file)

---

## Open Questions to Resolve

1. **How many scenarios per call?**
   - 9 (p10-p90) vs. 7 (p10, p25, p40, p50, p60, p75, p90)
   - More = better distribution, but more tokens

2. **How to handle unit errors?**
   - Detect and retry?
   - Detect and exclude outlier calls?
   - Detect and warn but continue?

3. **Log-scale vs. linear scale?**
   - For wide-range questions, fit GPR in log-space?
   - Or always use linear and trust GPR flexibility?

4. **Kernel parameters?**
   - Same as binary (RBF length_scale=20)?
   - Or tune per question type?

5. **Temporary distribution format?**
   - What to return from `_numeric_prompt_to_forecast()` before aggregation?
   - Simple distribution from 9 scenarios? Or pass-through?

---

## Next Session Checklist

When starting numeric implementation:

- [ ] Review binary implementation in `main.py`
- [ ] Review this plan document
- [ ] Decide on 7 vs. 9 scenarios per call
- [ ] Create prompt for numeric questions
- [ ] Implement `_numeric_prompt_to_forecast()`
- [ ] Implement `_gpr_aggregate_numeric()`
- [ ] Extend `_aggregate_predictions()` for numeric case
- [ ] Add unit consistency checking
- [ ] Create unit tests
- [ ] Test with simple numeric question
- [ ] Refine based on results

---

## Success Criteria for Numeric Implementation

**Must Have:**
- ✅ Produces valid `NumericDistribution` with 6 percentiles
- ✅ Percentiles are monotonically increasing
- ✅ GPR runs once on all scenarios (not multiple times)
- ✅ Handles unit interpretation errors gracefully
- ✅ Works with variable scenario counts
- ✅ Posts successfully to Metaculus

**Nice to Have:**
- ✅ Automatic outlier detection and exclusion
- ✅ Adaptive kernel parameters based on distribution width
- ✅ Logging of scenario quality metrics
- ✅ Distribution visualization in comments

---

## References

### Similar to Binary Implementation
- Data model: Reuse `MultiScenarioPrediction`
- Architecture: Override `_aggregate_predictions()`
- Storage: Instance variables for scenarios
- GPR: Same kernel approach

### Different from Binary
- Return type: `NumericDistribution` not `float`
- Scenarios: 9 percentiles not 3 confidence levels
- Challenge: Unit interpretation not just consistency
- Output: Full CDF not just p50

### Key Files to Reference
- `main.py` lines 371-401: Aggregation override pattern
- `main.py` lines 272-306: Parsing and storage pattern
- `main.py` lines 308-367: GPR implementation

---

*Plan created: December 31, 2025*
*Ready for implementation in new session*
*Prerequisites: Binary GPR working and tested*
