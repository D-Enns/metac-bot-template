# Skill: Download Forecast Logs

Quick reference for downloading GitHub Actions workflow logs and extracting forecast metadata.

## Purpose

Download complete workflow run logs from GitHub Actions and generate a TSV summary of forecast metadata including question numbers, timestamps, error counts, and submission status.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Python 3.9+

## Basic Usage

```bash
cd C:/Users/Donni/projects/metac_bot_Spring_2026/dre_tools
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30
```

## Common Commands

### Download logs for specific date range
```bash
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30
```

### Resume interrupted download
```bash
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --skip-existing
```

### Test with limited runs
```bash
python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --limit 10
```

### Download for current month
```bash
python download_forecast_logs.py --start-date 2026-01-01 --end-date 2026-01-31
```

## Output Files

All files saved to: `C:/Users/Donni/projects/metac_bot_Spring_2026/logs/`

1. **Raw logs:** `run_{number}_{timestamp}.log` - Complete workflow output
2. **TSV summary:** `forecast_logs_metadata.tsv` - Extracted metadata
3. **State file:** `downloaded_logs_state.json` - Download tracking
4. **Report:** `download_logs_report.json` - Statistics summary

## TSV Columns

- `run_number` - GitHub Actions run number
- `timestamp_utc` - Run start time (UTC)
- `timestamp_mountain` - Run start time (Mountain Time)
- `question_number` - Metaculus question ID
- `question_url` - Full question URL
- `question_title` - Question title (if extracted)
- `forecast_submitted` - "Yes" or "No"
- `error_count` - Number of errors
- `warning_count` - Number of warnings

## Quick Analysis

### Open TSV in Excel
Data → From Text/CSV → Select `forecast_logs_metadata.tsv` → Load

### Count forecasts with Python
```python
import pandas as pd
df = pd.read_csv('logs/forecast_logs_metadata.tsv', sep='\t')
print(f"Total forecasts: {(df['forecast_submitted'] == 'Yes').sum()}")
print(f"Total errors: {df['error_count'].sum()}")
```

### Find runs with errors
```python
errors = df[df['error_count'] > 0]
print(errors[['run_number', 'question_number', 'error_count']])
```

## Tips

- Use `--limit 10` for testing before downloading many runs
- Use `--skip-existing` to safely resume if interrupted
- Full logs are ~50-200 KB each, plan storage accordingly
- Downloads are sequential (~3-5 seconds per run)

## Related Skills

- `/download-artifacts` - Download forecast summary artifacts
- `/consolidate-forecasts` - Consolidate multiple forecast files

## Full Documentation

See `download_forecast_logs_README.md` for complete documentation.
