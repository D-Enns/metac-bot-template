# Recipe: Downloading Forecast Summaries from GitHub

**Created:** January 21, 2026

---

## Prerequisites

1. **Install GitHub CLI** (one-time):
   ```powershell
   winget install --id GitHub.cli
   ```

2. **Authenticate** (one-time):
   ```powershell
   gh auth login
   ```
   - Select: GitHub.com → HTTPS → Yes → Login with web browser

3. **Verify authentication**:
   ```powershell
   gh auth status
   ```

---

## Download Steps

### Step 1: List Recent Workflow Runs

```powershell
gh run list --repo D-Enns/metac-bot-template --workflow dre_run_bot_on_tournament.yaml --limit 100
```

Look for runs with **duration > 1m30s** - these are actual forecast runs.

### Step 2: Download Specific Runs

For each run ID with substantial duration:
```powershell
gh run download <RUN_ID> --repo D-Enns/metac-bot-template --dir all_forecast_summaries/run-<RUN_ID>
```

Example:
```powershell
gh run download 21141087177 --repo D-Enns/metac-bot-template --dir all_forecast_summaries/run-21141087177
```

### Step 3: Find Scenario Files

```powershell
dir all_forecast_summaries\run-*\*scenarios*.json
```

Or check question types:
```powershell
findstr "question_type" all_forecast_summaries\run-*\*scenarios*.json
```

---

## File Types Downloaded

Each forecasted question generates 3 files:
- `{question_id}_{tournament}_full_1.md` - Full summary
- `{question_id}_{tournament}_condensed_1.md` - Condensed summary
- `{question_id}_{tournament}_scenarios_1.json` - Raw scenario data (for aggregation analysis)

---

## Important Reminder

**TODO: Verify Scenario Saving Process**

The scenario-saving feature (`_save_scenario_data()`) was added on January 6, 2026. Before relying on this data:

1. **Verify in main.py** that `_save_scenario_data()` is called for:
   - Binary questions
   - Numeric questions
   - Multiple choice questions
   - Date questions

2. **Check GitHub Actions workflow** ensures `forecast_summaries/` directory contents are uploaded as artifacts.

3. **Confirm artifacts include scenario JSON files** - not just markdown summaries.

If scenario files are missing for certain question types, the saving logic may need to be updated.

---

## Notes

- GitHub artifacts expire after **90 days**
- Runs with duration < 1 minute typically didn't forecast any new questions (all were previously forecasted)
- Use Windows PowerShell for `gh` commands (not WSL/Git Bash unless gh is installed there)
