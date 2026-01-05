# Forecast Summary and Comment System

**Date:** December 31, 2025
**Purpose:** Documentation on how forecast summaries are generated and posted to Metaculus

---

## Overview

When the bot makes a forecast, it posts a detailed comment/summary to the Metaculus question page. This document explains how that summary is generated and how to customize it for the GPR multi-scenario forecasting approach.

---

## Current System Architecture

### Where Comments Are Generated

**Main Method:** `ForecastBot._create_comment()`

**Location:** forecasting-tools framework (not in main.py)

**Call Chain:**
```
forecast_questions()
  → _run_individual_question()
    → _create_comment()  ← Generates the comment text
      → _format_and_expand_research_summary()  ← "Forecaster 1, 2, 3, 4" section
      → _format_main_research()                ← RESEARCH section
      → _format_forecaster_rationales()        ← FORECASTS section with reasoning
    → MetaculusClient.post_comment()  ← Posts to Metaculus
```

### Method Signature

```python
def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,  # This is the FINAL GPR result
    final_cost: float,
    time_spent_in_minutes: float,
) -> str
```

**Key Parameters:**
- `research_prediction_collections` - List containing each "research report" with its predictions
  - For our config: 1 research report with 4 predictions
  - Each prediction contains the reasoning and the median value returned from that LLM call
- `aggregated_prediction` - The FINAL prediction after `_aggregate_predictions()` runs
  - For binary questions with GPR: This is the GPR p50 value
  - Without GPR override: This would be median of the 4 returned values

---

## Current Output Format

### Structure

```markdown
# SUMMARY
*Question*: [Question text]
*Final Prediction*: [GPR result] (6.51% in example)
*Total Cost*: [$0.1304 (estimated)]
*Time Spent*: [0.58 minutes]
*LLMs*: [Model configuration dict]
*Bot Name*: SpringTemplateBot2026

## Report 1 Summary
### Forecasts
*Forecaster 1*: 5.0%
*Forecaster 2*: 5.0%
*Forecaster 3*: 5.0%
*Forecaster 4*: 5.0%

### Research Summary
[Summarized research text]

# RESEARCH
[Full research articles]

# FORECASTS
## R1: Forecaster 1 Reasoning
[Full reasoning from LLM call 1]

## R1: Forecaster 2 Reasoning
[Full reasoning from LLM call 2]

## R1: Forecaster 3 Reasoning
[Full reasoning from LLM call 3]

## R1: Forecaster 4 Reasoning
[Full reasoning from LLM call 4]
```

---

## Issues with Current Format for GPR Approach

### 1. **Forecaster Values Don't Show Scenarios**

**Current:**
```
*Forecaster 1*: 5.0%
```

**Problem:** Only shows the median of the 3 scenarios from that call. Doesn't show the full distribution.

**Actual LLM Output:**
```
Forecaster 1: [10%, 5%, 2%]  (Low, Mid, High)
```

**Why it happens:** The framework only sees the median value we return from `_binary_prompt_to_forecast()`. It doesn't know about the full scenario list.

---

### 2. **No Mention of GPR Aggregation**

**Current:**
```
*Final Prediction*: 6.51%
```

**Problem:** Doesn't explain that this came from GPR aggregation of 12 scenarios.

**Better:**
```
*Final Prediction*: 6.51% (GPR aggregation of 12 scenarios)
```

---

### 3. **Formatting Issues**

**Problems:**
- Escaped underscores: `original\_model` instead of proper markdown
- Metadata all on one line in some sections
- No line breaks between fields

---

## How to Customize the Summary

### Option 1: Override `_create_comment()` - Complete Control

**Best for:** Major changes to structure and content

**Implementation:**
```python
class SpringTemplateBot2026(ForecastBot):
    # ... existing code ...

    def _create_comment(
        self,
        question: MetaculusQuestion,
        research_prediction_collections: list[ResearchWithPredictions],
        aggregated_prediction: PredictionTypes,
        final_cost: float,
        time_spent_in_minutes: float,
    ) -> str:
        """Custom comment format for GPR multi-scenario forecasting"""
        from forecasting_tools.data_models.data_organizer import DataOrganizer

        report_type = DataOrganizer.get_report_type_for_question_type(type(question))

        # Custom format for binary questions
        if isinstance(question, BinaryQuestion):
            return self._create_gpr_binary_comment(
                question, research_prediction_collections,
                aggregated_prediction, final_cost, time_spent_in_minutes
            )
        else:
            # Use default for other question types
            return super()._create_comment(
                question, research_prediction_collections,
                aggregated_prediction, final_cost, time_spent_in_minutes
            )
```

---

### Option 2: Modify Parent Output - Simpler

**Best for:** Adding information without restructuring

**Implementation:**
```python
def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    # Get default comment from parent
    parent_comment = super()._create_comment(
        question, research_prediction_collections,
        aggregated_prediction, final_cost, time_spent_in_minutes
    )

    # Add GPR information for binary questions
    if isinstance(question, BinaryQuestion):
        gpr_note = f"\n\n## Aggregation Method\n"
        gpr_note += f"**Method:** Gaussian Process Regression (GPR)\n"
        gpr_note += f"**Scenarios Aggregated:** {len(self._binary_scenarios_last_question)}\n"
        gpr_note += f"**Calls:** {self.predictions_per_research_report} LLM calls\n"
        gpr_note += f"**Scenarios per call:** 3 (Low, Mid, High)\n"
        return parent_comment + gpr_note

    return parent_comment
```

**Note:** Would need to store scenario count: `self._binary_scenarios_last_question`

---

### Option 3: Override Helper Methods - Targeted Changes

**Best for:** Changing specific sections only

**Methods to override:**
- `_format_and_expand_research_summary()` - Changes "Forecaster 1, 2, 3, 4" section
- `_format_main_research()` - Changes RESEARCH section
- `_format_forecaster_rationales()` - Changes FORECASTS section

**Example:**
```python
def _format_and_expand_research_summary(
    self,
    report_num: int,
    report_type,
    collection: ResearchWithPredictions
) -> str:
    """Custom format showing all scenarios for binary questions"""

    if report_type == BinaryReportType:
        # Custom format for binary with scenarios
        forecasts_section = "### Forecasts\n\n"
        for i, pred in enumerate(collection.predictions, 1):
            # Here we'd need access to the original scenarios
            # Currently only have the median value in pred.prediction
            forecasts_section += f"*Forecaster {i}*: {pred.prediction:.1%}\n"

        return f"## Report {report_num} Summary\n{forecasts_section}\n..."
    else:
        # Use default for other types
        return super()._format_and_expand_research_summary(
            report_num, report_type, collection
        )
```

---

## Recommended Approach for GPR Integration

### Phase 1: Simple Addition (Easiest)

**Modify:** Add GPR note to existing format

**Changes:**
- Override `_create_comment()`
- Call parent method
- Append GPR methodology note for binary questions

**Pros:**
- Minimal code changes
- Doesn't break anything
- Easy to test

**Cons:**
- Still shows misleading "Forecaster 1: 5%" values
- Doesn't show full scenario distributions

---

### Phase 2: Full Custom Format (Better Fit)

**Modify:** Complete rewrite of binary question comments

**Changes:**
- Override `_create_comment()` with custom logic for binary
- Show all scenarios for each forecaster
- Explain GPR aggregation method
- Add visualization of scenario distribution

**Example Output:**
```markdown
# SUMMARY
*Question*: Will humans go extinct before 2100?
*Final Prediction*: 6.51%
*Aggregation Method*: Gaussian Process Regression (GPR)
*Scenarios*: 12 total (4 calls × 3 scenarios per call)

## Scenario Distribution
**Call 1:** [10%, 5%, 2%]  (Low, Mid, High)
**Call 2:** [10%, 5%, 1%]
**Call 3:** [10%, 5%, 2%]
**Call 4:** [10%, 5%, 1%]

**GPR p50:** 6.51% (smoothed from 12 scenarios)
**Scenario Range:** 1% to 10%

## Research Summary
[Research text]

# DETAILED REASONING
[Show the 4 reasoning blocks]
```

**Pros:**
- Clear explanation of methodology
- Shows full data that went into forecast
- Transparent about GPR aggregation
- Better for readers who want to understand the process

**Cons:**
- More code to write and maintain
- Need to store scenarios between calls for later access
- Might be too verbose for some readers

---

## Implementation Considerations

### Storing Scenario Data for Comments

**Problem:** By the time `_create_comment()` is called, we've already returned median values and the framework doesn't know about individual scenarios.

**Solution:** Store scenario data in instance variables for later retrieval

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._binary_scenarios = []
    self._current_question_id = None
    self._current_call_number = 0
    # NEW: Store scenarios by call for comment generation
    self._scenarios_by_call = {}  # {question_url: [[s1, s2, s3], [s4, s5, s6], ...]}

async def _binary_prompt_to_forecast(...):
    # ... existing code ...

    # Store scenarios by call
    if question.page_url not in self._scenarios_by_call:
        self._scenarios_by_call[question.page_url] = []
    self._scenarios_by_call[question.page_url].append(
        [low_decimal, mid_decimal, high_decimal]
    )

    # ... rest of existing code ...
```

Then in `_create_comment()`:
```python
def _create_comment(...):
    scenarios_for_question = self._scenarios_by_call.get(question.page_url, [])
    # Now can access all scenarios for formatting
```

---

### Performance Impact

**Concern:** Does customizing comments slow down the bot?

**Answer:** No significant impact
- Comment generation happens AFTER forecasting completes
- Only affects time to post, not time to forecast
- Adding a few lines of text is negligible

---

## Alternative: Post Separate Analysis Comment

**Idea:** Keep the default comment format, post a second comment with GPR analysis

**Implementation:**
```python
async def _run_individual_question(...):
    # Let parent post standard comment
    report = await super()._run_individual_question(question)

    # Post additional GPR analysis comment for binary questions
    if isinstance(question, BinaryQuestion):
        gpr_analysis = self._create_gpr_analysis_comment(question)
        await self.metaculus_client.post_comment(question, gpr_analysis)

    return report
```

**Pros:**
- Doesn't modify existing format
- Easy to add/remove
- Separates methodology explanation from forecast

**Cons:**
- Two comments instead of one
- Might clutter the question page
- Need to track which questions already have analysis comments

---

## Next Steps for Implementation

### If You Want to Customize Now:

1. **Choose an approach** from the options above
2. **Test locally first** with a single test question
3. **Verify the comment looks correct** on Metaculus staging (if available) or a test question
4. **Deploy to production** once satisfied

### If You Want to Wait:

The current format works fine for now. You can customize later when you:
- Have more experience with how forecasts perform
- Decide what information is most valuable to display
- Get feedback from other Metaculus users

### Recommended First Step:

**Option 2 (Modify Parent Output)** is the safest starting point:
- Add a note about GPR methodology
- Keep everything else the same
- Easy to remove if you don't like it

---

## Technical Reference

### Key Classes and Methods

**From forecasting-tools framework:**
- `ForecastBot._create_comment()` - Main comment generation
- `ForecastBot._format_and_expand_research_summary()` - Forecaster section
- `ForecastBot._format_main_research()` - Research section
- `ForecastBot._format_forecaster_rationales()` - Reasoning section
- `MetaculusClient.post_comment()` - Posts to Metaculus API

**From your main.py:**
- `SpringTemplateBot2026._aggregate_predictions()` - GPR aggregation (where final value comes from)
- `SpringTemplateBot2026._binary_prompt_to_forecast()` - Where scenarios are stored

### Where to Override

Add custom methods in `SpringTemplateBot2026` class after the GPR aggregation methods (around line 400-450 in main.py).

---

## Examples to Reference

**Current summary example:**
`conversation and context docs/Example Forecast Summary Markdown - Binary Question 578, 12-31-2025.txt`

**What the framework sees:**
- 4 median values returned from `_binary_prompt_to_forecast()`
- 1 aggregated value from `_aggregate_predictions()` (GPR p50)
- Research text from `run_research()`
- Reasoning text from each LLM call

**What it doesn't see:**
- Individual scenarios (10%, 5%, 2%) - only medians
- That GPR was applied - just gets the final number
- How many scenarios were aggregated

---

*Document created: December 31, 2025*
*For: Metaculus Spring 2026 Forecasting Bot*
*GPR Multi-Scenario Binary Forecasting Implementation*
