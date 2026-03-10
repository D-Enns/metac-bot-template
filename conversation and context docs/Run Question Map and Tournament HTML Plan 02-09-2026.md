# Plan: Run-Question Map & Tournament HTML Parsing

**Date:** 2026-02-09
**Status:** In Progress
**Starting Notebook:** 008a (full run in progress)

---

## Goal

Build a comprehensive dataset mapping workflow runs to Metaculus questions, enriched with question metadata (names, types) from the tournament page.

---

## Completed

### 008 — Minimal Run→Question Map
- Ultra-minimal notebook: fetch runs, download logs, extract question numbers
- Output: `Run_Question_Map_2026-02-09.csv` (two columns: run number, question number)
- Tested with 20 runs, then 200 runs (43 questions found)

### 008a — Full Run + Target Run CSVs
- TEST_LIMIT = None (all ~1247 runs)
- Two outputs: full CSV + optional Target CSV for specific run numbers
- Currently running (~30-40 min estimated)

---

## Next Steps (Incremental)

### Step 1: Parse Tournament HTML (next session — 008b)
**Priority: HIGH — explore what data is available before planning further**

- Manually save tournament page HTML from browser
  - URL: `https://www.metaculus.com/tournament/spring-aib-2026/`
  - Multiple pages may be needed (page=1, page=2, ... page=20)
  - Save to `jupyter/Data/` or `products/`
- Create notebook 008b to parse the saved HTML
- Extract whatever is available: question names, question numbers, question types, open/close dates, etc.
- Output: CSV with question metadata

**Key question:** How many pages need to be saved? What data is in the HTML vs loaded by JavaScript?

### Step 2: Add Time-Date and Question Type (008c)
- Only process runs that have questions (from 008a's CSV)
- Re-download logs for just those ~60-80 runs (much faster than all 1247)
- Extract timestamp and question type using patterns from 007f
- Merge with question names from Step 1
- Output: enriched CSV

### Step 3: Switch to Excel (008d, when ready)
- Switch from CSV to Excel when we need:
  - Multiple sheets (summary + raw data)
  - Column formatting (widths, bold headers)
  - Sharing with others
- Not needed yet — CSV is fine during incremental build

---

## Design Principles

1. **Only work with question-runs** — skip the ~90% of runs with no questions
2. **Build incrementally** — each notebook adds one capability
3. **Question metadata from tournament HTML** — not from logs or API calls
4. **CSV until Excel is needed** — keep it simple

---

## Open Questions

- How many tournament pages need to be saved? (currently browsing page=20)
- Does the HTML contain question type, or just name + number?
- Will JavaScript-rendered content be in the saved HTML or missing?
- Should the target CSV feature carry forward to future notebooks?

---

## File Naming

- `008_Run_Question_Number_Map_02-09-2026.ipynb` — original minimal version
- `008a_...` — full run + target CSVs
- `008b_...` — tournament HTML parsing
- `008c_...` — time-date + question type from logs
- `008d_...` — Excel output (if needed)
