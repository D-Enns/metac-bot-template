# DRE Tools

Custom tools for managing and analyzing forecast bot data.

## Tools

### download_all_forecast_artifacts.py

Systematically downloads all forecast summary artifacts from GitHub Actions workflow runs.

**Purpose**: Ensure complete data recovery for all tournaments by downloading artifacts from all workflow runs.

**Requirements**:
- GitHub CLI (`gh`) installed and authenticated
- Python 3.7+

**Usage**:

```bash
# Basic usage - download all artifacts
python dre_tools/download_all_forecast_artifacts.py

# Download from specific workflow
python dre_tools/download_all_forecast_artifacts.py --workflow dre_run_bot_on_tournament.yaml

# Download last 500 runs only
python dre_tools/download_all_forecast_artifacts.py --limit 500

# Use custom output directory
python dre_tools/download_all_forecast_artifacts.py --output-dir my_forecasts

# Skip file consolidation step
python dre_tools/download_all_forecast_artifacts.py --no-consolidate
```

**Features**:
- ✅ Downloads artifacts from all successful workflow runs
- ✅ Tracks previously downloaded artifacts to avoid duplicates
- ✅ Organizes files by run number
- ✅ Generates comprehensive download report
- ✅ Optional file consolidation into main directory
- ✅ Handles expired artifacts gracefully
- ✅ Creates detailed logs for troubleshooting

**Output**:
- Files organized in `forecast_summaries/run_*/` directories
- Download log saved to `downloaded_artifacts_log.json`
- Summary report saved to `forecast_summaries/download_report.json`

**Example Output**:
```
FORECAST ARTIFACT DOWNLOADER
================================================================================
✓ GitHub CLI (gh) is available
✓ GitHub CLI is authenticated

Fetching workflow runs for: dre_run_bot_on_tournament.yaml
Repository: D-Enns/metac-bot-template
Limit: 1000 runs
✓ Found 908 workflow runs

Processing 908 workflow runs...
Output directory: /path/to/forecast_summaries
--------------------------------------------------------------------------------

[1/908] Run #909 (ID: 21415607575)
  Date: 2026-01-27T21:51:43Z
  Status: success
  - forecast-summaries-909 (0.05 MB)
    ✓ Downloaded to forecast_summaries/run_909/
...

DOWNLOAD SUMMARY
================================================================================

📊 Statistics:
  Total workflow runs processed: 908
  Runs with forecast artifacts: 250
  Total artifacts found: 250
  ✓ Downloaded: 200
  ⊙ Skipped (already downloaded): 50
  ✗ Failed: 0
  ⊗ Expired: 0

📁 Files organized in: /path/to/forecast_summaries/
📝 Unique questions with forecast data: 45
  Question IDs: 14333, 41379, 41384, 41392, ...

📄 Detailed report saved to: forecast_summaries/download_report.json
📋 Download log saved to: downloaded_artifacts_log.json

✅ Download complete!
```
