# Session: Fix Missed Questions Part 2 — 2026-03-06

## Context

10-30% of tournament questions were not receiving forecasts. Part 1 (2026-02-14) fixed two bugs: numeric integer bounds assertion and MC option name mismatches. This session investigated remaining causes.

Previous session: `Diagnostic Results and Fixes Session 02-14-2026.md`
Project doc: `PROJECT - Fix Missed Questions part 2, 03-06-2026 .md`

## Investigation

### Approach
- Listed last 60 runs (Mar 4-6), downloaded and analyzed 13 runs
- Listed all 100 runs from Mar 1-3, downloaded and analyzed all 40 runs that processed questions (2+ min duration)
- Downloaded `forecasting-tools` v0.2.85 wheel from PyPI, inspected MetaculusApi and MetaculusClient source for rate limiting

### Finding 1: Metaculus API rate limiting is NOT the problem
The `forecasting-tools` library sleeps 3.5-4.5 seconds between every Metaculus API call and retries with exponential backoff (3 retries, 2.5s initial, 3x exponential, jitter up to 8x, max 75s). Zero Metaculus 429 errors found across all 53 analyzed runs.

### Finding 2: AskNews 429 is the sole cause of missed questions
Every single failure (19 out of 66 attempts in Mar 1-3) was `RateLimitExceededError: 429000` from the AskNews API. The pattern:
- 1 question per run → **100% success rate**
- 2+ questions per run → 1st question succeeds, all subsequent fail with AskNews 429
- Worst case: run `22560365727` had 6 questions, only 2 succeeded, 4 failed

### Finding 3: Crash propagation bug
When a question failed with AskNews 429, the exception was included in the results list. `log_report_summary()` then raised `RuntimeError` processing these results, but the handler only caught `ValueError`. The process crashed before writing diagnostics JSON.

### Finding 4: 9 questions permanently missed in Mar 1-3
Of 56 unique questions attempted:
- 40 succeeded on first try (71%)
- 7 failed then succeeded on a later run (13%)
- 9 never succeeded — questions closed before retry (16%)

### Mar 1-3 Statistics

| Metric | Value |
|--------|-------|
| Total runs | 100 |
| Runs that processed questions | 40 |
| Unique questions attempted | 56 |
| Per-attempt failure rate | 19/66 (28.8%) |
| Questions eventually forecasted | 47/56 (83.9%) |
| Questions permanently missed | 9/56 (16.1%) |
| Runs with 2+ questions | 14 |
| Failure cause breakdown | 19/19 AskNews 429 (100%) |

## Fixes Applied

### Fix 1: Add 10s sleep after AskNews research calls (main.py)
Added `await asyncio.sleep(10)` after each `AskNewsSearcher().call_preconfigured_version()` call. This prevents consecutive AskNews calls from hitting the rate limit when multiple questions appear in the same run. 10-second interval confirmed from Discord forum as previously effective.

### Fix 2: Broaden exception handler around `log_report_summary` (main.py)
Changed from `except ValueError` to `except (ValueError, RuntimeError, Exception)`. Prevents the process from crashing when results contain failed forecast exceptions. Forecasts are already posted by this point.

### Fix 3: Add timestamps to all diagnostic entries (dre_forecasting_tools.py)
Added `api_fetch_time`, `forecast_start_time`/`forecast_end_time`, per-question `fetched_at`, and per-result `timestamp` to diagnostics JSON for timing correlation analysis.

### Fix 4: Updated SKILL_run_diagnostic_checks.md
Added AskNews 429 crash as known failure pattern #3 with symptoms, log clues, and fix status.

### Also created: CLAUDE.md
Repository guidance file for Claude Code with project overview, key commands, architecture, and development notes.

## Commits

1. `eaa3d3a` — Fix missed questions: prevent AskNews 429 crash, add diagnostic timestamps
2. `964a014` — Add 10s sleep after AskNews research to prevent 429 rate limit

## Files Modified

| File | Change |
|------|--------|
| `main.py` | Added 10s sleep after AskNews calls; broadened exception handler |
| `dre_forecasting_tools.py` | Added timestamps to all diagnostic entries |
| `dre_tools/SKILL_run_diagnostic_checks.md` | Added AskNews 429 failure pattern and session history |
| `CLAUDE.md` | New file — repository guidance for Claude Code |

## Next Steps

- Monitor runs over next few days — miss rate should drop significantly
- If AskNews 429 still occurs with 10s sleep, increase to 15-20s
- Consider reducing cron interval from 20 to 10-15 minutes for faster pickup of new questions
