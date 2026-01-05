# Multiple Choice GPR Implementation Session
**Date:** January 2, 2026
**Status:** ✅ Implementation Complete - Ready for Testing

---

## Executive Summary

Successfully designed and implemented a comprehensive multiple choice forecasting system using GPR (Gaussian Process Regression) aggregation for the Spring 2026 Metaculus AI Forecasting Bot tournament starting Monday. The implementation mirrors the successful binary and numeric GPR approaches, using a 3×3 world matrix (StatusQuo/Balanced/Unexpected × Trendline/Baseline/Chaos) to generate 9 probability distributions per LLM call.

---

## Session Goals

1. ✅ Design multiple choice prompt following binary prompt structure
2. ✅ Implement scenario-based forecasting (9 scenarios per call)
3. ✅ Create GPR aggregation per option with normalization
4. ✅ Build data models and parsing logic
5. ✅ Integrate with existing aggregation framework

---

## Design Philosophy

### Consistency with Binary/Numeric Approaches

**Binary Questions:**
- 3×3 world matrix → 9 scenarios per call
- Evidence bucketing: Low/Central/High forecast
- GPR aggregation on all scenarios
- Production: 4-8 calls = 36-72 scenarios

**Numeric Questions:**
- 3×3 world matrix → 9 scenarios per call
- World types: Low/Mid/High outcomes
- GPR aggregation for distributions
- Production: 4-8 calls = 36-72 scenarios

**Multiple Choice Questions (New):**
- 3×3 world matrix → 9 distributions per call
- World types: StatusQuo/Balanced/Unexpected
- Conditions: Trendline/Baseline/Chaos
- GPR aggregation per option + normalization
- Production: 4-8 calls = 36-72 scenarios per option

---

## Prompt Design

### Evidence Bucketing Framework

Instead of binary's "low/central/high forecast" buckets, we use outcome-based bucketing:

```
Bucket 1: Evidence supporting the status quo or most expected outcome
Bucket 2: Evidence suggesting balanced uncertainty or multiple plausible outcomes
Bucket 3: Evidence favoring unexpected, alternative, or less conventional outcomes
```

### Three-World Framework

**1. StatusQuo_World**
- Based on evidence supporting the most expected outcome
- Generates distributions favoring the default/status quo option
- Example: If Option A is expected, StatusQuo_World concentrates probability on A

**2. Balanced_World**
- Based on evidence suggesting uncertainty across options
- Generates more evenly distributed probabilities
- Captures scenarios where no clear winner emerges

**3. Unexpected_World**
- Based on evidence favoring alternative outcomes
- Generates distributions favoring less conventional options
- Explores tail scenarios and surprises

### Second-Level Conditions (Trendline/Baseline/Chaos)

For each world, generate 3 probability distributions:

**a) Trendline** - probability distribution if trends present in this world continue
- Extrapolates current dynamics
- May produce concentrated or trending distributions
- Good for time-dependent questions

**b) Baseline** - probability distribution most supported by evidence in this world
- Most straightforward interpretation
- The "anchor" distribution for each world
- Most reliable scenario

**c) Chaos** - probability distribution given chaotic conditions that could occur in this world
- Wild card scenarios
- Introduces high variance and tail outcomes
- Captures unexpected volatility

**Design Decision:** Chose trendline/baseline/chaos over confidence levels (low/mid/high) to generate wider diversity through intentional ambiguity. The lack of precision encourages LLM to explore different scenario types.

---

## Prompt Structure

### Complete Prompt Outline

1. **Professional Framing** - "You are a professional forecaster interviewing for a job"
2. **Question Context** - Question text, options list, background, resolution criteria
3. **Research Input** - Research assistant findings
4. **Workflow - Strategy** - Multi-scenario approach explanation
5. **Workflow - Precision** - Avoid round numbers, ensure distributions sum to 100%
6. **Before Answering** - 6 items including time left, status quo, trends, scenarios
7. **Rationale Reminders** - Status quo bias, moderate probability on multiple options
8. **Evidence Grouping** - Bucket evidence into 3 groups
9. **Multi-World Considerations** - Generate 3 distributions for each of 3 worlds
10. **Final Answer Format** - List of 9 lists, clear formatting instructions

### Key Prompt Features

**Precision Guidance:**
```
You do not preferentially choose round probabilities like 10%, 20%, 30%, etc.
Instead you make your best forecast, allowing values such as 12%, 17%, 34%, 48%, 71%...
Avoid forecasts below 1% or above 99%. You ensure that probabilities for all options
sum to exactly 100% for each distribution you provide.
```

**Final Answer Format:**
```
Write them in order as a list of 9 lists:
[[StatusQuo_World-Trendline], [StatusQuo_World-Baseline], [StatusQuo_World-Chaos],
[Balanced_World-Trendline], [Balanced_World-Baseline], [Balanced_World-Chaos],
[Unexpected_World-Trendline], [Unexpected_World-Baseline], [Unexpected_World-Chaos]]

Each inner list contains probabilities for the options in this exact order: {question.options}

IMPORTANT:
- Write probabilities as numbers without percent signs
- Each inner list must have exactly {len(question.options)} values
- Each inner list must sum to exactly 100
```

**Critical Decision:** Use **list of lists** format (not dictionaries) for LLM output because:
- Simpler for LLM to generate
- Easier to parse
- Consistent with binary's simple list format
- Convert to dict of lists during storage for easier aggregation

---

## Implementation Details

### 1. Data Model (`MultipleChoiceScenarios`)

```python
class MultipleChoiceScenarios(BaseModel):
    """Nine probability distributions from 3x3 world matrix approach.
    Each distribution is a list of probabilities (one per option) that sum to 100."""
    scenarios: list[list[float]] = Field(
        ...,
        description="List of 9 probability distributions. Each inner list contains probabilities (0-100) for all options in order. Each distribution must sum to 100.",
        min_length=9,
        max_length=9
    )
```

**Location:** `main.py` lines 52-61

### 2. Storage Initialization

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._binary_scenarios = []
    self._numeric_scenarios = []
    self._multiple_choice_scenarios = {}  # Dict of lists, keyed by option name
    self._current_question_id = None
    self._current_call_number = 0
```

**Structure:** `{"Option A": [p1, p2, ...], "Option B": [...], ...}`
**Location:** `main.py` line 153

### 3. Transpose Helper Function (`_transpose_mc_scenarios`)

**Purpose:** Convert LLM output (list of lists) to storage format (dict of lists)

```python
Input:  [[60, 30, 10], [65, 25, 10], ...]  # 9 distributions
Output: {"Opt A": [60, 65, ...], "Opt B": [30, 25, ...], "Opt C": [10, 10, ...]}
```

**Features:**
- Validates distribution sizes
- Logs warnings for malformed data
- Maps by option name for aggregation

**Location:** `main.py` lines 421-458

### 4. Parsing and Storage (`_multiple_choice_prompt_to_forecast`)

**Data Flow:**

```
1. Clear storage if new question
   ↓
2. LLM generates reasoning with 9 distributions
   ↓
3. structure_output parses into MultipleChoiceScenarios
   ↓
4. Transpose to dict of lists
   ↓
5. Store/extend scenario lists per option
   ↓
6. Calculate median per option, normalize
   ↓
7. Return PredictedOptionList to framework
```

**Key Code:**
```python
# Parse 9 distributions
mc_scenario_prediction: MultipleChoiceScenarios = await structure_output(
    reasoning,
    MultipleChoiceScenarios,
    model=self.get_llm("parser", "llm"),
    num_validation_samples=self._structure_output_validation_samples,
)

# Convert and store
scenarios_by_option = self._transpose_mc_scenarios(
    mc_scenario_prediction.scenarios,
    question.options
)

for option_name, probabilities in scenarios_by_option.items():
    if option_name not in self._multiple_choice_scenarios:
        self._multiple_choice_scenarios[option_name] = []
    self._multiple_choice_scenarios[option_name].extend(probabilities)
```

**Location:** `main.py` lines 613-687

### 5. GPR Aggregation Function (`_gpr_aggregate_multiple_choice`)

**Algorithm:**

```
For each option:
  1. Get list of scenarios (e.g., 36 values)
  2. If ≥9 scenarios: Run GPR (reuse _gpr_aggregate_binary)
  3. If <9 scenarios: Use median fallback
  4. Convert GPR result to 0-100 scale

Normalize all options to sum to 1.0

Return dict of {option: probability} in 0-1 scale
```

**Key Features:**
- **Independent GPR per option:** Smooths each option's scenarios separately
- **Reuses binary GPR logic:** Efficient code reuse
- **Automatic normalization:** Ensures probabilities sum to exactly 1.0
- **Graceful fallbacks:** Median if insufficient scenarios

**Example:**
```python
Input:  {
    "Option A": [60, 65, 55, ..., 58],  # 36 scenarios
    "Option B": [30, 25, 28, ..., 28],  # 36 scenarios
    "Option C": [10, 10, 17, ..., 14]   # 36 scenarios
}

GPR Processing:
  Option A: GPR(36 values) → p50 = 58.2%
  Option B: GPR(36 values) → p50 = 27.4%
  Option C: GPR(36 values) → p50 = 14.7%
  Sum = 100.3%

Normalize:
  Option A: 58.2 / 100.3 = 0.580
  Option B: 27.4 / 100.3 = 0.273
  Option C: 14.7 / 100.3 = 0.147
  Sum = 1.000 ✓

Output: {"Option A": 0.580, "Option B": 0.273, "Option C": 0.147}
```

**Location:** `main.py` lines 396-462

### 6. Aggregation Override (`_aggregate_predictions`)

**Added Multiple Choice Branch:**

```python
elif isinstance(question, MultipleChoiceQuestion) and self._multiple_choice_scenarios:
    # Check minimum scenario threshold (≥9 per option)
    first_option = list(self._multiple_choice_scenarios.keys())[0]
    num_scenarios = len(self._multiple_choice_scenarios[first_option])

    if num_scenarios >= 9:
        # Run GPR aggregation
        gpr_results = self._gpr_aggregate_multiple_choice(self._multiple_choice_scenarios)

        # Convert to PredictedOptionList
        predicted_options = [
            PredictedOption(name=opt, probability=prob)
            for opt, prob in gpr_results.items()
        ]
        result = PredictedOptionList(predicted_options)

        # Clear scenarios after aggregation
        self._multiple_choice_scenarios = {}
        self._current_question_id = None

        return result
```

**Threshold Logic:**
- **≥9 scenarios per option:** Use GPR aggregation
- **<9 scenarios per option:** Fall back to framework's default mean aggregation

**Location:** `main.py` lines 576-607

---

## Complete Data Flow Example

### Scenario: 3-option question with 4 LLM calls

**Question:** "Who will win the 2028 election?"
**Options:** ["Candidate A", "Candidate B", "Other"]

**Call 1 generates:**
```python
[
    [55, 35, 10],  # StatusQuo_World-Trendline
    [60, 30, 10],  # StatusQuo_World-Baseline
    [50, 32, 18],  # StatusQuo_World-Chaos
    [45, 45, 10],  # Balanced_World-Trendline
    [48, 42, 10],  # Balanced_World-Baseline
    [40, 38, 22],  # Balanced_World-Chaos
    [30, 55, 15],  # Unexpected_World-Trendline
    [35, 52, 13],  # Unexpected_World-Baseline
    [25, 48, 27],  # Unexpected_World-Chaos
]
```

**After transpose and store:**
```python
{
    "Candidate A": [55, 60, 50, 45, 48, 40, 30, 35, 25],
    "Candidate B": [35, 30, 32, 45, 42, 38, 55, 52, 48],
    "Other": [10, 10, 18, 10, 10, 22, 15, 13, 27]
}
```

**After 4 calls (36 scenarios total):**
```python
{
    "Candidate A": [55, 60, 50, ..., 52, 48, 51],  # 36 values
    "Candidate B": [35, 30, 32, ..., 34, 38, 35],  # 36 values
    "Other": [10, 10, 18, ..., 14, 14, 14]         # 36 values
}
```

**GPR Aggregation:**
```python
Candidate A: GPR(36 scenarios) → p50 = 0.498
Candidate B: GPR(36 scenarios) → p50 = 0.368
Other: GPR(36 scenarios) → p50 = 0.135

Normalization check: 0.498 + 0.368 + 0.135 = 1.001
Normalized: {
    "Candidate A": 0.497,
    "Candidate B": 0.368,
    "Candidate C": 0.135
}
Sum = 1.000 ✓
```

**Final Submission:** PredictedOptionList with these probabilities

---

## Key Design Decisions & Rationale

### 1. StatusQuo/Balanced/Unexpected vs Other Frameworks

**Considered alternatives:**
- Low/Mid/High uncertainty worlds
- Optimistic/Neutral/Pessimistic perspectives
- Historical/Current/Future-based scenarios

**Why StatusQuo/Balanced/Unexpected:**
- ✅ Intuitive for any question type
- ✅ Creates natural probability spreads
- ✅ Mirrors binary's evidence bucketing approach
- ✅ Encourages consideration of different outcome types

### 2. Trendline/Baseline/Chaos vs Confidence Levels

**Considered alternatives:**
- Low/Mid/High confidence distributions
- Conservative/Moderate/Aggressive weightings
- Narrow/Wide uncertainty spreads

**Why Trendline/Baseline/Chaos:**
- ✅ Creates scenario diversity through ambiguity
- ✅ Encourages different types of reasoning
- ✅ "Chaos" introduces beneficial variance
- ✅ Can validate empirically in testing

**User rationale:** "Lack of clarity may actually be beneficial in generating a wider distribution."

### 3. List of Lists vs Dictionaries for LLM Output

**List of Lists (Chosen):**
```python
[[60, 30, 10], [65, 25, 10], ...]
```
- ✅ Simple for LLM to generate
- ✅ Easy to parse with structure_output
- ✅ Mirrors binary's simplicity
- ✅ Convert to dict during storage

**Dictionaries (Rejected):**
```python
[{"A": 60, "B": 30, "C": 10}, ...]
```
- ❌ More complex for LLM
- ❌ Requires exact option name matching
- ❌ More verbose
- ✅ Self-documenting (only advantage)

**Best of both worlds:** LLM outputs simple format, we convert once during parsing

### 4. GPR per Option vs Single Multivariate GPR

**GPR per Option (Chosen):**
- Run binary GPR independently for each option
- Normalize results to sum to 1.0

**Advantages:**
- ✅ Reuses proven binary GPR code
- ✅ Simple to implement and debug
- ✅ Each option gets smoothing treatment
- ✅ Normalization ensures valid probability distribution

**Multivariate GPR (Not chosen):**
- Single GPR model with correlation structure
- More statistically sophisticated

**Why not:**
- ❌ Much more complex to implement
- ❌ Correlation structure unclear for MC scenarios
- ❌ Not worth added complexity for first implementation
- ❌ Can revisit if per-option GPR underperforms

### 5. Minimum Scenario Threshold: 9

**Binary:** ≥3 scenarios for GPR
**Numeric:** ≥9 scenarios for GPR
**Multiple Choice:** ≥9 scenarios per option for GPR

**Rationale:**
- 9 scenarios = 3×3 matrix from one call
- Matches numeric's threshold
- Provides sufficient data for smooth GPR curves
- Less than 9 → falls back to median or framework mean

---

## Technical Specifications

### Files Modified

**main.py** - All changes in single file:
1. **Lines 52-61:** Added `MultipleChoiceScenarios` data model
2. **Line 153:** Added `_multiple_choice_scenarios = {}` to `__init__`
3. **Lines 421-458:** Added `_transpose_mc_scenarios()` helper function
4. **Lines 396-462:** Added `_gpr_aggregate_multiple_choice()` aggregation function
5. **Lines 613-687:** Replaced `_multiple_choice_prompt_to_forecast()` with scenario-based version
6. **Lines 576-607:** Added MC branch to `_aggregate_predictions()`

### Prompt Location

**main.py** - Lines 514-609 in `_run_forecast_on_multiple_choice()`

User hand-wrote the prompt following the design specification. Prompt includes:
- Professional framing
- Evidence bucketing (StatusQuo/Balanced/Unexpected)
- Trendline/Baseline/Chaos conditions
- List of lists output format
- Clear formatting instructions

### Dependencies

**No new dependencies required.** Implementation uses existing libraries:
- `numpy` - For median calculations
- `sklearn.gaussian_process` - For GPR (already used by binary/numeric)
- `pydantic` - For data model validation (already used)
- `forecasting_tools` - For framework integration (already used)

### Performance Characteristics

**Per Question (4 calls × 9 scenarios = 36 total):**
- LLM calls: 4
- Parsing operations: 4
- Transpose operations: 4
- Storage operations: 4
- GPR operations: 3 (one per option for 3-option question)
- Normalization: 1

**Estimated Time (with GPT-5.2, 80s timeout):**
- Total processing: ~3-5 minutes
- Dominated by LLM generation time
- GPR aggregation: <1 second

**Estimated Cost (GPT-5.2 pricing):**
- Per question: ~$0.20-0.35
- Depends on prompt length and option count
- Similar to binary/numeric

---

## Testing Recommendations

### 1. Basic Functionality Test

**Test Question:** Simple 3-option MC question
**Configuration:** 4 LLM calls
**Expected:** 36 scenarios per option, GPR aggregation succeeds

**Validation Checklist:**
- [ ] All 4 calls complete without errors
- [ ] 9 distributions parsed per call
- [ ] Transpose produces correct dict structure
- [ ] Storage accumulates to 36 scenarios per option
- [ ] GPR runs for each option
- [ ] Final probabilities sum to 1.0
- [ ] Logging shows all debug messages

### 2. Edge Case Testing

**A. Minimum Threshold (9 scenarios exactly)**
- Configuration: 1 LLM call
- Expected: GPR should run (exactly 9 scenarios)

**B. Below Threshold (8 scenarios)**
- Configuration: Simulate parsing failure on 9th scenario
- Expected: Fall back to default aggregation with warning

**C. Many Options (5+ options)**
- Test with 5-option question
- Verify GPR runs for all 5 options
- Check normalization still works

**D. Malformed Distributions**
- Test distribution that doesn't sum to 100
- Test distribution with wrong number of values
- Verify warnings logged, graceful handling

### 3. Comparison Testing

**Compare GPR vs Mean Aggregation:**
- Run same question with GPR (≥9 scenarios)
- Run same question with mean (force <9 scenarios)
- Compare smoothness and reasonableness of results

### 4. Production Simulation

**Full Tournament Run:**
- Configuration: 8 LLM calls (72 scenarios)
- Run on 5-10 MC questions
- Monitor for:
  - Timeout issues (similar to binary)
  - Parsing failures
  - Normalization errors
  - Unexpected warnings

### 5. Prompt Quality Assessment

**Manual Review of LLM Outputs:**
- Do distributions follow trendline/baseline/chaos distinctions?
- Are StatusQuo/Balanced/Unexpected worlds generating different probability patterns?
- Is there sufficient diversity across 9 scenarios?
- Do scenarios explore the full probability space?

**If quality issues found:**
- Adjust prompt wording for clarity
- Consider different second-level conditions
- Tune temperature or model selection

---

## Known Limitations & Future Improvements

### Current Limitations

1. **Independent GPR per option** - Doesn't model correlation between options
2. **Fixed 9-scenario structure** - Can't adapt to question complexity
3. **Trendline/baseline/chaos ambiguity** - May confuse LLM on some questions
4. **No calibration** - Probabilities not adjusted based on historical performance
5. **Equal weighting** - All scenarios weighted equally, no quality assessment

### Potential Improvements

**Short-term (if testing reveals issues):**
- Adjust trendline/baseline/chaos descriptions for clarity
- Add validation for distribution sums
- Implement retry logic for parsing failures
- Tune GPR kernel parameters per option count

**Medium-term:**
- Track per-option Brier scores for calibration
- Implement scenario quality scoring
- Add extremization post-processing
- Test alternative second-level conditions

**Long-term:**
- Multivariate GPR with correlation structure
- Adaptive scenario count based on question complexity
- Meta-learning for world framework selection
- Ensemble with mean aggregation

---

## Comparison with Other Question Types

| Feature | Binary | Numeric | Multiple Choice |
|---------|--------|---------|-----------------|
| **World Framework** | Low/Mid/High forecast | Low/Mid/High outcome | StatusQuo/Balanced/Unexpected |
| **Second Level** | Low/Mid/High estimate | Low/Mid/High estimate | Trendline/Baseline/Chaos |
| **Scenarios per Call** | 9 probabilities | 9 distributions | 9 distributions |
| **Output Format** | List of floats | List of dicts | List of lists |
| **Storage Format** | List | List | Dict of lists |
| **Aggregation** | GPR → p50 | GPR → full dist | GPR per option → normalize |
| **Minimum Threshold** | ≥3 scenarios | ≥9 scenarios | ≥9 scenarios per option |
| **Fallback** | Median | Median | Mean (framework default) |
| **Scale** | 0-1 | Question-specific | 0-1 (sums to 1) |

---

## Production Readiness Checklist

### Code Complete ✅
- [x] Data model implemented
- [x] Storage initialization added
- [x] Transpose helper function created
- [x] Parsing logic updated
- [x] GPR aggregation function implemented
- [x] Aggregation override updated
- [x] Prompt hand-written by user
- [x] All debug logging added

### Documentation ✅
- [x] Session summary created
- [x] Design decisions documented
- [x] Data flow examples provided
- [x] Testing recommendations outlined

### Pre-Testing Checklist ⚠️
- [ ] Review prompt in main.py for any typos
- [ ] Verify all imports present
- [ ] Check GPR kernel parameters reasonable
- [ ] Confirm model configuration (GPT-5.2, timeout=80)
- [ ] Prepare test MC questions

### Testing Phase 🔄
- [ ] Run basic functionality test
- [ ] Run edge case tests
- [ ] Compare GPR vs mean results
- [ ] Conduct production simulation
- [ ] Review prompt quality

### Production Deployment 🚀
- [ ] All tests pass
- [ ] Prompt refined if needed
- [ ] Configuration finalized
- [ ] Monitoring plan established
- [ ] Backup plan for failures

---

## Configuration for Monday's Tournament

### Recommended Settings

```python
template_bot = SpringTemplateBot2026(
    research_reports_per_question=1,
    predictions_per_research_report=4,  # 4 calls × 9 = 36 scenarios per option
    use_research_summary_to_forecast=False,
    publish_reports_to_metaculus=True,
    skip_previously_forecasted_questions=True,
    extra_metadata_in_explanation=True,
    llms={
        "default": GeneralLlm(
            model="openrouter/openai/gpt-5.2",
            temperature=1,
            timeout=80,  # May need adjustment for MC - monitor logs
            allowed_tries=2,
        ),
        "summarizer": "openrouter/openai/gpt-4o-mini",
        "researcher": "asknews/news-summaries",
        "parser": "openrouter/openai/gpt-4o-mini",
    },
)
```

### Monitoring Strategy

**During Tournament:**
1. Check logs after first MC question completes
2. Verify 36 scenarios collected (4 calls × 9)
3. Confirm GPR runs without errors
4. Validate output probabilities sum to 1.0
5. Monitor for timeout issues

**If Issues Arise:**
- Timeout: Reduce to 3 calls (27 scenarios) or increase timeout
- Parsing failures: Review error logs, may need prompt adjustment
- Poor diversity: Consider adjusting temperature or conditions
- Normalization errors: Check for edge cases in data

---

## Key Takeaways

### What Worked Well

1. **Consistent Methodology:** Successfully adapted binary/numeric GPR approach to MC
2. **Clean Separation:** LLM output format optimized separately from aggregation format
3. **Code Reuse:** Binary GPR function reused for each option
4. **Comprehensive Logging:** Debug info at every step for troubleshooting
5. **Graceful Fallbacks:** System degrades gracefully with insufficient data

### Critical Success Factors

1. **Prompt Quality:** Hand-written by user following design spec
2. **Format Simplicity:** List of lists easier for LLM than dictionaries
3. **Normalization:** Automatic normalization ensures valid probabilities
4. **Threshold Logic:** ≥9 scenarios provides sufficient data for GPR
5. **Independent GPR:** Simpler than multivariate, proven to work for binary

### Next Steps

1. **Test thoroughly** before Monday's tournament
2. **Monitor first few MC questions** closely during tournament
3. **Collect performance data** for future improvements
4. **Document any issues** that arise in production
5. **Compare results** to framework's default mean aggregation

---

## Conclusion

The Multiple Choice GPR implementation is **complete and ready for testing**. The system successfully mirrors the proven binary and numeric GPR approaches while adapting to the unique requirements of multiple choice questions. Key innovations include:

- StatusQuo/Balanced/Unexpected world framework for outcome-based evidence bucketing
- Trendline/Baseline/Chaos conditions for scenario diversity
- Independent GPR per option with automatic normalization
- Clean data flow from simple LLM output to sophisticated aggregation

The implementation is production-ready pending successful testing. The design prioritizes consistency with existing systems, code reuse, and graceful degradation, making it a robust addition to the Spring 2026 forecasting bot.

---

*Implementation Summary by Claude Code (Sonnet 4.5)*
*January 2, 2026*
*Metaculus Spring 2026 AI Forecasting Bot Project*
