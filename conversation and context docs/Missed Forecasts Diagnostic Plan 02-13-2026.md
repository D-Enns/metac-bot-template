# Plan: Understand and Fix Missed Forecasts

## Context

~60% of Numeric questions and ~20% of Binary questions are silently skipped — never forecasted at all. GitHub Actions always reports "success." Questions are only open for **1 hour**, and the bot runs every 20 minutes, giving at most **3 attempts** per question.

**Key observation from the user**: Runs that produce forecasts take 2+ minutes (LLM work). Runs without forecasts take ~1 minute. There are NO unexplained 2+ minute runs without forecasts. This means **questions are being skipped before any LLM work begins** — the problem is in question fetching/filtering, not in LLM processing or aggregation.

## What We Don't Yet Know

The missed questions never reach the LLM stage. The cause must be one of:
1. **Metaculus API doesn't return the question** — traffic management, throttling, or API behavior with 120+ competing bots
2. **Question parsing silently fails** — the question JSON can't be parsed into a MetaculusQuestion and is dropped
3. **`already_forecasted` is incorrectly True** — the API reports the bot has forecasted a question it hasn't

We need diagnostic logging to determine which of these is the actual cause.

## Implementation Plan

### Phase 1: Question Pipeline Diagnostics (TOP PRIORITY)

**1a. Override `forecast_on_tournament` in `SpringTemplateBotExtended`** — `main.py`

Add a method override that wraps the framework's question fetching with detailed logging:

```python
async def forecast_on_tournament(self, tournament_id, return_exceptions=False):
    from forecasting_tools.helpers.metaculus_api import MetaculusApi

    # Fetch questions (same as framework)
    questions = MetaculusApi.get_all_open_questions_from_tournament(tournament_id)

    # Diagnostic logging — question pipeline
    logger.info(f"{'='*60}")
    logger.info(f"QUESTION PIPELINE: Tournament {tournament_id}")
    logger.info(f"Total open questions from API: {len(questions)}")

    by_type = {}
    for q in questions:
        q_type = type(q).__name__
        by_type[q_type] = by_type.get(q_type, 0) + 1
        q_id = getattr(q, 'id_of_post', '?')
        logger.info(f"  Q{q_id} [{q_type}] forecasted={q.already_forecasted}")
    logger.info(f"By type: {by_type}")

    unforecasted = [q for q in questions if not q.already_forecasted]
    logger.info(f"Unforecasted (will attempt): {len(unforecasted)}")
    for q in unforecasted:
        q_id = getattr(q, 'id_of_post', '?')
        logger.info(f"  ATTEMPT: Q{q_id} [{type(q).__name__}]")
    logger.info(f"{'='*60}")

    # Proceed with normal processing
    return await self.forecast_questions(questions, return_exceptions)
```

This tells us for every run:
- How many questions the API returns (and their types)
- Which are marked `already_forecasted`
- Which will actually be attempted

**1b. Add result inspection** — `main.py` (after each `asyncio.run(...)`)

Add a helper that separates successful `ForecastReport` objects from `BaseException` objects in the results list:
- Log count of successes vs failures
- Log the exception type and message for each failure
- Use `::warning::` GitHub Actions annotation syntax

**1c. Write diagnostic summary** — `main.py` (end of script)

Write `forecast_summaries/run_diagnostics.json` with:
- Questions returned by API (IDs, types, already_forecasted status)
- Questions attempted
- Successes and failures with error details
- This gets picked up by the existing artifact upload

**1d. Exit code** — `main.py` (end of script)
- If questions were attempted and ALL failed → `sys.exit(1)` so GitHub Actions shows failure
- Otherwise exit 0

### Phase 2: GitHub Actions Reporting

**2a. Add step summary** — `.github/workflows/dre_run_bot_on_tournament.yaml`
- New step after "Run bot" that reads `run_diagnostics.json` and writes to `$GITHUB_STEP_SUMMARY`
- Shows question counts, types, and any failures directly on the Actions run page

### Phase 3: Reliability Fixes (after diagnostics reveal the cause)

These are queued for after we observe a few runs with diagnostics. Depending on findings:

- **If API isn't returning questions**: May need to investigate Metaculus traffic management, or add retry logic for the API fetch itself
- **If parsing drops questions**: Fix the parser or add error handling
- **If `already_forecasted` is wrong**: Investigate the API response data
- **If questions DO reach LLM but fail** (contradicting current timing observation): Apply majority-vote fallback, lower temperature, increase retries/timeout

Specific reliability changes ready to apply if needed:
- `main.py:842-851`: Convert majority-vote hard failure to warning-with-fallback
- `main.py:1303`: Lower temperature from 1.0 to 0.5
- `main.py:1305`: Increase `allowed_tries` from 2 to 4
- `main.py:1304`: Increase timeout from 80 to 120

## Files Modified

| File | Phase | Changes |
|------|-------|---------|
| `main.py` | 1 | Override `forecast_on_tournament`, add result inspection helper, write diagnostics JSON, exit code logic |
| `.github/workflows/dre_run_bot_on_tournament.yaml` | 2 | Add step summary reporting step |
| `main.py` | 3 | Reliability fixes (pending diagnostic results) |

## Key Framework Files (read-only reference)

| File | Relevance |
|------|-----------|
| `forecasting_tools/forecast_bots/forecast_bot.py:160-166` | `forecast_on_tournament` — fetches questions then calls `forecast_questions` |
| `forecasting_tools/forecast_bots/forecast_bot.py:228-236` | `forecast_questions` — `skip_previously_forecasted_questions` filter |
| `forecasting_tools/helpers/metaculus_client.py:342-357` | API fetch — `get_all_open_questions_from_tournament` |
| `forecasting_tools/data_models/questions.py:127-131` | `already_forecasted` — checks `my_forecasts.history` from API |

## Verification

1. **Phase 1**: Push to GitHub, let it run for 1-2 days. Check GitHub Actions logs and `run_diagnostics.json` artifacts. Look for:
   - Are all expected questions appearing in the API response?
   - Are any incorrectly marked as `already_forecasted`?
   - Are any questions being attempted but failing?
2. **Phase 2**: Verify step summary appears on the GitHub Actions run page
3. **Phase 3**: Apply targeted fixes based on diagnostic findings, then compare success rates
