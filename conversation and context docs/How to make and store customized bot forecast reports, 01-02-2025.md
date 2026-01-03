# How to Make and Store Customized Bot Forecast Reports

**Date:** January 2, 2025
**Project:** Metaculus AI Forecasting Bot - Spring 2026
**Purpose:** Documentation for customizing forecast summaries posted to Metaculus

---

## Table of Contents

1. [Overview](#overview)
2. [Current Forecast Summary Architecture](#current-forecast-summary-architecture)
3. [Source Code Analysis](#source-code-analysis)
4. [Customization Goals](#customization-goals)
5. [Implementation Plan](#implementation-plan)
6. [Code Examples](#code-examples)

---

## Overview

This document explains how the forecasting-tools library creates forecast summaries and provides a roadmap for customizing them. The forecast summary (also called "explanation") is the markdown-formatted text posted to Metaculus alongside each prediction.

### Key Components

- **Source Repository:** https://github.com/Metaculus/forecasting-tools
- **Main Class:** `ForecastBot` in `forecast_bots/forecast_bot.py`
- **Key Method:** `_create_comment()` - assembles the complete forecast explanation
- **Your Bot Class:** `SpringTemplateBot2026` in `main.py`

---

## Current Forecast Summary Architecture

### Summary Structure

Every forecast posted to Metaculus follows this structure:

```markdown
# SUMMARY
*Question*: {question_text}
*Final Prediction*: {readable_prediction}
*Total Cost*: ${cost} (estimated)
*Time Spent*: {minutes} minutes
*LLMs*: `{llm_configuration}`
*Bot Name*: {bot_class_name}

## Report 1 Summary
### Forecasts
*Forecaster 1*: {prediction_1}
*Forecaster 2*: {prediction_2}
...

### Research Summary
{summary_report_text}

# RESEARCH
## Report 1 Research
{formatted_research_markdown}

# FORECASTS
## R1: Forecaster 1 Reasoning
{full_llm_reasoning_output}

## R1: Forecaster 2 Reasoning
{full_llm_reasoning_output}
...
```

### Prediction Display Formats

**Binary Questions:**
```
75.0%
```

**Numeric Questions:**
```
Probability distribution:
- 10.00% chance of value below 5.250000
- 50.00% chance of value below 17.500000
- 90.00% chance of value below 32.100000
```

**Multiple Choice Questions:**
```
- Option A: 45.67%
- Option B: 32.15%
- Option C: 22.18%
```

### Your Bot Configuration

From `main.py` lines 1416-1422:

```python
research_reports_per_question=1,      # 1 research cycle
predictions_per_research_report=4,    # 4 LLM calls per cycle
extra_metadata_in_explanation=True,   # Metadata visible
```

This creates:
- **1 Summary section** (with metadata)
- **1 Report Summary** (with 4 forecaster predictions listed)
- **1 Research section** (full research markdown)
- **4 Forecasts sections** (one complete reasoning per LLM call)

**Character Limit:** 150,000 characters (truncated to 2,000 if exceeded)

---

## Source Code Analysis

### Main Assembly Method: `_create_comment()`

**Location:** `forecasting_tools/forecast_bots/forecast_bot.py` (lines 585-645)

**Purpose:** Creates the complete forecast explanation posted to Metaculus API

```python
def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    """
    Creates the forecast report string that will be assigned to 'explanation' in the ForecastReport
    This is used as a comment in the Metaculus API
    """
    report_type = DataOrganizer.get_report_type_for_question_type(type(question))

    # Build three lists by iterating through each research report
    all_summaries = []
    all_core_research = []
    all_forecaster_rationales = []

    for i, collection in enumerate(research_prediction_collections):
        summary = self._format_and_expand_research_summary(
            i + 1, report_type, collection
        )
        core_research_for_collection = self._format_main_research(i + 1, collection)
        forecaster_rationales_for_collection = self._format_forecaster_rationales(
            i + 1, collection
        )
        all_summaries.append(summary)
        all_core_research.append(core_research_for_collection)
        all_forecaster_rationales.append(forecaster_rationales_for_collection)

    # Join all sections
    combined_summaries = "\n".join(all_summaries)
    combined_research_reports = "\n".join(all_core_research)
    combined_rationales = "\n".join(all_forecaster_rationales)

    # Format metadata
    time_spent_in_minutes_formatted = f"{round(time_spent_in_minutes, 2)} minutes"
    cost_formatted = f"${round(final_cost,4)} (estimated)"
    disabled_metadata_formatted = "extra_metadata_in_explanation is disabled"

    # Assemble the complete explanation
    full_explanation = clean_indents(
        f"""
        # SUMMARY
        *Question*: {question.question_text}
        *Final Prediction*: {report_type.make_readable_prediction(aggregated_prediction)}
        *Total Cost*: {cost_formatted if self.extra_metadata_in_explanation else disabled_metadata_formatted}
        *Time Spent*: {time_spent_in_minutes_formatted if self.extra_metadata_in_explanation else disabled_metadata_formatted}
        *LLMs*: `{self.make_llm_dict() if self.extra_metadata_in_explanation else disabled_metadata_formatted}`
        *Bot Name*: {self.__class__.__name__ if self.extra_metadata_in_explanation else disabled_metadata_formatted}

        {combined_summaries}

        # RESEARCH
        {combined_research_reports}

        # FORECASTS
        {combined_rationales}
        """
    )

    # Enforce character limit
    max_comment_size = 150000
    if len(full_explanation) > max_comment_size:
        full_explanation = (
            full_explanation[:2000]
            + "\n\n---\n\n The comment size exceeded max size and has been truncated"
        )
    return full_explanation
```

---

### Helper Method 1: `_format_and_expand_research_summary()`

**Purpose:** Creates summary section showing individual forecaster predictions

```python
@classmethod
def _format_and_expand_research_summary(
    cls,
    report_number: int,
    report_type: type[ForecastReport],
    predicted_research: ResearchWithPredictions,
) -> str:
    # Build bullet points for each forecaster's prediction
    forecaster_prediction_bullet_points = ""
    for j, forecast in enumerate(predicted_research.predictions):
        readable_prediction = report_type.make_readable_prediction(
            forecast.prediction_value
        )
        forecaster_prediction_bullet_points += (
            f"*Forecaster {j + 1}*: {readable_prediction}\n"
        )

    new_summary = clean_indents(
        f"""
        ## Report {report_number} Summary
        ### Forecasts
        {forecaster_prediction_bullet_points}

        ### Research Summary
        {predicted_research.summary_report}
        """
    )
    return new_summary
```

---

### Helper Method 2: `_format_main_research()`

**Purpose:** Formats research with adjusted markdown heading levels

```python
@classmethod
def _format_main_research(
    cls, report_number: int, predicted_research: ResearchWithPredictions
) -> str:
    markdown = predicted_research.research_report

    # Convert markdown to structured sections
    sections = MarkdownTree.turn_markdown_into_report_sections(markdown)

    try:
        # Adjust all headings to level 3 (###) or deeper
        modified_content = MarkdownTree.report_sections_to_markdown(sections, 3)
    except Exception as e:
        logger.error(f"Error formatting research report: {e}")
        # Fallback: replace # with [Hashtag] to avoid breaking structure
        modified_content = MarkdownTree.report_sections_to_markdown(
            sections, None
        ).replace("#", "[Hashtag]")

    final_content = f"## Report {report_number} Research\n{modified_content}"
    return final_content
```

---

### Helper Method 3: `_format_forecaster_rationales()`

**Purpose:** Formats each LLM's reasoning output (this is where your multi-world analysis appears)

```python
def _format_forecaster_rationales(
    self, report_number: int, researched_predictions: ResearchWithPredictions
) -> str:
    rationales = []

    # Process each forecaster's reasoning
    for j, forecast in enumerate(researched_predictions.predictions):
        # Convert the reasoning to structured markdown sections
        sections = MarkdownTree.turn_markdown_into_report_sections(
            forecast.reasoning  # <-- YOUR LLM'S FULL OUTPUT IS HERE
        )

        try:
            # Adjust headings to level 3 or deeper
            modified_content = MarkdownTree.report_sections_to_markdown(sections, 3)
        except Exception as e:
            logger.error(f"Error formatting research report: {e}")
            modified_content = MarkdownTree.report_sections_to_markdown(
                sections, None
            ).replace("#", "[Hashtag]")

        new_rationale = clean_indents(
            f"""
            ## R{report_number}: Forecaster {j + 1} Reasoning
            {modified_content}
            """
        )
        rationales.append(new_rationale)

    return "\n".join(rationales)
```

---

### Supporting Methods

**LLM Configuration Display:**
```python
def make_llm_dict(self) -> dict[str, str | dict[str, Any] | None]:
    llm_dict: dict[str, str | dict[str, Any] | None] = {}
    for key, value in self._llms.items():
        if isinstance(value, GeneralLlm):
            llm_dict[key] = value.to_dict()
        else:
            llm_dict[key] = value
    return llm_dict
```

**Prediction Formatting (Binary):**
```python
@classmethod
def make_readable_prediction(cls, prediction: float) -> str:
    return f"{round(prediction * 100, 2)}%"
```

**Prediction Formatting (Multiple Choice):**
```python
@classmethod
def make_readable_prediction(cls, prediction: PredictedOptionList) -> str:
    option_bullet_points = [
        f"- {option.option_name}: {round(option.probability * 100, 2)}%"
        for option in prediction.predicted_options
    ]
    combined_bullet_points = "\n".join(option_bullet_points)
    return f"\n{combined_bullet_points}\n"
```

---

## Customization Goals

### Goal 1: Save Full Forecast Report Locally

**Objective:** Preserve complete, unmodified forecast explanations before any customization

**Requirements:**
- Save to local directory before submission
- Include full explanation text
- Include metadata (timestamp, question ID, prediction value)
- Organize by date and question

**Use Cases:**
- Archive of all bot reasoning
- Debugging and analysis
- Creating training data
- Performance review

---

### Goal 2: Submit Condensed Version to Metaculus

**Objective:** Post a shorter, more readable summary while keeping full version locally

**Requirements:**
- Generate condensed version from full explanation
- Maintain key information (prediction, rationale)
- Stay within reasonable length (5,000-10,000 characters)
- Post condensed version to Metaculus API

**Use Cases:**
- Improve readability on Metaculus
- Reduce clutter in public comments
- Focus on key insights
- Save API bandwidth

---

### Goal 3: Arbitrary Custom Content Control

**Objective:** Full flexibility to design any forecast summary format

**Requirements:**
- Override default formatting completely
- Access all raw data (research, predictions, metadata)
- Create custom templates per question type
- Add custom sections (GPR info, confidence metrics, etc.)

**Use Cases:**
- Highlight GPR aggregation process
- Add custom confidence intervals
- Include scenario probability breakdowns
- Create bot-specific branding
- Optimize for tournament scoring

---

## Implementation Plan

### Phase 1: Save Full Reports (Goal 1)

**Step 1.1: Create Directory Structure**

```bash
mkdir -p forecast_summaries/full_reports
mkdir -p forecast_summaries/condensed_reports
mkdir -p forecast_summaries/metadata
```

**Step 1.2: Add Save Method to `SpringTemplateBot2026`**

Add this method to your bot class in `main.py`:

```python
def _save_full_forecast_copy(
    self,
    full_explanation: str,
    question: MetaculusQuestion,
    aggregated_prediction,
    final_cost: float,
    time_spent_in_minutes: float
) -> None:
    """Save complete forecast explanation to file"""
    import json
    from datetime import datetime
    from pathlib import Path

    # Create directories if they don't exist
    reports_dir = Path("forecast_summaries/full_reports")
    metadata_dir = Path("forecast_summaries/metadata")
    reports_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    question_id = question.page_url.split("/")[-2]  # Extract ID from URL

    # Save full explanation as markdown
    explanation_file = reports_dir / f"q{question_id}_{timestamp}.md"
    with open(explanation_file, 'w', encoding='utf-8') as f:
        f.write(full_explanation)

    # Save metadata as JSON
    metadata = {
        "timestamp": timestamp,
        "question_id": question_id,
        "question_url": question.page_url,
        "question_text": question.question_text,
        "prediction": str(aggregated_prediction),
        "cost": final_cost,
        "time_minutes": time_spent_in_minutes,
        "explanation_length": len(full_explanation),
        "explanation_file": str(explanation_file)
    }

    metadata_file = metadata_dir / f"q{question_id}_{timestamp}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved full forecast report to {explanation_file}")
```

**Step 1.3: Test Saving Without Modification**

Override `_create_comment()` temporarily to test:

```python
async def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    # Get standard explanation from parent class
    full_explanation = await super()._create_comment(
        question,
        research_prediction_collections,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    # Save it
    self._save_full_forecast_copy(
        full_explanation,
        question,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    # Return unchanged for now
    return full_explanation
```

---

### Phase 2: Create Condensed Version (Goal 2)

**Step 2.1: Design Condensed Format**

Example condensed format:
```markdown
# Forecast Summary

**Question:** {question_text}
**Prediction:** {final_prediction}

## Key Reasoning
{condensed_rationale}

## Research Highlights
{key_research_points}

---
*Full analysis saved locally. Cost: ${cost} | Time: {minutes}min*
```

**Step 2.2: Add Condensing Method**

```python
def _create_condensed_summary(
    self,
    full_explanation: str,
    aggregated_prediction: PredictionTypes,
    question: MetaculusQuestion,
    final_cost: float,
    time_spent_in_minutes: float
) -> str:
    """Create condensed version of forecast explanation"""
    from forecasting_tools.data_models.data_organizer import DataOrganizer

    # Get report type for prediction formatting
    report_type = DataOrganizer.get_report_type_for_question_type(type(question))
    readable_prediction = report_type.make_readable_prediction(aggregated_prediction)

    # Extract key sections from full explanation
    # Option A: Manual extraction
    lines = full_explanation.split('\n')

    # Find first forecaster reasoning section
    key_reasoning = ""
    in_reasoning = False
    for i, line in enumerate(lines):
        if "Forecaster 1 Reasoning" in line:
            in_reasoning = True
            continue
        if in_reasoning and line.startswith("## R"):
            break
        if in_reasoning:
            key_reasoning += line + "\n"

    # Truncate reasoning to ~2000 characters
    if len(key_reasoning) > 2000:
        key_reasoning = key_reasoning[:2000] + "\n\n*[Reasoning truncated...]*"

    # Create condensed version
    condensed = clean_indents(
        f"""
        # Forecast Summary

        **Question:** {question.question_text}
        **Prediction:** {readable_prediction}

        ## Key Reasoning
        {key_reasoning}

        ---
        *Full analysis saved locally. Cost: ${round(final_cost, 4)} | Time: {round(time_spent_in_minutes, 2)}min*
        """
    )

    return condensed
```

**Alternative: LLM-Based Summarization**

```python
async def _create_condensed_summary_with_llm(
    self,
    full_explanation: str,
    aggregated_prediction: PredictionTypes,
    question: MetaculusQuestion
) -> str:
    """Use LLM to create condensed summary"""

    summarizer_llm = self.get_llm("summarizer", "llm")

    prompt = clean_indents(
        f"""
        You are summarizing a forecast for the Metaculus platform.

        Original forecast explanation (full version):
        {full_explanation[:10000]}  # Pass first 10k chars to avoid token limits

        Create a condensed version (max 3000 characters) that includes:
        1. The final prediction
        2. 2-3 key reasons for the forecast
        3. Most important research findings

        Be concise but maintain the core reasoning.
        """
    )

    condensed = await summarizer_llm.invoke(prompt)
    return condensed
```

**Step 2.3: Modify `_create_comment()` to Use Condensed Version**

```python
async def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    # Generate full explanation from parent class
    full_explanation = await super()._create_comment(
        question,
        research_prediction_collections,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    # Save full version locally
    self._save_full_forecast_copy(
        full_explanation,
        question,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    # Create condensed version
    condensed_explanation = self._create_condensed_summary(
        full_explanation,
        aggregated_prediction,
        question,
        final_cost,
        time_spent_in_minutes
    )

    # Save condensed version too (optional)
    # ... save to forecast_summaries/condensed_reports/ ...

    # Return condensed version for Metaculus API submission
    return condensed_explanation
```

---

### Phase 3: Full Custom Control (Goal 3)

**Step 3.1: Access All Raw Data**

Available parameters in `_create_comment()`:
- `question: MetaculusQuestion` - All question details
- `research_prediction_collections: list[ResearchWithPredictions]` - All research and predictions
- `aggregated_prediction: PredictionTypes` - Final forecast value
- `final_cost: float` - API cost
- `time_spent_in_minutes: float` - Execution time

**Step 3.2: Create Custom Template**

Example custom format highlighting GPR aggregation:

```python
async def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    """Custom forecast explanation with GPR details"""
    from forecasting_tools.data_models.data_organizer import DataOrganizer

    # Get report type
    report_type = DataOrganizer.get_report_type_for_question_type(type(question))
    readable_prediction = report_type.make_readable_prediction(aggregated_prediction)

    # Extract data from collections
    all_predictions = []
    for collection in research_prediction_collections:
        for forecast in collection.predictions:
            all_predictions.append(forecast.prediction_value)

    # Calculate prediction statistics
    if isinstance(question, BinaryQuestion):
        pred_values = [p for p in all_predictions]
        pred_min = min(pred_values)
        pred_max = max(pred_values)
        pred_median = float(np.median(pred_values))
        pred_std = float(np.std(pred_values))

        stats_section = f"""
        ## Prediction Statistics
        - **Range:** {pred_min*100:.1f}% to {pred_max*100:.1f}%
        - **Median:** {pred_median*100:.1f}%
        - **Standard Deviation:** {pred_std*100:.1f}%
        - **Final (GPR Aggregated):** {readable_prediction}
        """
    else:
        stats_section = f"**Final Prediction:** {readable_prediction}"

    # Extract key reasoning (first forecaster)
    first_reasoning = research_prediction_collections[0].predictions[0].reasoning

    # Extract research summary
    research_summary = research_prediction_collections[0].summary_report

    # Build custom explanation
    custom_explanation = clean_indents(
        f"""
        # 🤖 SpringBot 2026 Forecast

        **Question:** {question.question_text}

        {stats_section}

        ## Aggregation Method
        This forecast used **Gaussian Process Regression (GPR)** to aggregate {len(all_predictions)}
        independent scenario-based predictions from a multi-world analysis framework.

        ## Key Analysis
        {first_reasoning[:2000]}

        {"*[Analysis truncated for brevity]*" if len(first_reasoning) > 2000 else ""}

        ## Research Summary
        {research_summary[:1000]}

        ---
        *Methodology: Multi-world scenario analysis with GPR aggregation*
        *Cost: ${round(final_cost, 4)} | Time: {round(time_spent_in_minutes, 2)} minutes*
        """
    )

    # Save full version using parent method
    full_explanation = await super()._create_comment(
        question,
        research_prediction_collections,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )
    self._save_full_forecast_copy(
        full_explanation,
        question,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    return custom_explanation
```

**Step 3.3: Question-Specific Templates**

```python
async def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    # Route to question-specific formatter
    if isinstance(question, BinaryQuestion):
        return self._create_binary_custom_comment(
            question, research_prediction_collections, aggregated_prediction
        )
    elif isinstance(question, NumericQuestion):
        return self._create_numeric_custom_comment(
            question, research_prediction_collections, aggregated_prediction
        )
    elif isinstance(question, MultipleChoiceQuestion):
        return self._create_mc_custom_comment(
            question, research_prediction_collections, aggregated_prediction
        )
    else:
        # Fallback to parent method
        return await super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

def _create_binary_custom_comment(self, question, collections, prediction):
    """Custom format for binary questions"""
    # Emphasize key scenarios and base rates
    ...

def _create_numeric_custom_comment(self, question, collections, prediction):
    """Custom format for numeric questions"""
    # Highlight distribution shape and confidence intervals
    ...

def _create_mc_custom_comment(self, question, collections, prediction):
    """Custom format for multiple choice questions"""
    # Show probability reasoning per option
    ...
```

---

## Code Examples

### Complete Implementation: All Three Goals

```python
# Add to SpringTemplateBot2026 class in main.py

import json
from pathlib import Path
from datetime import datetime
from typing import Any

class SpringTemplateBot2026(ForecastBot):
    # ... existing code ...

    def _save_full_forecast_copy(
        self,
        full_explanation: str,
        question: MetaculusQuestion,
        aggregated_prediction: Any,
        final_cost: float,
        time_spent_in_minutes: float
    ) -> None:
        """Save complete forecast explanation to file"""
        # Create directories
        reports_dir = Path("forecast_summaries/full_reports")
        metadata_dir = Path("forecast_summaries/metadata")
        reports_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        question_id = question.page_url.split("/")[-2]

        # Save explanation
        explanation_file = reports_dir / f"q{question_id}_{timestamp}.md"
        with open(explanation_file, 'w', encoding='utf-8') as f:
            f.write(full_explanation)

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "question_id": question_id,
            "question_url": question.page_url,
            "question_text": question.question_text,
            "prediction": str(aggregated_prediction),
            "cost": final_cost,
            "time_minutes": time_spent_in_minutes,
            "explanation_length": len(full_explanation),
            "explanation_file": str(explanation_file)
        }

        metadata_file = metadata_dir / f"q{question_id}_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved full forecast: {explanation_file}")

    def _create_condensed_summary(
        self,
        full_explanation: str,
        aggregated_prediction: Any,
        question: MetaculusQuestion,
        final_cost: float,
        time_spent_in_minutes: float
    ) -> str:
        """Create condensed version of forecast"""
        from forecasting_tools.data_models.data_organizer import DataOrganizer

        report_type = DataOrganizer.get_report_type_for_question_type(type(question))
        readable_prediction = report_type.make_readable_prediction(aggregated_prediction)

        # Extract first forecaster reasoning
        lines = full_explanation.split('\n')
        key_reasoning = ""
        in_reasoning = False

        for line in lines:
            if "Forecaster 1 Reasoning" in line:
                in_reasoning = True
                continue
            if in_reasoning and line.startswith("## R"):
                break
            if in_reasoning:
                key_reasoning += line + "\n"

        # Truncate
        max_chars = 2000
        if len(key_reasoning) > max_chars:
            key_reasoning = key_reasoning[:max_chars] + "\n\n*[Full reasoning saved locally]*"

        # Create condensed version
        condensed = clean_indents(
            f"""
            # Forecast Summary

            **Question:** {question.question_text}
            **Prediction:** {readable_prediction}

            ## Key Reasoning
            {key_reasoning}

            ---
            *Methodology: Multi-world GPR aggregation*
            *Cost: ${round(final_cost, 4)} | Time: {round(time_spent_in_minutes, 2)}min*
            """
        )

        return condensed

    async def _create_comment(
        self,
        question: MetaculusQuestion,
        research_prediction_collections: list[ResearchWithPredictions],
        aggregated_prediction: PredictionTypes,
        final_cost: float,
        time_spent_in_minutes: float,
    ) -> str:
        """
        Override to:
        1. Save full report locally
        2. Return condensed version for Metaculus
        """
        # Generate full explanation using parent method
        full_explanation = await super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        # Save full version locally (Goal 1)
        self._save_full_forecast_copy(
            full_explanation,
            question,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        # Create condensed version (Goal 2)
        condensed_explanation = self._create_condensed_summary(
            full_explanation,
            aggregated_prediction,
            question,
            final_cost,
            time_spent_in_minutes
        )

        # Return condensed for API submission
        return condensed_explanation
```

---

## Testing Checklist

### Phase 1 Testing (Save Full Reports)
- [ ] Run bot on test question
- [ ] Verify `forecast_summaries/full_reports/` directory created
- [ ] Verify `forecast_summaries/metadata/` directory created
- [ ] Check markdown file contains full explanation
- [ ] Check JSON metadata file has all fields
- [ ] Confirm files are named correctly (question ID + timestamp)

### Phase 2 Testing (Condensed Submission)
- [ ] Run bot on test question
- [ ] Check Metaculus for posted explanation
- [ ] Verify posted version is condensed (shorter)
- [ ] Verify full version saved locally
- [ ] Confirm condensed version is readable
- [ ] Check character count is reasonable (<10k)

### Phase 3 Testing (Custom Format)
- [ ] Verify custom structure appears on Metaculus
- [ ] Check all custom sections are included
- [ ] Verify markdown formatting is correct
- [ ] Test with binary, numeric, and MC questions
- [ ] Confirm no broken links or formatting errors

---

## Data Flow Summary

### Standard Flow (Without Customization)

1. Bot generates predictions → `ReasonedPrediction` objects with reasoning
2. Framework aggregates → Calls `_aggregate_predictions()`
3. Framework builds report → Calls `_create_comment()`:
   - Formats forecaster rationales
   - Formats research
   - Assembles SUMMARY/RESEARCH/FORECASTS
4. Posts to Metaculus → Full explanation submitted

### Custom Flow (With All Three Goals)

1. Bot generates predictions → `ReasonedPrediction` objects with reasoning
2. Framework aggregates → Calls `_aggregate_predictions()` (your GPR override)
3. Your `_create_comment()` override:
   - Calls `super()._create_comment()` → Get full explanation
   - Saves full explanation locally → **Goal 1 ✓**
   - Creates condensed version → **Goal 2 ✓**
   - OR creates custom format → **Goal 3 ✓**
   - Returns condensed/custom version
4. Posts to Metaculus → Condensed/custom explanation submitted

---

## Key Insights

### Architecture Understanding

- **All customization happens in `_create_comment()`** - This single method controls what gets posted
- **You have access to all raw data** - Research, predictions, metadata all available
- **Parent method can be called for reference** - Use `super()._create_comment()` to get default
- **No framework changes needed** - Everything done via subclass override

### Best Practices

1. **Always save full version** - Don't lose detailed reasoning
2. **Test with test_questions mode first** - Avoid polluting production forecasts
3. **Watch character limits** - Metaculus has 150k limit, but shorter is better
4. **Preserve markdown formatting** - Use proper headers, bullets, etc.
5. **Include key metadata** - Cost, time, methodology help with analysis

### Gotchas

- `_create_comment()` is **not async** in current version - Don't use `await` on parent call
- Check if it's async in your version - Use `await super()._create_comment()` if needed
- **MarkdownTree adjusts headings** - Custom content should use H3 (###) or lower
- **Character encoding** - Use `encoding='utf-8'` when saving files
- **Path creation** - Use `mkdir(parents=True, exist_ok=True)` to avoid errors

---

## Next Steps

### Recommended Implementation Order

1. **Start with Goal 1** (saving full reports)
   - Lowest risk, no user-facing changes
   - Creates archive for analysis
   - Test thoroughly before moving on

2. **Then add Goal 2** (condensed version)
   - Moderate risk, affects public comments
   - Test on test_questions first
   - Get feedback on condensed format

3. **Finally Goal 3** (custom format)
   - Highest flexibility
   - Requires design decisions
   - Can iterate on format over time

### Future Enhancements

- **LLM-based summarization** - Use summarizer LLM for better condensing
- **Template library** - Create templates for different question types
- **Confidence visualization** - Add ASCII charts or probability ranges
- **Comparison to community** - Include comparison to Metaculus community prediction
- **Historical performance** - Reference bot's past performance on similar questions
- **External links** - Link to full reports on personal website
- **Structured data** - Include JSON-LD for machine readability

---

## Resources

- **Forecasting Tools Repository:** https://github.com/Metaculus/forecasting-tools
- **ForecastBot Source:** `forecasting_tools/forecast_bots/forecast_bot.py`
- **Report Classes:** `forecasting_tools/data_models/*_report.py`
- **Your Bot Code:** `main.py` (SpringTemplateBot2026 class)

---

*Document created: January 2, 2025*
*Last updated: January 2, 2025*
*Project: Metaculus AI Forecasting Bot - Spring 2026*
