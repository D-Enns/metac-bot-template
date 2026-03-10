# Bot Forecast Log Generator

Generate a TSV (Tab-Separated Values) file containing one row per forecast, extracted from condensed forecast summary markdown files.

## Overview

This tool parses condensed forecast summaries from the `all_forecast_summaries/` directory and creates a structured TSV file with metadata and forecast values for each question. The TSV format makes it easy to analyze forecasts in Excel, pandas, or other data analysis tools.

## Features

- Parses all condensed forecast summaries with pattern `*_condensed_*.md`
- Extracts metadata: forecast number, date, time, question type, URL
- Extracts forecast values in question-type-specific formats:
  - **Binary**: Single percentage value
  - **Multiple Choice**: JSON dictionary with option-percentage pairs
  - **Numeric**: JSON dictionary with percentile values (p1, p25, p50, p75, p99)
- Replaces spaces with underscores in Multiple Choice option names
- Leaves `run` and `comments` columns empty for external population
- Provides comprehensive error handling and statistics
- Supports dry-run mode for validation without writing files

## Prerequisites

- Python 3.9+
- Standard library packages (no external dependencies)

## Installation

No installation required - just run the script directly:

```bash
cd C:/Users/Donni/projects/metac_bot_Spring_2026/dre_tools
python generate_bot_forecast_log.py --help
```

## Usage

### Basic Usage

Generate TSV from all condensed summaries in the default directory:

```bash
python generate_bot_forecast_log.py
```

This will:
1. Scan `all_forecast_summaries/` for files matching `*_condensed_*.md`
2. Parse metadata and forecast values from each file
3. Generate `all_forecast_summaries/bot_forecast_log.tsv`

### Advanced Usage

Specify custom source directory:

```bash
python generate_bot_forecast_log.py --source-dir custom_forecasts/
```

Specify custom output file:

```bash
python generate_bot_forecast_log.py --output my_forecast_log.tsv
```

Dry run (validate without writing):

```bash
python generate_bot_forecast_log.py --dry-run
```

Verbose mode for debugging:

```bash
python generate_bot_forecast_log.py --verbose
```

## Output Format

### TSV Columns

| Column | Description | Example |
|--------|-------------|---------|
| `run` | Run identifier (empty, for external population) | "" |
| `forecast_number` | Question ID without 'q' prefix | "41871" |
| `date` | Forecast date in YYYY-MM-DD format | "2026-01-26" |
| `time` | Forecast time in HH:MM:SS format (UTC) | "19:33:47" |
| `question_type` | Type of question | "Binary", "Multiple Choice", or "Numeric" |
| `tournament_name` | Tournament name | "Spring Aib 2026" |
| `question_url` | Full Metaculus question URL | "https://www.metaculus.com/questions/41871" |
| `comments` | User comments (empty, for external population) | "" |
| `forecast` | Forecast values (format varies by question type) | See below |
| `community_forecast` | Community forecast values (empty, for external population) | "" |
| `score` | Forecast score (empty, for external population) | "" |
| `community_score` | Community forecast score (empty, for external population) | "" |

### Forecast Value Formats

**Binary Questions:**
```
14.82
```
Single numeric value representing percentage (without % sign).

**Multiple Choice Questions:**
```json
{"Increases": 32.43, "Doesn't_change": 38.78, "Decreases": 28.78}
```
JSON dictionary with option names as keys and percentages as values. Note: spaces in option names are replaced with underscores (e.g., "Doesn't change" → "Doesn't_change").

**Numeric Questions:**
```json
{"p1": 6000000000.0, "p25": 6522869375.802217, "p50": 6961111111.111386, "p75": 7399352846.420557, "p99": 8000800000.0}
```
JSON dictionary with percentile keys (p1, p25, p50, p75, p99) and numeric values.

## Example Output

```
$ python generate_bot_forecast_log.py

================================================================================
BOT FORECAST LOG GENERATOR
================================================================================

Source directory: C:\Users\Donni\projects\metac_bot_Spring_2026\all_forecast_summaries
Output file: C:\Users\Donni\projects\metac_bot_Spring_2026\all_forecast_summaries\bot_forecast_log.tsv

Processing condensed forecast summaries...
--------------------------------------------------------------------------------

Found 22 condensed summary files

================================================================================
GENERATION SUMMARY
================================================================================

Statistics:
  Total files found: 22
  ✓ Successfully parsed: 22
  ⊙ Skipped (non-condensed): 0
  ⚠️  Parse errors: 0
  ⚠️  Missing metadata: 0
  ⚠️  Validation errors: 0
  ❌ Read errors: 0

Forecast Types:
  Binary: 5
  Multiple Choice: 8
  Numeric: 9

Output saved to: C:\Users\Donni\projects\metac_bot_Spring_2026\all_forecast_summaries\bot_forecast_log.tsv
Total rows written: 22

Sample rows:
  41613 | 2026-01-19 13:47:48 | Multiple Choice
  41614 | 2026-01-19 13:47:00 | Numeric
  41692 | 2026-01-26 15:50:14 | Multiple Choice

✅ Log generation complete!
```

## Sample TSV Output

```tsv
run	forecast_number	date	time	question_type	tournament_name	question_url	comments	forecast	community_forecast	score	community_score
	41613	2026-01-19	13:47:48	Multiple Choice	Unknown	https://www.metaculus.com/questions/41613		{"Increases": 32.43, "Doesn't_change": 38.78, "Decreases": 28.78}
	41614	2026-01-19	13:47:00	Numeric	Unknown	https://www.metaculus.com/questions/41614		{"p1": 228, "p25": 882, "p50": 1150, "p75": 1417, "p99": 2000}
	41837	2026-01-27	17:37:19	Binary	Spring Aib 2026	https://www.metaculus.com/questions/41837		14.82
```

## Troubleshooting

### No files found

**Problem**: Script reports "No condensed summary files found!"

**Solution**:
- Verify you're in the correct directory
- Check that `all_forecast_summaries/` contains files matching `*_condensed_*.md`
- Use `--source-dir` to specify a different directory

### Parse errors

**Problem**: Script reports parse errors for specific files

**Solution**:
- Run with `--verbose` flag to see detailed error messages
- Check that the condensed summary files have the expected format:
  - FORECAST METADATA section with required fields
  - SUMMARY FORECAST VALUES section with Final Prediction

### Missing metadata

**Problem**: Some files are skipped due to missing metadata

**Solution**:
- Run with `--verbose` to identify which files have missing metadata
- Verify that files contain these required fields:
  - Forecast Date
  - Question Type
  - Question URL

### Invalid JSON in output

**Problem**: Forecast values in TSV contain malformed JSON

**Solution**:
- Check source files for unusual formatting in the Final Prediction section
- Report issue with specific file name and question type

## Integration

### Populating the `run` Column

The `run` column is left empty by this tool. To populate it with GitHub Actions run numbers:

1. Use the `logs/forecast_logs_metadata.tsv` file which contains run_number mappings
2. Match forecasts by question_number or timestamp
3. Merge the data in Excel, pandas, or other tools

Example pandas merge:
```python
import pandas as pd

# Load both files
log = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')
metadata = pd.read_csv('logs/forecast_logs_metadata.tsv', sep='\t')

# Merge by question_number (assuming column names match)
merged = log.merge(
    metadata[['question_number', 'run_number']],
    left_on='forecast_number',
    right_on='question_number',
    how='left'
)

# Update run column
merged['run'] = merged['run_number']
merged.drop(['run_number', 'question_number'], axis=1, inplace=True)

# Save updated TSV
merged.to_csv('all_forecast_summaries/bot_forecast_log_with_runs.tsv', sep='\t', index=False)
```

### Using the TSV File

Import into Excel:
1. Open Excel
2. Data → From Text/CSV
3. Select `bot_forecast_log.tsv`
4. Delimiter: Tab
5. Import

Import into pandas:
```python
import pandas as pd
df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')
```

Parse JSON forecast values in pandas:
```python
import json
import pandas as pd

df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')

# For Multiple Choice or Numeric questions, parse JSON
df['parsed_forecast'] = df['forecast'].apply(
    lambda x: json.loads(x) if x and x.startswith('{') else x
)
```

## Command-Line Reference

```
usage: generate_bot_forecast_log.py [-h] [--source-dir SOURCE_DIR]
                                     [--output OUTPUT] [--dry-run] [--verbose]

Generate Bot Forecast Log TSV from condensed forecast summaries

optional arguments:
  -h, --help            show this help message and exit
  --source-dir SOURCE_DIR
                        Directory containing condensed forecast summaries
                        (default: all_forecast_summaries)
  --output OUTPUT       Output TSV file path (default:
                        all_forecast_summaries/bot_forecast_log.tsv)
  --dry-run             Validate files without writing output
  --verbose             Print detailed parsing information

Examples:
  # Generate TSV from all condensed summaries (default)
  python generate_bot_forecast_log.py

  # Specify custom source directory
  python generate_bot_forecast_log.py --source-dir custom_forecasts/

  # Specify custom output file
  python generate_bot_forecast_log.py --output custom_log.tsv

  # Dry run (validate without writing)
  python generate_bot_forecast_log.py --dry-run

  # Verbose mode for debugging
  python generate_bot_forecast_log.py --verbose
```

## Technical Details

### Parsing Logic

**Metadata Extraction:**
- Uses regex to find `**Field**: value` patterns in FORECAST METADATA section
- Extracts URLs from markdown links `[text](url)`
- Removes 'q' prefix from Forecast ID

**Forecast Value Extraction:**
- **Binary**: Regex pattern `*Final Prediction*: XX.XX%`
- **Multiple Choice**: Extracts bulleted list after Final Prediction, replaces spaces with underscores in option names
- **Numeric**: Maps percentile values (1%, 25%, 50%, 75%, 99%) to standard keys (p1, p25, p50, p75, p99)

**Error Handling:**
- Continue processing on individual file failures
- Track errors by category (read errors, parse errors, validation errors)
- Provide detailed summary of success/failure rates

## File Location

This tool is located at:
```
C:\Users\Donni\projects\metac_bot_Spring_2026\dre_tools\generate_bot_forecast_log.py
```

## See Also

- `consolidate_forecasts.py` - Consolidates forecast files from run directories
- `download_all_forecast_artifacts.py` - Downloads forecast summaries from GitHub Actions
- `download_forecast_logs.py` - Downloads and parses GitHub Actions logs
