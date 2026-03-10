# Binary Question Forecasting: Prompt and Aggregation Status
**Date:** January 29, 2026
**Status:** ✅ Production Ready
**Repository:** https://github.com/D-Enns/metac-bot-template

---

## Overview

This document summarizes the current methodology for binary question forecasting in the Metaculus AI Tournament bot. The system uses a sophisticated multi-scenario approach combined with Gaussian Process Regression (GPR) to generate well-calibrated probability forecasts.

**Key Innovation:** Rather than generating a single forecast, the system explores multiple plausible worlds based on different interpretations of the evidence, then uses GPR to aggregate these scenarios into a smooth, robust final prediction.

---

## Scenario Generation: 3×3 World Matrix Approach

### Evidence Bucketing Strategy

The forecasting prompt instructs the LLM to organize research evidence into three distinct buckets:

- **Bucket 1**: Evidence that would indicate a relatively **low** forecast
  - Risk-reducing factors
  - Reasons the event is unlikely
  - Historical base rates suggesting low probability

- **Bucket 2**: Evidence that would indicate a relatively **central or baseline** forecast
  - Status quo indicators
  - Balanced evidence
  - Moderate probability factors

- **Bucket 3**: Evidence that would indicate a **high** forecast
  - Risk-increasing factors
  - Reasons the event is likely
  - Signals suggesting elevated probability

**Rationale:** This bucketing forces the LLM to consider the full range of evidence rather than cherry-picking information that supports a single viewpoint.

### Multi-World Scenario Generation

For each evidence bucket, the LLM considers a corresponding "world" and generates three probability estimates within that world:

#### 1. Low_World (based on Bucket 1 evidence)
- **Low estimate**: Most pessimistic forecast given the low-risk evidence
- **Mid estimate**: Baseline forecast given the low-risk evidence
- **High estimate**: Optimistic forecast given the low-risk evidence

#### 2. Mid_World (based on Bucket 2 evidence)
- **Low estimate**: Most pessimistic forecast given the central evidence
- **Mid estimate**: Baseline forecast given the central evidence
- **High estimate**: Optimistic forecast given the central evidence

#### 3. High_World (based on Bucket 3 evidence)
- **Low estimate**: Most pessimistic forecast given the high-risk evidence
- **Mid estimate**: Baseline forecast given the high-risk evidence
- **High estimate**: Optimistic forecast given the high-risk evidence

### Output Format

Each LLM call produces exactly 9 scenarios in this format:

```
[Low_World-Low, Low_World-Mid, Low_World-High,
 Mid_World-Low, Mid_World-Mid, Mid_World-High,
 High_World-Low, High_World-Mid, High_World-High]
```

**Example output**: `[1.3, 2.4, 4.1, 4.0, 7.2, 12.5, 12.0, 20.0, 35.0]`

This provides a rich distribution of possible forecasts spanning from very low to very high probabilities.

---

## Parallel Execution Architecture

### Configuration

**Current (Testing)**:
- `predictions_per_research_report = 4` (main.py:1407)
- 4 parallel LLM calls × 9 scenarios each = **36 total scenarios**
- Processing time: ~2-3 minutes with GPT-5.2

**Planned (Production)**:
- `predictions_per_research_report = 8`
- 8 parallel LLM calls × 9 scenarios each = **72 total scenarios**
- Processing time: ~4-5 minutes

### Execution Flow

1. **Research Phase**: Single research report generated for the question

2. **Forecasting Phase (Parallel)**:
   - Framework spawns N async calls to `_run_forecast_on_binary()` (N=4 currently)
   - Each call independently:
     - Sends prompt to LLM (GPT-5.2 with 80-second timeout)
     - Receives 9 scenarios
     - Stores scenarios in `self._binary_scenarios` list
     - Returns median of its 9 scenarios to framework (for framework tracking)

3. **Aggregation Phase (Sequential)**:
   - Framework calls `_aggregate_predictions()` after all forecasts complete
   - Custom override in `dre_forecasting_tools.py:85-125` executes
   - GPR runs on all accumulated scenarios (36 or 72)
   - Returns single p50 value

**Critical Fix (Dec 31, 2025)**: Originally tried to detect "final call" inside async function, which caused race conditions. Solution was to override `_aggregate_predictions()` which runs after all async calls complete, eliminating race conditions entirely.

---

## GPR Aggregation Method

### Overview

**Gaussian Process Regression (GPR)** is used to smooth through the "blocky" distribution of scenario forecasts and extract a robust median (p50) value.

### Implementation Details

**Location**:
- Main GPR function: `main.py:372-406` (`_gpr_aggregate_binary()`)
- Called from: `dre_forecasting_tools.py:85-125` (`_aggregate_predictions()` override)

### Algorithm Steps

1. **Scale Conversion**
   - Input: Scenarios in 0-1 decimal scale
   - Convert to 0-100 percentage scale for GPR

2. **Sorting**
   - Sort all scenarios: `[0.01, 0.01, 0.02, 0.02, 0.05, 0.05, ...]`

3. **Empirical CDF Creation** (main.py:476-479)
   ```python
   percentiles = [100 * i / (1 + len(sorted_data)) for i in range(len(sorted_data))]
   ```
   - Maps each scenario to its empirical percentile position
   - Example with 36 scenarios: [2.7, 5.4, 8.1, ..., 97.3]

4. **GPR Model Fitting** (main.py:481-499)
   - **Kernel**: `C(1.0) * RBF(20.0) + WhiteKernel(1.0)`
     - **RBF (Radial Basis Function)**: Provides smooth interpolation
     - **WhiteKernel**: Handles noise/blockiness in scenarios
     - **ConstantKernel**: Scales the overall variance
   - **Training**: Fit model with 10 optimizer restarts for robustness
   - **Mapping**: percentile (X) → forecast value (y)

5. **P50 Extraction**
   ```python
   p50_pct = gpr_model.predict(np.array([[50]]))[0]
   ```
   - Query the fitted model at exactly the 50th percentile
   - Returns smoothed median forecast

6. **Final Conversion**
   - Convert back to 0-1 decimal scale
   - Clamp to safe range: `max(0.01, min(0.99, p50_decimal))`
   - Avoids extreme 0% or 100% predictions

### Why GPR Instead of Simple Median?

**Problem with simple median**:
- With blocky scenario data (e.g., `[5%, 5%, 5%, 10%, 10%, 10%, 20%, 20%, 20%]`)
- Median might land exactly on a repeated value
- Doesn't utilize the full distribution information

**Benefits of GPR**:
- Smooths through blocky/repeated values
- Considers the entire distribution shape
- Interpolates between scenarios more intelligently
- More robust to outliers
- Produces calibrated results that avoid "round number bias"

---

## Prompt Engineering Features

### Professional Framing
```
You are a professional forecaster interviewing for a job.
```
- Creates accountability mindset
- Encourages thoughtful, serious forecasting
- Frames task as high-stakes decision

### Precision Guidance
```
You do not preferentially choose forecast probabilities of 5%, 10%, 15%, 20% etc.
Instead you make your best forecast, allowing values such as 12%, 17%, 34%, 48%, 71%...
```
- Combats round-number bias
- Encourages decimal precision for extreme probabilities (e.g., 2.3%, 95.7%)
- Avoids <1% or >99% extremes

### Status Quo Reminder
```
Good forecasters put extra weight on the status quo outcome
since the world changes slowly most of the time.
```
- Counteracts sensationalism in research
- Important calibration nudge
- Grounds forecasts in base rates

### Structured Thinking Steps

Before generating scenarios, LLM must write:
1. Time remaining until question resolves
2. Status quo outcome if nothing changed
3. Expectations of experts and markets
4. Scenario resulting in "No" outcome
5. Scenario resulting in "Yes" outcome

This ensures comprehensive consideration of the question before making probabilistic judgments.

---

## Model Configuration

### Primary Model: GPT-5.2
**Location**: main.py:1107
```python
"default": GeneralLlm(
    model="openrouter/openai/gpt-5.2",
    temperature=1,
    timeout=80,  # Increased from 40 (Dec 31, 2025)
    allowed_tries=2,
)
```

**Timeout Fix (Jan 1, 2026)**:
- Original 40-second timeout caused 4th LLM call to fail
- GPT-5.2 needs ~40-50 seconds for complex 9-scenario prompts
- Increased to 80 seconds provides sufficient buffer

**Why temperature=1?**
- Encourages diverse scenario generation across multiple calls
- Higher temperature → more variation in evidence bucketing
- Produces richer 36-72 scenario distributions for GPR

### Supporting Models
- **Summarizer**: `openrouter/openai/o4-mini`
- **Researcher**: `asknews/news-summaries`
- **Parser**: `openrouter/openai/o4-mini`

---

## Data Handling

### Scenario Storage
**Instance Variables** (main.py:177-179):
```python
self._binary_scenarios = []           # Accumulates all scenarios
self._current_question_id = None      # Tracks current question
self._current_call_number = 0         # Tracks call count
```

### Flexible Parsing (main.py:42-49)
```python
class MultiScenarioPrediction(BaseModel):
    scenarios: list[float] = Field(
        description="List of forecast probabilities from low to high (0-100)",
        min_length=1  # Accepts any count
    )
```

**Design Decision**: Flexible list instead of fixed structure
- Works with 3, 9, or any number of scenarios
- Robust to LLM miscounts (asks for 9, gets 8 → still works)
- Easy to change scenario count via prompt only (no code changes)
- Graceful degradation: with 72 scenarios, losing a few won't impact aggregation

### Auto-Correction Feature (main.py:336-342)
If LLM returns decimals (0-1) instead of percentages (0-100):
```python
if max(scenario_prediction.scenarios) < 1.0:
    logger.warning("[DECIMAL DETECTED] Auto-correcting by ×100")
    scenario_prediction.scenarios = [s * 100 for s in scenario_prediction.scenarios]
```

---

## Quality Indicators

### Expected Scenario Characteristics

**Good distribution spans wide range**:
- Example: 1.3% to 42.3% for extinction question
- Low_World scenarios: typically cluster below 10%
- Mid_World scenarios: typically cluster 5-20%
- High_World scenarios: typically cluster above 15%

**Within-world progression**:
- Generally: Low < Mid < High within each world
- Minor inversions acceptable (smoothed by GPR)

**Cross-world progression**:
- Low_World estimates < Mid_World estimates < High_World estimates
- Provides good coverage of probability space

---

## Development History

### December 30, 2025
- Initial GPR implementation for binary questions
- Basic 3×3 world matrix prompt

### December 31, 2025
- **Critical fix**: Async concurrency bug causing multiple GPR runs
- **Solution**: Override `_aggregate_predictions()` instead of detecting final call
- **Enhancement**: Flexible scenario count (any length list)
- **Fix**: Prompt parsing errors (removed % symbols from format)
- **Fix**: `question.id` → `question.page_url` attribute error
- Status: ✅ Tested successfully via GitHub Actions

### January 1, 2026
- **Critical fix**: Bucket-to-world mapping was backwards
  - Bucket 2 now correctly maps to Mid_World (was mapping to high evidence)
  - Bucket 3 now correctly maps to High_World (was mapping to central evidence)
- **Enhancement**: Clarified "pessimistic/optimistic" terminology
- **Fix**: Timeout increased from 40 to 80 seconds for GPT-5.2
- **Polish**: Fixed typos, formatting consistency, section hierarchy
- Status: ✅ Production ready

### January 21, 2026
- Moved aggregation logic to `dre_forecasting_tools.py` for better organization
- Added scenario data saving functionality
- Integrated with multiple question types (binary, numeric, multiple choice)

---

## Current Production Status

### ✅ Completed Features
- [x] 3×3 world matrix prompt with corrected bucket mapping
- [x] GPR aggregation on all scenarios
- [x] Async-safe execution (no race conditions)
- [x] Flexible scenario count handling
- [x] Appropriate timeout for GPT-5.2
- [x] Auto-correction for decimal/percentage confusion
- [x] Comprehensive debug logging
- [x] Scenario data saving

### ⚙️ Current Configuration
- Testing with 4 calls (36 scenarios)
- GPT-5.2 as primary model
- 80-second timeout per call
- Temperature = 1 for diversity

### 🚀 Production Scaling Plan
- Increase to 8 calls (72 scenarios)
- Monitor timeout performance
- Validate scenario quality at scale
- No code changes required (config only)

---

## Related Documentation

### Session Documents
- [Binary GPR Aggregation Debug and Enhancement Session 12-31-2025.md](./Binary%20GPR%20Aggregation%20Debug%20and%20Enhancement%20Session%2012-31-2025.md)
  - Async concurrency fix
  - Flexible scenario handling implementation

- [Binary Production Prompt Session 01-01-2026.md](./Binary%20Production%20Prompt%20Session%2001-01-2026.md)
  - Bucket mapping correction
  - Timeout fix
  - Prompt quality improvements

### Code Locations
- **Binary prompt**: `main.py:225-303`
- **Scenario parsing**: `main.py:312-370`
- **GPR aggregation**: `main.py:372-406`
- **Aggregation override**: `dre_forecasting_tools.py:85-125`
- **Helper functions**: `main.py:476-499`

### Test Questions
- Binary example: https://www.metaculus.com/questions/578/human-extinction-by-2100/

---

## Technical Dependencies

### Required Libraries
```python
numpy==2.3.5                    # Array operations, statistics
scikit-learn==1.8.0             # GPR implementation
pydantic==2.12.5                # Data validation
forecasting-tools               # Metaculus framework
```

### Key Imports
```python
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C
```

---

## Conclusion

The binary question forecasting system uses a sophisticated multi-scenario approach that:

1. **Explores uncertainty** through 3×3 world matrix (9 scenarios per call)
2. **Scales naturally** through parallel execution (4-8 calls)
3. **Aggregates intelligently** using GPR to smooth and calibrate
4. **Handles edge cases** with flexible parsing and auto-correction
5. **Executes reliably** with async-safe architecture

The system is production-ready and validated through successful GitHub Actions testing. It can scale from 36 to 72 scenarios with configuration changes only, providing a robust foundation for the Metaculus AI Tournament.

---

*Document created: January 29, 2026*
*Author: Claude Code (Sonnet 4.5)*
*Metaculus Spring 2026 AI Forecasting Bot Project*
