# Plan: Minimal Bot Testbed Notebook (Numeric Forecasting)

## Context
Self-contained Jupyter notebook replicating the bot's numeric forecasting pipeline without `forecasting-tools`. Serves as a testbed to experiment with new forecasting approaches. News summaries provided as input. No forecast submission — display only.

**Output file:** `jupyter/012_Metaculus_Bot_Testbed_03-07-2026.ipynb`

## Notebook Cell Structure (12 cells)

### Cell 1 — Markdown: Title & Overview
- "Minimal Bot Testbed -- Numeric Forecasting"
- Pipeline: Question Input -> LLM Prompting (x6) -> Scenario Parsing -> Majority Vote -> Probit Aggregation -> CDF -> Visualization

### Cell 2 — Markdown: Update Procedure
How to sync with upstream when bot code changes:
- Numeric prompt -> `main.py` lines 663-741
- Bounds messages -> `main.py` lines 1146-1175
- Majority vote -> `main.py` lines 827-895
- Probit aggregation -> `dre_forecasting_tools.py` lines 42-71, 312-402
- NumericDistribution/CDF -> `main_with_no_framework.py` lines 650-1125
- Check model names in `main.py` bottom `llms` dict
- Upstream repos: `github.com/Metaculus/metac-bot-template`, `github.com/Metaculus/forecasting-tools`

### Cell 3 — Code: Imports & LLM Setup
- `os, json, asyncio, datetime, requests`
- `numpy, scipy (quad, splrep, splev, linregress), matplotlib, pydantic, nest_asyncio`
- `openai.AsyncOpenAI` with `base_url="https://openrouter.ai/api/v1"`, key from env
- `nest_asyncio.apply()` for Jupyter async compatibility
- Models (matching current `main.py` llms dict):
  - `DEFAULT_MODEL = "openai/gpt-5.2"` (temperature=1)
  - `PARSER_MODEL = "openai/o4-mini"`

### Cell 4 — Code: Fetch Question Data from Metaculus API
- Uses `METACULUS_TOKEN` from env and `requests.get` to `https://www.metaculus.com/api/posts/{post_id}/`
- Extracts from `post_details["question"]`: `title`, `description`, `resolution_criteria`, `fine_print`, `type`, `unit`, `scaling` (range_min, range_max, zero_point), `open_upper_bound`, `open_lower_bound`
- Builds a `question` dict with all needed fields
- Generates `upper_bound_message` and `lower_bound_message` (logic from `main.py:1146-1175`)
- User sets `POST_ID = <number>` at top of cell
- Print summary of loaded question

### Cell 5 — Code: News Summary Input
- `news_summary = """..."""` — user pastes research text here
- Could also be loaded from a file

### Cell 6 — Code: Forecast Prompt
- Build the 9-scenario multi-world prompt string (from `main.py:663-741`)
- f-string substitution with question dict fields and news_summary
- Outputs: Low_World (low/mid/high), Mid_World (low/mid/high), High_World (low/mid/high) = 9 values

### Cell 7 — Code: LLM Call & Scenario Parsing
- `async call_llm(prompt, model, temperature)` — single OpenRouter chat completion
- `MultiScenarioPrediction(BaseModel)` with `scenarios: list[float]` (from `main.py:48-54`)
- `async parse_scenarios(reasoning_text)` — sends text to parser model, extracts 9 scenario values as JSON

### Cell 8 — Code: Multi-Run Accumulation
- `N_RUNS = 6` (configurable, same as bot)
- Sequential loop: call LLM -> parse scenarios -> extend `all_scenarios` list
- Print progress and parsed values per run
- Total: 6 runs x 9 scenarios = 54 scenarios

### Cell 9 — Code: Majority Vote Validation
- `validate_majority_vote(scenarios)` — standalone function from `main.py:827-895`
- Groups into calls of 9, computes medians, clusters within 3x, keeps largest cluster
- Raises ValueError if <3 calls agree

### Cell 10 — Code: Probit Aggregation
- Z-spline setup: `_pdf_normal`, `_pcntl_from_z`, precomputed `_Z_SPLINE` (from `dre_forecasting_tools.py:42-71`)
- `probit_aggregate(scenarios, question)` — sort, assign empirical percentiles, linregress in z-space, generate p1-p99, clamp to bounds, ensure strictly increasing (from `dre_forecasting_tools.py:312-402` and `main.py:989-1046`)
- Returns: list of 99 `(percentile, value)` tuples, R-squared, slope, intercept

### Cell 11 — Code: CDF Generation (201 points)
- `Percentile` Pydantic model (from `main_with_no_framework.py:673-689`)
- `NumericDefaults` class with `DEFAULT_CDF_SIZE=201`, `get_max_pmf_value()` (from `main_with_no_framework.py:650-670`)
- `NumericDistribution` class with full CDF logic (from `main_with_no_framework.py:692-1125`):
  - `_nominal_location_to_cdf_location()` — linear and log-scale
  - `_cdf_location_to_nominal_location()` — inverse
  - `_add_explicit_upper_lower_bound_percentiles()` — open/closed bound handling
  - `_get_cdf_at()` — linear interpolation
  - `_standardize_cdf()` — minimum mass, PMF capping
  - `get_cdf()` — produces 201-point CDF
- Output: `cdf_201` list of 201 floats

### Cell 12 — Code: Visualization (Final Cell)
Three subplots:
1. **CDF Curve** — 201 points, x = values from lower to upper bound, y = cumulative probability
2. **Scenario Distribution** — validated scenarios as histogram + strip plot
3. **Probit Fit** — z-scores vs values, empirical points + regression line, R-squared annotation

Print key summary stats: p5, p25, p50, p75, p95, R-squared

## Source Files Referenced
| Component | Source File | Lines |
|---|---|---|
| Numeric prompt | `main.py` | 663-741 |
| Bounds messages | `main.py` | 1146-1175 |
| MultiScenarioPrediction | `main.py` | 48-54 |
| Majority vote validation | `main.py` | 827-895 |
| Ensure strictly increasing | `main.py` | 989-1046 |
| Probit z-spline | `dre_forecasting_tools.py` | 42-71 |
| Probit aggregate | `dre_forecasting_tools.py` | 312-402 |
| Percentile model | `main_with_no_framework.py` | 673-689 |
| NumericDefaults | `main_with_no_framework.py` | 650-670 |
| NumericDistribution + CDF | `main_with_no_framework.py` | 692-1125 |
| API fetch pattern | `main_with_no_framework.py` | 238-251 |

## Key Design Decisions
1. **Question data fetched from API** — Cell 4 calls `GET /api/posts/{post_id}/` with METACULUS_TOKEN to get all fields (title, description, criteria, bounds, units, zero_point). No manual entry needed.
2. **No API submission** — notebook is display-only. Final cell shows visualization and summary stats.
3. **Models match current main.py** — `openai/gpt-5.2` (default, temp=1) and `openai/o4-mini` (parser), both via OpenRouter.
4. **NumericDistribution copied from upstream** — verified consistent with `main_with_no_framework.py` in `github.com/Metaculus/metac-bot-template`. The CDF standardization logic is required by Metaculus and cannot be simplified.
5. **Write tool for notebook** — per project convention, avoids NotebookEdit breaking cell structure.
6. **Sequential LLM calls** — simpler for notebook, easier to inspect each run.

## Verification
1. Run Cell 3 — confirm OpenRouter client initializes
2. Run Cell 4 — set a real numeric question POST_ID, confirm all fields populated
3. Run Cells 6-8 — confirm LLM returns reasoning with 9 scenarios, parsing succeeds
4. Run Cell 9 — confirm majority vote passes
5. Run Cell 10 — confirm probit produces 99 percentiles with R-squared reported
6. Run Cell 11 — confirm CDF produces exactly 201 values in [0, 1]
7. Run Cell 12 — visually inspect CDF curve, scenario distribution, probit fit
