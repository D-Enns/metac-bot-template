# SKILL: Consolidate Forecast Files

**Tool**: `consolidate_forecasts.py`
**Purpose**: Merge all forecast files from run_* subdirectories into a single consolidated folder, removing duplicates
**Category**: Data Management & Organization
**Created**: January 27, 2026

---

## Quick Start

```bash
# Navigate to project root
cd /mnt/c/Users/Donni/projects/metac_bot_Spring_2026

# Run consolidation
python3 dre_tools/consolidate_forecasts.py
```

**Result**: All unique forecast files will be in `forecast_summaries/consolidated/`

---

## When to Use This Tool

### Use Cases
1. **After downloading artifacts** - Organize downloaded files for easy access
2. **Remove duplicates** - Clean up redundant copies across multiple runs
3. **Before analysis** - Prepare a clean dataset with one copy of each file
4. **Storage optimization** - Reduce disk usage by ~95%
5. **Simplify access** - Work with all files in one location

### Signs You Need This Tool
- You have hundreds of `run_*` subdirectories
- Same files repeated across multiple runs
- Hard to find specific forecast files
- Need to analyze all unique forecasts
- Want to reduce storage usage

---

## What It Does

### Process Overview
1. **Scans** all `run_*` subdirectories in `forecast_summaries/`
2. **Identifies** unique files based on filename AND content hash (MD5)
3. **Copies** unique files to `forecast_summaries/consolidated/`
4. **Skips** true duplicates (same content)
5. **Handles** same filename with different content (renames with run number)
6. **Reports** statistics on files processed

### Duplicate Detection
- **True duplicates**: Same filename + same content hash → Skip
- **Different versions**: Same filename + different content → Rename as `filename_runXXX.ext`

This ensures you never lose data even if the same question was forecast multiple times with different results.

---

## Output Structure

### Before Consolidation
```
forecast_summaries/
├── run_410/
│   ├── 41871_spring_aib_2026_full_1.md
│   ├── 41871_spring_aib_2026_condensed_1.md
│   └── ...
├── run_411/
│   ├── 41871_spring_aib_2026_full_1.md  ← Duplicate
│   └── ...
├── run_412/
├── ... (497 more directories)
└── run_909/
```

### After Consolidation
```
forecast_summaries/
├── consolidated/                    ← New! All unique files here
│   ├── 14333_unknown_full_1.md
│   ├── 14333_unknown_full_2.md
│   ├── 41871_spring_aib_2026_full_1.md
│   ├── 41871_spring_aib_2026_condensed_1.md
│   ├── 41871_spring_aib_2026_scenarios_1.json
│   └── [230 more unique files...]
├── run_410/ to run_909/            ← Original (can be deleted)
├── download_report.json
└── downloaded_artifacts_log.json
```

---

## Console Output

### During Consolidation
```
================================================================================
FORECAST FILE CONSOLIDATION
================================================================================

Source: /path/to/forecast_summaries
Target: /path/to/forecast_summaries/consolidated

Processing run_* subdirectories...
--------------------------------------------------------------------------------
Found 499 run directories to process

Processing 1/499...
Processing 51/499...
Processing 101/499...
...
```

### Summary Report
```
================================================================================
CONSOLIDATION SUMMARY
================================================================================

📊 Statistics:
  Total files found: 5581
  ✓ Unique files copied: 235
  ⊙ Duplicates skipped: 5346
  ❌ Errors: 0

📁 Files in consolidated directory:
  Full summaries: 80
  Condensed summaries: 78
  Scenario JSONs: 75
  Other files: 2

📝 Unique questions: 79
  Question IDs: 14333, 41379, 41384, ...

💾 Total size: 6.7 MB

✅ Consolidation complete!
   Files are in: /path/to/forecast_summaries/consolidated
```

---

## Understanding the Output

### Statistics Breakdown

**Total files found**: All files discovered across all `run_*` directories
- Includes duplicates, hidden files, etc.

**Unique files copied**: Files with unique content copied to consolidated folder
- Based on content hash, not just filename

**Duplicates skipped**: Files that were exact duplicates (same content)
- Typical: 95%+ of files are duplicates across runs
- This is normal - same forecasts downloaded multiple times

**Errors**: Files that couldn't be copied
- Should be 0 in normal operation

### File Type Counts

**Full summaries** (`*_full_*.md`):
- Complete forecast analysis
- Typically 50-80 KB each
- Contains all research, scenarios, reasoning

**Condensed summaries** (`*_condensed_*.md`):
- Shorter version posted to Metaculus
- Typically 4-5 KB each
- Key insights only

**Scenario JSONs** (`*_scenarios_*.json`):
- Structured data of forecast scenarios
- Typically 1-5 KB each
- Available for forecasts after ~Jan 6, 2026

**Other files**:
- Example files
- Documentation
- Should be minimal

### Unique Questions
- Count of distinct Metaculus questions with forecast data
- Based on question ID extracted from filenames

---

## Common Workflows

### Workflow 1: After Downloading Artifacts

**Goal**: Organize newly downloaded forecast data

```bash
# Download latest artifacts
python3 dre_tools/download_all_forecast_artifacts.py --limit 500

# Consolidate into single folder
python3 dre_tools/consolidate_forecasts.py

# Access consolidated files
ls forecast_summaries/consolidated/

# Optional: Remove run_* directories to save space
# (Only do this after verifying consolidated/ has everything!)
# rm -rf forecast_summaries/run_*/
```

### Workflow 2: Re-consolidate After New Downloads

**Goal**: Update consolidated folder with new data

```bash
# Download new runs
python3 dre_tools/download_all_forecast_artifacts.py --limit 100

# Delete old consolidated folder (it will be recreated)
rm -rf forecast_summaries/consolidated/

# Reconsolidate everything
python3 dre_tools/consolidate_forecasts.py
```

**Note**: The script recreates the consolidated folder from scratch each time, so delete it first if you want to ensure a clean rebuild.

### Workflow 3: Verify Consolidation

**Goal**: Check that consolidation worked correctly

```bash
# Run consolidation
python3 dre_tools/consolidate_forecasts.py

# Count files in consolidated
ls forecast_summaries/consolidated/ | wc -l

# List by type
echo "Full summaries:"
ls forecast_summaries/consolidated/*_full_*.md | wc -l
echo "Condensed summaries:"
ls forecast_summaries/consolidated/*_condensed_*.md | wc -l
echo "Scenario JSONs:"
ls forecast_summaries/consolidated/*_scenarios_*.json | wc -l

# Check total size
du -sh forecast_summaries/consolidated/
```

### Workflow 4: Extract Specific Questions

**Goal**: Work with forecasts for specific questions

```bash
# Consolidate first
python3 dre_tools/consolidate_forecasts.py

# Find all files for a specific question
cd forecast_summaries/consolidated
ls 41871_*

# Copy to separate folder for analysis
mkdir ../../analysis/
cp 41871_* ../../analysis/
```

---

## Space Savings

### Typical Results

**Before consolidation**:
- 499 run directories
- 5,581 total files
- 419 MB total size

**After consolidation**:
- 1 consolidated directory
- 235 unique files
- 6.7 MB total size

**Savings**: ~98% reduction in storage!

**Why so many duplicates?**
- Bot runs every 20 minutes
- Most questions don't get new forecasts each run
- Same files downloaded repeatedly across runs
- This is normal and expected behavior

---

## File Verification

### Ensure No Data Loss

The consolidation script uses **content hashing** (MD5) to detect duplicates:

```python
# Two files are duplicates if:
1. Same filename AND
2. Same content hash (MD5)

# If filename is same but content differs:
→ Both versions are kept with run number suffix
```

**Example**:
- `run_500/41871_full_1.md` (original)
- `run_600/41871_full_1.md` (different content)
- Result: Both saved as `41871_full_1.md` and `41871_full_1_run600.md`

### Manual Verification

```bash
# Check for renamed files (rare)
cd forecast_summaries/consolidated
ls *_run*.md *_run*.json

# Compare with original run count
ls -d ../run_*/ | wc -l
ls *.md *.json | wc -l
```

---

## Cleanup After Consolidation

### When to Delete run_* Directories

✅ **Safe to delete when**:
1. Consolidation completed successfully (0 errors)
2. Consolidated folder has expected file count
3. You've verified key files exist in consolidated/
4. You've backed up important data elsewhere

❌ **Don't delete if**:
- Any errors during consolidation
- You haven't verified the output
- You need to track which run produced which file
- You want to preserve download history

### How to Clean Up

```bash
# Option 1: Delete all run_* directories (saves ~400 MB)
cd forecast_summaries
rm -rf run_*/

# Option 2: Keep most recent run for reference
rm -rf run_{410..908}/
# Keeps run_909/ (most recent)

# Option 3: Archive before deleting
tar -czf run_archives_$(date +%Y%m%d).tar.gz run_*/
rm -rf run_*/
```

**Recommendation**: Keep the run_* directories for at least a week after consolidation, then delete once you've verified everything works.

---

## Integration with Analysis Tools

### Loading Consolidated Files

```python
from pathlib import Path

# Access consolidated files
consolidated_dir = Path("forecast_summaries/consolidated")

# Get all full summaries
full_summaries = sorted(consolidated_dir.glob("*_full_*.md"))
print(f"Found {len(full_summaries)} full summaries")

# Get all files for a specific question
question_files = consolidated_dir.glob("41871_*")
for f in question_files:
    print(f"  {f.name}")
```

### Creating Analysis Dataset

```python
import json
import re
from pathlib import Path

consolidated_dir = Path("forecast_summaries/consolidated")

# Build dataset of all forecasts
forecasts = []

for file in consolidated_dir.glob("*_full_*.md"):
    # Extract question ID
    qid = file.name.split('_')[0]

    # Read content
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse metadata
    metadata = {}
    for line in content.split('\n'):
        if match := re.match(r'\*\*(.+?)\*\*:\s*(.+)', line):
            metadata[match.group(1)] = match.group(2)

    forecasts.append({
        'question_id': qid,
        'file': file.name,
        'metadata': metadata
    })

print(f"Processed {len(forecasts)} forecasts")
```

---

## Troubleshooting

### Issue: "No run_* directories found"

**Cause**: Running from wrong directory or no downloads yet

**Solution**:
```bash
# Verify you're in the right directory
pwd
# Should be: /path/to/metac_bot_Spring_2026

# Check if run directories exist
ls forecast_summaries/run_*/

# If empty, download artifacts first
python3 dre_tools/download_all_forecast_artifacts.py --limit 100
```

### Issue: "consolidated folder already exists"

**Cause**: Previous consolidation run

**Solution**:
```bash
# The script will add to existing consolidated folder
# To start fresh, delete it first:
rm -rf forecast_summaries/consolidated/
python3 dre_tools/consolidate_forecasts.py
```

### Issue: Fewer files than expected

**Cause**: Many duplicates are normal

**Check**:
```bash
# Count total files across all runs
find forecast_summaries/run_*/ -type f | wc -l

# Count unique files
ls forecast_summaries/consolidated/ | wc -l

# This is normal - 95%+ duplicates is expected!
```

### Issue: Different content warning

**Output**:
```
⚠️ Different content for 41871_full_1.md, saving as 41871_full_1_run600.md
```

**Meaning**: Same question was forecast multiple times with different results

**Action**: This is normal if:
- Question was updated on Metaculus
- Bot logic changed between runs
- Aggregation method changed (GPR → Probit)
- No action needed - both versions are preserved

---

## Best Practices

### 1. Always Consolidate After Downloading

```bash
# Good workflow
python3 dre_tools/download_all_forecast_artifacts.py --limit 500
python3 dre_tools/consolidate_forecasts.py
```

### 2. Verify Before Deleting

```bash
# Check consolidation worked
ls forecast_summaries/consolidated/ | wc -l

# Compare with expected (unique questions × 2-3 files per question)
# Example: 79 questions × 3 files ≈ 235 files ✓
```

### 3. Keep Consolidated Folder Updated

```bash
# When downloading new data, reconsolidate:
rm -rf forecast_summaries/consolidated/
python3 dre_tools/consolidate_forecasts.py
```

### 4. Backup Before Bulk Operations

```bash
# Before deleting run_* directories:
cd forecast_summaries
tar -czf ../forecast_backup_$(date +%Y%m%d).tar.gz consolidated/
```

### 5. Use Consolidated for Analysis

Always work from `consolidated/` folder, not `run_*/` directories:
- ✅ Faster (fewer files)
- ✅ No duplicates
- ✅ Easier to navigate
- ✅ Smaller storage footprint

---

## Command Reference

### Basic Commands

```bash
# Run consolidation
python3 dre_tools/consolidate_forecasts.py

# View results
ls -lh forecast_summaries/consolidated/

# Count files by type
ls forecast_summaries/consolidated/*_full_*.md | wc -l
ls forecast_summaries/consolidated/*_condensed_*.md | wc -l
ls forecast_summaries/consolidated/*_scenarios_*.json | wc -l

# Check total size
du -sh forecast_summaries/consolidated/

# List unique questions
ls forecast_summaries/consolidated/*.md | sed 's/.*\/\([0-9]*\)_.*/\1/' | sort -u
```

### Cleanup Commands

```bash
# Delete run directories (after verifying consolidated/)
rm -rf forecast_summaries/run_*/

# Archive before deleting
tar -czf forecast_runs_archive.tar.gz forecast_summaries/run_*/
rm -rf forecast_summaries/run_*/

# Reset and reconsolidate
rm -rf forecast_summaries/consolidated/
python3 dre_tools/consolidate_forecasts.py
```

---

## Performance

### Typical Run Time
- **499 runs, 5,581 files**: ~30-60 seconds
- **100 runs, ~1,000 files**: ~10 seconds

### Memory Usage
- Minimal (only hashes small chunks at a time)
- Safe for large datasets (10,000+ files)

### Disk I/O
- Read: All source files (for hashing)
- Write: Only unique files
- Efficient: ~98% reduction in writes due to deduplication

---

## Related Files

- `consolidate_forecasts.py` - Main consolidation script
- `download_all_forecast_artifacts.py` - Downloads source data
- `SKILL_download_all_forecast_artifacts.md` - Download documentation

---

## Quick Reference Card

```bash
# Most Common Commands

# After downloading artifacts
python3 dre_tools/download_all_forecast_artifacts.py --limit 500
python3 dre_tools/consolidate_forecasts.py

# Reconsolidate (e.g., after new downloads)
rm -rf forecast_summaries/consolidated/
python3 dre_tools/consolidate_forecasts.py

# View consolidated files
ls forecast_summaries/consolidated/

# Count unique questions
ls forecast_summaries/consolidated/*.md | \
  sed 's/.*\/\([0-9]*\)_.*/\1/' | sort -u | wc -l

# Clean up run directories (after verification!)
rm -rf forecast_summaries/run_*/
```

---

## Success Metrics

After consolidation, you should see:

✅ **Consolidation Success**:
- `✓ Unique files copied: X` where X is ~2-3× number of unique questions
- `⊙ Duplicates skipped: Y` where Y is 90-98% of total files
- `❌ Errors: 0`

✅ **File Organization**:
- All files in single `consolidated/` directory
- ~80 full summaries, ~80 condensed, ~75 scenarios for 79 questions
- Total size: 5-10 MB (down from 400+ MB)

✅ **Data Integrity**:
- File count matches expected: questions × ~3 files per question
- No renamed files (or very few) - indicates consistent forecasts
- All question IDs present in filename listing

---

**Last Updated**: January 27, 2026
**Version**: 1.0
**Maintainer**: Dre + Claude
**Status**: Production Ready ✅
