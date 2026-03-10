# SKILL: Generate Bot Forecast Log

**Tool**: `generate_bot_forecast_log.py`
**Purpose**: Generate a TSV file with one row per forecast from condensed summary markdown files
**Category**: Data Analysis & Reporting
**Created**: January 31, 2026

---

## Quick Start

```bash
# Navigate to project root
cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026

# Generate TSV log
python3 dre_tools/generate_bot_forecast_log.py
```

**Result**: `all_forecast_summaries/bot_forecast_log.tsv` created with forecast metadata and values

---

## When to Use This Tool

### Use Cases
1. **Analyze forecasts in Excel/pandas** - Create structured dataset from markdown files
2. **Track forecast performance** - Build historical record for analysis
3. **Compare question types** - Aggregate Binary, Multiple Choice, and Numeric forecasts
4. **Prepare data for visualization** - Export forecast values in parseable format
5. **Audit forecast submissions** - Review all forecasts in tabular format

### Signs You Need This Tool
- Need to analyze forecast patterns across multiple questions
- Want to import forecasts into Excel or pandas
- Building dashboard or visualization from forecast data
- Comparing forecast values across question types
- Preparing data for statistical analysis

---

## What It Does

### Process Overview
1. **Scans** `all_forecast_summaries/` for files matching `*_condensed_*.md`
2. **Extracts** metadata from FORECAST METADATA section:
   - Forecast ID → forecast_number
   - Question URL
   - Question Type
   - Forecast Date → splits into date and time
3. **Parses** forecast values from SUMMARY FORECAST VALUES section:
   - **Binary**: Single percentage value
   - **Multiple Choice**: JSON dictionary with option-percentage pairs
   - **Numeric**: JSON dictionary with percentile values (p1, p25, p50, p75, p99)
4. **Formats** data as TSV with 8 columns
5. **Validates** each row before writing
6. **Reports** statistics on success/failure rates

### Data Transformations
- **Forecast ID**: Removes 'q' prefix (`q41871` → `41871`)
- **Question URL**: Extracts from markdown links
- **Date/Time**: Splits Forecast Date into separate fields
- **Multiple Choice options**: Replaces spaces with underscores (`Doesn't change` → `Doesn't_change`)
- **Percentages**: Removes % symbol, stores as numeric values
- **Percentiles**: Maps `1%`, `25%`, `50%`, `75%`, `99%` to `p1`, `p25`, `p50`, `p75`, `p99`

---

## Output Structure

### TSV Columns

| Column | Example | Description |
|--------|---------|-------------|
| `run` | "" | Empty, for external population (e.g., GitHub run number) |
| `forecast_number` | "41871" | Question ID without 'q' prefix |
| `date` | "2026-01-26" | Forecast date (YYYY-MM-DD) |
| `time` | "19:33:47" | Forecast time (HH:MM:SS UTC) |
| `question_type` | "Numeric" | Binary, Multiple Choice, or Numeric |
| `tournament_name` | "Spring Aib 2026" | Tournament name |
| `question_url` | "https://..." | Full Metaculus question URL |
| `comments` | "" | Empty, for user notes/annotations |
| `forecast` | JSON | Forecast values (format varies by type) |
| `community_forecast` | "" | Empty, for external population |
| `score` | "" | Empty, for external population |
| `community_score` | "" | Empty, for external population |

### Forecast Value Examples

**Binary:**
```
14.82
```

**Multiple Choice:**
```json
{"Increases": 32.43, "Doesn't_change": 38.78, "Decreases": 28.78}
```

**Numeric:**
```json
{"p1": 6000000000.0, "p25": 6522869375.802217, "p50": 6961111111.111386, "p75": 7399352846.420557, "p99": 8000800000.0}
```

---

## Console Output

### Typical Run
```
================================================================================
BOT FORECAST LOG GENERATOR
================================================================================

Source directory: /path/to/all_forecast_summaries
Output file: /path/to/all_forecast_summaries/bot_forecast_log.tsv

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

Output saved to: /path/to/all_forecast_summaries/bot_forecast_log.tsv
Total rows written: 22

Sample rows:
  41613 | 2026-01-19 13:47:48 | Multiple Choice
  41614 | 2026-01-19 13:47:00 | Numeric
  41692 | 2026-01-26 15:50:14 | Multiple Choice

✅ Log generation complete!
```

---

## Common Workflows

### Workflow 1: Basic Log Generation

**Goal**: Create TSV from all condensed summaries

```bash
# Generate log with defaults
python3 dre_tools/generate_bot_forecast_log.py

# View output
head all_forecast_summaries/bot_forecast_log.tsv

# Count rows
wc -l all_forecast_summaries/bot_forecast_log.tsv
```

### Workflow 2: Validate Before Writing

**Goal**: Check parsing logic without creating file

```bash
# Dry run to validate
python3 dre_tools/generate_bot_forecast_log.py --dry-run

# If validation succeeds, generate actual file
python3 dre_tools/generate_bot_forecast_log.py
```

### Workflow 3: Debug Parsing Issues

**Goal**: Identify files with parsing errors

```bash
# Run with verbose output
python3 dre_tools/generate_bot_forecast_log.py --verbose

# Review detailed error messages
# Fix problematic files if needed
```

### Workflow 4: Custom Output Location

**Goal**: Generate log in different directory

```bash
# Specify custom output path
python3 dre_tools/generate_bot_forecast_log.py \
  --output analysis/forecasts_2026.tsv

# Or process different source directory
python3 dre_tools/generate_bot_forecast_log.py \
  --source-dir forecast_summaries/consolidated \
  --output analysis/consolidated_log.tsv
```

### Workflow 5: Import to Excel

**Goal**: Analyze forecasts in Excel

```bash
# Generate TSV
python3 dre_tools/generate_bot_forecast_log.py

# Open Excel
# Data → From Text/CSV
# Select: all_forecast_summaries/bot_forecast_log.tsv
# Delimiter: Tab
# Import
```

### Workflow 6: Analyze with pandas

**Goal**: Load and analyze forecast data in Python

```python
import pandas as pd
import json

# Load TSV
df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')

# Parse JSON forecast values for Multiple Choice
def parse_mc(value):
    if isinstance(value, str) and value.startswith('{'):
        return json.loads(value)
    return value

df['parsed_values'] = df['forecast'].apply(parse_mc)

# Analyze by question type
print(df.groupby('question_type').size())

# View Binary forecasts
binary_df = df[df['question_type'] == 'Binary']
print(binary_df[['forecast_number', 'date', 'forecast']])
```

---

## Integration with Other Tools

### Populating the `run` Column

The `run` column is left empty by this tool. To populate it:

**Option 1: Merge with GitHub Actions metadata**
```python
import pandas as pd

# Load both files
log = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')
metadata = pd.read_csv('logs/forecast_logs_metadata.tsv', sep='\t')

# Merge by question number
merged = log.merge(
    metadata[['question_number', 'run_number']],
    left_on='forecast_number',
    right_on='question_number',
    how='left'
)

# Update run column
merged['run'] = merged['run_number']
merged = merged.drop(['run_number', 'question_number'], axis=1)

# Save
merged.to_csv('all_forecast_summaries/bot_forecast_log_with_runs.tsv', sep='\t', index=False)
```

**Option 2: Manual entry in Excel**
1. Open `bot_forecast_log.tsv` in Excel
2. Add run numbers manually to the `run` column
3. Save as TSV

### Adding Comments

The `comments` column is empty for user annotations:

```python
import pandas as pd

df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')

# Add comments based on conditions
df.loc[df['question_type'] == 'Binary', 'comments'] = 'Binary question'
df.loc[df['forecast_number'] == '41871', 'comments'] = 'NVIDIA Q4 forecast'

# Save updated version
df.to_csv('all_forecast_summaries/bot_forecast_log_annotated.tsv', sep='\t', index=False)
```

### Using with Consolidation Tool

**Recommended workflow:**
```bash
# 1. Download artifacts
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# 2. Consolidate forecasts
python3 dre_tools/consolidate_forecasts.py

# 3. Copy consolidated files to all_forecast_summaries
cp forecast_summaries/consolidated/*_condensed_*.md all_forecast_summaries/

# 4. Generate log
python3 dre_tools/generate_bot_forecast_log.py
```

---

## Understanding the Output

### Statistics Explained

**Total files found**: All `*_condensed_*.md` files in source directory

**Successfully parsed**: Files with complete metadata and valid forecast values
- Should be ~100% for properly formatted condensed summaries

**Parse errors**: Files with missing Final Prediction section or malformed values
- Investigate with `--verbose` flag

**Missing metadata**: Files lacking required fields (Forecast Date, Question Type, URL)
- Check FORECAST METADATA section format

**Validation errors**: Files that parsed but failed validation (e.g., invalid date format)
- Review validation logic

### Forecast Type Counts

Shows breakdown by question type:
- **Binary**: Yes/No questions → single percentage
- **Multiple Choice**: 3+ options → JSON dictionary
- **Numeric**: Range questions → percentile distribution

Typical distribution for AIB 2026:
- ~25% Binary
- ~35% Multiple Choice
- ~40% Numeric

---

## Troubleshooting

### Issue: "No condensed summary files found!"

**Cause**: Source directory empty or wrong location

**Solution**:
```bash
# Check current directory
pwd

# List condensed summaries
ls all_forecast_summaries/*_condensed_*.md

# If empty, check forecast_summaries/consolidated/
ls forecast_summaries/consolidated/*_condensed_*.md

# Use --source-dir to specify location
python3 dre_tools/generate_bot_forecast_log.py \
  --source-dir forecast_summaries/consolidated
```

### Issue: Parse errors for specific files

**Symptom**: `⚠️  Parse errors: 3`

**Solution**:
```bash
# Run with verbose to see which files failed
python3 dre_tools/generate_bot_forecast_log.py --verbose

# Check the problematic files
cat all_forecast_summaries/FILENAME_condensed_1.md

# Common issues:
# - Missing "# FORECAST METADATA" header
# - Missing "*Final Prediction*:" line
# - Malformed percentage format
```

### Issue: JSON parsing errors in output

**Symptom**: forecast contains "ERROR: ..."

**Cause**: Unexpected format in Final Prediction section

**Solution**:
```bash
# Identify problematic files with verbose mode
python3 dre_tools/generate_bot_forecast_log.py --verbose

# Check format of Final Prediction section
# Binary should have: *Final Prediction*: XX.XX%
# MC should have: - Option: XX.XX%
# Numeric should have: XX.XX% chance of value below YY.YY
```

### Issue: Missing metadata errors

**Symptom**: `⚠️  Missing metadata: 5`

**Cause**: Files missing required metadata fields

**Required fields**:
- Forecast Date
- Question Type
- Question URL

**Solution**:
```bash
# Find files with missing metadata (verbose mode)
python3 dre_tools/generate_bot_forecast_log.py --verbose

# Check FORECAST METADATA section format:
# **Forecast ID**: q41871
# **Question URL**: [text](url)
# **Question Type**: Binary/Multiple Choice/Numeric
# **Forecast Date**: YYYY-MM-DD HH:MM:SS UTC
```

### Issue: Spaces not replaced with underscores

**Symptom**: Multiple Choice options still have spaces

**Cause**: Script is working correctly, but output viewer may not show underscores

**Verification**:
```bash
# Check raw TSV content
grep "Doesn't_change" all_forecast_summaries/bot_forecast_log.tsv

# Should show underscores in JSON
# {"Increases": 32.43, "Doesn't_change": 38.78, "Decreases": 28.78}
```

---

## Best Practices

### 1. Validate Before Production

```bash
# Always dry-run first
python3 dre_tools/generate_bot_forecast_log.py --dry-run

# Then generate actual file
python3 dre_tools/generate_bot_forecast_log.py
```

### 2. Backup Existing Logs

```bash
# Before regenerating
if [ -f all_forecast_summaries/bot_forecast_log.tsv ]; then
  cp all_forecast_summaries/bot_forecast_log.tsv \
     all_forecast_summaries/bot_forecast_log_backup_$(date +%Y%m%d).tsv
fi

# Then generate new log
python3 dre_tools/generate_bot_forecast_log.py
```

### 3. Update After New Forecasts

```bash
# After bot creates new condensed summaries
python3 dre_tools/generate_bot_forecast_log.py

# Log will include all forecasts (new and old)
```

### 4. Version Control

```bash
# Track changes to log over time
git add all_forecast_summaries/bot_forecast_log.tsv
git commit -m "Update bot forecast log with new forecasts"
```

### 5. Use Consistent Source

Always generate from the same source directory:
- ✅ `all_forecast_summaries/` - Current forecasts
- ✅ `forecast_summaries/consolidated/` - Deduplicated archives
- ❌ Mixed sources - Leads to inconsistent logs

---

## Advanced Usage

### Custom Parsing for Specific Questions

```python
import pandas as pd
import json

# Load TSV
df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')

# Extract specific percentile for Numeric questions
def get_median(value):
    if isinstance(value, str) and value.startswith('{'):
        data = json.loads(value)
        return data.get('p50', None)
    return None

df['median_forecast'] = df.apply(
    lambda row: get_median(row['forecast'])
                if row['question_type'] == 'Numeric' else None,
    axis=1
)

# Calculate average Binary prediction
binary_forecasts = df[df['question_type'] == 'Binary']['forecast'].astype(float)
print(f"Average Binary forecast: {binary_forecasts.mean():.2f}%")
```

### Exporting Subsets

```bash
# Export only Binary forecasts
python3 -c "
import pandas as pd
df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')
binary_df = df[df['question_type'] == 'Binary']
binary_df.to_csv('binary_forecasts.tsv', sep='\t', index=False)
"

# Export forecasts from January 2026
python3 -c "
import pandas as pd
df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t')
jan_df = df[df['date'].str.startswith('2026-01')]
jan_df.to_csv('january_2026_forecasts.tsv', sep='\t', index=False)
"
```

---

## Command Reference

### Basic Commands

```bash
# Generate log (defaults)
python3 dre_tools/generate_bot_forecast_log.py

# Dry run
python3 dre_tools/generate_bot_forecast_log.py --dry-run

# Verbose mode
python3 dre_tools/generate_bot_forecast_log.py --verbose

# Custom source
python3 dre_tools/generate_bot_forecast_log.py --source-dir forecast_summaries/consolidated

# Custom output
python3 dre_tools/generate_bot_forecast_log.py --output custom_log.tsv

# View help
python3 dre_tools/generate_bot_forecast_log.py --help
```

### Analysis Commands

```bash
# Count rows (subtract 1 for header)
wc -l all_forecast_summaries/bot_forecast_log.tsv

# View first 10 rows
head -n 10 all_forecast_summaries/bot_forecast_log.tsv

# Search for specific question
grep "41871" all_forecast_summaries/bot_forecast_log.tsv

# Count by question type
cut -f5 all_forecast_summaries/bot_forecast_log.tsv | sort | uniq -c
```

---

## Performance

### Typical Run Time
- **22 files**: < 1 second
- **100 files**: ~2-3 seconds
- **1000 files**: ~15-20 seconds

### Memory Usage
- Minimal (processes one file at a time)
- Safe for large datasets (1000+ files)

### Output Size
- ~1 KB per forecast row
- 22 forecasts ≈ 25 KB TSV file

---

## Related Files

- `generate_bot_forecast_log.py` - Main generation script
- `generate_bot_forecast_log_README.md` - Full documentation
- `consolidate_forecasts.py` - Source data consolidation
- `download_all_forecast_artifacts.py` - Download source summaries

---

## Quick Reference Card

```bash
# Most Common Commands

# Basic generation
python3 dre_tools/generate_bot_forecast_log.py

# Validate first
python3 dre_tools/generate_bot_forecast_log.py --dry-run
python3 dre_tools/generate_bot_forecast_log.py

# Debug parsing
python3 dre_tools/generate_bot_forecast_log.py --verbose

# View output
head all_forecast_summaries/bot_forecast_log.tsv
cat all_forecast_summaries/bot_forecast_log.tsv

# Count forecasts
wc -l all_forecast_summaries/bot_forecast_log.tsv

# Import to pandas
python3 -c "import pandas as pd; df = pd.read_csv('all_forecast_summaries/bot_forecast_log.tsv', sep='\t'); print(df.head())"
```

---

## Success Metrics

After generation, you should see:

✅ **Parse Success**:
- `✓ Successfully parsed: X` where X matches file count
- `⚠️  Parse errors: 0` (or very few)
- `❌ Read errors: 0`

✅ **Output Quality**:
- TSV file exists at expected location
- Row count = successfully parsed + 1 (header)
- All forecast types represented (Binary, MC, Numeric)

✅ **Data Integrity**:
- `run` and `comments` columns empty (as expected)
- forecast contain valid JSON for MC/Numeric
- No "ERROR:" entries in forecast values
- Dates in YYYY-MM-DD format
- Times in HH:MM:SS format

---

**Last Updated**: January 31, 2026
**Version**: 1.0
**Maintainer**: Dre + Claude
**Status**: Production Ready ✅
