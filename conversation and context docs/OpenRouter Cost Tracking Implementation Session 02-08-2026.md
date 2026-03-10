# OpenRouter Cost Tracking Implementation Session
**Date:** February 8, 2026
**Status:** ✅ Complete
**Deliverable:** Jupyter Notebook for tracking OpenRouter API costs

---

## Project Overview

### Objective
Track OpenRouter API spending on a per-session basis to monitor costs for the Metaculus forecasting bot. Calculate cost per question and maintain cumulative statistics across all forecast sessions.

### Background
- The forecasting bot uses OpenRouter API (via LiteLLM) for three model types:
  - `openrouter/openai/gpt-5.2` (main reasoning model)
  - `openrouter/openai/gpt-4o-mini` (summarizer)
  - `openrouter/openai/o4-mini` (parser)
- OpenRouter provides a `limit_remaining` balance via their API
- Need to track usage between sessions to understand cost per question

### Original Requirements
From `OpenRouter Cost Tracking Project 02-08-2026.md`:
1. Read history spreadsheet to get prior balance and question count
2. Get new balance from OpenRouter API
3. Optionally ask for number of questions forecast
4. Calculate usage from last access and cost per question
5. Report stats on screen
6. Write new row to spreadsheet with comprehensive metrics

---

## Implementation Decisions

### Planning Session Q&A

**Q1: Where should the cost tracking history be stored?**
- Options considered: Local CSV, Google Sheets (via API), Local Excel
- **Decision:** Local Excel (.xlsx) - Simple, no external dependencies beyond openpyxl, easy to view

**Q2: Where should the tracker live?**
- Options considered: dre_tools/ script, Colab notebook extension, standalone script
- **Decision:** Initially planned for Colab extension, then pivoted to Jupyter notebook for local execution

**Q3: Where should the Excel file be stored?**
- Options considered: Google Drive (mounted in Colab), Local download/upload
- **Decision:** Local filesystem (same directory as notebook) for simplicity

### Final Architecture
- **Tool:** Jupyter Notebook (`jupyter/006_OpenRouter Usage Tracker 02-08-2026.ipynb`)
- **Storage:** Excel file (`openrouter_cost_history.xlsx`) in notebook directory
- **Dependencies:** openpyxl (for Excel I/O)
- **API:** OpenRouter `/api/v1/auth/key` endpoint

---

## Implementation Details

### Notebook Structure

#### Cell 1: Markdown - Introduction
- Project description and purpose

#### Cell 2: Markdown - Setup header

#### Cell 3: Code - Install dependencies
```python
# !pip install openpyxl  # Uncommented by user if needed
```

#### Cell 4: Code - Imports
```python
import os, urllib.request, json
from openpyxl import load_workbook, Workbook
from datetime import datetime
from pathlib import Path
```

#### Cell 5: Code - Configuration
- `HISTORY_FILE`: Path to Excel file
- `OPENROUTER_API_KEY`: Loaded from environment or set directly
- Validates API key is set

#### Cell 6: Markdown - API section header

#### Cell 7: Code - Get current balance
- `get_openrouter_balance(api_key)` function
- Calls `https://openrouter.ai/api/v1/auth/key`
- Returns `limit_remaining` value
- Error handling for failed API calls

#### Cell 8: Markdown - History section header

#### Cell 9: Code - Load history from Excel
- Defines column schema (9 columns)
- `load_history()` function:
  - Creates new workbook with headers if file doesn't exist
  - Loads existing workbook and reads all rows
- Extracts prior session values:
  - `prior_balance` = previous session's `current_balance`
  - `total_questions_prior` = cumulative question count
  - `total_cost_prior` = cumulative cost
- Displays loaded values or "starting fresh" message

#### Cell 10: Markdown - Calculate section header

#### Cell 11: Code - Calculate and report
- Prompts user for `questions_this_session`
- Calculates:
  - `cost_this_session` = prior_balance - current_balance
  - `cost_per_q_session` = cost / questions (session only)
  - `total_questions` = prior + current
  - `total_cost` = prior + current
  - `avg_cost_per_q` = total cost / total questions (inception)
- Displays formatted report with session and cumulative stats

#### Cell 12: Markdown - Save section header

#### Cell 13: Code - Save to Excel
- Creates new row with timestamp
- Appends row to worksheet
- Saves workbook
- Confirms save with absolute path

#### Cell 14: Markdown - Schema reference table

---

## Excel Schema

File: `openrouter_cost_history.xlsx`

| Column Name | Type | Description |
|-------------|------|-------------|
| `datetime` | String | Timestamp of this tracking session (YYYY-MM-DD HH:MM:SS) |
| `prior_balance` | Float | `limit_remaining` from the previous session |
| `current_balance` | Float | `limit_remaining` from this session (from API) |
| `cost_this_session` | Float | Calculated: prior_balance - current_balance |
| `questions_this_session` | Integer | User-entered: number of questions forecast this session |
| `cost_per_question_session` | Float | Calculated: cost_this_session / questions_this_session |
| `total_questions_inception` | Integer | Cumulative: all questions since inception |
| `avg_cost_per_question_inception` | Float | Cumulative: total_cost / total_questions |
| `total_cost_inception` | Float | Cumulative: all costs since inception |

### Data Flow
1. **First session:** `prior_balance` = `current_balance` (no cost yet)
2. **Subsequent sessions:** `prior_balance` = previous row's `current_balance`
3. **Cumulative tracking:** Each row builds on `total_*_inception` from previous row

---

## Usage Instructions

### Prerequisites
1. Python 3.x with Jupyter Notebook/Lab
2. Install openpyxl: `pip install openpyxl`
3. Set `OPENROUTER_API_KEY` environment variable OR paste key directly in Cell 5

### Running the Tracker

1. Open notebook: `jupyter/006_OpenRouter Usage Tracker 02-08-2026.ipynb`
2. Run all cells in sequence (Kernel → Run All, or Shift+Enter through each cell)
3. When prompted in Cell 11, enter the number of questions forecast this session
4. Review the on-screen report
5. Verify Excel file saved successfully

### Example Output

```
💰 Current balance (limit_remaining): $8.2450

============================================================
HISTORY LOADED
============================================================
Prior balance:         $10.3200
Prior total questions: 24
Prior total cost:      $1.7550
Total sessions logged: 3
============================================================

How many questions were forecast this session? (0 if none): 6

============================================================
📊 SESSION COST REPORT
============================================================
Cost this session:             $2.0750
Questions this session:        6
Avg cost/question (session):   $0.3458
------------------------------------------------------------
Total cost (inception):        $3.8300
Total questions (inception):   30
Avg cost/question (total):     $0.1277
============================================================

✅ History saved to: C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter\openrouter_cost_history.xlsx
```

---

## Integration with Forecasting Bot

### Current Bot Configuration
From `main.py` (lines 1300-1310):
```python
llms={
    "default": GeneralLlm(
        model="openrouter/openai/gpt-5.2",
        temperature=1,
        timeout=80,
        allowed_tries=2,
    ),
    "summarizer": "openrouter/openai/gpt-4o-mini",
    "parser": "openrouter/openai/o4-mini",
}
```

### Bot Execution Modes
- `--mode tournament`: Forecasts on AI competition + MiniBench
- `--mode metaculus_cup`: Forecasts on Metaculus Cup questions
- `--mode test_questions`: Test questions only

### Tracking Workflow
1. **Before forecast run:** Note current question list (e.g., from logs or GitHub Actions metadata)
2. **Run forecast bot:** Execute `python main.py --mode <mode>`
3. **After forecast run:**
   - Run this Jupyter notebook
   - Count questions from bot logs or artifacts
   - Enter count when prompted
   - Review cost report

### Question Count Sources
- GitHub Actions logs: Use `dre_tools/download_forecast_logs.py` to get metadata
- Bot artifacts: Check `forecast_summaries/` directory
- Manually count from bot output

---

## Files Created

### Primary Deliverable
- **`jupyter/006_OpenRouter Usage Tracker 02-08-2026.ipynb`**
  - Interactive notebook for cost tracking
  - 14 cells (7 markdown, 7 code)
  - ~150 lines of code
  - Complete with documentation and schema reference

### Generated Data File
- **`openrouter_cost_history.xlsx`** (created on first run)
  - Saved in same directory as notebook
  - Persistent across sessions
  - Column headers automatically created

### Documentation
- **`conversation and context docs/OpenRouter Cost Tracking Implementation Session 02-08-2026.md`** (this file)

---

## Testing & Validation

### Validation Checklist
- ✅ API call successfully retrieves `limit_remaining`
- ✅ Excel file created with correct schema on first run
- ✅ Prior balance correctly loaded from last row
- ✅ Cumulative totals calculated correctly
- ✅ New row appended with all 9 columns
- ✅ On-screen report displays all key metrics
- ✅ File path shown correctly at end

### Error Handling
- API key validation (warns if not set)
- API call exception handling (network errors, invalid key)
- Safe division (handles 0 questions)
- Excel file creation if missing
- Null handling for empty history rows

---

## Future Enhancements (Optional)

### Potential Additions
1. **Visualization:** Add matplotlib charts showing cost trends over time
2. **Model breakdown:** Track cost per model type (gpt-5.2 vs gpt-4o-mini vs o4-mini)
3. **Auto question count:** Parse bot logs/artifacts to auto-detect question count
4. **Budget alerts:** Warn when approaching spending limits
5. **Export to CSV:** Option to export history as CSV for analysis
6. **Time tracking:** Add session duration to calculate cost per hour
7. **GitHub Actions integration:** Auto-run tracker after bot workflows

### Integration with dre_tools
If desired, could create a standalone Python script version in `dre_tools/` following the pattern of:
- `dre_tools/track_openrouter_costs.py` (CLI script with argparse)
- `dre_tools/SKILL_track_openrouter_costs.md` (skill invocation)
- `dre_tools/track_openrouter_costs_README.md` (usage documentation)

---

## Technical Notes

### Dependencies
- **openpyxl:** Pure Python Excel library, no Excel installation required
- **urllib.request:** Standard library, no external HTTP client needed
- **pathlib:** Modern path handling (Python 3.4+)

### API Details
- **Endpoint:** `https://openrouter.ai/api/v1/auth/key`
- **Method:** GET
- **Auth:** Bearer token (OPENROUTER_API_KEY)
- **Response:** JSON with `data.limit_remaining` field (float, USD)

### Excel Format
- **Format:** Office Open XML (.xlsx)
- **Compatibility:** Excel 2007+, Google Sheets, LibreOffice Calc
- **Size:** Minimal (~10KB for 100 sessions)
- **Performance:** Fast even with 1000+ rows

---

## Session Summary

### What Was Built
A complete, self-contained Jupyter notebook that:
- Tracks OpenRouter API spending per forecast session
- Maintains historical data in Excel format
- Calculates session and cumulative statistics
- Provides clear on-screen reporting
- Handles errors gracefully
- Requires minimal setup (just API key)

### Key Features
- **Zero manual balance tracking:** Prior balance automatically pulled from last session
- **Cumulative analytics:** Tracks total cost and questions since inception
- **User-friendly:** Clear prompts, formatted output, absolute file paths
- **Portable:** Runs locally, no cloud dependencies
- **Extensible:** Easy to add charts, exports, or automation

### Time Investment
- Planning: ~15 minutes (exploring codebase, clarifying requirements)
- Implementation: ~20 minutes (writing notebook, testing structure)
- Documentation: ~15 minutes (this comprehensive session doc)
- **Total:** ~50 minutes

### Outcome
✅ **Project Complete** - User reported "The Jupyter Notebook works great"

---

## Related Files & Context

### Project Documents
- `OpenRouter Cost Tracking Project 02-08-2026.md` - Original requirements
- `forecasting_bot_improvement_ideas_edit 02-08-2026.xlsx` - May include cost tracking as improvement item

### Relevant Code
- `main.py` (lines 1300-1310) - LLM configuration with OpenRouter models
- `dre_forecasting_tools.py` - LiteLLM integration and model usage
- `.env.template` - OPENROUTER_API_KEY placeholder

### Related Tools
- `dre_tools/download_forecast_logs.py` - Can provide question counts from GitHub logs
- `dre_tools/generate_bot_forecast_log.py` - Generates forecast logs with metadata

---

**End of Session Documentation**
