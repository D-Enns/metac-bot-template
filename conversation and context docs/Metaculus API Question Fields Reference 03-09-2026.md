# Metaculus API Question Fields Reference — 03-09-2026
## Overview

Documents all question information available from the Metaculus API, focused on numeric questions but covering all types. Based on fields used in the bot codebase, the `forecasting-tools` library, and notebooks 010b, 011a, and 012.

**API Endpoint:** `GET https://www.metaculus.com/api/posts/{POST_ID}/`
Authentication: `Authorization: Token {METACULUS_TOKEN}` header (required for `my_forecasts`)

---

## Section 1: Fields Used in Bot Testbed Notebook (012)

These fields are extracted from the API in `jupyter/012_Metaculus_Bot_Testbed_NUMERIC_03-07-2026.ipynb` cell 4.

### Text Fields

| Field | API Path | Description |
|-------|----------|-------------|
| `title` | `post["question"]["title"]` | Full question headline |
| `description` | `post["question"]["description"]` | Background and context text |
| `resolution_criteria` | `post["question"]["resolution_criteria"]` | How the question will be resolved |
| `fine_print` | `post["question"]["fine_print"]` | Edge cases and caveats |
| `type` | `post["question"]["type"]` | `binary`, `numeric`, `multiple_choice`, `date`, `discrete`, `group` |
| `unit` | `post["question"]["label"]` | Unit of measure (may be empty string) |

### Bounds: `range_min`/`range_max` vs `open_lower_bound`/`open_upper_bound`

These serve **different purposes** and come from **different places** in the API JSON:

| Field | API Path | Type | Description |
|-------|----------|------|-------------|
| `range_min` | `post["question"]["scaling"]["range_min"]` | float | Absolute lower limit of the answer space. The 201-point CDF is defined over [range_min, range_max]. |
| `range_max` | `post["question"]["scaling"]["range_max"]` | float | Absolute upper limit of the answer space. |
| `open_lower_bound` | `post["question"]["open_lower_bound"]` | bool | Whether the lower bound is soft (True) or hard (False). |
| `open_upper_bound` | `post["question"]["open_upper_bound"]` | bool | Whether the upper bound is soft (True) or hard (False). |
| `zero_point` | `post["question"]["scaling"]["zero_point"]` | float or null | Reference point for log-scaled questions. If null, linear scaling is used. |

**Key distinction:**
- **`range_min`/`range_max`** define the numeric interval — the CDF always spans this range.
- **`open_lower_bound`/`open_upper_bound`** define whether the true answer *can exceed* that range:
  - `open=True` (soft limit): Probability mass is allocated outside the range (~1% in each open tail). In the prompt: *"The question creator thinks the number is likely not higher than X."*
  - `open=False` (hard limit): No mass outside the range. In the prompt: *"The outcome cannot be higher than X."*

**Example from notebook 012:** CO2 ppm question — range [420, 435] with both bounds open. The actual CO2 reading *could* fall outside 420–435, but it's unlikely.

### `zero_point` — Log-Scale Questions

When `zero_point` is not null, the CDF uses logarithmic scaling instead of linear. This is for questions where ratios matter more than absolute differences (e.g., "GDP growth multiplier").

- Validation constraint: `lower_bound > zero_point` and all percentile values > `zero_point`
- Transform: `deriv_ratio = (range_max - zero_point) / (range_min - zero_point)`, then location = log-based formula
- When `zero_point is None`: simple linear scaling `(value - range_min) / (range_max - range_min)`

### Not in Notebook 012 but Available: `nominal_min`/`nominal_max`

| Field | API Path | Description |
|-------|----------|-------------|
| `nominal_min` | `post["question"]["scaling"]["nominal_min"]` | Narrower "realistic" lower bound the question creator expects |
| `nominal_max` | `post["question"]["scaling"]["nominal_max"]` | Narrower "realistic" upper bound the question creator expects |

The bot's `main.py:1149-1157` **prefers nominal bounds over range bounds for prompting** when available:
```python
if question.nominal_upper_bound is not None:
    upper_bound_number = question.nominal_upper_bound
else:
    upper_bound_number = question.upper_bound
```

Also not in notebook 012: `scaling["inbound_outcome_count"]` — used for discrete questions to set CDF size (instead of the default 201).

---

## Section 2: Additional Fields Available from the API

These fields are extracted in `jupyter/010b_Question_Data_from_API_02-11-2026.ipynb` and `jupyter/011a_Bot_Question_Tracking_API_03-07-2026.ipynb`.

### Post-Level Fields (top-level of API response)

| Field         | API Path | Description |
|-------------------|---------------------------|----------------------------------------|
| `id`              | `post["id"]`              | Post ID number (used in URLs)          |
| `short_title`     | `post["short_title"]`     | Abbreviated title                      |
| `slug`            | `post["slug"]`            | URL-safe identifier                    |
| `status`          | `post["status"]`          | `open`, `closed`, `resolved`, etc.     |
| `resolved`        | `post["resolved"]`        | Boolean: whether question has resolved |
| `comment_count`   | `post["comment_count"]`   | Number of comments                     |
| `nr_forecasters`  | `post["nr_forecasters"]`  | Count of unique forecasters            |
| `forecasts_count` | `post["forecasts_count"]` | Total forecasts submitted              |
| `author_username` | `post["author_username"]` | Question author                        |
| `curation_status` | `post["curation_status"]` | Editorial/curation status              |

### Dates (all ISO 8601 datetime strings)

| Field | API Path | Description |
|--------------------------|----------------------------------|----------------------------------------------|
| `created_at`             | `post["created_at"]`             | When question was created                    |
| `published_at`           | `post["published_at"]`           | When question was published                  |
| `edited_at`              | `post["edited_at"]`              | Last edit time                               |
| `open_time`              | `post["open_time"]`              | When forecasting opens                       |
| `scheduled_close_time`   | `post["scheduled_close_time"]`   | Planned close date                           |
| `actual_close_time`      | `post["actual_close_time"]`      | Actual close date                            |
| `scheduled_resolve_time` | `post["scheduled_resolve_time"]` | Planned resolution date                      |
| `actual_resolve_time`    | `post["actual_resolve_time"]`    | Actual resolution date (empty if unresolved) |

### Question Sub-Object — Additional Fields

| Field | API Path | Description |
|-----------------------|-------------------------------------------|-------------|
| `resolution`          | `post["question"]["resolution"]`          | Resolution value. Binary: 0.0/1.0. Numeric: raw value. MC: option value. Empty if unresolved.|
| `resolution_set_time` | `post["question"]["resolution_set_time"]` | When resolution was set |
| `question_weight`     | `post["question"]["question_weight"]`     | Tournament weight multiplier (e.g., 0.5, 1.0) |
| `options`             | `post["question"]["options"]`             | MC only: array of option label strings |

### Tournament/Project Info

| Field | API Path | Description |
|-------------------|-----------------------------------------------|-----------------------|
| `tournament_id`   | `post["projects"]["default_project"]["id"]`   | Primary tournament ID |
| `tournament_name` | `post["projects"]["default_project"]["name"]` | Tournament name       |
| `tournament_slug` | `post["projects"]["default_project"]["slug"]` | Tournament URL slug   |

### Community Aggregation (public, no auth needed)

All under `post["question"]["aggregations"]["unweighted"]`:

| Field | Path (relative to `unweighted`) | Description |
|--------------------------|-------------------------------------------------------------|---------------------------------------------|
| `forecaster_count`       | `latest.forecaster_count`                                   | Number of forecasters in latest aggregation |
| `forecast_values`        | `latest.forecast_values`                                    | Community forecast. Binary: [p_no, p_yes]. MC: [p_opt1, p_opt2, ...]. Numeric: array of CDF values. |
| `means`                  | `latest.means`                                              | Mean values. For numeric: `means[0]` is the community mean. |
| `interval_lower_bounds`  | `latest.interval_lower_bounds`                              | Lower confidence interval bounds |
| `interval_upper_bounds`  | `latest.interval_upper_bounds`                              | Upper confidence interval bounds |
| `coverage`               | `score_data.coverage`                                       | Float 0–1: proportion of question lifetime with forecasts |
| `peer_score`             | `score_data.peer_score`                                     | Community peer prediction score |
| `baseline_score`         | `score_data.baseline_score`                                 | Baseline/control score |
| `spot_peer_score`        | `score_data.spot_peer_score`                                | Recent/spot peer score |
| `spot_baseline_score`    | `score_data.spot_baseline_score`                            | Recent/spot baseline score |

### Bot's Own Forecasts (requires authentication)

All under `post["question"]["my_forecasts"]`:

| Field | Path (relative to `my_forecasts`) | Description |
|-------------------|--------------------------|-------------------------------------------------------------------------------------------|
| `forecast_values` | `latest.forecast_values` | Bot's submitted forecast. Same format as community. Binary: `forecast_values[1]` = p_yes. |
| `means`           | `latest.means`           | Bot's mean forecast. Numeric: `means[0]`.                                                 |

Bot's personal scores are also available under `my_forecasts.score_data` with the same structure as community scores.

---

## Section 3: API Path Summary

```
post (GET /api/posts/{id}/)
├── id, title, short_title, slug
├── status, resolved
├── comment_count, nr_forecasters, forecasts_count
├── author_username, curation_status
├── created_at, published_at, edited_at
├── open_time, scheduled_close_time, actual_close_time
├── scheduled_resolve_time, actual_resolve_time
├── projects
│   └── default_project
│       ├── id, name, slug
├── question
│   ├── title, description, resolution_criteria, fine_print
│   ├── type, label (unit)
│   ├── open_upper_bound, open_lower_bound
│   ├── resolution, resolution_set_time, question_weight
│   ├── options (MC only)
│   ├── scaling
│   │   ├── range_min, range_max
│   │   ├── nominal_min, nominal_max
│   │   ├── zero_point
│   │   └── inbound_outcome_count (discrete only)
│   ├── aggregations
│   │   └── unweighted
│   │       ├── latest
│   │       │   ├── forecaster_count
│   │       │   ├── forecast_values, means
│   │       │   └── interval_lower_bounds, interval_upper_bounds
│   │       └── score_data
│   │           ├── coverage, peer_score, baseline_score
│   │           └── spot_peer_score, spot_baseline_score
│   └── my_forecasts (auth required)
│       ├── latest
│       │   ├── forecast_values, means
│       └── score_data (same structure as community)
```

---

## References

- **Notebook 010b:** `jupyter/010b_Question_Data_from_API_02-11-2026.ipynb` — Community data extraction with `extract_question_fields()` function
- **Notebook 011a:** `jupyter/011a_Bot_Question_Tracking_API_03-07-2026.ipynb` — Authenticated extraction with `my_forecasts`
- **Notebook 012:** `jupyter/012_Metaculus_Bot_Testbed_NUMERIC_03-07-2026.ipynb` — Minimal API fetch for numeric testbed
- **Bot code:** `main.py:1146-1175` (bound messages), `main_with_no_framework.py:1128-1200` (full numeric pipeline)
- **Library:** `forecasting_tools/data_models/questions.py` — `NumericQuestion.from_metaculus_api_json()` field parsing
- **Rate limiting:** 2s between requests, exponential backoff on 429 (5s base, 3 retries)
