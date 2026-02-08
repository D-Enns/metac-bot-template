# Re-enable Paused GitHub Workflow Scheduled Runs

## The Problem

GitHub Actions automatically pauses scheduled workflows after consecutive failures. This is a resource-saving feature, but it can be confusing because:
- The workflow still shows as "active" in the UI
- Manual runs (`workflow_dispatch`) still work
- Only the cron schedule stops firing

## How to Diagnose

Check if scheduled runs have stopped:
```bash
gh run list --repo D-Enns/metac-bot-template --workflow=dre_run_bot_on_tournament.yaml --limit 20
```

Look at the "event" column - if you see only `workflow_dispatch` and no `schedule` events for an extended period, the schedule is likely paused.

## How to Re-enable

### Option 1: GitHub CLI (Recommended)

```bash
# First, get the workflow ID
gh workflow list --repo D-Enns/metac-bot-template

# Then enable it (replace 220638909 with your workflow ID)
gh api repos/D-Enns/metac-bot-template/actions/workflows/220638909/enable --method PUT
```

### Option 2: GitHub Web UI

1. Go to https://github.com/D-Enns/metac-bot-template/actions
2. Click on "Dre Tournament Bot" in the left sidebar
3. If disabled, you'll see an "Enable workflow" button - click it

### Option 3: Push a Commit

Any commit pushed to the repository will re-enable paused scheduled workflows.

## Prevention

The schedule pauses when consecutive runs fail. To reduce this risk:
- Add error handling to your bot script so it exits gracefully
- Consider using `continue-on-error: true` for non-critical steps
- Monitor your workflow runs and fix failures promptly
