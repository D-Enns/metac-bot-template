# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The overall objective is build and continuously update a AI bot to maximize forecasting performance in metaculus.com FutureEval Bot Tournaments (AI Forecasting Tournaments)

- The Bot builds on and modifies the Metaculus code from https://github.com/Metaculus/metac-bot-template and https://github.com/Metaculus/forecasting-tools
- Metaculus AI Forecasting Tournament bot. Runs every 20 minutes via GitHub Actions, picks up new tournament questions (Binary, Multiple Choice, Numeric), researches them via LLMs and news APIs, generates multi-scenario forecasts, aggregates predictions, and submits to Metaculus.

## Key Commands

```bash
# Install dependencies
poetry install

# Run bot in test mode (single example questions, no tournament sweep)
poetry run python main.py --mode test_questions

# Run bot on tournament (production mode, skips already-forecasted questions)
poetry run python main.py --mode tournament

# Run bot on Metaculus Cup (regular open questions)
poetry run python main.py --mode metaculus_cup

# Run tests
poetry run pytest tests/

# Run a single test
poetry run pytest tests/test_gpr_aggregation.py -v
```

Environment variables are loaded from `.env` (copy `.env.template`). Required: `METACULUS_TOKEN`, `OPENROUTER_API_KEY`.

## Architecture

### Bot Inheritance Chain

`ForecastBot` (from `forecasting-tools` library) → `SpringTemplateBot2026` (`main.py`) → `SpringTemplateBotExtended` (`dre_forecasting_tools.py`)

- **`main.py`**: Modified from Template bot from Metaculus. Defines research prompts, forecast prompts, and aggregation for all question types. Uses 9-scenario framework (Low/Mid/High worlds × Low/Mid/High estimates) with 6 prediction runs per question.
- **`dre_forecasting_tools.py`**: Custom extensions. Adds probit aggregation for numeric questions, diagnostic tracking (per-question success/failure/skip), forecast file saving, and exit code logic. This is the class actually instantiated in the `if __name__ == "__main__"` block at the bottom of `main.py`.

### Execution Flow

1. `main.py` bottom: Parses `--mode`, creates `SpringTemplateBotExtended` instance, calls `forecast_on_tournament()`
2. For each question: `run_research()` → `run_forecast()` × 6 → `aggregate_predictions()` → submit to Metaculus
3. After all questions: `write_diagnostics_json()` produces `forecast_summaries/run_diagnostics.json`

### Forecast Output Files

Written to `forecast_summaries/` during each run:
- `{question_id}_{tournament}_full_{run_number}.md` — Complete research and reasoning
- `{question_id}_{tournament}_condensed_{run_number}.md` — LLM-summarized version with metadata header
- `{question_id}_{tournament}_scenarios_{run_number}.json` — Raw scenario values
- `run_diagnostics.json` — Per-tournament summary of what was attempted/skipped/succeeded/failed

### GitHub Actions

- **`dre_run_bot_on_tournament.yaml`**: Production workflow. Runs every 20 min, uploads forecast_summaries as artifacts (90-day retention), writes step summary from diagnostics JSON.
- **`dre_test_bot.yaml`**: Manual trigger, test mode.
- Concurrency group prevents parallel runs.

## Key Technical Details

- **Probit aggregation** (numeric questions): Converts scenario percentiles to z-scores via spline lookup, fits linear regression, generates 99 output percentiles (p1–p99). Implemented in `dre_forecasting_tools.py`.
- **Option name normalization** (multiple choice): Handles Unicode smart quote variants (`'` vs `'`). Uses positional fallback if exact name match fails.
- **LLM configuration**: Models set via `GeneralLlm` with OpenRouter routing. Default model, researcher, summarizer, and parser are independently configurable.
- **The `forecasting-tools` library** (PyPI package) handles Metaculus API calls, question loading, prediction submission, and the `ForecastBot` base class. Pin version carefully—numeric question parsing and bounds assertions have broken between versions.

## Project Layout

- `dre_tools/` — Standalone Python utilities (log download, forecast consolidation). Each has a `SKILL_*.md` doc file.
- `jupyter/` — Analysis notebooks. Naming: `NNN_Description_MM-DD-YYYY.ipynb`, iterations use letters (`008`, `008a`, `008b`).
- `products/` — CSV/Excel analysis outputs, date-stamped.
- `forecast_summaries/` — Bot output files (generated at runtime).
- `conversation and context docs/` — Session documentation files.

## Development Notes

- Python 3.11+, Poetry for dependency management.
- WSL2 development environment; user runs Jupyter notebooks from Windows.
- `NotebookEdit` can break notebook cell structure—prefer using `Write` to rewrite entire notebooks when editing `.ipynb` files.
- When extracting GitHub Actions logs via `gh` CLI: strip ANSI codes with `re.sub(r'\x1b\[[0-9;]*m', '', text)`, handle pagination by brace-counting concatenated JSON, and use byte-based subprocess capture for Windows Unicode safety.
