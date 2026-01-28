# SKILL: Download All Forecast Artifacts

**Tool**: `download_all_forecast_artifacts.py`
**Purpose**: Systematically recover all forecast summary data from GitHub Actions workflow runs
**Category**: Data Recovery & Management
**Created**: January 27, 2026

---

## Quick Start

```bash
# Navigate to project root
cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026

# Download from most recent 500 runs (recommended for regular updates)
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Download all available runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000
```

---

## When to Use This Tool

### Use Cases
1. **Regular Data Backup**: Download new forecast artifacts after bot runs
2. **Historical Recovery**: Recover forecast data that was previously lost due to artifact overwriting
3. **Complete Archive**: Ensure you have all forecast summaries for specified tournaments
4. **Data Analysis**: Gather complete dataset for performance analysis
5. **After Code Changes**: Verify new forecast formats are being saved correctly

### Signs You Need This Tool
- Missing forecast summaries for certain questions
- Can't find forecasts from specific date ranges
- Need to verify bot predictions against Metaculus posts
- Want to analyze forecast performance across tournaments
- GitHub artifact artifacts are expiring (90-day retention)

---

## Prerequisites

### Required
1. **GitHub CLI (`gh`)** - Must be installed and authenticated
   ```bash
   # Check if installed
   gh --version

   # If not installed, install it
   # On Ubuntu/Debian:
   sudo apt install gh

   # Authenticate (first time only)
   gh auth login
   ```

2. **Python 3.7+**
   ```bash
   python3 --version
   ```

3. **Repository Access** - Must have read access to `D-Enns/metac-bot-template`

### Verification
```bash
# Verify setup
gh auth status
gh repo view D-Enns/metac-bot-template
```

---

## Command Reference

### Basic Usage

```bash
# Download from default workflow (last 500 runs)
python3 dre_tools/download_all_forecast_artifacts.py

# Download specific number of runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 200

# Use different output directory
python3 dre_tools/download_all_forecast_artifacts.py --output-dir backups/forecasts

# Skip consolidation prompt
python3 dre_tools/download_all_forecast_artifacts.py --no-consolidate
```

### Advanced Usage

```bash
# Download from specific workflow
python3 dre_tools/download_all_forecast_artifacts.py \
    --workflow dre_run_bot_on_tournament.yaml \
    --limit 500

# Download to custom location
python3 dre_tools/download_all_forecast_artifacts.py \
    --output-dir ../forecast_archive_2026 \
    --limit 1000

# Full command with all options
python3 dre_tools/download_all_forecast_artifacts.py \
    --repo D-Enns/metac-bot-template \
    --workflow dre_run_bot_on_tournament.yaml \
    --limit 500 \
    --output-dir forecast_summaries \
    --no-consolidate
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--repo` | `D-Enns/metac-bot-template` | GitHub repository (owner/repo) |
| `--workflow` | `dre_run_bot_on_tournament.yaml` | Workflow file to download from |
| `--limit` | `1000` | Maximum number of runs to process |
| `--output-dir` | `forecast_summaries` | Where to save downloaded files |
| `--no-consolidate` | False | Skip file consolidation prompt |

---

## Understanding the Output

### Directory Structure

After running, files are organized as:
```
forecast_summaries/
├── run_909/              # Most recent run
│   ├── 41871_spring_aib_2026_full_1.md
│   ├── 41871_spring_aib_2026_condensed_1.md
│   ├── 41871_spring_aib_2026_scenarios_1.json
│   └── [other question files...]
├── run_908/
├── run_907/
...
├── run_410/              # Oldest run in this batch
├── download_report.json  # Summary of download operation
└── downloaded_artifacts_log.json  # Tracks what's been downloaded
```

### File Naming Convention

Files follow this pattern:
```
{question_id}_{tournament_slug}_{type}_{counter}.{ext}

Examples:
41871_spring_aib_2026_full_1.md        # Full forecast summary
41871_spring_aib_2026_condensed_1.md   # Condensed version
41871_spring_aib_2026_scenarios_1.json # Scenario data (JSON)
41392_unknown_full_1.md                # Unknown tournament
```

**Components:**
- `question_id`: Metaculus question number (e.g., 41871)
- `tournament_slug`: Tournament identifier (e.g., spring_aib_2026, unknown)
- `type`: File type (full, condensed, scenarios)
- `counter`: Version number if multiple forecasts on same question
- `ext`: File extension (.md or .json)

### Output Files

**1. Download Report** (`forecast_summaries/download_report.json`)
```json
{
  "timestamp": "2026-01-27T15:30:00",
  "repository": "D-Enns/metac-bot-template",
  "workflow": "dre_run_bot_on_tournament.yaml",
  "statistics": {
    "total_runs": 500,
    "runs_with_artifacts": 499,
    "total_artifacts": 499,
    "downloaded": 499,
    "skipped": 0,
    "failed": 0,
    "expired": 0
  },
  "unique_questions": [14333, 41379, ...]
}
```

**2. Download Log** (`downloaded_artifacts_log.json`)
```json
{
  "downloaded_artifacts": {
    "872:forecast-summaries-872": {
      "run_number": 872,
      "run_id": 21371081739,
      "artifact_name": "forecast-summaries-872",
      "path": "forecast_summaries/run_872",
      "downloaded_at": "2026-01-27T15:14:23"
    }
  },
  "last_updated": "2026-01-27T15:30:00"
}
```

---

## Console Output Interpretation

### During Download
```
[247/500] Run #663 (ID: 21181676805)
  Date: 2026-01-20T17:48:10Z
  Status: success
  - forecast-summaries-663 (0.10 MB)
    ✓ Downloaded to forecast_summaries/run_663/
```

**What this means:**
- Processing run 247 out of 500 total
- Run #663 in workflow history
- GitHub database ID: 21181676805
- Run date: January 20, 2026
- Status: successful run
- Artifact size: 0.10 MB (~100 KB)
- Downloaded to: `forecast_summaries/run_663/`

### Symbols
- `✓` = Successfully downloaded
- `⊙` = Skipped (already downloaded or no artifacts)
- `✗` = Failed to download
- `⊗` = Artifact expired (cannot download)

### Summary Statistics
```
📊 Statistics:
  Total workflow runs processed: 500
  Runs with forecast artifacts: 499
  Total artifacts found: 499
  ✓ Downloaded: 499
  ⊙ Skipped (already downloaded): 0
  ✗ Failed: 0
  ⊗ Expired: 0
```

---

## Common Workflows

### Workflow 1: Regular Backup (Weekly)

**Goal**: Keep local archive up-to-date with latest forecasts

```bash
# Download last week's forecasts (assuming ~3 runs/hour * 24 * 7 ≈ 500 runs)
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Review what was downloaded
cat forecast_summaries/download_report.json

# Count new files
ls -la forecast_summaries/run_*/
```

### Workflow 2: Complete Historical Recovery

**Goal**: Recover all available forecast data

```bash
# Download maximum available runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Check for any expired artifacts
grep "Expired" forecast_summaries/download_report.json

# Get unique question count
cat forecast_summaries/download_report.json | grep -A 1 "unique_questions"
```

### Workflow 3: Tournament-Specific Archive

**Goal**: Collect forecasts for a specific tournament

```bash
# Download all runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Filter by tournament (after download)
cd forecast_summaries
find . -name "*spring_aib_2026*" | wc -l
find . -name "*spring_aib_2026*" -exec cp {} ../spring_2026_archive/ \;
```

### Workflow 4: Verify Recent Forecasts

**Goal**: Check that bot is saving forecasts correctly

```bash
# Download last 10 runs only
python3 dre_tools/download_all_forecast_artifacts.py --limit 10

# List what questions were forecast
cd forecast_summaries
for dir in run_*; do
    echo "=== $dir ==="
    ls $dir/*.md | head -3
done
```

---

## File Consolidation

After download completes, you'll be prompted:
```
Consolidate files into main directory? (y/n):
```

### If you answer "y":
- Moves all files from `run_*/` subdirectories to `forecast_summaries/` root
- Detects duplicates (same filename + size)
- Renames different versions with run number suffix
- Result: All files in one directory for easier access

### If you answer "n":
- Keeps files organized by run number in subdirectories
- Better for tracking which run produced which forecast
- Preserves download history

**Recommendation**:
- Answer "n" if you want to track provenance
- Answer "y" if you want easier access to all files

---

## Troubleshooting

### Error: "GitHub CLI (gh) is not installed"

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install gh

# macOS
brew install gh

# Windows (WSL)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login
```

### Error: "GitHub CLI is not authenticated"

**Solution:**
```bash
gh auth login
# Follow prompts to authenticate with GitHub
```

### Error: "Failed to get workflow runs"

**Possible causes:**
1. Wrong repository name
2. Wrong workflow file name
3. No access to repository

**Solution:**
```bash
# Verify repository access
gh repo view D-Enns/metac-bot-template

# List workflows
gh workflow list --repo D-Enns/metac-bot-template

# Use correct workflow name
python3 dre_tools/download_all_forecast_artifacts.py \
    --workflow dre_run_bot_on_tournament.yaml
```

### Warning: "Artifact expired"

**Cause**: GitHub artifacts expire after retention period (default 90 days)

**Solution**: Cannot download expired artifacts. For older data:
1. Check if files already exist locally
2. Try extracting from run logs (see Option 3 below)
3. Check if data was committed to repository

### Issue: "No forecast artifacts found"

**Possible causes:**
1. Runs before artifact upload was implemented
2. Failed runs (no artifacts generated)
3. Different workflow name

**Solution:**
```bash
# Check specific run manually
gh run view <run_id> --repo D-Enns/metac-bot-template

# List artifacts for a run
gh api repos/D-Enns/metac-bot-template/actions/runs/<run_id>/artifacts
```

### Issue: Download is very slow

**Cause**: Large number of runs, GitHub API rate limiting

**Solutions:**
1. Reduce `--limit` parameter
2. Download in batches (e.g., 100 at a time)
3. Run during off-peak hours
4. Use `--no-consolidate` to skip interactive prompt

---

## Data Analysis After Download

### Count Forecasts by Question

```bash
cd forecast_summaries

# Count unique question IDs
ls run_*/*.md | sed 's/.*\/\([0-9]*\)_.*/\1/' | sort -u | wc -l

# List all unique questions
ls run_*/*.md | sed 's/.*\/\([0-9]*\)_.*/\1/' | sort -u
```

### Count Forecasts by Tournament

```bash
cd forecast_summaries

# Count by tournament
ls run_*/*.md | grep -o '_[^_]*_full' | sed 's/_full//' | sed 's/_//' | sort | uniq -c

# Example output:
#  150 minibench
#  1200 spring_aib_2026
#  100 unknown
```

### Find Specific Question

```bash
# Find all files for question 41871
find forecast_summaries -name "41871_*"

# Find all forecasts for a date range (by run number)
ls forecast_summaries/run_{700..750}/*.md
```

### Check File Sizes

```bash
# Total size by file type
du -sh forecast_summaries/run_*/*_full_*.md | awk '{sum+=$1} END {print sum " MB"}'
du -sh forecast_summaries/run_*/*_condensed_*.md | awk '{sum+=$1} END {print sum " MB"}'
```

---

## Integration with Other Tools

### Loading Data for Analysis

```python
import json
from pathlib import Path

# Load download report
report_file = Path("forecast_summaries/download_report.json")
with open(report_file) as f:
    report = json.load(f)

print(f"Total questions: {len(report['unique_questions'])}")
print(f"Date range: {report['timestamp']}")
print(f"Downloaded: {report['statistics']['downloaded']} artifacts")

# Load specific forecast
forecast_file = Path("forecast_summaries/run_872/41871_spring_aib_2026_full_1.md")
with open(forecast_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Parse metadata
import re
metadata = {}
for line in content.split('\n'):
    if match := re.match(r'\*\*(.+?)\*\*:\s*(.+)', line):
        metadata[match.group(1)] = match.group(2)
```

### Comparing with Metaculus Posts

```bash
# Extract question IDs
cat forecast_summaries/download_report.json | grep -A 1000 unique_questions

# For each question, check Metaculus
for qid in 41871 41872 41873; do
    echo "Question $qid: https://www.metaculus.com/questions/$qid"
done
```

---

## Best Practices

### 1. Regular Backups
Run the tool weekly to keep archives current:
```bash
# Add to crontab (weekly on Sundays at 2 AM)
0 2 * * 0 cd /path/to/project && python3 dre_tools/download_all_forecast_artifacts.py --limit 500 --no-consolidate
```

### 2. Verify Downloads
Always check the summary statistics:
- Ensure no failed downloads
- Check unique question count matches expectations
- Verify date range covers intended period

### 3. Preserve Original Structure
Keep files in `run_*/` subdirectories for:
- Tracking which run produced which forecast
- Debugging issues with specific runs
- Comparing forecasts across runs

### 4. Document Your Downloads
Add notes to track what you've downloaded:
```bash
# Create download log
echo "Downloaded 500 runs on $(date)" >> download_history.txt
echo "Date range: $(ls -d forecast_summaries/run_* | head -1) to $(ls -d forecast_summaries/run_* | tail -1)" >> download_history.txt
```

### 5. Monitor Artifact Expiration
GitHub artifacts expire after 90 days. Download before expiration:
```bash
# Check oldest run
gh run list --repo D-Enns/metac-bot-template --workflow dre_run_bot_on_tournament.yaml --limit 1000 | tail -1
```

---

## Success Metrics

After running the tool, you should see:

✅ **Download Success**:
- `✓ Downloaded: X` where X > 90% of processed runs
- `✗ Failed: 0` (or very low)
- `⊗ Expired: 0` for recent runs (last 90 days)

✅ **Data Completeness**:
- Unique questions count matches expectations for date range
- Each question has: full summary + condensed summary (+ scenarios JSON if after Jan 6)

✅ **File Organization**:
- Files in predictable `run_X/` structure
- No missing artifacts for successful runs
- Download log created successfully

---

## Related Files

- `download_all_forecast_artifacts.py` - Main tool script
- `download_all_forecast_artifacts_README.md` - Technical documentation
- `downloaded_artifacts_log.json` - Tracks download history (auto-generated)
- `forecast_summaries/download_report.json` - Summary report (auto-generated)

---

## Future Enhancements

Potential improvements to consider:

1. **Incremental Downloads**: Only download new runs since last download
2. **Parallel Downloads**: Speed up by downloading multiple artifacts simultaneously
3. **Filtering Options**: Download only specific tournaments or date ranges
4. **Data Validation**: Verify downloaded files match expected format
5. **Cloud Backup**: Automatically upload to cloud storage after download
6. **Notification**: Send email/slack when download completes
7. **Analysis Integration**: Auto-generate reports after download

---

## Quick Reference Card

```bash
# Most Common Commands

# Regular weekly backup
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Full historical recovery
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Quick check (last 10 runs)
python3 dre_tools/download_all_forecast_artifacts.py --limit 10

# View results
cat forecast_summaries/download_report.json
ls -lh forecast_summaries/run_*/

# Count questions
cat forecast_summaries/download_report.json | grep unique_questions

# Find specific question
find forecast_summaries -name "41871_*"
```

---

**Last Updated**: January 27, 2026
**Version**: 1.0
**Maintainer**: Dre + Claude
**Status**: Production Ready ✅
