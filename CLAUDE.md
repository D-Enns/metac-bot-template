# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Metaculus AI Forecasting Tournament bot. Runs every 20 minutes via GitHub Actions, picks up new tournament questions (Binary, Multiple Choice, Numeric, Date), researches them via LLMs and news APIs, generates multi-scenario forecasts, aggregates predictions, and submits to Metaculus.

- Builds on the Metaculus template from https://github.com/Metaculus/metac-bot-template and https://github.com/Metaculus/forecasting-tools
- The objective is to maximize forecasting performance in metaculus.com FutureEval Bot Tournaments

## Key Commands

```bash
# Install dependencies
poetry install

# Run bot in test mode (edit EXAMPLE_QUESTIONS list in main.py to uncomment desired question type)
poetry run python main.py --mode test_questions

# Run bot on tournament (production mode, skips already-forecasted questions)
# Default mode — runs on both seasonal tournament and minibench
poetry run python main.py --mode tournament

# Run bot on Metaculus Cup (regular open questions, re-forecasts allowed)
poetry run python main.py --mode metaculus_cup

# Run tests
poetry run pytest tests/

# Run a single test (currently the only test file)
poetry run pytest tests/test_gpr_aggregation.py -v
```

Environment variables are loaded from `.env` (copy `.env.template`).
- **Required**: `METACULUS_TOKEN`, `OPENROUTER_API_KEY`
- **Optional**: `ASKNEWS_CLIENT_ID`, `ASKNEWS_SECRET` (used for AskNews research), `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `EXA_API_KEY`, `ANTHROPIC_API_KEY`

## Architecture

### Bot Inheritance Chain

`ForecastBot` (from `forecasting-tools` library) → `SpringTemplateBot2026` (`main.py`) → `SpringTemplateBotExtended` (`dre_forecasting_tools.py`)

- **`main.py`**: Modified from Metaculus template bot. Defines research prompts, forecast prompts, and aggregation for all question types. Uses 9-scenario framework (Low/Mid/High worlds × Low/Mid/High estimates) with 6 prediction runs per question. Contains the `if __name__ == "__main__"` block that parses `--mode`, creates `SpringTemplateBotExtended`, and runs it.
- **`dre_forecasting_tools.py`**: Custom extensions. Adds Skew-T aggregation for numeric questions, diagnostic tracking (per-question success/failure/skip), condensed summary generation via LLM, forecast file saving, and exit code logic. This is the class actually instantiated at runtime. **Import note**: This file uses `sys.path.insert` + `from main import SpringTemplateBot2026` — be aware of this circular dependency when refactoring.

### Execution Flow

1. `main.py` bottom: Parses `--mode`, creates `SpringTemplateBotExtended` instance
2. `tournament` mode calls `forecast_on_tournament()` twice: once for `CURRENT_AI_COMPETITION_ID`, once for `CURRENT_MINIBENCH_ID`
3. For each question: `run_research()` → `run_forecast()` × 6 → `aggregate_predictions()` → submit to Metaculus
4. After all questions: `write_diagnostics_json()` produces `forecast_summaries/run_diagnostics.json`

### Current LLM Configuration

Models are set in `main.py` at the bottom via the `llms` dict. Current configuration:
- **default**: `openrouter/openai/gpt-5.2` (temperature=1, timeout=80s, allowed_tries=2)
- **summarizer**: `openrouter/openai/gpt-4o-mini` (condensed forecast summaries)
- **researcher**: `asknews/news-summaries`
- **parser**: `openrouter/openai/o4-mini`

Models are accessed through OpenRouter using an API key. The current `forecasting-tools` version is `^0.2.80` (see `pyproject.toml`).

### Forecast Output Files

Written to `forecast_summaries/` during each run:
- `{question_id}_{tournament}_full_{run_number}.md` — Complete research and reasoning
- `{question_id}_{tournament}_condensed_{run_number}.md` — LLM-summarized version with metadata header
- `{question_id}_{tournament}_scenarios_{run_number}.json` — Raw scenario values
- `run_diagnostics.json` — Per-tournament summary of what was attempted/skipped/succeeded/failed

### GitHub Actions

- **`dre_run_bot_on_tournament.yaml`**: Production workflow. Runs every 20 min, uploads forecast_summaries as artifacts (90-day retention), writes step summary from diagnostics JSON.
- **`run_bot_on_metaculus_cup.yaml`**: Metaculus Cup workflow.
- **`dre_test_bot.yaml`**: Manual trigger, test mode.
- Concurrency group prevents parallel runs.

## Key Technical Details

- **Skew-T aggregation** (numeric questions): Fits an Azzalini skew-t distribution via method of quantiles (matching Bowley skewness, IQR, and median) with CvM refinement. Generates 99 output percentiles (p1–p99). Handles asymmetric distributions unlike the previous probit method. Implemented in `dre_forecasting_tools.py`. State tracked via `self._numeric_scenarios` list and `self._current_question_id`.
- **Option name normalization** (multiple choice): Handles Unicode smart quote variants (`'` vs `'`). Uses positional fallback if exact name match fails.
- **LLM configuration**: Models set via `GeneralLlm` with OpenRouter routing. Default model, researcher, summarizer, and parser are independently configurable.
- **The `forecasting-tools` library** (PyPI package) handles Metaculus API calls, question loading, prediction submission, and the `ForecastBot` base class. Pin version carefully—numeric question parsing and bounds assertions have broken between versions.
- **AskNews rate limiting**: A 10-second sleep is added after AskNews research calls to prevent 429 errors.
- **Prediction runs and majority-vote validation** (numeric questions): Each question gets `predictions_per_research_report` forecast calls (configurable, typically 4–8), each producing 9 scenarios. Before Skew-T aggregation, a majority-vote validator clusters call medians—calls within 3× of each other are considered agreeing. If fewer than 3 calls agree (e.g., unit interpretation errors), the forecast bails out with a `ValueError` rather than submitting an unreliable prediction. Only scenarios from the majority cluster are used.
- **Metaculus Cup mode**: Unlike `tournament` mode, `metaculus_cup` sets `skip_previously_forecasted_questions=False`, allowing re-forecasts on questions the bot has already answered.

## Project Layout

- `dre_tools/` — Standalone Python utilities (log download, forecast consolidation). Each has a `SKILL_*.md` doc file and a corresponding `*_README.md`.
- `jupyter/` — Analysis notebooks. Naming: `NNN_Description_MM-DD-YYYY.ipynb`, iterations use letters (`008`, `008a`, `008b`).
- `products/` — CSV/Excel analysis outputs, date-stamped.
- `forecast_summaries/` — Bot output files (generated at runtime).
- `conversation and context docs/` — Session documentation files.
- `prompts/` — Versioned prompt text files (e.g., `NUMERIC_prompt_NV02_01-21-2026.md`). Used for prompt development/iteration outside main code.

## Development Notes

- Python 3.11+, Poetry for dependency management. Direct dependencies include `numpy ^2.3.0` and `openai ^2.0.0`. Key implicit dependencies (via `forecasting-tools`): `scipy`, `scikit-learn`.
- WSL2 development environment; user runs Jupyter notebooks from Windows.
- `NotebookEdit` can break notebook cell structure—prefer using `Write` to rewrite entire notebooks when editing `.ipynb` files.
- When extracting GitHub Actions logs via `gh` CLI: strip ANSI codes with `re.sub(r'\x1b\[[0-9;]*m', '', text)`, handle pagination by brace-counting concatenated JSON, and use byte-based subprocess capture for Windows Unicode safety.
