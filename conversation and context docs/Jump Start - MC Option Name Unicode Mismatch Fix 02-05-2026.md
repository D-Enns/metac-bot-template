# Jump Start: Multiple Choice Option Name Unicode Mismatch Fix

**Date:** 2026-02-05
**Status:** On hold - Metaculus may have fixed on their side. Apply if error recurs.

---

## Problem Summary

ValueError during Multiple Choice prediction aggregation:
```
Bot: SpringTemplateBotExtended
ValueError - All predictions must have the same option names, but
{'Decreases', "Doesn't change", 'Increases'} != ['Increases', 'Doesn't change', 'Decreases']
```

**Affected question:** https://www.metaculus.com/questions/42006
**Failed run:** https://github.com/D-Enns/metac-bot-template/actions/runs/21719015542/job/62643095322

### Root Cause
The Python repr output reveals the issue:
- Set shows: `"Doesn't change"` (double quotes = contains ASCII apostrophe U+0027)
- List shows: `'Doesn't change'` (single quotes = contains Unicode U+2019)

**These are different strings despite looking identical visually.** The forecasting-tools library correctly rejects them as mismatched.

---

## Diagnosis Details

### How Python repr reveals the difference
When Python prints a string containing `'` (ASCII apostrophe), it uses double quotes around it. When the string contains a different Unicode character that *looks* like an apostrophe (like U+2019), Python uses single quotes. This is how we know the two "Doesn't change" strings are actually different.

### Current Normalization Function (main.py:451-481)
The existing `_normalize_mc_option_names()` has three flaws:

**Flaw 1: Incomplete Unicode Coverage**
Only handles 4 characters:
- U+2019 (RIGHT SINGLE QUOTATION MARK)
- U+2018 (LEFT SINGLE QUOTATION MARK)
- U+201C (LEFT DOUBLE QUOTATION MARK)
- U+201D (RIGHT DOUBLE QUOTATION MARK)

But LLMs can output many more apostrophe-like characters.

**Flaw 2: Dangerous Fallback**
```python
canonical_name = canonical_map.get(key, pred.option_name)  # fallback to original
```
When lookup fails, returns raw LLM output (potentially with Unicode variants), causing inconsistency.

**Flaw 3: Values Not Normalized**
The `canonical_map` stores original `question.options` values (may contain Unicode). Only the keys are normalized for lookup. So all successful lookups return the Unicode variant from question.options.

---

## Fix: Replace _normalize_mc_option_names Method

**File:** `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/main.py`
**Location:** Lines 451-481

### Replace entire method with:

```python
def _normalize_mc_option_names(
    self,
    prediction: PredictedOptionList,
    question: MultipleChoiceQuestion
) -> PredictedOptionList:
    """
    Map predicted option names to question's canonical options.

    Handles Unicode quote/apostrophe variants (smart quotes, modifier letters, etc.)
    that cause aggregation failures when LLM outputs differ across runs.

    The fix ensures ALL returned option names use consistent ASCII apostrophes,
    regardless of what Unicode variants appear in question.options or LLM output.
    """
    import re

    def normalize_text(s: str) -> str:
        """
        Normalize text for matching: convert all apostrophe-like and quote-like
        Unicode characters to ASCII equivalents, normalize whitespace.
        """
        # Single quote-like characters -> ASCII apostrophe U+0027
        apostrophe_chars = (
            '\u2019'   # RIGHT SINGLE QUOTATION MARK (most common smart quote)
            '\u2018'   # LEFT SINGLE QUOTATION MARK
            '\u201B'   # SINGLE HIGH-REVERSED-9 QUOTATION MARK
            '\u02BC'   # MODIFIER LETTER APOSTROPHE
            '\u02B9'   # MODIFIER LETTER PRIME
            '\u0060'   # GRAVE ACCENT
            '\u00B4'   # ACUTE ACCENT
            '\u2032'   # PRIME
            '\u2035'   # REVERSED PRIME
            '\uFF07'   # FULLWIDTH APOSTROPHE
            '\uA78C'   # LATIN SMALL LETTER SALTILLO
        )
        for char in apostrophe_chars:
            s = s.replace(char, "'")

        # Double quote-like characters -> ASCII double quote U+0022
        double_quote_chars = (
            '\u201C'   # LEFT DOUBLE QUOTATION MARK
            '\u201D'   # RIGHT DOUBLE QUOTATION MARK
            '\u201F'   # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
            '\u00AB'   # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
            '\u00BB'   # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
            '\u2033'   # DOUBLE PRIME
            '\u2036'   # REVERSED DOUBLE PRIME
            '\uFF02'   # FULLWIDTH QUOTATION MARK
        )
        for char in double_quote_chars:
            s = s.replace(char, '"')

        # Normalize whitespace: collapse multiple spaces to single, strip edges
        s = re.sub(r'\s+', ' ', s).strip()

        return s

    # Build lookup: normalized canonical name -> normalized canonical name
    # IMPORTANT: We normalize BOTH key and value to ensure consistent output
    canonical_options_normalized = [normalize_text(opt) for opt in question.options]
    canonical_map = {opt.lower(): opt for opt in canonical_options_normalized}

    normalized_options = []
    for pred in prediction.predicted_options:
        key = normalize_text(pred.option_name).lower()

        if key in canonical_map:
            # Match found - use the normalized canonical name
            canonical_name = canonical_map[key]
        else:
            # No match found - log warning and use best-effort normalized version
            logger.warning(
                f"MC option name mismatch: '{pred.option_name}' (normalized: '{key}') "
                f"not found in question options: {canonical_options_normalized}. "
                f"Using normalized version as fallback."
            )
            canonical_name = normalize_text(pred.option_name)

        normalized_options.append(
            PredictedOption(option_name=canonical_name, probability=pred.probability)
        )

    return PredictedOptionList(predicted_options=normalized_options)
```

### Key Changes from Original:
1. **Expanded Unicode coverage** - 11 apostrophe-like + 8 double-quote-like characters
2. **Normalize values too** - `canonical_map` stores normalized versions, not originals
3. **Better fallback** - Returns `normalize_text(pred.option_name)` instead of raw input
4. **Whitespace normalization** - Handles extra spaces via `re.sub(r'\s+', ' ', s).strip()`
5. **Warning log** - Logs when fallback is used for debugging

---

## Verification After Applying Fix

1. Run the bot workflow on question 42006
2. All 6 MC runs should complete without ValueError
3. Check logs for any normalization warnings (indicates partial mismatch)
4. Verify aggregated prediction has consistent option names

---

## Related Files

- `main.py:451-481` - Current normalization function
- `main.py:616` - Where normalization is called in `_run_forecast_on_multiple_choice()`
- `dre_forecasting_tools.py:129` - Where aggregation delegates to library
- forecasting-tools library `multiple_choice_report.py` - Where error is raised

---

## Library Code Reference (forecasting-tools)

The validation that raises the error:
```python
# In forecasting_tools/data_models/multiple_choice_report.py
first_list_option_names = [
    pred_option.option_name for pred_option in predictions[0].predicted_options
]

for option_list in predictions:
    current_option_names = {
        option.option_name for option in option_list.predicted_options
    }
    if current_option_names != set(first_list_option_names):
        raise ValueError(
            f"All predictions must have the same option names, but {current_option_names} != {first_list_option_names}"
        )
```

The comparison uses `set()` correctly, so the error only occurs when strings are actually different (not just type mismatch).
