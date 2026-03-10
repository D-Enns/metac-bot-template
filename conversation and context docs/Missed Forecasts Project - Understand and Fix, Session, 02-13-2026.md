# Project: Understand and Fix Missed Forecasts in Metaculus Spring 2026 Bot Tournament
My github actions are not running for all questions, especially the Numeric category

## Current Behavior
- About 60% or more of Numeric questions are skipped with out any forecast or explanation from github actions
- About 20% of Binary questions skipped in a similar way
- At least 1 of about 6 Multiple Choice questions were skipped
- All question types are giving reasonable forecasts when a forecast is actually made
- Generally github actions is never (or almost never) reporting a failed workflow run

## Desired Behavior
- Forecast on all questions as they become available
- Notify when a forecast is not made, skipped, or fails for some reason
- Document reason for skipped runs and failures when a forecast is not made on an open question

## Possible Causes and Ideas

### The problem may already be well handled by the Metaculus Framework
- Compare main in https://github.com/Metaculus/metac-bot-template to main in https://github.com/D-Enns/metac-bot-template
- Compare forecasting tools in https://github.com/Metaculus/forecasting-tools to dre_forecasting_tools in https://github.com/D-Enns/metac-bot-template
- Compare Metaculus .yaml to my Dre Tournament Bot .yaml in https://github.com/D-Enns/metac-bot-template/actions

### There may be a problem with the .yaml file:
It seems like we added code that silenced some types of failures

### Something in main for https://github.com/D-Enns/metac-bot-template
- Question interval?
- Something that skips questions for some reason?
- Silent skipping?

### Metaculus Scheduling
- I believe that Metaculus manages traffic for bots trying to forecast on the same question
- Could there be a prioritization system?
- There appear to be more than 120 bots running right now, a significant increase from last season (about 95)
- Binary questions appear to have around 110-120 forecasts, but numeric questions have more like 90
- Could there be collisions as bots compete to forecast in a tight window, especially for numeric questions that take more time?

---

## Implementation Session 02-13-2026: Diagnostic Logging

### Key Insight
Runs that produce forecasts take 2+ minutes (LLM work). Runs without forecasts take ~1 minute. There are NO unexplained 2+ minute runs without forecasts. This means questions are being skipped **before any LLM work begins** — the problem is in question fetching/filtering, not in LLM processing or aggregation.

### What Was Implemented

#### Phase 1: Question Pipeline Diagnostics

**`dre_forecasting_tools.py` — Override `forecast_on_tournament`**
- Overrides the framework's 2-line method with diagnostic wrapper
- Calls `MetaculusApi.get_all_open_questions_from_tournament()` (same as framework)
- Logs every question returned: ID, type, `already_forecasted` status, text
- Logs counts by type, how many will be attempted vs skipped
- After `forecast_questions()` returns, inspects results for successes vs failures
- Failures get `::warning::` GitHub Actions annotations

**`dre_forecasting_tools.py` — Diagnostics helper methods**
- `_inspect_results()`: Separates `ForecastReport` objects from `BaseException` objects
- `write_diagnostics_json()`: Writes `forecast_summaries/run_diagnostics.json` with full pipeline data
- `_build_diagnostics_summary()`: Aggregates across tournament runs
- `get_exit_code()`: Returns 1 if all attempts failed, 0 otherwise

**`main.py` — End-of-script diagnostics**
- Calls `write_diagnostics_json()` after log summary
- Calls `get_exit_code()` and exits with code 1 if all forecasts failed

#### Phase 2: GitHub Actions Reporting

**`.github/workflows/dre_run_bot_on_tournament.yaml`**
- New "Write step summary from diagnostics" step (runs always)
- Reads `run_diagnostics.json` and writes a markdown table to `$GITHUB_STEP_SUMMARY`
- Shows: open questions, skipped, attempted, successes, failures per tournament
- Runs before artifact upload

### What This Will Tell Us

After 1-2 days of runs, the diagnostics will reveal:

1. **How many questions the API returns** each run — if fewer than expected, Metaculus API is the bottleneck
2. **Which are marked `already_forecasted`** — if questions we never forecasted show as already forecasted, the API flag is wrong
3. **Which question types are returned** — if Numeric questions are systematically missing, parsing is the issue
4. **If any attempted forecasts fail** — if they do, the error type/message tells us what to fix

### Files Modified

| File | Changes |
|------|---------|
| `dre_forecasting_tools.py` | Added `forecast_on_tournament` override, `_inspect_results`, `write_diagnostics_json`, `_build_diagnostics_summary`, `get_exit_code` |
| `main.py` | Added `import sys`, diagnostics write + exit code at end of script |
| `.github/workflows/dre_run_bot_on_tournament.yaml` | Added step summary reporting step |

### Phase 3 (Pending Diagnostic Results)

Specific reliability fixes ready to apply depending on findings:
- If API isn't returning questions: retry logic for API fetch
- If parsing drops questions: fix parser
- If `already_forecasted` is wrong: investigate API response
- If questions reach LLM but fail: lower temperature, increase retries/timeout, majority-vote fallback
