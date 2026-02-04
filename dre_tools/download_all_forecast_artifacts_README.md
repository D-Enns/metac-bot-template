# DRE Tools - Download All Forecast Artifacts

Custom tool for downloading and managing forecast bot data from GitHub Actions.

## Tool: download_all_forecast_artifacts.py (v3.0)

Systematically downloads forecast summary artifacts from GitHub Actions workflow runs, **keeping only the first occurrence of each question** to minimize disk space and maintain a clean, navigable archive.

### Purpose

Ensure complete data recovery for forecasting bot while maintaining an efficient, space-saving archive. Downloads only the first time each question appears, with ability to add missing file types in subsequent runs.

### Requirements

- GitHub CLI (`gh`) installed and authenticated
- Python 3.7+

### Installation

```bash
# Install GitHub CLI (if not already installed)
# Ubuntu/Debian:
sudo apt install gh

# Authenticate
gh auth login
```

### Usage

```bash
# Basic usage - download all artifacts
python dre_tools/download_all_forecast_artifacts.py

# Download last 500 runs only
python dre_tools/download_all_forecast_artifacts.py --limit 500

# Use custom output directory
python dre_tools/download_all_forecast_artifacts.py --output-dir my_forecasts
```

### Key Features

- ✅ Downloads only **first occurrence** of each question (space-efficient)
- ✅ Automatically adds missing file types in subsequent runs
- ✅ Versioned TSV manifest tracks all questions (new version each run)
- ✅ Tool run logs capture all console output
- ✅ Smart skip logic (checks latest TSV + files on disk)
- ✅ Handles expired artifacts gracefully
- ✅ **~90% space reduction** vs keeping all versions

### Output Structure

```
forecast_summaries/
├── 41871_spring_aib_2026_full_r872.md
├── 41871_spring_aib_2026_condensed_r872.md
├── 41871_spring_aib_2026_scenarios_r872.json
├── 41872_spring_aib_2026_full_r909.md
├── 41872_spring_aib_2026_condensed_r909.md
├── Question_Run_and_Date_2026-02-03_v1.txt    ← First run today
├── Question_Run_and_Date_2026-02-03_v2.txt    ← Second run today
├── Question_Run_and_Date_2026-02-04_v1.txt    ← First run tomorrow
├── tool_run_2026-02-03_15-30.log
└── tool_run_2026-02-03_16-45.log
```

**Note:** Files may have different run numbers if file types were discovered in different runs (e.g., full from run 872, condensed added in run 909).

### TSV Manifest Format

`Question_Run_and_Date_YYYY-MM-DD_v{n}.txt`:
```tsv
question_id	first_run	first_run_date	tournament	file_count	notes
41871	872	2026-01-27 15:14:23 UTC	spring_aib_2026	3
41872	909	2026-01-27 21:51:43 UTC	spring_aib_2026	2
```

**Versioning:**
- A new version is created each time you run the tool
- Version number resets to 1 each day
- Tool always loads the most recent version at start
- Previous versions are preserved (never overwritten)

**Columns:**
- `question_id` - Metaculus question number
- `first_run` - First workflow run where question appeared
- `first_run_date` - Forecast Date extracted from the full summary file
- `tournament` - Tournament identifier
- `file_count` - Number of file types downloaded
- `notes` - Error messages or blank

### Example Output

```
FORECAST ARTIFACT DOWNLOADER v3.0 - First Occurrence Only
================================================================================
✓ GitHub CLI (gh) is available
✓ GitHub CLI is authenticated
✓ Loaded TSV manifest: 17 questions tracked (Question_Run_and_Date_2026-02-03_v1.txt)

Fetching workflow runs for: dre_run_bot_on_tournament.yaml
Repository: D-Enns/metac-bot-template
✓ Found 50 workflow runs

Processing 50 workflow runs...
--------------------------------------------------------------------------------

[9/50] Run #1045 (ID: 21601452534)
  Date: 2026-02-02T17:59:51Z
  Status: success
  - forecast-summaries-1045 (0.06 MB)
      ✓ 41909_spring_aib_2026_full_r1045.md
      ✓ 41909_spring_aib_2026_condensed_r1045.md
      ✓ 41909_spring_aib_2026_scenarios_r1045.json
    ✓ Downloaded 3 file(s)

DOWNLOAD SUMMARY
================================================================================
📊 Statistics:
  Total workflow runs processed: 50
  Runs with forecast artifacts: 14
  ✓ Files downloaded: 42
  ⊙ Files skipped (already have): 0

📝 Unique questions with forecast data: 17
📁 Files organized in: /path/to/forecast_summaries/
📄 TSV manifest: (saved after summary)
📋 Tool run log: tool_run_2026-02-03_15-30.log

✅ Download complete!

Updating TSV manifest...
✓ TSV manifest saved: 17 questions
  Location: Question_Run_and_Date_2026-02-03_v2.txt
```

---

## Version History

### v3.0 (February 2026) - **First Occurrence Only** ✅ CURRENT

**Strategy:** Keep only first occurrence of each question

**Key Changes:**
- Download only first run per question
- Add missing file types in subsequent runs
- Versioned TSV manifest (`Question_Run_and_Date_{date}_v{n}.txt`)
- `first_run_date` extracted from Forecast Date in full summary files
- Tool run logs capture all console output
- Remove JSON reports (replaced by TSV)
- Significant space savings (~90%)

**Why This Version:**
- Clean, navigable directory structure
- Minimal disk space usage
- Practical for forecasting bot use case
- Easy to find "the" forecast for each question
- Versioned TSV prevents data loss if file is open

### v2.0 (February 2026) - Keep All Versions [DEPRECATED]

**Strategy:** Keep ALL versions of every question with run numbers

**Issues Discovered:**
- ❌ Excessive disk space (multiple copies of same question)
- ❌ Cluttered directory (hard to browse)
- ❌ Distracting when looking for specific forecast
- ❌ Cognitive overhead managing multiple versions

**Why We Changed:**
After testing with 50+ runs, we realized:
1. Users typically only need one forecast per question
2. Multiple versions consumed too much space
3. Navigation became difficult with many files
4. Historical tracking wasn't as valuable as initially thought

**Lesson Learned:** Optimize for the common case (single forecast lookup), not the edge case (version tracking).

### v1.0 (January 2026) - Original

**Strategy:** Basic download with `run_*/` subdirectories

**Issues:**
- Directory clutter with many subdirectories
- Needed consolidation step
- No manifest tracking

---

## Migration Guide

### From v2.0 to v3.0

If you have existing downloads with multiple versions:

**Option A: Clean Start (Recommended)**
```bash
# Backup existing downloads
mv forecast_summaries forecast_summaries_v2_backup

# Create new directory
mkdir forecast_summaries

# Download fresh with v3.0
python3 dre_tools/download_all_forecast_artifacts.py --limit 1000
```

---

## Troubleshooting

### Error: "GitHub CLI (gh) is not installed"
```bash
sudo apt install gh
gh auth login
```

### Error: "GitHub CLI is not authenticated"
```bash
gh auth login
```

### Files Not Downloading

Check tool run log:
```bash
tail -50 forecast_summaries/tool_run_*.log
```

### TSV Manifest Corrupted

Delete all TSV files — tool will rebuild from files on disk:
```bash
rm forecast_summaries/Question_Run_and_Date_*.txt

# Rerun (will rebuild)
python3 dre_tools/download_all_forecast_artifacts.py --limit 10
```

---

## Best Practices

1. **Regular Downloads:** Run weekly to capture new questions
2. **Check Logs:** Review tool run logs for any errors
3. **TSV Versions:** Previous TSV versions are preserved automatically — no data loss risk
4. **Monitor Space:** Even with first-occurrence-only, check disk usage periodically

---

## Related Files

- `download_all_forecast_artifacts.py` - Main tool script
- `SKILL_download_all_forecast_artifacts.md` - Detailed usage guide
- `Question_Run_and_Date_*.txt` - Versioned tracking manifests (auto-generated)
- `tool_run_*.log` - Run logs (auto-generated)

---

**Last Updated:** February 3, 2026
**Version:** 3.0
**Maintainer:** Dre + Claude
**Status:** Production Ready ✅
