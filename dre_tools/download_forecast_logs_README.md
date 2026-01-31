# GitHub Actions Log Downloader

Download GitHub Actions workflow run logs for the forecast bot, extract metadata from each run, and generate a TSV summary for analysis.

## Overview

This tool downloads full workflow logs (all 7 steps) from GitHub Actions, parses them to extract forecast-related metadata, and generates a comprehensive TSV file with one row per question processed.

## Features

- Downloads complete workflow run logs for a specified date range
- Extracts metadata: run number, timestamps (UTC + Mountain Time), question number, error count, submission status
- Generates TSV file for easy analysis in Excel or other tools
- Supports resumable downloads with state tracking
- Sequential downloads with rate limiting to respect GitHub API limits
- Saves raw logs as plain text files for manual inspection

## Prerequisites

- Python 3.9+
- GitHub CLI (`gh`) installed and authenticated
- Required Python packages:
  - `zoneinfo` (Python 3.9+ standard library)
  - Standard library packages: `argparse`, `csv`, `json`, `re`, `subprocess`, `time`, `datetime`, `pathlib`, `dataclasses`

### Installing GitHub CLI

If you don't have the GitHub CLI installed:

1. Download from: https://cli.github.com/
2. Install and authenticate: `gh auth login`
3. Verify: `gh auth status`

## Installation

No installation required - just run the script directly:

```bash
cd C:/Users/Donni/projects/metac_bot_Spring_2026/dre_tools
python download_forecast_logs.py --help
```

## Usage

### Basic Usage

Download logs for a specific date range:

```bash
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30
```

### Common Options

```bash
# Skip already downloaded runs (resume interrupted download)
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --skip-existing

# Limit number of runs (useful for testing)
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --limit 10

# Custom output directory
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --output-dir /path/to/logs

# Different repository
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --repo username/repo-name
```

### Command-Line Arguments

**Required:**
- `--start-date YYYY-MM-DD` - Start of date range (inclusive)
- `--end-date YYYY-MM-DD` - End of date range (inclusive)

**Optional:**
- `--repo OWNER/REPO` - GitHub repository (default: `D-Enns/metac-bot-template`)
- `--workflow FILE` - Workflow filename (default: `dre_run_bot_on_tournament.yaml`)
- `--output-dir PATH` - Output directory (default: `C:/Users/Donni/projects/metac_bot_Spring_2026/logs`)
- `--skip-existing` - Skip already downloaded runs (enables resumable downloads)
- `--limit N` - Maximum number of runs to process (useful for testing)

## Output Files

The tool generates four types of output in the specified output directory:

### 1. Raw Log Files

Individual `.log` files for each workflow run:

```
logs/run_981_2026-01-30_15-48-13.log
logs/run_980_2026-01-29_14-58-17.log
```

**Naming format:** `run_{run_number}_{timestamp_UTC}.log`

These are plain text files containing the complete output from all workflow steps.

### 2. TSV Metadata File

`forecast_logs_metadata.tsv` - Tab-separated values file with metadata extracted from each log:

**Columns:**
- `run_number` - GitHub Actions run number
- `timestamp_utc` - Run start time in UTC (YYYY-MM-DD HH:MM:SS UTC)
- `timestamp_mountain` - Run start time in Mountain Time (YYYY-MM-DD HH:MM:SS MST/MDT)
- `question_number` - Metaculus question number (or "None")
- `question_url` - Full Metaculus question URL (or "None")
- `question_title` - Extracted question title if available (or "None")
- `forecast_submitted` - "Yes" or "No"
- `error_count` - Number of ERROR log entries for this question
- `warning_count` - Number of WARNING log entries for this question

**Format:** UTF-8 encoded, tab-delimited, sorted by run_number descending (newest first)

### 3. State Tracking File

`downloaded_logs_state.json` - Tracks which runs have been downloaded:

```json
{
  "downloaded_runs": {
    "981": {
      "run_id": 21521668225,
      "created_at": "2026-01-30T15:48:13Z",
      "log_file": "run_981_2026-01-30_15-48-13.log",
      "downloaded_at": "2026-01-30T16:00:00Z",
      "questions_found": 2,
      "conclusion": "success"
    }
  },
  "last_updated": "2026-01-30T16:00:00Z",
  "total_runs_downloaded": 1,
  "total_questions_processed": 2
}
```

This file enables resumable downloads using `--skip-existing`.

### 4. Summary Report

`download_logs_report.json` - Statistical summary of the download:

```json
{
  "generated_at": "2026-01-30T16:00:00Z",
  "summary": {
    "total_runs_downloaded": 10,
    "total_questions_processed": 25,
    "questions_with_forecasts": 23,
    "total_errors": 2,
    "total_warnings": 5
  },
  "output_files": {
    "tsv_file": "forecast_logs_metadata.tsv",
    "state_file": "downloaded_logs_state.json",
    "log_directory": "C:/Users/Donni/projects/metac_bot_Spring_2026/logs"
  }
}
```

## Examples

### Example 1: Download logs for last week

```bash
python download_forecast_logs.py --start-date 2026-01-23 --end-date 2026-01-30
```

### Example 2: Test with limited runs

```bash
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-30 --limit 5
```

### Example 3: Resume interrupted download

If a download was interrupted, resume it with:

```bash
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-30 --skip-existing
```

This will skip any runs that were already successfully downloaded.

### Example 4: Analyze specific month

```bash
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-31
```

## Analyzing the Output

### Opening TSV in Excel

1. Open Excel
2. Go to Data → From Text/CSV
3. Select `forecast_logs_metadata.tsv`
4. Excel will auto-detect tab delimiter
5. Click "Load"

### Basic Analysis Queries

**Count forecasts submitted:**
```python
import pandas as pd
df = pd.read_csv('forecast_logs_metadata.tsv', sep='\t')
print(f"Total forecasts: {(df['forecast_submitted'] == 'Yes').sum()}")
```

**Find runs with errors:**
```python
errors = df[df['error_count'] > 0]
print(errors[['run_number', 'question_number', 'error_count']])
```

**Questions never processed:**
```python
all_questions = df['question_number'].unique()
submitted = df[df['forecast_submitted'] == 'Yes']['question_number'].unique()
never_submitted = set(all_questions) - set(submitted)
print(f"Questions never submitted: {never_submitted}")
```

## Performance

- **Download speed:** ~3-5 seconds per run (sequential with rate limiting)
- **Storage:** ~50-200 KB per log file
- **Estimated time:**
  - 10 runs: ~1 minute
  - 50 runs: ~4 minutes
  - 100 runs: ~8 minutes
- **TSV file size:** ~100 bytes per row

## Troubleshooting

### Error: "gh CLI is not authenticated"

**Solution:** Run `gh auth login` and follow the prompts

### Error: "No workflow runs found in date range"

**Possible causes:**
1. Date range doesn't match any runs
2. Wrong repository or workflow name
3. Network connectivity issues

**Solution:**
- Check GitHub Actions page for available runs
- Verify repository name and workflow file name
- Try a broader date range

### Warning: "Could not load state file"

**Impact:** Minor - state file will be recreated

**Solution:** No action needed - this is expected on first run

### Download fails for specific runs

**Impact:** Script continues with other runs

**Details:** Some runs may fail due to:
- Network timeouts
- API rate limits
- Run still in progress

**Solution:**
- Wait and retry with `--skip-existing`
- Check if run completed on GitHub

### Large number of runs causes slow downloads

**Solution:** Use `--limit` to download in batches:

```bash
# Download first 50
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-31 --limit 50

# Then next 50 (skip existing)
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-31 --limit 100 --skip-existing
```

## Technical Details

### Metadata Extraction

The tool uses regex patterns to extract information from logs:

- **Question URLs:** Matches `https://www.metaculus.com/questions/\d+/...`
- **Errors:** Counts lines matching `- ERROR -`
- **Warnings:** Counts lines matching `- WARNING -`
- **Submissions:** Looks for "Forecasted URL", "Posted forecast", "Saved full forecast"

### Timezone Handling

- Timestamps from GitHub API are in UTC
- Converted to America/Denver timezone (Mountain Time)
- Automatically handles MST (UTC-7) vs MDT (UTC-6) depending on date

### Rate Limiting

- 0.5 second delay between downloads
- 3 retry attempts on failures with 2 second backoff
- Respects GitHub API rate limits

## Related Tools

- `download_all_forecast_artifacts.py` - Downloads forecast summary artifacts
- `consolidate_forecasts.py` - Consolidates multiple forecast files

## Support

For issues or questions:
1. Check this README for troubleshooting tips
2. Verify your GitHub CLI authentication: `gh auth status`
3. Test with a small date range and `--limit 5`
4. Review the generated report file for diagnostic information
