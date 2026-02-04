# SKILL: Download All Forecast Artifacts

**Tool**: `download_all_forecast_artifacts.py`
**Purpose**: Download forecast summary data from GitHub Actions (first occurrence only)
**Category**: Data Management & Recovery
**Version**: 3.0
**Created**: January 27, 2026
**Updated**: February 3, 2026

**Key Strategy:** Keep only the **first occurrence** of each question for space efficiency and clean navigation. TSV manifest is versioned — a new version is created each run, nothing is ever overwritten.

---

## Quick Start

```bash
# Navigate to project root
cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026

# Download from most recent 500 runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Download all available runs (recommended for initial setup)
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000
```

---

## When to Use This Tool

### Primary Use Cases
1. **Initial Archive Setup**: Download all historical forecasts
2. **Regular Updates**: Weekly downloads to capture new questions
3. **Data Recovery**: Recover forecasts after local data loss
4. **Missing File Types**: Add condensed/scenarios files discovered later

### Signs You Need This Tool
- Need to analyze bot's historical predictions
- Want to verify forecasts against Metaculus outcomes
- Missing forecast data for certain questions
- Setting up new analysis environment

---

## Prerequisites

### Required
1. **GitHub CLI (`gh`)** - Must be installed and authenticated
   ```bash
   gh --version
   sudo apt install gh   # if not installed
   gh auth login         # first time only
   ```

2. **Python 3.7+**

3. **Repository Access** - Read access to `D-Enns/metac-bot-template`

---

## Command Reference

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--repo` | `D-Enns/metac-bot-template` | GitHub repository (owner/repo) |
| `--workflow` | `dre_run_bot_on_tournament.yaml` | Workflow file to download from |
| `--limit` | `1000` | Maximum number of runs to process |
| `--output-dir` | `forecast_summaries` | Where to save downloaded files |

---

## Understanding the Output

### Directory Structure

```
forecast_summaries/
├── 41871_spring_aib_2026_full_r872.md
├── 41871_spring_aib_2026_condensed_r872.md
├── 41871_spring_aib_2026_scenarios_r872.json
├── 41872_spring_aib_2026_full_r909.md
├── ... (all other forecast files)
├── Question_Run_and_Date_2026-02-03_v1.txt    ← First run on Feb 3
├── Question_Run_and_Date_2026-02-03_v2.txt    ← Second run on Feb 3
├── Question_Run_and_Date_2026-02-04_v1.txt    ← First run on Feb 4
├── tool_run_2026-02-03_10-30.log
└── tool_run_2026-02-03_14-45.log
```

### File Naming Convention

```
{question_id}_{tournament_slug}_{type}_r{run_number}.{ext}

Examples:
41871_spring_aib_2026_full_r872.md         # Full forecast, run 872
41871_spring_aib_2026_condensed_r909.md    # Condensed, run 909 (added later)
41871_spring_aib_2026_scenarios_r872.json  # Scenarios data
41872_unknown_full_r1045.md                # Unknown tournament
```

**Components:**
- `question_id` - Metaculus question number
- `tournament_slug` - Tournament identifier (e.g., spring_aib_2026, unknown)
- `type` - File type (full, condensed, scenarios)
- `run_number` - GitHub workflow run number (preserved from original artifact)
- `ext` - File extension (.md or .json)

**Note:** Files for the same question may have different run numbers if file types were discovered in different runs.

### TSV Manifest

`Question_Run_and_Date_YYYY-MM-DD_v{n}.txt`:
```tsv
question_id	first_run	first_run_date	tournament	file_count	notes
41871	872	2026-01-27 15:14:23 UTC	spring_aib_2026	3
41872	909	2026-01-27 21:51:43 UTC	spring_aib_2026	2
41873	908	2026-01-27 20:15:30 UTC	unknown	1	download_error: network timeout
```

**Versioning Behavior:**
- Each tool run creates a new version
- Version number (`v1`, `v2`, ...) resets to 1 each calendar day
- Tool loads the most recent version (latest date, highest version number)
- All previous versions are preserved — nothing is overwritten
- If a file happens to be open in another app, no conflict — next version is used

**Columns:**
- `question_id` - Question number
- `first_run` - First workflow run where this question was forecasted
- `first_run_date` - Extracted from `**Forecast Date**` in the full summary file
- `tournament` - Tournament identifier
- `file_count` - Number of file types downloaded (1-3)
- `notes` - Error messages or blank

### Tool Run Log

`tool_run_2026-02-03_10-30.log` - Complete capture of console output with timestamps:
```
[2026-02-03 10:30:00] ================================================================================
[2026-02-03 10:30:00] FORECAST ARTIFACT DOWNLOADER v3.0 - First Occurrence Only
[2026-02-03 10:30:01] ✓ GitHub CLI (gh) is available
[2026-02-03 10:30:01] ✓ Loaded TSV manifest: 17 questions tracked (Question_Run_and_Date_2026-02-03_v1.txt)
...
```

---

## Console Output Interpretation

### During Download
```
[9/50] Run #1045 (ID: 21601452534)
  Date: 2026-02-02T17:59:51Z
  Status: success
  - forecast-summaries-1045 (0.06 MB)
      ✓ 41909_spring_aib_2026_full_r1045.md
      ✓ 41909_spring_aib_2026_condensed_r1045.md
      ⊙ 41909_spring_aib_2026_scenarios_r1045.json (already have)
    ✓ Downloaded 2 file(s)
    ⊙ Skipped 1 file(s) (already have)
```

**Symbols:**
- `✓` = Successfully downloaded
- `⊙` = Skipped (already have this file type)
- `✗` = Failed to download
- `⊗` = Artifact expired (cannot download)

---

## Common Workflows

### Workflow 1: Initial Archive Setup

```bash
# Download all historical forecasts
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Check results
wc -l forecast_summaries/Question_Run_and_Date_*.txt | tail -1

# Review log for any errors
tail -50 forecast_summaries/tool_run_*.log
```

### Workflow 2: Regular Weekly Update

```bash
# Download last week's runs (~70 runs/week)
python3 dre_tools/download_all_forecast_artifacts.py --limit 100

# Verify new questions added
tail forecast_summaries/$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1 | xargs basename)
```

### Workflow 3: Recovery After Data Loss

```bash
# Clean start
rm -rf forecast_summaries
mkdir forecast_summaries

# Download everything
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000
```

### Workflow 4: Check Specific Question

```bash
# List files for question 41871
ls forecast_summaries/41871_*

# View TSV entry (from latest manifest)
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)
grep "^41871" "$latest"
```

---

## Data Analysis

### Count Questions by Tournament

```bash
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)

# Count by tournament
cut -f4 "$latest" | tail -n +2 | sort | uniq -c | sort -rn
```

### Find Latest Questions (by first_run number)

```bash
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)

# Sort by first_run descending, show top 10
sort -t$'\t' -k2 -nr "$latest" | head -10
```

### List Questions with Issues

```bash
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)

# Find questions with notes (errors)
awk -F'\t' 'NR>1 && $6 != ""' "$latest"
```

### Check File Coverage

```bash
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)

# Questions with all 3 file types
awk -F'\t' 'NR>1 && $5 == 3' "$latest" | wc -l

# Questions with only 1 file type (might get more later)
awk -F'\t' 'NR>1 && $5 == 1' "$latest"
```

---

## Integration with Analysis Tools

### Python Example

```python
import csv
from pathlib import Path

# Find latest TSV manifest
output_dir = Path('forecast_summaries')
tsv_files = sorted(output_dir.glob("Question_Run_and_Date_*.txt"))
latest_tsv = tsv_files[-1]

# Load manifest
manifest = {}
with open(latest_tsv) as f:
    reader = csv.DictReader(f, delimiter='\t')
    for row in reader:
        manifest[row['question_id']] = row

# Find question info
qid = '41871'
info = manifest[qid]
print(f"Question {qid}:")
print(f"  First run: {info['first_run']}")
print(f"  Forecast date: {info['first_run_date']}")
print(f"  Tournament: {info['tournament']}")
print(f"  File count: {info['file_count']}")

# Load forecast content
full_files = list(output_dir.glob(f"{qid}_*_full_r*.md"))
if full_files:
    with open(full_files[0]) as f:
        content = f.read()
        print(f"\nForecast length: {len(content)} characters")
```

### R Example

```r
library(readr)

# Find latest TSV
tsv_files <- list.files("forecast_summaries", pattern="Question_Run_and_Date_.*\\.txt", full.names=TRUE)
latest_tsv <- tail(sort(tsv_files), 1)

manifest <- read_tsv(latest_tsv)

# Summary
summary(manifest)
table(manifest$tournament)
```

---

## Troubleshooting

### Issue: No New Files Downloaded

**Cause**: All questions already exist locally

**Solution**:
```bash
# Increase run limit to find new questions
python3 dre_tools/download_all_forecast_artifacts.py --limit 2000
```

### Issue: TSV Manifest Missing or Corrupted

**Cause**: Manual deletion or file corruption

**Solution**: Tool rebuilds from files on disk automatically:
```bash
# Delete all TSV manifests
rm forecast_summaries/Question_Run_and_Date_*.txt

# Rerun — will rebuild from existing forecast files
python3 dre_tools/download_all_forecast_artifacts.py --limit 10
```

### Issue: Missing File Types

**Cause**: File type added in later run but not yet downloaded

**Solution**:
```bash
# Rerun with more runs to discover missing file types
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000
```

### Issue: Download Errors

```bash
# Check log for details
tail -100 forecast_summaries/tool_run_*.log
```

**Common causes:**
- Network interruption
- GitHub API rate limiting
- Expired artifacts (>90 days old)

---

## Best Practices

1. **Regular Updates:** Run weekly to capture new questions
2. **Check Logs:** Review tool run logs after each session
3. **TSV Versions Are Safe:** Previous versions are never overwritten — no data loss risk even if a file is open
4. **Monitor Disk Space:** `du -sh forecast_summaries/`
5. **Keep Logs:** Tool run logs are valuable for debugging — don't delete them

---

## Design Evolution & Version History

### v3.0 (February 2026) - First Occurrence Only ✅ CURRENT

**Strategy:** Keep only first occurrence of each question

**Implementation:**
- Versioned TSV manifest: `Question_Run_and_Date_{date}_v{n}.txt`
- `first_run_date` extracted from `**Forecast Date**` in full summary files
- Tool run logs capture all output
- Smart skip logic (loads latest TSV, falls back to file scan)
- Support for adding missing file types in later runs

**Rationale:**
- Clean, navigable directory
- Minimal disk space (~90% savings vs v2.0)
- Versioned TSV prevents data loss
- Practical for bot use case

### v2.0 (February 2026) - Keep All Versions [DEPRECATED]

**Strategy:** Keep ALL versions with run numbers

**Why We Built It:**
- Seemed valuable to track forecast evolution
- Complete historical record

**Why We Abandoned It:**
After testing with 50+ runs:
1. **Space**: 3-5 versions per question = 3-5x disk usage
2. **Navigation**: Hard to browse with so many files
3. **Cognitive load**: Distracting to see multiple versions
4. **Unused**: Rarely needed version comparison

### v1.0 (January 2026) - Original

**Strategy:** Basic download with `run_*/` subdirectories

**Issues:** Too many subdirectories, needed manual consolidation, no tracking.

---

## Quick Reference

```bash
# Most Common Commands

# Initial setup - download everything
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000

# Weekly update - recent runs only
python3 dre_tools/download_all_forecast_artifacts.py --limit 100

# Find latest TSV manifest
ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1

# List all questions (from latest manifest)
latest=$(ls -t forecast_summaries/Question_Run_and_Date_*.txt | head -1)
cut -f1 "$latest" | tail -n +2

# Find question details
grep "^41871" "$latest"

# Count questions by tournament
cut -f4 "$latest" | tail -n +2 | sort | uniq -c

# Check disk usage
du -sh forecast_summaries/

# View latest log
ls -t forecast_summaries/tool_run_*.log | head -1 | xargs less
```

---

**Last Updated**: February 3, 2026
**Version**: 3.0
**Maintainer**: Dre + Claude
**Status**: Production Ready ✅
