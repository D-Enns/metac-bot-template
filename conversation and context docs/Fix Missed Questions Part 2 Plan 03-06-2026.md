# Fix Missed Questions Part 2 — Session 03-06-2026

## Context

10-30% of tournament questions still don't receive a forecast. Part 1 (2026-02-14) fixed two specific bugs: numeric integer bounds assertion and MC option name mismatches. This session investigates remaining causes and implements fixes.

**Key observation:** Missed questions are more common when many questions are released over a short period of time.

## Investigation Results

### Data collected
- Listed last 60 GitHub Actions runs (2026-03-04 to 2026-03-06)
- Downloaded and analyzed logs from 13 runs (all 14 runs with 2+ min duration, plus the only failure)
- Downloaded and inspected `forecasting-tools` v0.2.85 wheel source code

### Finding 1: Zero Metaculus API 429 errors
The `forecasting-tools` library sleeps 3.5-4.5 seconds between every Metaculus API call and retries with exponential backoff (3 retries, 2.5s initial delay, 3x exponential, jitter up to 8x). This is working correctly — no Metaculus rate limit errors found.

### Finding 2: AskNews rate limit caused the only failure
Run 22576198226 (2026-03-02): 3 open questions in minibench, 2 unforecasted → attempted both. Q42391 succeeded, Q42390 failed with `RateLimitExceededError: 429000` from AskNews API. This was the only failure in the last 200 runs.

### Finding 3: Crash propagation bug
The AskNews 429 caused the framework to include an exception in the results list. `log_report_summary()` then raised `RuntimeError` when processing results containing exceptions. The handler only caught `ValueError`, so the process crashed with exit code 1 **before diagnostics JSON was written**.

### Finding 4: Bot only sees 0-1 questions per run
Across all 13 analyzed runs, the bot never saw more than 1 unforecasted question per tournament (except the failed run which had 2). Questions typically open one at a time with ~20-minute spacing matching the cron schedule.

### Finding 5: No framework parsing drops since v0.2.85
Zero silent question drops from framework parsing errors in the analyzed period.

### Summary: What actually causes missed questions
1. **AskNews rate limiting** when 2+ questions appear simultaneously → crash kills the whole run (FIXED in this session)
2. **Questions opening between run windows** — normal with 20-min cron, some questions may not overlap with a run
3. The original bugs from Part 1 (numeric bounds, MC option names) were already fixed

## Fixes Applied

### Fix 1: Broaden exception handler around `log_report_summary` (main.py)
Changed from `except ValueError` to `except (ValueError, RuntimeError, Exception)` so that framework errors from failed forecast results don't crash the process. The forecasts are already posted by this point — the summary log is not critical.

### Fix 2: Add timestamps to ALL diagnostic entries (dre_forecasting_tools.py)
- `api_fetch_time` — when the question list was fetched
- `forecast_start_time` / `forecast_end_time` — bracket around the forecast pipeline
- `fetched_at` — per-question fetch timestamp
- `timestamp` — on each success and failure result

This allows correlating timing with question release patterns.

## Files Modified

| File | Change |
|------|--------|
| `main.py` | Broadened exception handler around `log_report_summary` from `ValueError` to `Exception` |
| `dre_forecasting_tools.py` | Added timestamps to all diagnostic entries (API fetch, forecast start/end, per-question, per-result) |

## Open Questions / Next Steps

- **Should the bot retry AskNews on 429?** The framework doesn't retry research provider errors. Could add a wrapper with backoff around the research call.
- **Should the cron interval be reduced?** Running every 10-15 minutes instead of 20 would reduce the window for missed questions, but at the cost of more API calls and GitHub Actions minutes.
- **Monitor after fixes:** The crash-prevention fix means that if 2+ questions appear and 1 fails (AskNews 429), the other will still succeed and diagnostics will be written.
