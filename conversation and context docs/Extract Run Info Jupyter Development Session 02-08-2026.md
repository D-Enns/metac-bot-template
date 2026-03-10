# Extract Run Info from GitHub Actions - Jupyter Development Session

**Date:** 2026-02-08
**Session Type:** Interactive Development & Debugging
**Approach:** Hybrid - Jupyter notebook prototype, then convert to standalone script

---

## Project Overview

**Goal:** Extract key information from GitHub Actions workflow runs and create an Excel summary with one row per run.

**Output File:** `C:/Users/Donni/projects/metac_bot_Spring_2026/products/Runs and Question Numbers.xlsx`

**Excel Columns:**
1. `workflow_run_number` - Run number from GitHub Actions
2. `time_date` - First timestamp in "Run bot" section
3. `has_question` - Y/N whether run processed a question
4. `question_number` - Metaculus question ID (empty if no question)
5. `forecast_value` - Forecast value (format varies by type: Binary, MC, Numeric)
6. `error_flag` - Y/N whether run had exit code 1 error

---

## Development Approach Decision

**Question:** Should we implement in Jupyter or as a standalone script?

**Decision:** Hybrid Approach - Jupyter first
- **Rationale:**
  - Quick iteration on regex patterns
  - Interactive inspection of log content
  - User comfortable with Jupyter (OpenRouter cost tracker example)
  - Can test on single runs before batch processing
- **Plan:** Develop in Jupyter, then convert working code to standalone script later

---

## Notebook Versions Created

### 007 - Initial Version
**File:** `jupyter/007_bot_logs_runs_summaries_02-08-2026.ipynb`

**Status:** Failed - multiple issues discovered

**Structure:**
1. Setup & Configuration
2. GitHub CLI Functions
3. Test Single Log Download
4. Data Extraction Functions
5. Test Extraction
6. Process Multiple Runs
7. Excel Output
8. Full Processing (commented out)
9. Summary Statistics

### 007a - ANSI Code Fix
**File:** `jupyter/007a_bot_logs_runs_summaries_02-08-2026.ipynb`

**Key Addition:** `strip_ansi_codes()` utility function
- Removes ANSI color codes from gh CLI output
- Uses regex: `r'\x1b\[[0-9;]*m'`

**Problem Identified:** Pagination still broken

### 007b - Pagination Fix
**File:** `jupyter/007b_bot_logs_runs_summaries_02-08-2026.ipynb`

**Status:** Working for most runs, Unicode issue on runs with questions

**Key Fixes:**
1. ANSI color code stripping
2. Proper pagination handling (brace counting)
3. UTF-8 encoding with error handling

**Remaining Issue:** Unicode decoding failure on run 1221 (the run with a question)

---

## Issues Encountered & Solutions

### Issue 1: ANSI Color Codes in Output

**Problem:**
```
First char: '\x1b'
❌ JSON parsing failed: Expecting value: line 1 column 1 (char 0)
```

**Root Cause:** `gh` CLI outputs colored JSON with ANSI escape codes (`\x1b[1;38m`, etc.)

**Solution:**
```python
def strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)
```

**Status:** ✅ Fixed

---

### Issue 2: Pagination Handling

**Problem:**
```
❌ No runs found in response
```

**Root Cause:** With `--paginate`, gh CLI returns 13 separate JSON objects concatenated together (not NDJSON). Simple line-by-line parsing failed.

**Discovery:**
- Total output: 18.9 MB
- 13 JSON objects (pages)
- Each page has 100 runs (last page: 24 runs)
- Total: 1224 runs

**Failed Approach:** Splitting by `}\n{` pattern didn't work due to nested JSON

**Solution:** Brace counting to find complete JSON objects
```python
json_objects = []
current_obj = ""
brace_count = 0

for char in clean_output:
    current_obj += char
    if char == '{':
        brace_count += 1
    elif char == '}':
        brace_count -= 1
        if brace_count == 0 and current_obj.strip():
            json_objects.append(current_obj.strip())
            current_obj = ""
```

**Result:**
```
Found 13 paginated responses
  Page 1: 100 runs
  Page 2: 100 runs
  ...
  Page 13: 24 runs
✅ Total: 5 runs (with limit=5)
```

**Status:** ✅ Fixed

---

### Issue 3: Unicode Decoding Error (Initial)

**Problem:**
```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 125848
```

**Root Cause:** Windows default encoding (cp1252) can't handle all characters in logs

**Solution v1:**
```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=120
)
```

**Status:** ⚠️ Partially fixed - still fails on run 1221 (the run with a question!)

---

### Issue 4: Unicode Decoding Error (Subprocess Thread)

**Problem:** Even with `encoding='utf-8', errors='replace'`, subprocess internal thread still crashes:
```
Exception in thread Thread-23 (_readerthread):
UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d
```

**Root Cause:** Subprocess's internal threading tries to decode before our error handling

**Solution v2 (proposed):**
Capture as raw bytes, decode manually:
```python
result = subprocess.run(cmd, capture_output=True, timeout=120)  # No text=True
log_text = result.stdout.decode('utf-8', errors='replace')
```

**Status:** 🔄 Testing in progress

---

## Working Components (007b)

### ✅ GitHub CLI Authentication
```python
verify_gh_cli() -> bool
```
- Checks `gh auth status`
- Returns True if authenticated

### ✅ Workflow Runs Fetching
```python
get_workflow_runs(repo, workflow, limit=None) -> List[Dict]
```
- Fetches all 1224 runs across 13 pages
- Handles pagination correctly
- Returns list with fields: id, run_number, created_at, conclusion

### ✅ Log Download (Mostly)
```python
download_run_log(repo, run_id, run_number) -> Optional[str]
```
- Downloads log via `gh run view --log`
- Strips ANSI codes
- Works for 9/10 test runs
- **Issue:** Fails on run 1221 (the run with a question)

### ✅ Data Extraction Functions

All defined and ready to test once logs download successfully:

1. `extract_timestamp(log_content) -> str`
2. `check_has_question(log_content) -> str`
3. `extract_question_number(log_content) -> str`
4. `detect_question_type(log_content) -> Optional[str]`
5. `extract_binary_forecast(log_content) -> str`
6. `extract_mc_forecast(log_content) -> str`
7. `extract_numeric_forecast(log_content) -> str`
8. `extract_forecast_value(log_content, question_type) -> str`
9. `check_error_flag(log_content) -> str`
10. `process_log(log_content, run_number) -> RunInfo`

### ✅ Excel Output
```python
write_to_excel(run_info_list, output_file)
```
- Creates workbook with headers
- Formats columns (bold headers, proper widths)
- Sorts by run_number descending
- Ready to use once data extraction works

---

## Test Results (007b with TEST_LIMIT=10)

**Runs Processed:**
```
Processing 10 runs...

[1/10] Processing run #1224... ✓ (Question: N, Error: N)
[2/10] Processing run #1223... ✓ (Question: N, Error: N)
[3/10] Processing run #1222... ✓ (Question: N, Error: N)
[4/10] Processing run #1221... ❌ Unicode error (HAS QUESTION!)
[5/10] Processing run #1220... ✓ (Question: N, Error: N)
[6/10] Processing run #1219... ✓ (Question: N, Error: N)
[7/10] Processing run #1218... ✓ (Question: N, Error: N)
[8/10] Processing run #1217... ✓ (Question: N, Error: N)
[9/10] Processing run #1216... ✓ (Question: N, Error: N)
[10/10] Processing run #1215... ✓ (Question: N, Error: N)

✅ Processed 9 runs successfully
```

**Key Observation:** Run 1221 is the ONLY run with a question, and it's the one that fails!

**Implication:** We need to fix the Unicode handling to process runs with questions, which are the most valuable data.

---

## Current Status

### What's Working ✅
- GitHub API authentication
- Fetching workflow runs with pagination (1224 total runs)
- ANSI code stripping
- Downloading logs for runs without questions (9/10 test runs)
- All extraction functions defined
- Excel output function defined

### What's Broken ❌
- Downloading logs for runs WITH questions (Unicode error)
- Cannot test extraction functions on real forecast data yet

### Next Steps 🔄
1. Fix Unicode handling with byte-based approach
2. Test extraction on run 1221 (has question + forecast)
3. Verify forecast value extraction works for all question types
4. Run full batch (TEST_LIMIT=50 or 100) to validate
5. Process all 1224 runs (~40-60 minutes)
6. Generate final Excel file

---

## Technical Learnings

### GitHub CLI Quirks
1. **Color codes:** gh CLI adds ANSI codes even in non-interactive mode
2. **Pagination format:** Multiple complete JSON objects concatenated (not NDJSON)
3. **Unicode handling:** Subprocess text decoding can fail on Windows with special chars

### Windows Encoding Issues
- Default encoding: cp1252 (limited character support)
- Solution: Explicit UTF-8 with error handling
- Subprocess threading complicates error handling

### JSON Parsing with Pagination
- Can't use simple `json.loads()` on concatenated objects
- Can't split on `}{` due to nested JSON
- Brace counting is robust solution

---

## Files Created This Session

1. **Implementation Plan:** `Extract Run Info from GitHub Actions Implementation Plan 02-08-2026.md`
2. **Notebook 007:** `jupyter/007_bot_logs_runs_summaries_02-08-2026.ipynb` (initial, broken)
3. **Notebook 007a:** `jupyter/007a_bot_logs_runs_summaries_02-08-2026.ipynb` (ANSI fix)
4. **Notebook 007b:** `jupyter/007b_bot_logs_runs_summaries_02-08-2026.ipynb` (pagination + partial Unicode fix)

---

## Architecture Pattern

### Data Flow
```
GitHub API (gh CLI)
    ↓
Strip ANSI codes
    ↓
Parse paginated JSON (13 pages)
    ↓
Extract run metadata (id, run_number, created_at)
    ↓
For each run:
    Download log (gh run view --log)
    ↓
    Strip ANSI codes
    ↓
    Extract 6 data fields:
      - timestamp
      - has_question (Y/N)
      - question_number
      - forecast_value (type-specific)
      - error_flag (Y/N)
    ↓
    Build RunInfo dataclass
    ↓
Write to Excel (openpyxl)
```

### Reusable Patterns from Existing Tools

**From `download_forecast_logs.py`:**
- `verify_gh_cli()` pattern
- Regex patterns for URLs, timestamps, errors
- Subprocess command patterns

**From `generate_bot_forecast_log.py`:**
- Forecast extraction patterns (not yet tested)
- Question type detection logic

**From OpenRouter Jupyter notebook:**
- openpyxl usage pattern
- Workbook creation and row appending
- Column width formatting

---

## Performance Estimates

**API Calls:**
- Fetching runs: ~10 seconds (13 pages)
- Downloading log per run: ~2-5 seconds
- Total for 1224 runs: **40-100 minutes**

**Data Size:**
- Paginated API response: 18.9 MB
- Average log size: ~500 KB
- Total log data: ~600 MB

**Optimization Opportunities:**
- Run downloads in parallel (ThreadPoolExecutor)
- Cache downloaded logs to disk
- Resume capability for interrupted runs

---

## Known Limitations

1. **No resume capability:** If process crashes, must start over
2. **No incremental updates:** Each run creates fresh Excel file
3. **No log caching:** Re-running requires re-downloading all logs
4. **Sequential processing:** One run at a time (could parallelize)
5. **Memory intensive:** Holds all data in memory before writing

These are acceptable for MVP, can be enhanced in standalone script version.

---

## Next Session TODO

1. ✅ Fix Unicode handling (byte-based decode)
2. Test extraction on run 1221 (with question)
3. Validate forecast value extraction for all types:
   - Binary: single percentage
   - Multiple Choice: JSON dict
   - Numeric: JSON array
4. Test with larger batch (50-100 runs)
5. Process all 1224 runs
6. Review Excel output
7. Create standalone script version (if needed)

---

## Session Notes

- **User is comfortable with Jupyter** - Good choice for prototyping
- **Windows environment** - Encoding issues expected
- **Large dataset** - 1224 runs, need efficient processing
- **Critical data in questions** - Must fix Unicode issue to get forecast data
- **Iterative debugging** - Created 3 notebook versions to solve issues progressively

**Lesson learned:** Test with data that actually contains forecasts early! We spent time fixing runs without questions, but the real challenge is runs with questions.
