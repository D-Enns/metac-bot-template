# MC Option Name Normalization Fix Session
**Date:** February 4, 2026
**Status:** Complete — fix implemented and production-verified
**File Modified:** `main.py`

---

## Problem

Forecast runs were failing on multiple choice questions with this error:

```
ValueError - All predictions must have the same option names, but
{'Decreases', 'Increases', 'Doesn't change'} != ['Increases', "Doesn't change", 'Decreases']
```

Affected questions: q/42000, q/42001 (and potentially any MC question with apostrophes in option names)

---

## Root Cause

**Unicode apostrophe mismatch in LLM output.**

The option `Doesn't change` contains an apostrophe that exists in two visually identical but byte-different forms:

| Character | Unicode | Name |
|-----------|---------|------|
| `'` | U+0027 | ASCII apostrophe (straight) |
| `'` | U+2019 | Right single quotation mark (curly/smart) |

The LLM (`gpt-5.2` via OpenRouter) intermittently outputs the curly variant in some predictions. Since the bot runs 6 predictions per question, if 5 use ASCII and 1 uses Unicode, the framework's `MultipleChoiceReport.aggregate_predictions()` detects a mismatch and raises `ValueError`.

The error message is misleading because both apostrophe variants render identically in logs/terminals.

---

## Solution

Added a normalization step in `main.py` that maps all predicted option names back to the question's canonical options after `structure_output` parsing.

### New Method: `_normalize_mc_option_names`

**Location:** `main.py`, lines 451-481 (in `SpringTemplateBot2026` class)

```python
def _normalize_mc_option_names(
    self,
    prediction: PredictedOptionList,
    question: MultipleChoiceQuestion
) -> PredictedOptionList:
    """
    Map predicted option names to question's canonical options.

    Handles Unicode quote variants (smart quotes vs ASCII) that cause
    aggregation failures when LLM outputs differ across runs.
    """
    def normalize_quotes(s: str) -> str:
        # Replace smart/curly quotes with ASCII equivalents
        return (s.replace('\u2019', "'")   # Right single quote → apostrophe
                 .replace('\u2018', "'")   # Left single quote → apostrophe
                 .replace('\u201c', '"')   # Left double quote → straight double
                 .replace('\u201d', '"')   # Right double quote → straight double
                 .strip())

    # Build lookup: normalized canonical name -> original canonical name
    canonical_map = {normalize_quotes(opt).lower(): opt for opt in question.options}

    normalized_options = []
    for pred in prediction.predicted_options:
        key = normalize_quotes(pred.option_name).lower()
        canonical_name = canonical_map.get(key, pred.option_name)  # fallback to original if no match
        normalized_options.append(
            PredictedOption(option_name=canonical_name, probability=pred.probability)
        )

    return PredictedOptionList(predicted_options=normalized_options)
```

### Call Site

**Location:** `main.py`, line 616 (in `_run_forecast_on_multiple_choice`)

```python
mc_prediction: PredictedOptionList = await structure_output(
    reasoning, PredictedOptionList, model=self.get_llm("parser", "llm")
)

# Normalize option names to match question's canonical options (handles Unicode quote variants)
mc_prediction = self._normalize_mc_option_names(mc_prediction, question)
```

### New Import

**Location:** `main.py`, line 41

```python
from forecasting_tools.data_models.multiple_choice_report import PredictedOption
```

---

## Additional Issue: asknews Rate Limit

During diagnosis, the bot was also hitting `RateLimitExceededError` from `asknews/news-summaries`. This is an external API quota issue unrelated to code.

**Workaround:** Temporarily switched researcher to `smart-searcher/openai/gpt-4o-mini` for testing.

**Current config** (line 1308):
```python
"researcher": "asknews/news-summaries",  # Working alternative: "smart-searcher/openai/gpt-4o-mini"
```

---

## Verification

1. **Test run:** Passed on test question with MC options including "Doesn't change"
2. **Production run:** Succeeded on full tournament

---

## Changes NOT Related to This Fix

The earlier "Condensed Summary Fix Session 02-04-2026" changes were confirmed to have no involvement in these errors. Those changes only touched:
- Aggregation method labels in metadata (cosmetic)
- Debug log tag rename (cosmetic)
- Condensed summary prompt updates
- Post-generation validation (warn-only)

None of those code paths execute before or during MC aggregation.

---

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Added `PredictedOption` import, `_normalize_mc_option_names()` method, and normalization call in `_run_forecast_on_multiple_choice()` |

---

*Session completed by Claude Opus 4.5*
*February 4, 2026*
*Metaculus Spring 2026 AI Forecasting Bot Project*
