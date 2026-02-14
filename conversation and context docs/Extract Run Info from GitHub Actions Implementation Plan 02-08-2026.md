# Implementation Plan: Extract Run Information from GitHub Actions Logs to Excel

## Context

The forecasting bot runs every 20 minutes in GitHub Actions. Each workflow run generates logs containing information about whether a question was forecast, what the forecast was, and if any errors occurred. Currently, this information is scattered across individual log files and is difficult to analyze at scale.

This tool will extract key information from GitHub Actions workflow runs and consolidate it into an Excel spreadsheet with one row per run, making it easy to:
- Track which runs processed questions vs. ran without finding questions
- Review forecast values across runs
- Identify runs with errors
- Analyze bot behavior over time

## Implementation Approach

Create a standalone Python tool (`extract_run_info.py`) that:
1. Fetches workflow run metadata from GitHub Actions API using `gh` CLI
2. Downloads the full log for each run
3. Parses the "Run bot" section to extract required data
4. Writes results to Excel using `openpyxl`

The tool will follow established patterns from `download_forecast_logs.py` for GitHub integration and the OpenRouter cost tracker Jupyter notebook for Excel output.

## Critical Files to Modify/Create

**New Files:**
- `dre_tools/extract_run_info.py` - Main tool implementation (~450 lines)
- `dre_tools/extract_run_info_README.md` - Usage documentation
- `dre_tools/SKILL_extract_run_info.md` - Claude Code integration

**Reference Files (not modified):**
- `dre_tools/download_forecast_logs.py` - GitHub CLI patterns and regex
- `dre_tools/generate_bot_forecast_log.py` - Forecast value extraction patterns
- `jupyter/006_OpenRouter Usage Tracker 02-08-2026.ipynb` - Excel output with openpyxl

## Excel Output Schema

**File Location:** `C:/Users/Donni/projects/metac_bot_Spring_2026/products/Runs and Question Numbers.xlsx`

**Columns:**

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `workflow_run_number` | Integer | Run number from GitHub Actions | `1220` |
| `time_date` | String | First timestamp in "Run bot" section | `2026-01-03 14:02:21` |
| `has_question` | String (Y/N) | Whether run processed a question | `Y` or `N` |
| `question_number` | String | Metaculus question ID | `41851` (empty if no question) |
| `forecast_value` | String | Forecast value (format varies by type) | `1.8` or `[2.45, 2.60, ...]` |
| `error_flag` | String (Y/N) | Whether run had exit code 1 error | `Y` or `N` |

**Sorting:** Rows sorted by `workflow_run_number` descending (newest first)

## Detailed Implementation Steps

### 1. Setup and Configuration

**File:** `dre_tools/extract_run_info.py`

**Imports:**
```python
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment
```

**Constants:**
```python
REPO = "D-Enns/metac-bot-template"
WORKFLOW = "dre_run_bot_on_tournament.yaml"
```

**Data Structure:**
```python
@dataclass
class RunInfo:
    workflow_run_number: int
    time_date: str
    has_question: str
    question_number: str
    forecast_value: str
    error_flag: str
```

### 2. GitHub CLI Integration

**Class:** `RunInfoExtractor`

**Method: `verify_gh_cli()`**
- Reuse pattern from `download_forecast_logs.py` lines 115-133
- Check `gh auth status` via subprocess
- Return bool, print error if not authenticated

**Method: `get_all_runs(limit: Optional[int])`**
- Command: `gh api repos/{repo}/actions/workflows/{workflow}/runs --paginate -q '.workflow_runs[] | {id, run_number, created_at, conclusion}'`
- Parse NDJSON output line by line with `json.loads()`
- Sort by `run_number` descending
- Apply limit if specified (for testing)
- Return list of run dicts

**Method: `download_log(run_id: int, run_number: int)`**
- Command: `gh run view {run_id} --repo {repo} --log`
- Timeout: 120 seconds
- Return log content as string or None on failure

### 3. Data Extraction Methods

**Method: `extract_timestamp(log_content: str)`**
- Find line containing `##[group]Run poetry run python main.py`
- Extract timestamp using regex: `r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)'`
- Convert from ISO 8601 UTC to readable format: `YYYY-MM-DD HH:MM:SS`
- Search first 50 lines of log
- Return formatted string or empty string if not found

**Method: `check_has_question(log_content: str)`**
- Search for pattern: `r'Found Research for URL\s+(https://www\.metaculus\.com/questions/\d+)'`
- Return "Y" if found, "N" otherwise
- This is more reliable than just checking for URL presence

**Method: `extract_question_number(log_content: str)`**
- Only call if `has_question == "Y"`
- Search for pattern: `r'https://www\.metaculus\.com/questions/(\d+)'`
- Extract numeric ID from URL
- Return question number string or empty string

**Method: `detect_question_type(log_content: str)`**
- Check for indicators:
  - Binary: `"BinaryQuestion"` in log or `"*Final Prediction*:"` present
  - Multiple Choice: `"MultipleChoiceQuestion"` in log
  - Numeric: `"NumericQuestion"` in log or `"Probability distribution:"` present
- Return `"Binary"`, `"MultipleChoice"`, `"Numeric"`, or `None`

**Method: `extract_forecast_value(log_content: str, question_type: Optional[str])`**
- Dispatch to type-specific extraction method
- Wrap in try/except, return `"ERROR: {message}"` on failure

**Method: `_extract_binary_forecast(log_content: str)`**
- Try patterns in order:
  1. `r'\*Final Prediction\*:\s*(\d+\.?\d*)%?'`
  2. `r'\*\*Probability:\s*(\d+\.?\d*)%?'`
- Return percentage value as string (e.g., `"1.8"`)
- Raise ValueError if not found

**Method: `_extract_mc_forecast(log_content: str)`**
- Look for `# Final Answer` section with JSON dict: `r'# Final Answer\s*\n\s*(\{[^}]+\})'`
- Alternative: Parse bullet list format with `r'-\s*([^:]+):\s*(\d+\.?\d*)%?'`
- Build dict: `{option_name: probability}`
- Return as JSON string
- Raise ValueError if not found

**Method: `_extract_numeric_forecast(log_content: str)`**
- Look for `# Final Answer` section with array: `r'# Final Answer\s*\n\s*(\[[\d.,\s]+\])'`
- Return array as JSON string (e.g., `"[2.45, 2.60, 2.75, ...]"`)
- Raise ValueError if not found

**Method: `check_error_flag(log_content: str)`**
- Check last 200 lines for pattern: `r'Error: Process completed with exit code 1\.'`
- Return "Y" if found, "N" otherwise

**Method: `process_log(log_content: str, run_number: int)`**
- Extract all fields by calling above methods
- Handle missing data gracefully (empty strings for missing fields)
- Return `RunInfo` dataclass instance

### 4. Excel Output

**Method: `initialize_excel()`**
- Check if output file exists
- If exists: Load with `load_workbook()`
- If not: Create new `Workbook()`, add header row with column names
- Format header: Bold font, center alignment
- Return workbook and worksheet objects

**Method: `write_to_excel(run_info_list: List[RunInfo])`**
- Initialize or load workbook
- Sort run_info_list by `workflow_run_number` descending
- For each RunInfo:
  - Append row with: `[run_number, time_date, has_question, question_number, forecast_value, error_flag]`
- Set column widths:
  - A: 20 (workflow_run_number)
  - B: 20 (time_date)
  - C: 15 (has_question)
  - D: 18 (question_number)
  - E: 50 (forecast_value - wider for JSON arrays)
  - F: 12 (error_flag)
- Save workbook to output path
- Print success message

### 5. Main Execution Flow

**Method: `run(limit: Optional[int] = None)`**
1. Verify gh CLI authentication
2. Fetch all runs (or limited set)
3. For each run:
   - Print progress indicator: `[i/total] Processing run #{run_number}...`
   - Download log
   - Process log to extract RunInfo
   - Handle errors gracefully (skip run, continue)
4. Write all extracted data to Excel
5. Print summary statistics

### 6. Command-Line Interface

**Function: `main()`**

Arguments:
- `--repo` (default: `D-Enns/metac-bot-template`) - GitHub repository
- `--workflow` (default: `dre_run_bot_on_tournament.yaml`) - Workflow filename
- `--output` (default: `C:/Users/Donni/projects/metac_bot_Spring_2026/products/Runs and Question Numbers.xlsx`) - Output Excel path
- `--limit` (optional) - Limit number of runs to process (for testing)

Example usage:
```bash
# Process all runs
python dre_tools/extract_run_info.py

# Test with 5 most recent runs
python dre_tools/extract_run_info.py --limit 5

# Custom output path
python dre_tools/extract_run_info.py --output test_output.xlsx
```

## Reusable Components

### From `download_forecast_logs.py`:

**Lines 115-133:** `verify_gh_cli()` method
- Direct reuse for authentication verification

**Lines 182-235:** `get_workflow_runs()` method pattern
- Adapt to use simpler API call without date filtering
- Keep pagination and NDJSON parsing logic

**Lines 30-37:** Regex patterns
- `QUESTION_URL_PATTERN`, `QUESTION_NUMBER_PATTERN`, `TIMESTAMP_PATTERN`
- Direct reuse

### From `generate_bot_forecast_log.py`:

**Lines 113-122:** Binary forecast extraction pattern
- Adapt regex for log format (vs. markdown summary format)

**Lines 124-154:** Multiple Choice extraction pattern
- Adapt for log output format

**Lines 156-189:** Numeric forecast extraction pattern
- Adapt to extract list from "# Final Answer" section

### From `jupyter/006_OpenRouter Usage Tracker 02-08-2026.ipynb`:

**Cell 8:** Excel workbook loading/creation
- Pattern: Check if file exists → `load_workbook()` vs. `Workbook()`
- Header creation: `ws.append(['col1', 'col2', ...])`

**Cell 15:** Data row appending and saving
- Pattern: `ws.append([val1, val2, ...])`
- Saving: `wb.save(filepath)`

## Error Handling

**GitHub API Errors:**
- Authentication failure → Exit with error message
- Network timeout → Skip run, log warning, continue
- Rate limiting → Currently sequential (0.5s delay between runs), sufficient for now

**Log Parsing Errors:**
- Missing timestamp → Use empty string, continue
- No question found → Valid case, record as has_question="N"
- Forecast extraction failure → Record as `"ERROR: Could not extract forecast"`
- Malformed data → Extract what's possible, fill rest with empty strings

**Excel Writing Errors:**
- File locked → Clear error message suggesting to close Excel
- Permission denied → Report error with path
- Invalid path → Create parent directories if needed

**Strategy:** Graceful degradation - extract as much data as possible, continue processing even if individual runs fail

## Testing Plan

**Test 1: Limited run set**
```bash
python dre_tools/extract_run_info.py --limit 5
```
- Verify: 5 runs processed, Excel file created with 6 rows (header + 5 data)

**Test 2: Binary question run**
- Use a known run with binary question
- Verify: `forecast_value` contains single percentage

**Test 3: Numeric question run**
- Use a known run with numeric question
- Verify: `forecast_value` contains JSON array

**Test 4: Run without question**
- Verify: `has_question="N"`, `question_number=""`, `forecast_value=""`

**Test 5: Run with error**
- Verify: `error_flag="Y"` detected correctly

**Test 6: Full run processing**
```bash
python dre_tools/extract_run_info.py
```
- Verify: All runs processed, Excel file sorted correctly, no crashes

## Dependencies

**Required Package:**
- `openpyxl` - Excel file manipulation
- Install: `pip install openpyxl` or add to `pyproject.toml`

**System Requirements:**
- Python 3.9+
- GitHub CLI (`gh`) installed and authenticated
- Network access to GitHub API
- Write permissions to output directory

## Documentation Files

### README (`extract_run_info_README.md`)

Include:
1. **Overview** - What the tool does and why
2. **Prerequisites** - gh CLI, openpyxl installation
3. **Installation** - `pip install openpyxl`
4. **Usage Examples** - Basic and advanced commands with flags
5. **Output Format** - Excel schema with column descriptions
6. **Troubleshooting** - Common issues (auth errors, file locked, etc.)
7. **Performance Notes** - Expected runtime (2-5 seconds per run)
8. **Related Tools** - Links to download_forecast_logs.py and other tools

### SKILL File (`SKILL_extract_run_info.md`)

```markdown
# Extract Run Info Skill

Extract workflow run information from GitHub Actions logs to Excel.

## Usage

```bash
python dre_tools/extract_run_info.py
```

## Options

- `--limit N` - Process only N most recent runs
- `--output PATH` - Custom output file path

## Output

Creates: `products/Runs and Question Numbers.xlsx`
```

## Implementation Priority

**Phase 1: Core Functionality (MVP)**
1. GitHub CLI integration (verify + fetch runs)
2. Log downloading (single log)
3. Timestamp extraction
4. Question detection (Y/N)
5. Question number extraction
6. Error flag detection
7. Binary forecast extraction
8. Excel output (basic write)
9. Batch processing loop
10. CLI interface

**Phase 2: Extended Question Types**
11. Numeric forecast extraction
12. Multiple Choice extraction

**Phase 3: Polish**
13. Error handling improvements
14. Progress indicators
15. Documentation (README + SKILL)

**Estimated Time:** 4-6 hours for Phase 1, 2-3 hours for Phase 2, 1-2 hours for Phase 3

## Verification Steps

After implementation:

1. **Test with limited runs:**
   ```bash
   python dre_tools/extract_run_info.py --limit 10
   ```
   - Verify Excel file created at specified path
   - Open Excel and check all columns present
   - Verify data looks correct (run numbers, dates, Y/N flags)

2. **Verify forecast values:**
   - Find a run with Binary question → Check single percentage value
   - Find a run with Numeric question → Check JSON array format
   - Find a run without question → Check empty forecast_value

3. **Verify error detection:**
   - Find a failed run → Check error_flag="Y"

4. **Test full processing:**
   ```bash
   python dre_tools/extract_run_info.py
   ```
   - Verify processes all runs without crashing
   - Check total row count matches expected

5. **Verify Excel formatting:**
   - Open in Excel
   - Check column widths are reasonable
   - Verify header row is bold
   - Check data is sorted newest-first

## Future Enhancements (Post-MVP)

- **Resume capability:** Track processed runs, skip already-extracted runs
- **Incremental updates:** Append new runs to existing Excel file
- **Advanced Excel formatting:** Conditional formatting (errors in red), freeze header row
- **Date range filtering:** `--start-date` and `--end-date` flags
- **Summary statistics:** Success rate, question coverage percentage
- **Log caching:** Save downloaded logs to disk for re-processing

These can be added after the MVP is validated and working.
