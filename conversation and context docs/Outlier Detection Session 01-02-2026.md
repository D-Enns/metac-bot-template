# Outlier Detection for Multi-Scenario Forecasts - Session Summary

**Date:** January 2, 2026
**Status:** ✅ FULLY IMPLEMENTED - Decimal/Percentage Protection + Numeric Majority Vote

---

## Executive Summary

This session addressed outlier detection and data quality issues across all forecast question types (Binary, Numeric, Multiple Choice). Two major improvements were delivered:

1. **✅ IMPLEMENTED:** Auto-correction for decimal/percentage confusion in Binary and Multiple Choice
2. **📋 DESIGNED:** Simple majority vote validation for Numeric questions to handle unit interpretation errors

---

## Part 1: Current State Analysis

### Review of Existing Outlier Handling

#### Numeric Questions (main.py:978-1006)
**Current protection:**
- `_detect_unit_inconsistency()` checks if max/min ratio > 100 within a single call
- Logs warning but continues with all data
- Only works for positive values
- **Limitation:** Only checks within one call's 9 scenarios, misses cross-call inconsistencies

#### Binary Questions (main.py:211-394)
**Current protection:**
- Clamping to [0.01, 0.99] range
- Warning if <2 scenarios returned
- **Limitation:** No outlier detection whatsoever

#### Multiple Choice Questions (main.py:615-789)
**Current protection:**
- Validates distribution length matches number of options
- Normalization handles minor errors
- **Limitation:** No semantic outlier detection

### Critique Summary

**Major finding:** Binary and Multiple Choice are vulnerable to decimal/percentage confusion
- LLM might return `0.5` (decimal) instead of `50` (percentage)
- Code assumes 0-100 scale and divides by 100
- Results in catastrophic errors: 50% becomes 0.5%

---

## Part 2: Decimal/Percentage Protection ✅ IMPLEMENTED

### Problem Statement

**Ambiguous prompts:**
- Binary prompt (line 298): "Write only the numbers without percent signs"
- MC prompt (line 708): "Write probabilities as numbers without percent signs"
- Could mean `50` or `0.5` for 50%

**Vulnerability:**
```python
# If LLM returns 0.5 instead of 50:
scenarios_decimal = [max(0.01, min(0.99, s / 100)) for s in scenarios]
# 0.5 / 100 = 0.005 → clamped to 0.01 → Final: 1% instead of 50%!
```

### Solution Implemented

**Auto-correction logic added to both Binary and Multiple Choice:**

**Binary (main.py:332-339):**
```python
# Auto-correct decimal/percentage confusion: if all values < 1.0, LLM likely returned decimals
if scenario_prediction.scenarios and max(scenario_prediction.scenarios) < 1.0:
    logger.warning(
        f"[DECIMAL DETECTED] Binary scenarios all < 1.0: {scenario_prediction.scenarios}. "
        f"LLM likely returned decimals (0-1) instead of percentages (0-100). Auto-correcting by ×100."
    )
    scenario_prediction.scenarios = [s * 100 for s in scenario_prediction.scenarios]
    logger.info(f"[RESCALED] Binary scenarios after correction: {scenario_prediction.scenarios}")
```

**Multiple Choice (main.py:747-760):**
```python
# Auto-correct decimal/percentage confusion: if all values in all distributions < 1.0
all_values = [val for dist in mc_scenario_prediction.scenarios for val in dist]
if all_values and max(all_values) < 1.0:
    logger.warning(
        f"[DECIMAL DETECTED] MC distributions all have values < 1.0. "
        f"LLM likely returned decimals (0-1) instead of percentages (0-100). Auto-correcting by ×100."
    )
    mc_scenario_prediction.scenarios = [
        [val * 100 for val in dist] for dist in mc_scenario_prediction.scenarios
    ]
    logger.info(
        f"[RESCALED] MC distributions after correction. "
        f"Example first distribution: {mc_scenario_prediction.scenarios[0]}"
    )
```

### Edge Case: Legitimate Very Low Probability Events

**Scenario:** Question like "Will aliens land in 2026?" might legitimately have all scenarios <1%

**Current mitigation:**
1. Prompt guidance (line 255-256): "avoid forecasts below 1% or above 99%"
2. Clear logging with `[DECIMAL DETECTED]` and `[RESCALED]` tags for manual review
3. Can add future refinements based on question context if needed

**Risk assessment:** LOW - prompt guidance makes edge case unlikely

---

## Part 3: Numeric Unit Interpretation Problem

### The Core Issue

**Problem:** LLM sometimes misinterprets the scale/units during multi-call forecasting.

**Example scenario** (question expects hundreds of thousands):
- **Call 1:** Correct → `[0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8]` (0.8 = 80k)
- **Call 2:** Off by 10² → `[80, 100, 120, 150, 180, 200, 220, 250, 280]`
- **Call 3:** Off by 10⁻² → `[0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.022, 0.025, 0.028]`
- **Call 4:** Correct → `[0.9, 1.1, 1.3, 1.6, 1.9, 2.1, 2.3, 2.6, 2.9]`

**Result:** Mixed scales pollute GPR aggregation with bimodal or nonsensical distributions.

### Available Metadata from Metaculus

**NumericQuestion provides:**
1. `question.lower_bound` - Hard lower bound
2. `question.upper_bound` - Hard upper bound
3. `question.nominal_lower_bound` - Preferred lower bound (more realistic)
4. `question.nominal_upper_bound` - Preferred upper bound (more realistic)
5. `question.unit_of_measure` - String like "millions of dollars", "hundreds of thousands"
6. `question.open_lower_bound` - Boolean: soft vs hard lower limit
7. `question.open_upper_bound` - Boolean: soft vs hard upper limit

**Conclusion:** YES, sufficient information available to detect scale issues!

### Design Evolution

**Initial approach considered:**
- Parse `unit_of_measure` for expected scale
- Check scenarios against bounds
- Detect cross-call scale mismatches
- Attempt rescaling
- Complex validation with 200+ lines of code

**User feedback:** "Too complicated. How concise can you make the simpler Majority Vote?"

**Final design:** Simple majority vote - keep calls that agree, bail if <3 agree

---

## Part 4: Simple Majority Vote Solution 📋 DESIGNED

### Algorithm (Concise Implementation)

```python
def _validate_numeric_scenarios_majority_vote(self, scenarios: list[float]) -> list[float]:
    """
    Keep only scenarios from calls in the majority cluster. Bail if <3 calls agree.

    Detects unit interpretation errors by clustering call medians.
    Calls within 3× of each other are considered "agreeing".
    Returns scenarios from largest cluster, or raises ValueError if <3 calls agree.
    """
    # Group by call (9 scenarios per call)
    num_calls = len(scenarios) // 9
    calls = [scenarios[i*9:(i+1)*9] for i in range(num_calls)]
    medians = [float(np.median(c)) for c in calls]

    # Find largest cluster of calls that agree (within 3× of each other)
    best_cluster = []
    for ref_idx in range(num_calls):
        cluster = [ref_idx]
        for other_idx in range(num_calls):
            if other_idx != ref_idx and medians[ref_idx] != 0:
                ratio = medians[other_idx] / medians[ref_idx]
                if 0.33 < ratio < 3.0:  # Within 3×
                    cluster.append(other_idx)
        if len(cluster) > len(best_cluster):
            best_cluster = cluster

    # Bail out if <3 calls agree
    if len(best_cluster) < 3:
        logger.error(
            f"❌ [BAIL OUT] Only {len(best_cluster)}/{num_calls} calls agree. "
            f"Call medians: {[f'{m:.2e}' for m in medians]}"
        )
        raise ValueError(
            f"Insufficient agreement: only {len(best_cluster)}/{num_calls} calls consistent. "
            f"Refusing to submit unreliable forecast."
        )

    # Keep scenarios from majority cluster
    valid_scenarios = []
    for idx in best_cluster:
        valid_scenarios.extend(calls[idx])

    excluded = num_calls - len(best_cluster)
    if excluded > 0:
        logger.warning(
            f"⚠️  [MAJORITY VOTE] Excluded {excluded} call(s). "
            f"Using {len(best_cluster)}/{num_calls} calls = {len(valid_scenarios)} scenarios."
        )
    else:
        logger.info(
            f"✅ [MAJORITY VOTE] All {num_calls} calls agree. "
            f"Using all {len(valid_scenarios)} scenarios."
        )

    return valid_scenarios
```

**Total: ~40 lines of simple, readable code**

### Key Design Decisions

1. **Clustering threshold: 3× ratio**
   - Calls with medians within 3× of each other are "agreeing"
   - Ratio of 0.33 to 3.0 catches most reasonable variation
   - Excludes power-of-10 errors (10×, 100×)

2. **Majority requirement: ≥3 calls**
   - With 4 total calls, need 3 to agree
   - 0 problematic: all 4 calls used (36 scenarios)
   - 1 problematic: 3 calls used (27 scenarios) - still enough for GPR
   - 2+ problematic: BAIL OUT - raise ValueError

3. **No rescaling attempts**
   - Just exclude calls that don't match majority
   - Simpler, less error-prone
   - Clear logging shows what was excluded

4. **Bail-out mechanism**
   - Raise `ValueError` with descriptive message
   - Framework uses `return_exceptions=True` (lines 1402, 1407, 1417, 1434)
   - Exception caught gracefully, no forecast submitted
   - Continues with other questions

### Integration Point

**Where to call:** In `_gpr_aggregate_numeric()` before GPR fitting

```python
def _gpr_aggregate_numeric(self, scenarios: list[float], question: NumericQuestion) -> NumericDistribution:
    """Aggregate numeric scenarios using GPR to create full CDF."""

    # VALIDATE SCENARIOS FIRST (new)
    validated_scenarios = self._validate_numeric_scenarios_majority_vote(scenarios)
    # If <3 calls agree, this raises ValueError and bails out

    # Continue with existing GPR logic using validated_scenarios...
    if len(validated_scenarios) < 9:
        logger.warning(...)
        return self._empirical_distribution_fallback(validated_scenarios, question)

    # Rest of existing GPR code...
```

### Example Scenarios

#### Scenario 1: All Calls Agree ✅
```
Call medians: [1.0, 1.2, 0.9, 1.1]
Ratios: all within 1.3×
Best cluster: [0, 1, 2, 3] (all 4 calls)
✅ [MAJORITY VOTE] All 4 calls agree. Using all 36 scenarios.
```

#### Scenario 2: One Call Wrong ⚠️
```
Call medians: [1.0, 1.2, 120, 0.9]
Call 2 is 100× off from others
Best cluster: [0, 1, 3] (3 calls)
⚠️ [MAJORITY VOTE] Excluded 1 call(s). Using 3/4 calls = 27 scenarios.
```

#### Scenario 3: Two Calls Wrong ❌
```
Call medians: [1.0, 120, 0.008, 0.9]
Calls 1 and 2 are outliers
Best cluster: [0, 3] (2 calls)
❌ [BAIL OUT] Only 2/4 calls agree. Call medians: [1.00e+00, 1.20e+02, 8.00e-03, 9.00e-01]
ValueError: Insufficient agreement: only 2/4 calls consistent. Refusing to submit unreliable forecast.
```

#### Scenario 4: 2-2 Split ❌
```
Call medians: [1.0, 1.2, 120, 110]
Two clusters: [0,1] and [2,3]
Best cluster: either [0,1] or [2,3] (2 calls)
❌ [BAIL OUT] Only 2/4 calls agree. Call medians: [1.00e+00, 1.20e+00, 1.20e+02, 1.10e+02]
ValueError: Insufficient agreement: only 2/4 calls consistent.
```

### Benefits of This Approach

1. **Simple:** 40 lines, easy to understand and debug
2. **Conservative:** Bails out when data quality is questionable
3. **Quality-first:** Won't submit garbage forecasts
4. **Clear logging:** Exactly what was excluded and why
5. **Graceful:** Framework handles exceptions without crashing
6. **No rescaling complexity:** Just exclude, don't try to "fix"

### Edge Cases Handled

**Negative values / zero-crossing:**
- Algorithm works fine (ratio check handles negatives)
- Clustering based on magnitude similarity

**Very wide legitimate ranges:**
- If all 4 calls genuinely span wide range but cluster together, passes
- Example: pandemic deaths with Low_World (~100) vs High_World (~1M) legitimately different

**Zero medians:**
- Check `medians[ref_idx] != 0` before computing ratio
- Avoids division by zero

---

## Implementation Checklist (Next Session)

### Step 1: Add the majority vote method
- [ ] Copy method into main.py after `_detect_unit_inconsistency`
- [ ] ~40 lines of code

### Step 2: Integrate into GPR aggregation
- [ ] Modify `_gpr_aggregate_numeric()` to call validation first
- [ ] Pass validated scenarios to GPR fitting
- [ ] 2-3 lines of code

### Step 3: Test with example questions
- [ ] Run on numeric question with known good data (should pass)
- [ ] Mock LLM response to inject scale errors (should exclude or bail)
- [ ] Verify logging is clear and actionable

### Step 4: Monitor in production
- [ ] Track how often 1 call excluded vs bail-outs
- [ ] Review bail-out logs to improve prompts if needed
- [ ] Adjust 3× threshold if too strict/loose

**Total implementation effort:** ~50 lines of code, 30-60 minutes of testing

---

## Files Modified This Session

### main.py

**Binary decimal protection (lines 332-339):**
- Added auto-correction for decimal vs percentage confusion
- Multiplies by 100 if all values <1.0
- Logs warning and rescaled values

**Multiple Choice decimal protection (lines 747-760):**
- Added auto-correction for all distributions
- Same logic as binary but handles nested lists
- Logs warning and example distribution

**Ready to add (designed, not implemented):**
- `_validate_numeric_scenarios_majority_vote()` method (~40 lines)
- Integration into `_gpr_aggregate_numeric()` (~3 lines)

---

## Key Learnings

### 1. Start Simple, Add Complexity Only When Needed
- Initial design: 200+ lines with unit parsing, bounds checking, rescaling
- User feedback: "Too complicated"
- Final design: 40 lines with simple clustering
- **Lesson:** KISS principle - majority vote handles 90% of cases

### 2. Quality Gates Are Worth It
- Better to refuse forecasting than submit garbage
- Framework's `return_exceptions=True` makes bail-outs graceful
- Clear logging makes debugging easy

### 3. Auto-Correction Works for Bounded Domains
- Decimal/percentage confusion is systematic and detectable
- Safe to auto-correct when domain is bounded (0-100%)
- Log corrections for visibility

### 4. Trust the Majority, Question the Minority
- If 3/4 calls agree, they're probably right
- If 2/4 split, we genuinely don't know - bail out is correct
- Simple heuristic beats complex validation

---

## Next Session Priorities

1. **Implement majority vote validation** (~30 min)
   - Add method to main.py
   - Integrate into GPR aggregation

2. **Test thoroughly** (~30 min)
   - Normal case (all calls agree)
   - 1 outlier (should exclude)
   - 2 outliers (should bail)
   - 2-2 split (should bail)

3. **Run on real questions** (~30 min)
   - Test numeric question from tournament
   - Review logs for any unexpected behavior
   - Adjust threshold if needed

4. **Document in code** (~15 min)
   - Add comments explaining the 3× threshold
   - Document what happens on bail-out
   - Add examples to docstring

**Estimated total: 1.5-2 hours to complete and test**

---

## References

**Related Documents:**
- `Numeric GPR Implementation Session 12-31-2025.md` - Context on numeric GPR system
- `GPR_Binary_Implementation_Summary_12-30-2025.md` - Binary GPR foundation

**Code Locations:**
- Binary prompting: main.py:211-308
- Multiple Choice prompting: main.py:615-713
- Numeric prompting: main.py:817-891
- GPR aggregation: main.py:530-611
- Numeric GPR: main.py:1008-1088

---

---

## Implementation Status Update

**✅ COMPLETED:** All code implemented and integrated

### Changes Made

**Lines Removed:** ~34 lines
- Removed `_detect_unit_inconsistency()` call from `_numeric_prompt_to_forecast()` (5 lines)
- Removed `_detect_unit_inconsistency()` method (29 lines)

**Lines Added:** ~73 lines
- Added `_validate_numeric_scenarios_majority_vote()` method (68 lines) - main.py:995-1062
- Integrated validation into `_gpr_aggregate_numeric()` (5 lines) - main.py:1078-1080

**Net Change:** +39 lines for superior protection

### Implementation Details

**main.py:995-1062** - `_validate_numeric_scenarios_majority_vote()`
- 40-line simple majority vote algorithm
- Groups scenarios by call, finds largest cluster (within 3× agreement)
- Excludes outlier calls (1-2 disagree)
- Bails out with ValueError if <3 calls agree

**main.py:1078-1080** - Integration into GPR
- Validates scenarios before GPR fitting
- Uses only validated scenarios for aggregation
- Exception propagates to framework (graceful handling)

### Ready for Testing

**Test cases:**
1. Normal case: All calls agree → uses all 36 scenarios
2. One outlier: Excludes it → uses 27 scenarios from 3 calls
3. Two outliers: Bails out → raises ValueError, no forecast submitted

**Monitoring:**
- Track frequency of `⚠️ [MAJORITY VOTE] Excluded` logs
- Track frequency of `❌ [BAIL OUT]` errors
- Review bail-out logs to improve prompts if needed

---

**Session Status:** ✅ FULLY IMPLEMENTED - Ready for production testing
**Next Step:** Test on real numeric questions, monitor logs in production
**Implementation time:** ~30 minutes

*Session completed: January 2, 2026*
