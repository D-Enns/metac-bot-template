# Skill: Run Diagnostic Checks

Quick reference for diagnosing GitHub Actions bot run failures, silent skips, and question pipeline issues.

## Purpose

Investigate why the Metaculus forecasting bot missed questions, failed on specific question types, or silently skipped forecasts. Uses the diagnostic logging added to `dre_forecasting_tools.py` and `main.py` on 2026-02-13.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Python 3 available (for extracting zip logs)
- Repo: `D-Enns/metac-bot-template`, branch: `bot-dev`

## Step 0: Check Framework Version

Before diving into logs, verify what version of `forecasting-tools` is running. Many issues trace back to framework bugs fixed in newer versions.

```bash
# Check pinned version in poetry.lock
grep -A 2 'name = "forecasting-tools"' poetry.lock

# Check allowed range in pyproject.toml
grep forecasting pyproject.toml
```

If you need to inspect the source code of a specific version:

```bash
# Download the wheel from PyPI
curl -sL "https://pypi.org/pypi/forecasting-tools/VERSION/json" | \
  python3 -c "import json,sys; [print(u['url']) for u in json.load(sys.stdin)['urls'] if u['filename'].endswith('.whl')]"
# Download and extract
curl -sL "WHEEL_URL" -o /tmp/ft_VERSION.whl
python3 -c "
import zipfile
zf = zipfile.ZipFile('/tmp/ft_VERSION.whl')
data = zf.read('forecasting_tools/path/to/file.py').decode('utf-8')
for i, line in enumerate(data.split('\n'), 1):
    if 'SEARCH_TERM' in line:
        print(f'L{i}: {line.strip()}')
"
```

This was critical for finding the `assert isinstance(upper_bound, float)` bug in v0.2.80 that didn't exist in the GitHub `main` branch (already fixed there).

## Step 1: List Recent Runs

```bash
gh run list --limit 20 -R D-Enns/metac-bot-template --workflow dre_run_bot_on_tournament.yaml
```

Key signals:
- **~1 min duration** = no questions processed (API returned 0 open questions)
- **2+ min duration** = at least one question was attempted
- **failure conclusion** = forecast attempted but crashed (exit code 1)

## Step 2: Download and Extract Logs

```bash
# Download raw logs zip for a specific run
gh api repos/D-Enns/metac-bot-template/actions/runs/RUN_ID/logs \
  -H "Accept: application/vnd.github+json" > /tmp/run_LABEL.zip

# Extract with Python (unzip may not be available in WSL)
python3 -c "
import zipfile, os
zf = zipfile.ZipFile('/tmp/run_LABEL.zip')
os.makedirs('/tmp/run_LABEL_logs', exist_ok=True)
zf.extractall('/tmp/run_LABEL_logs')
print([f for f in zf.namelist()])
"
```

The main log file is `0_forecast_job.txt`.

## Step 3: Search Logs for Diagnostic Output

### Quick scan for pipeline diagnostics
```bash
# Search for key diagnostic lines
grep -E "QUESTION PIPELINE|Total open|By type|Unforecasted|ATTEMPT|RESULTS for|FAILURE|exit code" \
  /tmp/run_LABEL_logs/0_forecast_job.txt
```

### Search for a specific question number
```bash
grep "QNUMBER" /tmp/run_LABEL_logs/0_forecast_job.txt
```

### Search for errors and warnings
```bash
grep -E "ERROR|WARNING|Exception|AssertionError|ValueError" \
  /tmp/run_LABEL_logs/0_forecast_job.txt
```

### Check individual LLM prediction outputs (aggregation failures)
When aggregation fails (e.g., MC option name mismatch), check what each individual LLM run returned:
```bash
grep "Forecasted URL.*QNUMBER.*prediction" /tmp/run_LABEL_logs/0_forecast_job.txt
```
This reveals inconsistencies between runs — e.g., some returning correct option names and others returning `Option_A` placeholders.

## Step 4: Batch Scan Multiple Runs

Scan many runs at once for a specific question or pattern:

```bash
for run_id in ID1 ID2 ID3; do
  echo "=== RUN $run_id ==="
  gh api repos/D-Enns/metac-bot-template/actions/runs/$run_id/logs \
    -H "Accept: application/vnd.github+json" > /tmp/run_${run_id}.zip 2>/dev/null
  python3 -c "
import zipfile
zf = zipfile.ZipFile('/tmp/run_${run_id}.zip')
data = zf.read('0_forecast_job.txt').decode('utf-8', errors='replace')
for line in data.split('\n'):
    if any(k in line for k in ['QUESTION PIPELINE', 'RESULTS for', 'QNUMBER', 'Total open', 'By type', 'ERROR', 'WARNING', 'ATTEMPT']):
        print(line[28:].strip() if len(line) > 28 else line.strip())
"
done
```

Replace `QNUMBER` with the Metaculus question ID to investigate.

## Step 5: Download Artifacts (if diagnostics JSON was written)

```bash
gh run download RUN_ID -R D-Enns/metac-bot-template -D /tmp/run_LABEL
find /tmp/run_LABEL -name "run_diagnostics.json"
```

Note: `run_diagnostics.json` is NOT written if the process crashes before reaching the summary code (e.g., on exit code 1 failures). In that case, use the raw logs instead.

## Diagnostic Log Format Reference

The diagnostic logging in `dre_forecasting_tools.py` outputs these key lines:

| Log Line | Meaning |
|----------|---------|
| `QUESTION PIPELINE: Tournament XXXX` | Start of pipeline for a tournament |
| `Total open questions from API: N` | How many questions the Metaculus API returned |
| `By type: {dict}` | Breakdown by question type (BinaryQuestion, NumericQuestion, MultipleChoiceQuestion) |
| `Q##### [Type] forecasted=True/False` | Individual question status |
| `Unforecasted (will attempt): N` | Questions that will be processed |
| `ATTEMPT: Q##### [Type]` | A specific question is being sent to the LLM |
| `RESULTS for tournament XXXX: N successes, N failures` | Outcome summary |
| `FAILURE: ErrorType: message` | Details of a failed forecast |

## Known Failure Patterns

### 1. Framework Parser Drops Questions Silently
**Symptom:** `Total open questions from API: 0` but questions should be open.
**Log clue:** `Error processing post ID XXXXX: AssertionError ...`
**Cause:** The framework's `metaculus_client.py` parser has assertions that reject questions with unexpected bounds/formats. The question is fetched from the API but silently discarded during parsing.
**Example:** `AssertionError Upper bound is 150` for numeric Q42105 — the Metaculus API returned `range_max: 150` as a JSON integer, but v0.2.80 had `assert isinstance(upper_bound, float)` which fails because `isinstance(150, float)` is `False` in Python.
**Fixed:** 2026-02-14 by updating `forecasting-tools` from 0.2.80 to 0.2.85. v0.2.85 wraps bounds in `float()` instead of asserting. If this pattern recurs, check if a newer framework version fixes it (see Step 0).

### 2. Multiple Choice Option Name Mismatch
**Symptom:** Run fails with exit code 1 on a MultipleChoiceQuestion.
**Log clue:** `All predictions must have the same option names, but {'Option_A', ...} != ['Actual Name', ...]`
**Cause:** The LLM sometimes returns generic placeholder names (Option_A, Option_B) instead of the actual option labels. When multiple LLM runs return different formats, the framework's `aggregate_predictions` rejects the mismatch. Use the "Check individual LLM prediction outputs" search (Step 3) to see which runs returned bad names.
**Fixed:** 2026-02-14 with two changes in `main.py`:
1. Prompt now lists exact option names as the output format instead of `Option_A` placeholders
2. `_normalize_mc_option_names` maps `Option_A`/`Option_B` back to canonical names by position as a safety net
If this recurs, check if the prompt output format has drifted or if a new naming variant needs handling in the normalizer.

### 3. No Questions Available (Normal)
**Symptom:** `Total open questions from API: 0` for both tournaments, run takes ~1 min.
**Cause:** Normal — no new unforecasted questions were open during this run window. Questions are only open for ~1 hour with runs every 20 minutes.

## Related Files

| File | Role |
|------|------|
| `dre_forecasting_tools.py` | `forecast_on_tournament` override with pipeline logging, `_inspect_results`, `write_diagnostics_json`, `get_exit_code` |
| `main.py` | Calls `write_diagnostics_json()` and `get_exit_code()` at end of script |
| `.github/workflows/dre_run_bot_on_tournament.yaml` | Step summary reporting from `run_diagnostics.json` |
| `forecast_summaries/run_diagnostics.json` | Per-run diagnostic output (uploaded as artifact) |

## Related Skills

- `SKILL_download_forecast_logs.md` — Download full workflow logs in bulk
- `SKILL_download_all_forecast_artifacts.md` — Download forecast summary artifacts
- `SKILL_generate_bot_forecast_log.md` — Generate consolidated forecast log

## Session History

- **2026-02-13:** Diagnostic logging implemented (Phase 1 & 2)
- **2026-02-14:** First diagnostic results analyzed and both issues fixed:
  - Numeric: framework v0.2.80 `assert isinstance(upper_bound, float)` fails on integer bounds → updated to v0.2.85
  - MC: prompt used `Option_A` placeholders causing inconsistent LLM outputs → prompt now uses exact names + positional fallback normalizer
