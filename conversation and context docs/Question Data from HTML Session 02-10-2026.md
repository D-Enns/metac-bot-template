# Question Data from HTML — Session Summary

**Date:** 2026-02-10
**Session Type:** Research + notebook development
**Continuation of:** Run Question Map Session 02-09-2026

---

## What We Did

### 1. Verified 008a Full Run Results

The full run of `008a_Run_Question_Number_Map_02-09-2026.ipynb` completed overnight:
- **1,247 total runs** processed
- **147 runs** had questions
- **145 unique questions** found (range Q41435–Q42077)
- Output: `products/Run_Question_Map_2026-02-09_v02.csv`

The user was re-running 008a during this session to produce an updated map.

### 2. Explored Saved Tournament HTML

Analyzed the saved HTML file:
- `data/Spring 2026 AI Forecasting Benchmark Tournament 02-10-2026.html` (4.2 MB)
- `data/Spring 2026 AI Forecasting Benchmark Tournament_files 02-10-2026.html/` (companion directory of CSS/JS assets — not used)

The HTML is from **page 20** of the tournament (`?order_by=-open_time&page=20`). It contains **95 unique questions**, all from the Spring tournament.

### 3. Compared HTML Questions vs Run-Log Questions

- **66 questions** appear in both the HTML and the run-log CSV
- **79 questions** are in the CSV only — these come from a **second tournament** (MiniBench or similar)
- **29 questions** are in the HTML only — the bot never forecasted on these

### 4. Discovered Three Data Sources in the HTML

#### Source 1 — Question Cards (visual HTML)
Each question renders as a card with an `<h4>` title. Parsing approach:
- Find each `<h4>`, look backward for `/questions/NNNNN/slug` URL
- Look forward for forecast data, status, MC options

**Fields extracted:**
| Field | Binary | Numeric | Multiple Choice | Group |
|---|---|---|---|---|
| title, slug, qnum | ✓ | ✓ | ✓ | ✓ |
| community_forecast | NN% chance | median (IQR) | top 3 options + % | ✗ (sparkline only) |
| my_forecast ("me:") | NN.N% | median (IQR) | **not on card** | ✗ |
| status/resolution | Yes/No | — | winning option | — |
| forecaster_count | ✓ | ✓ | ✓ | ✓ |

**Key HTML patterns:**
- Binary community: `font-bold text-xl` → `NN%` + `chance`
- Numeric community: `font-bold md:text-base` → value + `(range)`
- "me:" forecast: `me: <span class="font-bold">VALUE</span>`
- MC options (open): `class="resize-label min-w-0 flex-1"` → name, `class="resize-label flex-shrink-0"` → %
- MC options (resolved): same name div, then `class="whitespace-pre text-right"` → Yes/No
- MC tile marker: `class="MultipleChoiceTile"`
- Resolved binary: `Resolved</span>` then `purple-800` → Yes/No
- Annulled: text `Annulled` in gray-700
- Pending reveal: `Revealed <relative-time>` with `<template>` containing "in X hours"

**Question type detection:**
- `MultipleChoiceTile` in first 500 chars after h4 → multiple_choice
- Binary gauge pattern → binary
- Numeric bold+range pattern → numeric
- None of the above → group (grouped/conditional questions with sub-questions)

#### Source 2 — "My Score" Table (embedded Next.js script data)
Hidden in `<script>self.__next_f.push(...)` tags. Contains a table titled "My Score" with columns:
- **Question** (title + `/questions/NNNNN` link)
- **Coverage** — 0–100% (how much of the question's life the bot had an active forecast)
- **Score** — numeric score, only populated for resolved questions (positive = good, negative = bad)
- **Question Weight** — 0.5, 0.7, 0.8, or 1.0

All 95 questions have rows. 10 have scores (resolved), 77 have coverage but no score (open), 18 have no coverage (not forecast on).

**Parsing approach:** Find scripts containing `/questions/`, unescape `\"` → `"` and `\/` → `/`, then regex for `"href":"/questions/NNNNN"` followed by `"children":"VALUE"` triplets.

#### Source 3 — Tournament Leaderboard (embedded JSON)
A large JSON blob (~32K chars) in one script tag, containing:
- Tournament metadata (id, project_id, score_type `spot_peer_tournament`, prize_pool $50,000)
- Leaderboard entries with: username, is_bot, score, rank, excluded, coverage, contribution_count, prize

The bot (`metac-claude-opus-4-5-high-32k+asknews`) was **rank 1** with score **222.08** at time of HTML save.

### 5. Built Notebook 009

Created `jupyter/009_Question_Data_from_HTML_02-10-2026.ipynb` with 11 cells:

| Cell | Purpose |
|---|---|
| Markdown | Overview of all three data sources |
| Config | Imports, DATA_DIR, OUTPUT_DIR, HTML_FILES list |
| Source 1 | `extract_tournament_name()`, `parse_mc_options()`, `parse_question_cards()` |
| Source 2 | `parse_my_score_table()` |
| Source 3 | `parse_leaderboard()` |
| Process | Runs all parsers on each HTML file |
| Merge | Combines Sources 1 & 2, prints summary stats |
| Display All | Full question table with all fields |
| Display MC | Multiple choice detail with per-option breakdowns |
| Display Resolved | Resolved/annulled questions with scores |
| Display Leaderboard | Top 30 entries |
| Write CSVs | Two output files |

**Outputs:**
- `products/Question_Data_from_HTML_YYYY-MM-DD.csv` — 17 columns, 95 rows (per HTML file)
- `products/Tournament_Leaderboard_YYYY-MM-DD.csv` — 8 columns

**Dependencies:** Python stdlib only (re, csv, json, html, pathlib, datetime)

**Status:** Written but not yet run by the user.

---

## Key Findings

1. **MC "me:" forecasts are NOT in the tournament listing HTML** — the card only shows community options. Per-option bot forecasts would need to come from run logs or individual question pages.

2. **Grouped/conditional questions** (Q41454, Q41458, Q41468, Q41472, Q41537, Q41538, Q41540, Q41838) show only a sparkline chart — no extractable text data. These are multi-part questions with sub-questions.

3. **The HTML contains only page 20 of the Spring tournament.** The 79 questions from the second tournament (MiniBench) are not covered. A saved HTML from that tournament page is needed.

4. **The "My Score" table in the scripts is a rich data source** — it has coverage and weight for every question, and actual numeric scores for resolved ones, including some that the card-level parser can't extract (e.g., grouped questions).

5. **Resolved MC questions show the winner** via Yes/No labels per option, not probabilities. The score from the My Score table is available for these.

---

## Files Created/Modified

| File | Description |
|---|---|
| `jupyter/009_Question_Data_from_HTML_02-10-2026.ipynb` | Main notebook — parses all 3 data sources |
| `conversation and context docs/Question Data from HTML Session 02-10-2026.md` | This file |

---

## Next Steps

### Immediate
1. **Run notebook 009** — verify it works end-to-end on the Spring tournament HTML
2. **Save the MiniBench tournament HTML** from the browser and add it to `HTML_FILES` in the notebook
3. **Check the updated 008a run** — the user was re-running the run-question mapper during this session

### Future (from the incremental plan)
4. **009a** — Merge 009 output with 008a run-question map to associate question metadata with workflow runs
5. **Step 2 from plan (008c equivalent)** — Re-download logs for just the ~147 question-runs to extract timestamps and question types from the logs
6. **Switch to Excel** when formatting/sharing needs arise

### Open Questions
- What is the exact name/URL of the second tournament (MiniBench)?
- Should grouped/conditional questions be expanded to their sub-questions?
- Should the leaderboard be tracked over time (save HTML periodically)?

---

## Reference: Plan Document
`conversation and context docs/Run Question Map and Tournament HTML Plan 02-09-2026.md`

## Reference: Notebook Naming Convention
- `008x` — Run → Question Number Map (from GitHub workflow logs)
- `009x` — Question Data from HTML (from saved tournament pages)
- Suffix: `a`, `b`, `c`... for iterations; date at end of filename
