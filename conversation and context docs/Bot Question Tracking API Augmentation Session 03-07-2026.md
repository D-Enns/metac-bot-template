# Bot Question Tracking - API Augmentation Session 03-07-2026

## Goal

Create notebook 011a to augment the 182-question HTML extract (from 011) with fields from the Metaculus API: my_forecast, open_date, resolution_date, resolution_value, question_type.

## What Was Done

Created `jupyter/011a_Bot_Question_Tracking_API_03-07-2026.ipynb` — a 6-cell notebook that:

1. Loads `products/Bot_Question_Tracking_2026-03-07_v01.csv` (182 rows, 5 columns from HTML)
2. Fetches each question from the authenticated Metaculus API (`/api2/questions/{id}/`)
3. Extracts 5 new fields per question
4. Merges into a 10-column DataFrame and writes `products/Bot_Question_Tracking_API_2026-03-07_v01.csv`

## Output CSV Schema (10 columns)

| Column | Source | Notes |
|--------|--------|-------|
| question_number | HTML | e.g. 42095 |
| title | HTML | Full question title |
| coverage | HTML | e.g. 100.0% |
| score | HTML | e.g. 59.838 |
| question_weight | HTML | e.g. 1.0 |
| my_forecast | API | Binary: `85.3%`, Numeric: decimal, MC: `opt: pct; ...`, or `Not Forecast` |
| open_date | API | `YYYY-MM-DD` from open_time |
| resolution_date | API | `YYYY-MM-DD` from actual_resolve_time, empty if unresolved |
| resolution_value | API | Binary: `Yes`/`No`, Numeric/MC: raw value, empty if unresolved |
| question_type | API | `binary` / `numeric` / `multiple_choice` |

## Key Implementation Details

- Auth: `METACULUS_BOT_API_TOKEN` env var, sent as `Authorization: Token {token}`
- Rate limiting: 2s between requests, exponential backoff on 429 (5s base, 3 retries)
- My forecast path: `data['question']['my_forecasts']['latest']['forecast_values']`
- Binary forecast: `forecast_values[1]` (p_yes), formatted as percentage
- Numeric forecast: `latest['means'][0]`
- MC forecast: zipped with option names from `question['options']`
- Resolution: binary mapped to Yes/No, others left as raw value
- Runtime: ~6 minutes (182 questions x 2s)

## Reference

- Pattern reused from `jupyter/010b_Question_Data_from_API_02-11-2026.ipynb` (fetch function, auth, backoff)
- Input from `jupyter/011_Bot_Question_Tracking_03-07-2026.ipynb` (HTML extraction)

## Status

Notebook created, not yet run. Requires `METACULUS_BOT_API_TOKEN` env var set in the Jupyter environment.
