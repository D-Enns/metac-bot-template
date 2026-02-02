# SKILL: Download All Forecast Artifacts

**Tool**: `download_all_forecast_artifacts.py`
**Purpose**: Systematically recover all forecast summary data from GitHub Actions workflow runs
**Category**: Data Recovery & Management
**Created**: January 27, 2026
**Updated**: February 2, 2026

**Key Feature**: All downloaded files are automatically renamed with run numbers to prevent overwrites and maintain complete version history.

---

## Quick Start

```bash
# Navigate to project root
cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026

# Download from most recent 500 runs (recommended for regular updates)
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Download all available runs with versions manifest
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000 --generate-manifest
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
# Download from default workflow (last 1000 runs)
python3 dre_tools/download_all_forecast_artifacts.py

# Download specific number of runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 200

# Use different output directory
python3 dre_tools/download_all_forecast_artifacts.py --output-dir backups/forecasts

# Generate versions manifest after download
python3 dre_tools/download_all_forecast_artifacts.py --generate-manifest
```

### Advanced Usage

```bash
# Download from specific workflow
python3 dre_tools/download_all_forecast_artifacts.py \
    --workflow dre_run_bot_on_tournament.yaml \
    --limit 500

# Download to custom location with manifest
python3 dre_tools/download_all_forecast_artifacts.py \
    --output-dir ../forecast_archive_2026 \
    --limit 1000 \
    --generate-manifest

# Full command with all options
python3 dre_tools/download_all_forecast_artifacts.py \
    --repo D-Enns/metac-bot-template \
    --workflow dre_run_bot_on_tournament.yaml \
    --limit 500 \
    --output-dir forecast_summaries \
    --generate-manifest
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--repo` | `D-Enns/metac-bot-template` | GitHub repository (owner/repo) |
| `--workflow` | `dre_run_bot_on_tournament.yaml` | Workflow file to download from |
| `--limit` | `1000` | Maximum number of runs to process |
| `--output-dir` | `forecast_summaries` | Where to save downloaded files |
| `--generate-manifest` | False | Generate versions manifest file |

---

## Understanding the Output

### Directory Structure

After running, files are organized as:
```
forecast_summaries/
├── 41871_spring_aib_2026_full_r909.md          # Question 41871, run 909
├── 41871_spring_aib_2026_condensed_r909.md
├── 41871_spring_aib_2026_scenarios_r909.json
├── 41871_spring_aib_2026_full_r908.md          # Same question, run 908
├── 41871_spring_aib_2026_condensed_r908.md
├── 41872_spring_aib_2026_full_r909.md          # Question 41872, run 909
├── ... (all other forecast files with run numbers)
├── reports/                                     # Download reports
│   ├── download_report_2026-02-02_15-30.json
│   ├── download_report_2026-01-27_14-22.json
│   └── ...
├── versions_manifest.json                       # Optional: quick lookup
└── downloaded_artifacts_log.json                # Tracks what's been downloaded
```

### File Naming Convention

Files follow this pattern:
```
{question_id}_{tournament_slug}_{type}_r{run_number}.{ext}

Examples:
41871_spring_aib_2026_full_r909.md        # Full forecast, run 909
41871_spring_aib_2026_condensed_r909.md   # Condensed version, run 909
41871_spring_aib_2026_scenarios_r909.json # Scenario data (JSON), run 909
41871_spring_aib_2026_full_r908.md        # Same question, earlier run 908
41392_unknown_full_r872.md                # Unknown tournament, run 872
```

**Components:**
- `question_id`: Metaculus question number (e.g., 41871)
- `tournament_slug`: Tournament identifier (e.g., spring_aib_2026, unknown)
- `type`: File type (full, condensed, scenarios)
- `run_number`: GitHub workflow run number (e.g., 909, 908)
- `ext`: File extension (.md or .json)

**Key Points:**
- Run number makes each file unique - no overwrites ever occur
- Higher run numbers = more recent forecasts
- Same question can have multiple versions from different runs

### Output Files

**1. Download Report** (`forecast_summaries/reports/download_report_2026-02-02_15-30.json`)
```json
{
  "timestamp": "2026-02-02T15:30:00",
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
  "unique_questions": ["14333", "41379", "41871", "41872"],
  "question_to_runs_map": {
    "41871": [909, 908, 872],
    "41872": [909, 907],
    "41875": [909, 908, 907, 905]
  },
  "runs_processed": [
    {
      "run_number": 909,
      "run_id": 21415607575,
      "date": "2026-01-27T21:51:43Z",
      "questions": ["41871", "41872", "41875"]
    },
    {
      "run_number": 908,
      "run_id": 21415123456,
      "date": "2026-01-27T20:15:30Z",
      "questions": ["41871", "41875"]
    }
  ]
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
      "files": [
        "forecast_summaries/41871_spring_aib_2026_full_r872.md",
        "forecast_summaries/41871_spring_aib_2026_condensed_r872.md"
      ],
      "questions": ["41871"],
      "downloaded_at": "2026-01-27T15:14:23"
    }
  },
  "last_updated": "2026-01-27T15:30:00"
}
```

**3. Versions Manifest** (optional: `forecast_summaries/versions_manifest.json`)
```json
{
  "41871_full": {
    "question_id": "41871",
    "type": "full",
    "latest_run": 909,
    "version_count": 3,
    "versions": [
      {
        "run_number": 909,
        "file_path": "41871_spring_aib_2026_full_r909.md",
        "size_bytes": 12458,
        "modified": "2026-02-02T15:30:00"
      },
      {
        "run_number": 908,
        "file_path": "41871_spring_aib_2026_full_r908.md",
        "size_bytes": 12301,
        "modified": "2026-02-01T14:22:00"
      },
      {
        "run_number": 872,
        "file_path": "41871_spring_aib_2026_full_r872.md",
        "size_bytes": 11987,
        "modified": "2026-01-27T15:14:00"
      }
    ]
  }
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
      ✓ 41871_spring_aib_2026_full_r663.md
      ✓ 41871_spring_aib_2026_condensed_r663.md
      ✓ 41871_spring_aib_2026_scenarios_r663.json
    ✓ Processed 3 file(s)
```

**What this means:**
- Processing run 247 out of 500 total
- Run #663 in workflow history
- GitHub database ID: 21181676805
- Run date: January 20, 2026
- Status: successful run
- Artifact size: 0.10 MB (~100 KB)
- Files automatically renamed with `_r663` suffix
- All files saved directly to `forecast_summaries/`

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
ls forecast_summaries/reports/ | tail -1 | xargs -I {} cat "forecast_summaries/reports/{}"

# Count new files
ls -1 forecast_summaries/*_r*.md | wc -l
```

### Workflow 2: Complete Historical Recovery

**Goal**: Recover all available forecast data with manifest

```bash
# Download maximum available runs and generate manifest
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000 --generate-manifest

# Check latest report for any expired artifacts
cat forecast_summaries/reports/download_report_*.json | tail -1 | jq '.statistics.expired'

# Get unique question count from latest report
ls -t forecast_summaries/reports/*.json | head -1 | xargs cat | jq '.unique_questions | length'
```

### Workflow 3: Tournament-Specific Archive

**Goal**: Collect forecasts for a specific tournament

```bash
# Download all runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Filter by tournament (all files are in main directory now)
cd forecast_summaries
ls *spring_aib_2026*.md | wc -l

# Copy tournament-specific files to archive
mkdir -p ../spring_2026_archive/
cp *spring_aib_2026* ../spring_2026_archive/
```

### Workflow 4: Verify Recent Forecasts

**Goal**: Check that bot is saving forecasts correctly

```bash
# Download last 10 runs only
python3 dre_tools/download_all_forecast_artifacts.py --limit 10

# List what questions were forecast in latest run
cd forecast_summaries
latest_run=$(ls *_r*.md | grep -o '_r[0-9]*' | sed 's/_r//' | sort -n | tail -1)
echo "Latest run: $latest_run"
ls *_r${latest_run}.md
```

---

## Versions Manifest (Optional)

You can optionally generate a versions manifest file that provides quick lookup of all forecast versions:

```bash
python3 dre_tools/download_all_forecast_artifacts.py --generate-manifest
```

### What the Manifest Provides:
- Quick lookup of which runs forecasted each question
- Latest run number for each question/type combination
- Total version count per question
- File paths and metadata for all versions

### When to Use:
- After downloading a large batch of forecasts
- When you need to quickly find all versions of a question
- For automated analysis scripts that need version information
- To verify data completeness

### Example Queries with Manifest:
```python
import json

# Load manifest
with open('forecast_summaries/versions_manifest.json') as f:
    manifest = json.load(f)

# Find latest forecast for question 41871
latest = manifest['41871_full']['latest_run']
print(f"Latest run: {latest}")

# Get all versions
versions = manifest['41871_full']['versions']
print(f"Total versions: {len(versions)}")

# Find file for specific run
for v in versions:
    if v['run_number'] == 909:
        print(f"File: {v['file_path']}")
```

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
ls *_r*.md | grep -o '^[0-9]*' | sort -u | wc -l

# List all unique questions
ls *_r*.md | grep -o '^[0-9]*' | sort -u

# Count versions per question (using manifest if available)
cat versions_manifest.json | jq '.[] | {question: .question_id, versions: .version_count}'
```

### Count Forecasts by Tournament

```bash
cd forecast_summaries

# Count by tournament
ls *_r*.md | grep -o '_[^_]*_[^_]*_r' | sed 's/_r$//' | sed 's/^_//' | sort | uniq -c

# Example output:
#  450 spring_aib_2026_full
#  450 spring_aib_2026_condensed
#  300 minibench_full
```

### Find Specific Question

```bash
# Find all files for question 41871
ls forecast_summaries/41871_*

# Find latest forecast for question 41871
ls forecast_summaries/41871_*_r*.md | sort -t'r' -k2 -n | tail -1

# Find all forecasts from a run range (e.g., 900-910)
ls forecast_summaries/*_r{900..910}.md
```

### Check File Sizes

```bash
cd forecast_summaries

# Total size by file type
du -sh *_full_r*.md | awk '{sum+=$1} END {print sum}'
du -sh *_condensed_r*.md | awk '{sum+=$1} END {print sum}'

# Size of all forecast data
du -sh *.md *.json | awk '{sum+=$1} END {print sum}'
```

---

## Integration with Other Tools

### Loading Data for Analysis

```python
import json
from pathlib import Path
import re

# Load latest download report
reports_dir = Path("forecast_summaries/reports")
latest_report = sorted(reports_dir.glob("*.json"))[-1]

with open(latest_report) as f:
    report = json.load(f)

print(f"Total questions: {len(report['unique_questions'])}")
print(f"Date range: {report['timestamp']}")
print(f"Downloaded: {report['statistics']['downloaded']} artifacts")

# Check which runs forecasted a specific question
question_id = "41871"
runs = report['question_to_runs_map'].get(question_id, [])
print(f"Question {question_id} was forecasted in {len(runs)} runs: {runs}")

# Load specific forecast (latest version)
forecast_file = Path(f"forecast_summaries/41871_spring_aib_2026_full_r{runs[0]}.md")
with open(forecast_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Parse metadata
metadata = {}
for line in content.split('\n'):
    if match := re.match(r'\*\*(.+?)\*\*:\s*(.+)', line):
        metadata[match.group(1)] = match.group(2)

# Load versions manifest (if available)
manifest_file = Path("forecast_summaries/versions_manifest.json")
if manifest_file.exists():
    with open(manifest_file) as f:
        manifest = json.load(f)

    # Get all versions for a question
    key = f"{question_id}_full"
    if key in manifest:
        versions = manifest[key]['versions']
        print(f"Found {len(versions)} versions")
        for v in versions:
            print(f"  Run {v['run_number']}: {v['file_path']}")
```

### Comparing with Metaculus Posts

```bash
# Extract question IDs from latest report
cd forecast_summaries/reports
latest=$(ls -t *.json | head -1)
cat "$latest" | jq -r '.unique_questions[]' > /tmp/question_ids.txt

# For each question, build Metaculus URL
while read qid; do
    echo "Question $qid: https://www.metaculus.com/questions/$qid"
done < /tmp/question_ids.txt
```

---

## Best Practices

### 1. Regular Backups
Run the tool weekly to keep archives current:
```bash
# Add to crontab (weekly on Sundays at 2 AM)
0 2 * * 0 cd /path/to/project && python3 dre_tools/download_all_forecast_artifacts.py --limit 500 --generate-manifest
```

### 2. Verify Downloads
Always check the summary statistics from latest report:
```bash
cd forecast_summaries/reports
cat $(ls -t *.json | head -1) | jq '.statistics'
```
- Ensure no failed downloads
- Check unique question count matches expectations
- Verify date range covers intended period

### 3. Never Overwrite - Run Numbers Ensure Safety
The tool automatically prevents overwrites:
- Each file includes its run number
- Existing files are never modified
- You can safely rerun downloads without losing data
- Run numbers provide complete audit trail

### 4. Document Your Downloads
Track download history through reports:
```bash
# List all download sessions
ls -lh forecast_summaries/reports/

# Check what was downloaded in each session
for report in forecast_summaries/reports/*.json; do
    echo "=== $report ==="
    cat "$report" | jq '{timestamp, total_runs: .statistics.total_runs, downloaded: .statistics.downloaded}'
done
```

### 5. Monitor Artifact Expiration
GitHub artifacts expire after 90 days. Download before expiration:
```bash
# Check oldest available run
gh run list --repo D-Enns/metac-bot-template --workflow dre_run_bot_on_tournament.yaml --limit 1000 | tail -1

# Check for expired artifacts in latest report
cat forecast_summaries/reports/$(ls -t forecast_summaries/reports/*.json | head -1) | jq '.statistics.expired'
```

### 6. Use Versions Manifest for Analysis
Generate manifest after major downloads:
```bash
python3 dre_tools/download_all_forecast_artifacts.py --generate-manifest

# Quick lookup of question versions
cat forecast_summaries/versions_manifest.json | jq '.["41871_full"]'
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
- All files have run numbers in filenames (e.g., `_r909.md`)

✅ **File Organization**:
- All forecast files directly in `forecast_summaries/` with run numbers
- Reports organized in `forecast_summaries/reports/` with timestamps
- Download log created successfully
- No overwrites - existing files preserved

✅ **Question Tracking**:
- Download report includes `question_to_runs_map`
- Each run lists which questions it forecasted
- Can quickly identify which runs forecasted any question

---

## Related Files

- `download_all_forecast_artifacts.py` - Main tool script
- `download_all_forecast_artifacts_README.md` - Technical documentation
- `downloaded_artifacts_log.json` - Tracks download history (auto-generated)
- `forecast_summaries/reports/download_report_*.json` - Timestamped summary reports (auto-generated)
- `forecast_summaries/versions_manifest.json` - Version tracking manifest (optional, auto-generated)

---

## Future Enhancements

Potential improvements to consider:

1. **Incremental Downloads**: Automatically detect and download only new runs since last session
2. **Parallel Downloads**: Speed up by downloading multiple artifacts simultaneously
3. **Filtering Options**: Download only specific tournaments or date ranges
4. **Data Validation**: Verify downloaded files match expected format and are complete
5. **Cloud Backup**: Automatically upload to cloud storage after download
6. **Notification**: Send email/slack when download completes or errors occur
7. **Analysis Integration**: Auto-generate performance reports after download
8. **Compression**: Optionally compress older forecasts to save disk space
9. **Archival**: Move forecasts older than X days to separate archive directory

---

## Quick Reference Card

```bash
# Most Common Commands

# Regular weekly backup with manifest
python3 dre_tools/download_all_forecast_artifacts.py --limit 500 --generate-manifest

# Full historical recovery
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Quick check (last 10 runs)
python3 dre_tools/download_all_forecast_artifacts.py --limit 10

# View latest results
cd forecast_summaries/reports && cat $(ls -t *.json | head -1) | jq

# List all downloaded files
ls -lh forecast_summaries/*_r*.md

# Count questions
cat forecast_summaries/reports/$(ls -t forecast_summaries/reports/*.json | head -1) | jq '.unique_questions | length'

# Find specific question (all versions)
ls forecast_summaries/41871_*

# Find latest version of question
ls forecast_summaries/41871_*_full_r*.md | sort -t'r' -k2 -n | tail -1

# Check which runs forecasted a question
cat forecast_summaries/reports/$(ls -t forecast_summaries/reports/*.json | head -1) | jq '.question_to_runs_map["41871"]'
```

---

**Last Updated**: February 2, 2026
**Version**: 2.0
**Maintainer**: Dre + Claude
**Status**: Production Ready ✅
**Breaking Changes**: v2.0 introduces flat file structure with run numbers in filenames
