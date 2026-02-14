# Session: First Diagnostic Results and Fixes — 2026-02-14

## Context

Follow-up to the "Missed Forecasts" diagnostic logging session (02-13-2026). The diagnostic code had been running overnight and we analyzed the first results.

## Findings

### 1. Numeric Questions Silently Dropped by Framework Parser

**Question:** Q42105 (numeric, upper bound = 150)
**Error:** `Error processing post ID 42105: AssertionError Upper bound is 150`
**Root cause:** `forecasting-tools` v0.2.80 had `assert isinstance(upper_bound, float)` in `_get_bounds_from_api_json`. The Metaculus API returned `range_max: 150` as a JSON integer. Python's `isinstance(150, float)` is `False`, so the assertion failed. The framework's `_get_questions_from_api` caught the exception and silently dropped the question, logging only a warning.
**Appeared in:** 4 consecutive runs (10:47–11:50 UTC) — every time Q42105 was open.
**Fix:** Updated `forecasting-tools` from 0.2.80 to 0.2.85 in `poetry.lock`. v0.2.85 wraps bounds in `float()` with a try/except instead of asserting.

### 2. Multiple Choice Option Name Mismatch (Q42104)

**Question:** Q42104 — Quebec by-election, 6 options (CAQ, PQ, PLQ, QS, Conservative, Other)
**Error:** `All predictions must have the same option names, but {'Option_F', ...} != ['CAQ', ...]`
**Root cause:** The MC prompt (main.py lines 602-606) instructed the LLM to output `Option_A: Probability_A` format. Out of 6 LLM runs:
- 4 returned correct names (CAQ, Parti Québécois, etc.)
- 1 returned hybrid format (Option_A (CAQ), Option_B (PQ), etc.)
- 1 returned pure generic placeholders (Option_A, Option_B, etc.)
The existing `_normalize_mc_option_names` only handled Unicode quote variants, not positional mapping. The framework's `aggregate_predictions` rejected the name mismatch.
**Fix:** Two changes in `main.py`:
1. Prompt output format now lists exact option names instead of Option_A placeholders
2. `_normalize_mc_option_names` extended with positional fallback: `Option_A` → 1st option, `Option_B` → 2nd option, etc.

### 3. Diagnostic Infrastructure Working Well

- Pipeline logging correctly shows question counts, types, and attempts for every run
- Exit code logic works (failed runs show as failures in GitHub Actions)
- `run_diagnostics.json` not written on crash runs (process exits before reaching that code) — raw logs needed instead

## Key Diagnostic Technique: Inspecting Installed Package Source

The `assert isinstance(upper_bound, float)` line existed in the installed v0.2.80 wheel but had already been fixed on the framework's GitHub `main` branch. To find it:
1. Check `poetry.lock` for exact pinned version
2. Download wheel from PyPI: `curl -sL "https://pypi.org/pypi/forecasting-tools/0.2.80/json" | ...`
3. Extract and grep with `zipfile`

This is documented in the updated `SKILL_run_diagnostic_checks.md`.

## Files Modified

| File | Change |
|------|--------|
| `poetry.lock` | `forecasting-tools` 0.2.80 → 0.2.85 |
| `main.py` | MC prompt uses exact option names; `_normalize_mc_option_names` adds positional fallback; comment added |
| `dre_tools/SKILL_run_diagnostic_checks.md` | New skill file for diagnostic workflow |

## Commits

1. `6d02610` — Update forecasting-tools 0.2.80 -> 0.2.85 to fix numeric question parsing
2. `092d31f` — Fix MC option name mismatch: use exact names in prompt and add positional fallback

## Next Steps

- Monitor runs over next 1-2 days to confirm both fixes work
- Watch for new numeric questions with integer bounds (should now parse correctly)
- Watch for next MC question (should use correct option names consistently)
- If the "silent skip" rate for numeric questions doesn't improve, there may be additional parsing issues beyond the integer bounds assertion
