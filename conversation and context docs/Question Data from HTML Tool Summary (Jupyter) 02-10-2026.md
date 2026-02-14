# Question Data from HTML Tool — Summary

**Date:** 2026-02-10
**Tool:** `jupyter/009a_Question_Data_from_HTML_02-10-2026.ipynb`
**Purpose:** Extract question metadata from saved Metaculus tournament HTML pages

---

## What It Does

Parses saved tournament HTML files to extract question-level data and tournament leaderboards.

### Inputs
- Saved HTML files in `data/` directory
- Currently processes: `Spring 2026 AI Forecasting Benchmark Tournament 02-10-2026.html`

### Outputs
- `products/Question_Data_from_HTML_YYYY-MM-DD.csv` (17 columns, 95 rows from Spring tournament)
- `products/Tournament_Leaderboard_YYYY-MM-DD.csv` (8 columns, currently 0 rows - parser not working)

---

## Three Data Sources Extracted

### Source 1 — Question Cards (Visual HTML)
Parses the rendered question cards on the tournament page.

**Extracted fields:**
- `question_number`, `title`, `slug`, `question_type`
- `community_forecast`, `community_range` (for numeric questions)
- `my_forecast`, `my_range` (for numeric questions)
- `status`, `resolution`
- `mc_options` (formatted as "option: value | option: value")
- `forecaster_count`, `comment_count`
- `tournament`

**Question types detected:**
- `binary` — Binary yes/no questions
- `numeric` — Numeric range questions
- `multiple_choice` — MC questions with discrete options
- `group` — Grouped/conditional questions with sub-questions

### Source 2 — "My Score" Table (Embedded Script Data)
Parses Next.js script data containing the tournament score table.

**Extracted fields:**
- `coverage` — 0–100%, how much of question's lifetime had an active forecast
- `score` — Numeric score (only for resolved questions)
- `question_weight` — 0.5 to 1.0

### Source 3 — Tournament Leaderboard (Embedded JSON)
Attempts to parse leaderboard from embedded JSON.

**Status:** Parser not working (0 entries extracted)

---

## Key Findings

### What Works ✓

1. **Tournament name extraction** — Correctly extracts from `<title>` tag
   - Result: "Spring 2026 AI Forecasting Benchmark"

2. **Question identification** — Successfully finds all 95 questions on page 20

3. **Status inference from scores** — Logic added to mark questions as resolved if they have a score
   - 10 questions have scores → all correctly marked as resolved

4. **Community forecasts** — Extracts for binary (69 questions) and numeric questions

5. **Bot forecasts ("me:")** — Extracts for 61 questions where visible on cards

6. **Multiple choice options** — Extracts top options with probabilities or Yes/No resolution markers

7. **Coverage and scores** — Successfully extracts from script data (77 with coverage, 10 with scores)

### What Doesn't Work ✗

1. **Resolution values** — Only 6 of 13 resolved questions have resolution data
   - **Issue:** Group questions and some others don't show resolution on tournament listing cards
   - **Missing examples:** Q41521, Q41835, Q41839, Q41892 (all group questions with scores but no resolution text)

2. **Forecaster counts** — All empty despite regex attempts
   - **Issue:** HTML structure doesn't match expected patterns

3. **Comment counts** — All empty
   - **Issue:** HTML structure doesn't match expected patterns

4. **Leaderboard** — Parser extracts 0 entries
   - **Issue:** Regex pattern not matching the embedded JSON structure

5. **Bot forecasts for MC questions** — Not shown on tournament listing cards
   - Per-option bot forecasts would need individual question pages or API

6. **Group question details** — Show only sparklines, no extractable data on cards

---

## Data Quality Assessment

**95 questions on page 20 of Spring tournament:**

| Field | Count | Notes |
|---|---|---|
| Tournament name | 95 | ✓ All correct |
| Question type | 95 | ✓ 31 binary, 38 numeric, 8 MC, 18 group |
| Status | 95 | ✓ 13 resolved, 1 annulled, 2 pending_reveal, 79 open |
| Resolution | 6 | ✗ Missing for 7 resolved questions (group Qs) |
| Community forecast | 69 | ✓ Binary and numeric only |
| My forecast | 61 | ~ Visible on some cards, not others |
| MC options | 8 | ✓ All MC questions |
| Coverage | 77 | ✓ From script data |
| Score | 10 | ✓ All resolved questions we forecast on |
| Forecaster count | 0 | ✗ Parser not working |
| Comment count | 0 | ✗ Parser not working |

---

## Important Limitations

### 1. Status Field Reliability
**The `status` field from card HTML is NOT reliable.**

- Group questions often don't show "Resolved" text on their cards
- We infer resolved status by checking if `score` field exists
- This is a workaround, not authoritative data

### 2. Incomplete Tournament Coverage
**The HTML file contains only page 20 of the Spring tournament.**

From run-question map comparison:
- 66 questions appear in both HTML and run logs
- 79 questions are in run logs only (from MiniBench or other tournament)
- 29 questions are in HTML only (bot never forecast on these)

To get complete data, need to save additional tournament pages.

### 3. HTML Parsing is Fragile
**Regex-based parsing breaks when HTML structure changes.**

- Patterns are brittle and depend on exact CSS classes
- Next.js updates could break the parsers
- No guarantees of long-term stability

---

## Fixes Applied in 009a

**From 009 → 009a:**

1. **Tournament name** — Now extracts from `<title>` and removes "| Metaculus" suffix
2. **Status/score alignment** — Added logic: `if score exists and status=='open', set status='resolved'`
3. **Forecaster/comment counts** — Broadened regex search with case-insensitive matching (still doesn't work)

---

## Next Steps

### Immediate
**Investigate Metaculus API** before further HTML parsing work.

The API should provide:
- ✓ Authoritative question status and resolution values
- ✓ Forecaster counts, comment counts
- ✓ Question metadata (type, title, dates)
- ✓ Tournament membership
- ✓ Bot forecast history
- ✓ More reliable than HTML scraping

### If Continuing with HTML Parsing
1. Debug forecaster/comment count patterns with actual HTML samples
2. Fix leaderboard parser
3. Save MiniBench tournament HTML
4. Consider saving all pages of Spring tournament (not just page 20)

### Alternative Approach
Convert notebook to standalone Python script in `dre_tools/` if we plan to:
- Run regularly to update question data
- Make it a reusable tool with SKILL file
- Integrate with other bot workflows

---

## Files

| File | Description |
|---|---|
| `jupyter/009_Question_Data_from_HTML_02-10-2026.ipynb` | Initial version |
| `jupyter/009a_Question_Data_from_HTML_02-10-2026.ipynb` | Current version with fixes |
| `data/Spring 2026 AI Forecasting Benchmark Tournament 02-10-2026.html` | Input HTML (4.2 MB, page 20) |
| `products/Question_Data_from_HTML_2026-02-10.csv` | Latest output (95 questions) |
| `products/Tournament_Leaderboard_2026-02-10.csv` | Latest output (0 entries) |

---

## Related Documentation

- **Session notes:** `Question Data from HTML Session 02-10-2026.md`
- **Project plan:** `Run Question Map and Tournament HTML Plan 02-09-2026.md`
- **Predecessor:** `Run Question Map Session 02-09-2026.md` (008 series notebooks)
