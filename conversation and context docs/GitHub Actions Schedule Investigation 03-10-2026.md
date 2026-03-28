# GitHub Actions Schedule Investigation 03-10-2026

## Question
Run 22933973168 appeared to show a surprisingly long interval between bot runs. Is the "Dre Tournament Bot" still scheduled every 20 minutes?

## Findings

**The cron config is correct.** `dre_run_bot_on_tournament.yaml` line 6:
```yaml
cron: "*/20 * * * *"
```
No changes were made to the schedule.

**Run 22933973168 was a manual dispatch** (`workflow_dispatch`), not a scheduled run, so it doesn't reflect the cron interval.

**Scheduled runs do show variable gaps**, caused by GitHub Actions infrastructure delays — not config issues. Sample gaps from the 15 most recent runs (all on 2026-03-10/11 UTC):

| Gap | Notes |
|-----|-------|
| ~95 min | 23:54 → 01:29 (overnight) |
| ~63 min | 21:19 → 22:23 |
| ~57 min | 18:26 → 19:23 |
| ~49 min | 17:37 → 18:26 |
| ~23–34 min | Several runs in this range |

Most gaps are 25–50 minutes rather than the configured 20. A few exceed 60 minutes.

## Explanation
GitHub's docs state that cron-triggered workflows are not guaranteed to run on time and can be delayed during periods of high load on GitHub Actions infrastructure. This is a known platform limitation — there is no fix on the user side. The bot's `concurrency` setting (`cancel-in-progress: false`) is also correct and does not cause skips; it just queues runs if one is already in progress.

## Conclusion
No action needed. The schedule configuration is correct. The observed delays are normal GitHub Actions behavior.
