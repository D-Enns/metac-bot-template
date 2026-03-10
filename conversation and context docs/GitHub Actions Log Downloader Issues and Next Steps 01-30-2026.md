# GitHub Actions Log Downloader - Issues and Next Steps
**Date:** January 30, 2026
**Session:** Implementation and testing of download_forecast_logs.py
**Status:** Tool implemented but requires fixes before production use

---

## Executive Summary

Successfully implemented a tool to download GitHub Actions workflow logs and extract forecast metadata. The tool runs and completes without errors, but has critical data extraction issues that need to be resolved.

### What Works ✓
- Downloads all workflow run logs from GitHub Actions
- Fetches question titles from Metaculus API when `--fetch-titles` flag is used
- Generates TSV, JSON state file, and summary report
- Proper timezone conversion (UTC → Mountain Time)
- Correct submission detection for runs that have questions
- Sequential downloads with rate limiting

### What Needs Fixing ✗
1. TSV filename needs to include run range (avoid overwrites)
2. Only 1 out of 349 runs has actual question data extracted
3. Only 6 out of 349 log files are non-empty (343 are 0 bytes)

---

## Test Run Results

### Command Executed
```bash
python3 download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --fetch-titles
```

### Output Statistics
- **Total runs downloaded:** 349
- **Date range:** January 20-30, 2026
- **Run number range:** 989 (newest) to 641 (oldest)
- **Total questions processed:** 349 (but only 1 with actual data)
- **Forecasts submitted:** 1
- **Total errors:** 0
- **Total warnings:** 5

### File Locations
All files saved to: `C:\Users\Donni\projects\metac_bot_Spring_2026\logs\`

---

## ISSUE #1: TSV Filename Overwrites

### Problem
The TSV metadata file is always named `forecast_logs_metadata.tsv`, which means:
- Running the tool multiple times overwrites previous results
- Cannot keep separate datasets for different date ranges
- Risk of losing data

### Current Behavior
```
logs/forecast_logs_metadata.tsv  (always the same name)
```

### Required Behavior
```
logs/forecast_logs_metadata_runs_989_to_641.tsv
logs/forecast_logs_metadata_runs_1200_to_1050.tsv
```

### Implementation Location
File: `dre_tools/download_forecast_logs.py`
Method: `LogDownloader.__init__()` and `LogDownloader.generate_tsv()`

**Current code (line ~77):**
```python
self.tsv_file = output_dir / "forecast_logs_metadata.tsv"
```

**Required change:**
- Determine first and last run numbers during download
- Update `self.tsv_file` path before calling `generate_tsv()`
- Format: `forecast_logs_metadata_runs_{highest}_to_{lowest}.tsv`

### Implementation Strategy
1. Add instance variables to track min/max run numbers:
   ```python
   self.min_run_number = None
   self.max_run_number = None
   ```

2. Update these during `process_runs()`:
   ```python
   for run in runs:
       run_number = run['run_number']
       if self.min_run_number is None or run_number < self.min_run_number:
           self.min_run_number = run_number
       if self.max_run_number is None or run_number > self.max_run_number:
           self.max_run_number = run_number
   ```

3. Update TSV filename before generating:
   ```python
   self.tsv_file = output_dir / f"forecast_logs_metadata_runs_{self.max_run_number}_to_{self.min_run_number}.tsv"
   ```

---

## ISSUE #2: Only One Run Has Question Data

### Problem
Out of 349 runs, only run #986 has actual question metadata extracted:
- `question_number`: 41898
- `question_url`: https://www.metaculus.com/questions/41898
- `question_title`: Will SpaceX conduct 2 or more orbital Starship launch attempts before May 1, 2026?
- `forecast_submitted`: Yes

All other 348 runs show:
- `question_number`: None
- `question_url`: None
- `question_title`: None
- `forecast_submitted`: No

### Data Evidence

**Run 986 (the only one with data):**
```
986	2026-01-30 19:51:38 UTC	2026-01-30 12:51:38 MST	41898	https://www.metaculus.com/questions/41898	Yes	0	0	Will SpaceX conduct 2 or more orbital Starship launch attempts before May 1, 2026?
```

**All other runs (example):**
```
989	2026-01-30 21:44:58 UTC	2026-01-30 14:44:58 MST	None	None	No	0	1	None
987	2026-01-30 20:38:54 UTC	2026-01-30 13:38:54 MST	None	None	No	0	1	None
```

### Root Cause Analysis Required

Possible causes to investigate:
1. **Empty log files** - 343 out of 349 logs are 0 bytes (see Issue #3)
2. **URL pattern matching failure** - Regex may not be catching question URLs in most logs
3. **Log format changed** - Recent runs may have different logging format
4. **Bot behavior** - Most runs may not be processing questions (just checking tournaments)

### Investigation Steps for Tomorrow

1. **Check non-empty log files:**
   ```bash
   ls -lh /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs/run_*.log | grep -v " 0 "
   ```
   This will show the 6 non-empty files.

2. **Examine a non-empty log manually:**
   ```bash
   cat /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs/run_986_2026-01-30T19-51-38.log | grep -i "metaculus.com/questions"
   ```

3. **Test URL regex pattern:**
   ```python
   import re
   QUESTION_URL_PATTERN = re.compile(r'(https://www\.metaculus\.com/questions/\d+(?:/[^/\s]+)?)')
   # Test against sample log lines
   ```

4. **Check for "skipped questions" logs:**
   ```bash
   grep -i "skipping\|already forecasted\|no questions" /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs/run_9*.log
   ```

### Hypothesis
Most likely: The empty log files (0 bytes) indicate that the download failed or the workflow runs didn't actually execute. Need to verify:
- Are these runs actually complete in GitHub Actions?
- Did `gh run view --log` fail silently for most runs?
- Are there error messages we're not capturing?

---

## ISSUE #3: 343 of 349 Log Files Are Empty (0 bytes)

### Problem
The tool successfully "downloaded" 349 log files, but:
- **343 files are 0 bytes** (empty)
- **6 files have content** (ranging from 77KB to 174KB)

### File Size Distribution
```
343 files: 0 bytes (empty)
3 files:  78KB
2 files:  77KB
1 file:   174KB
```

### Files to Examine

**The 6 non-empty files (likely):**
```bash
# Find them with:
find /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs -name "run_*.log" -size +1k -ls
```

These files should be examined to understand:
- What's different about these runs?
- Why did download succeed for these but fail for others?
- Are they all from the same date/time period?

### Root Cause Analysis

**Possible causes:**

1. **GitHub API rate limiting:**
   - We're downloading 349 runs sequentially
   - GitHub may have throttled requests
   - Tool doesn't detect/report rate limit errors

2. **Silent gh CLI failures:**
   - Command: `gh run view {run_id} --log`
   - May be failing without raising exceptions
   - Error output not being captured

3. **Incomplete workflow runs:**
   - Many runs may not have completed
   - `gh run view --log` returns empty for incomplete runs
   - Need to filter by `status: completed` before downloading

4. **Timeout issues:**
   - Downloads timing out after certain number
   - Exceptions being caught but not reported

### Code Location to Investigate

File: `dre_tools/download_forecast_logs.py`
Method: `LogDownloader.download_run_log()` (lines ~215-265)

**Current error handling:**
```python
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

if result.returncode != 0:
    if attempt < max_retries - 1:
        print(f"    Retry {attempt + 1}/{max_retries - 1}...")
        time.sleep(2)
        continue
    else:
        print(f"    Error downloading log: {result.stderr}")
        return None
```

**Issues:**
- Returns `None` on failure but continues processing
- Doesn't distinguish between "empty log" and "failed download"
- Saves 0-byte files when download fails

### Fix Strategy

1. **Check subprocess return code and output:**
   ```python
   if result.returncode != 0 or not result.stdout:
       # Log the error and skip this run
       print(f"    Warning: Empty or failed download for run {run_number}")
       return None
   ```

2. **Don't save empty log files:**
   ```python
   if len(result.stdout) == 0:
       print(f"    Warning: Run {run_number} has no log content")
       return None
   ```

3. **Add download validation:**
   ```python
   # After saving file
   if log_path.stat().st_size == 0:
       print(f"    Warning: Downloaded log is empty, removing")
       log_path.unlink()
       return None
   ```

4. **Filter runs before download:**
   ```python
   # In get_workflow_runs(), only return completed runs:
   for run in runs:
       if run.get('status') == 'completed' and run.get('conclusion') in ['success', 'failure']:
           filtered_runs.append(run)
   ```

---

## Successful Implementation Details (For Reference)

### What Was Fixed in This Session

1. ✅ **Path issue resolved** - Uses relative path that works in both WSL and Windows
2. ✅ **Submission detection fixed** - Now detects "Posted comment", "Posted prediction", "Saved full forecast"
3. ✅ **API title fetching implemented** - `--fetch-titles` flag fetches question titles from Metaculus API
4. ✅ **TSV column order optimized** - Question title moved to last column for readability

### Code Changes Made

**File:** `dre_tools/download_forecast_logs.py`

**Key improvements:**
- Added `urllib.request` for API calls
- Added `fetch_question_title()` method to query Metaculus API
- Updated `SUBMISSION_PATTERN` to include: `Posted prediction|Posted comment`
- Updated question pattern to match: `(?:question|post|forecast_summaries/).*{question_number}|\b{question_number}\b`
- Changed default output directory from hardcoded `C:/Users/...` to `Path(__file__).parent.parent / "logs"`

### Working Features

**Metadata extraction correctly handles:**
- Timezone conversion (UTC → Mountain Time with MST/MDT)
- Error counting (ERROR pattern matching)
- Warning counting (WARNING pattern matching)
- Forecast submission detection (multiple patterns)
- Question title fetching from Metaculus API (with rate limiting)
- State tracking for resumable downloads

---

## Next Session Action Plan

### Priority 1: Fix Empty Log Downloads (Critical)

1. **Investigate why 343 logs are empty:**
   - Manually check GitHub Actions for these run IDs
   - Test `gh run view --log` for a few empty runs
   - Check if runs are actually completed

2. **Add better error handling:**
   - Validate subprocess output before saving
   - Don't save empty files
   - Report download failures clearly

3. **Filter runs before download:**
   - Only download completed runs
   - Add status checking in `get_workflow_runs()`

### Priority 2: Fix Question Data Extraction (Critical)

1. **Analyze the 6 non-empty logs:**
   - Identify which runs have content
   - Check if they all have question data
   - Compare with run 986 (known working)

2. **Test URL extraction regex:**
   - Verify pattern matches question URLs in logs
   - Test on sample log content

3. **If most runs genuinely have no questions:**
   - This may be expected behavior
   - Bot may skip already-forecasted questions
   - Document this in README

### Priority 3: Implement Run Range in Filename (Important)

1. **Track min/max run numbers during processing**
2. **Update TSV filename before generation**
3. **Test with multiple downloads to ensure no overwrites**

### Priority 4: Testing and Validation

1. **Test with smaller date range:**
   ```bash
   python3 download_forecast_logs.py --start-date 2026-01-30 --end-date 2026-01-30 --limit 10 --fetch-titles
   ```

2. **Verify all 10 runs download properly**
3. **Check TSV has correct filename with run range**
4. **Ensure only non-empty logs are saved**

### Priority 5: Update Documentation

1. Update `download_forecast_logs_README.md` with:
   - New filename format
   - Expected behavior for runs with no questions
   - Troubleshooting for empty log files

2. Update `SKILL_download_forecast_logs.md`

---

## Code Locations Reference

### Files Modified This Session
- `dre_tools/download_forecast_logs.py` - Main implementation (new file, ~630 lines)
- `dre_tools/download_forecast_logs_README.md` - Documentation (new file)
- `dre_tools/SKILL_download_forecast_logs.md` - Quick reference (new file)

### Key Methods to Modify Tomorrow

**Issue #1 (Filename):**
- `LogDownloader.__init__()` - Line ~72
- `LogDownloader.process_runs()` - Line ~385
- `LogDownloader.generate_tsv()` - Line ~427

**Issue #2 (Data extraction):**
- `LogDownloader.extract_metadata_from_log()` - Line ~287
- `QUESTION_URL_PATTERN` regex - Line ~29

**Issue #3 (Empty logs):**
- `LogDownloader.download_run_log()` - Line ~215
- `LogDownloader.get_workflow_runs()` - Line ~188

---

## Test Data Available

### Current Test Files
```
Location: C:\Users\Donni\projects\metac_bot_Spring_2026\logs\

TSV file: forecast_logs_metadata.tsv (349 rows, only 1 with data)
State:    downloaded_logs_state.json
Report:   download_logs_report.json
Logs:     349 .log files (343 empty, 6 with content)
```

### Known Good Example
**Run 986:**
- Has complete question data
- Log file: `run_986_2026-01-30T19-51-38.log` (77KB or 174KB)
- Question: 41898
- Title: "Will SpaceX conduct 2 or more orbital Starship launch attempts before May 1, 2026?"
- Submission: Yes
- Use this as reference for testing

---

## Questions to Answer Tomorrow

1. **Why are 343 log files empty?**
   - Are these runs incomplete in GitHub Actions?
   - Is `gh run view --log` failing silently?
   - Do we need different filtering criteria?

2. **Should we expect most runs to have no questions?**
   - Is the bot skipping already-forecasted questions?
   - Are these runs just checking tournaments?
   - What's the expected ratio of runs with questions?

3. **What's the correct way to identify runs with questions?**
   - Should we pre-filter based on workflow conclusion?
   - Should we check run duration (quick runs = no questions)?
   - Can we query GitHub API for runs with artifacts?

---

## Success Criteria for Next Session

✅ All downloaded log files have content (no 0-byte files)
✅ TSV filename includes run range: `forecast_logs_metadata_runs_XXX_to_YYY.tsv`
✅ Question data extracted for all runs that processed questions
✅ Clear reporting of which runs had questions vs. which didn't
✅ Tool can be run multiple times without overwriting previous results

---

## Additional Notes

- Tool successfully fetches question titles from Metaculus API
- Rate limiting working correctly (0.3s between API calls)
- Timezone conversion accurate (UTC → MST/MDT)
- Submission detection working for runs that have questions
- State tracking allows resumable downloads with `--skip-existing`

**The core functionality is solid - we just need to fix the data acquisition issues.**

---

## Quick Start for Tomorrow

1. **Navigate to project:**
   ```bash
   cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/dre_tools
   ```

2. **Open main script:**
   ```bash
   code download_forecast_logs.py
   ```

3. **Start with Issue #3 investigation:**
   ```bash
   # Find non-empty logs
   find /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs -name "run_*.log" -size +1k

   # Test gh CLI for a run that has empty log
   gh run view 21531714072 --repo D-Enns/metac-bot-template --log
   ```

4. **Test fix with small sample:**
   ```bash
   # Clean test directory
   rm -rf /mnt/c/Users/Donni/projects/metac_bot_Spring_2026/logs_test

   # Test with 5 runs
   python3 download_forecast_logs.py --start-date 2026-01-30 --end-date 2026-01-30 --limit 5 --output-dir ../logs_test
   ```

---

**End of Document**
