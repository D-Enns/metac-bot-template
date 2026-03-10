# Metaculus API with Authentication - Session Summary

**Date:** 2026-02-11
**Status:** Paused at authentication setup
**Goal:** Extract bot's personal forecasts and scores from Metaculus API

---

## What We Accomplished

### 1. Created Three Notebook Versions

**010 - Initial API extraction** (had rate limit issues)
- Fetched question data from Metaculus API
- Hit 429 rate limit errors after ~10 questions

**010a - Fixed rate limiting**
- Increased delay to 2 seconds between requests
- Added exponential backoff retry logic
- Added progress saves every 25 questions
- ✅ Successfully fetched all 193 questions

**010b - Fixed score extraction**
- **Problem discovered:** Score columns were all empty
- **Root cause:** Scores at `question.aggregations.unweighted.score_data`, not `aggregations.unweighted.latest.score_data`
- ✅ Fixed extraction path for community scores

**010c - Added authentication** ⭐ CURRENT VERSION
- Added support for `METACULUS_BOT_API_TOKEN`
- Extracts bot's personal forecasts and scores:
  - `my_latest_forecast`, `my_coverage`, `my_peer_score`, `my_baseline_score`
- Renamed community fields for clarity: `community_coverage`, `community_peer_score`, etc.
- Falls back gracefully if no token provided

### 2. Files Created

| File | Purpose |
|------|---------|
| `jupyter/010_Question_Data_from_API_02-11-2026.ipynb` | Initial version (has rate limit issues) |
| `jupyter/010a_Question_Data_from_API_02-11-2026.ipynb` | Fixed rate limiting ✅ |
| `jupyter/010b_Question_Data_from_API_02-11-2026.ipynb` | Fixed score extraction ✅ |
| `jupyter/010c_Question_Data_from_API_02-11-2026.ipynb` | **With authentication** ⭐ |
| `products/Question_Data_from_API_2026-02-11_test.csv` | Test output (no scores - from 010/010a) |

### 3. What We Learned

**Community Scores (from API):**
- Located at: `question.aggregations.unweighted.score_data`
- Shows how well the community predicted each question
- Fields: `coverage`, `peer_score`, `baseline_score`, `spot_peer_score`, `spot_baseline_score`

**Bot's Personal Scores (requires auth):**
- Located at: `question.my_forecasts.score_data`
- Shows how well YOUR bot performed on each question
- Same score fields as community, plus `my_latest_forecast`

---

## WHERE WE STOPPED

**Issue:** `METACULUS_BOT_API_TOKEN` not visible to Jupyter

User set the token in Windows environment, but Jupyter shows:
```
Authentication: ❌ No token - will fetch public data only
```

**Possible causes:**
1. Jupyter was already running when token was set (needs restart)
2. Token set in wrong scope (needs system variable, not just user)
3. Variable name mismatch
4. Jupyter can't see Windows env vars (unlikely if running Jupyter on Windows)

---

## NEXT STEPS (Resume Here Tomorrow)

### Step 1: Check what Jupyter can see

Add this cell to notebook 010c (after cell 2):
```python
import os
print("Environment variables with 'METACULUS' or 'TOKEN':")
for key, value in os.environ.items():
    if 'METACULUS' in key.upper() or 'TOKEN' in key.upper():
        print(f"{key}: {value[:20]}..." if len(value) > 20 else f"{key}: {value}")
```

Run it to see what environment variables are visible.

### Step 2: Set token directly in notebook (if env var not working)

In cell 2 of `010c`, change:
```python
METACULUS_TOKEN = os.getenv('METACULUS_BOT_API_TOKEN')
```

To:
```python
METACULUS_TOKEN = 'paste_your_actual_token_here'  # Set directly
```

### Step 3: Test with 5 questions

Run notebook 010c with `TEST_LIMIT = 5`:
- Should show "Authentication: ✅ Token found"
- Output should show "my:✓" for questions where bot has forecasts
- Check the test output to see if `my_coverage`, `my_peer_score` fields are populated

### Step 4: If test works, run full batch

Set `TEST_LIMIT = None` and run all cells:
- Will fetch all 193 questions (~7 minutes at 2s per question)
- Output: `products/Question_Data_from_API_2026-02-11_vNN.csv`
- Should have BOTH community scores AND bot's personal scores

---

## Key Files for Reference

**Input:**
- `products/Run_Question_Map_2026-02-10_v01.csv` - 193 unique questions

**Notebook:**
- `jupyter/010c_Question_Data_from_API_02-11-2026.ipynb` ⭐ USE THIS

**Expected Output:**
- `products/Question_Data_from_API_2026-02-11_v01.csv` (or higher version)

---

## Quick Reference: What Each Notebook Does

| Notebook | Rate Limit | Scores | Auth | Status |
|----------|------------|--------|------|--------|
| 010      | ❌ 0.5s (too fast) | ❌ Empty | ❌ No | Don't use |
| 010a     | ✅ 2s + retry | ❌ Empty | ❌ No | Use for public data only |
| 010b     | ✅ 2s + retry | ✅ Community only | ❌ No | Use for community scores |
| 010c     | ✅ 2s + retry | ✅ Community + Bot | ✅ Yes | **USE THIS** ⭐ |

---

## Data Schema (010c Output)

**45+ columns including:**

**Basic Info:** question_id, title, short_title, question_type, status, resolved, resolution

**Counts:** nr_forecasters, comment_count, forecasts_count

**Tournament:** tournament_id, tournament_name, tournament_slug, question_weight

**Community Data:**
- `community_forecast`, `community_forecast_mean`
- `community_coverage`, `community_peer_score`, `community_baseline_score`
- `community_spot_peer_score`, `community_spot_baseline_score`

**Bot's Personal Data (requires auth):**
- `my_latest_forecast`, `my_latest_forecast_time`
- `my_coverage`, `my_peer_score`, `my_baseline_score`
- `my_spot_peer_score`, `my_spot_baseline_score`

**Type-specific:** mc_options, numeric_range_min/max, open_upper_bound, open_lower_bound

**Dates:** created_at, published_at, open_time, close_time, resolve_time, etc.

**Full text:** description, resolution_criteria, fine_print

---

## Related Documentation

- **Plan:** `Metaculus API Question Data Extraction Plan 02-10-2026.md`
- **HTML parsing (for comparison):** `Question Data from HTML Tool Summary (Jupyter) 02-10-2026.md`
- **Run mapping:** `Run Question Map Session 02-09-2026.md`
- **Notebook 007f:** Full run log extraction with forecasts

---

## Questions/Decisions for Tomorrow

1. **Token visibility** - Why isn't Jupyter seeing the Windows env var?
2. **Token validity** - User said "I'm not positive it is the latest" - might need to refresh from Metaculus
3. **Full run** - Once auth works, do we run for all 193 questions or a larger test batch first?
4. **Next analysis** - What do we do with the data once we have bot scores? Comparison to community? Performance analysis?
