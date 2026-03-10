# Metaculus API Question Data Extraction Plan

**Date:** 2026-02-10
**Goal:** Extract question data via Metaculus API for identified questions, producing a CSV similar to HTML extraction but with complete and authoritative data

---

## Background

We've identified **~145 unique questions** that the bot has forecast on (from run-question map 008a). The HTML parsing approach (009a) has significant limitations:
- Missing resolution values for 7 of 13 resolved questions
- Empty forecaster/comment counts
- Fragile regex-based parsing
- Only covers one page of one tournament

The **Metaculus API** provides authoritative, structured data for all questions.

---

## API Investigation Results

### Available Endpoints

**1. Single Question Endpoint**
```
GET https://www.metaculus.com/api2/questions/{question_id}/
```
Returns comprehensive question data (no auth required for public questions).

**2. Tournament Questions List**
```
GET https://www.metaculus.com/api2/questions/?project={project_id}&limit={N}&offset={M}
```
Returns paginated list of questions in a tournament.

- Spring 2026 AI Benchmark project_id: `32916`
- Returns count, next/previous URLs, and results array
- Each result has same structure as single question endpoint

**3. User Forecasts** (requires authentication)
```
GET https://www.metaculus.com/api2/questions/{question_id}/forecast/
```
Would return bot's own forecasts (not tested - may need METACULUS_TOKEN).

### Data Available from API

From `/api2/questions/{id}/` response:

**Top-level fields:**
- `id`, `title`, `short_title`, `slug`
- `status` — "open", "closed", "resolved", etc. (authoritative!)
- `resolved` — boolean
- `comment_count` — integer (works!)
- `nr_forecasters` — forecaster count (works!)
- `created_at`, `published_at`, `edited_at`
- `actual_close_time`, `scheduled_close_time`
- `actual_resolve_time`, `scheduled_resolve_time`
- `projects` — contains tournament info

**`question` sub-object:**
- `type` — "binary", "numeric", "multiple_choice", "date", "group"
- `resolution` — actual resolution value (works for all resolved Qs!)
- `resolution_set_time`
- `question_weight` — 0.5 to 1.0
- `options` — array of MC option strings
- `scaling` — for numeric questions (range_min, range_max, etc.)
- `description`, `resolution_criteria`, `fine_print` — full text

**`aggregations.unweighted` sub-object:**
- `latest.forecaster_count` — community forecaster count
- `latest.forecast_values` — community prediction (array for MC, [p_no, p_yes] for binary)
- `latest.means` — mean probabilities
- `latest.interval_lower_bounds`, `latest.interval_upper_bounds`
- `score_data` — coverage, peer_score, baseline_score, etc.

**Score data fields:**
- `coverage` — 0.0 to 1.0 (proportion of question lifetime with forecast)
- `peer_score`, `baseline_score` — scoring metrics
- `spot_peer_score`, `spot_baseline_score`
- Multiple archived score variants

---

## Implementation Plan

### Step 1: Prepare Input Data
**Input:** Question list from 008a run-question map
**Format:** CSV with columns: `run_id`, `question_number`, `timestamp`

**Actions:**
1. Read `products/Run_Question_Map_2026-02-09_v02.csv`
2. Extract unique question numbers (should be ~145)
3. Store as list for iteration

---

### Step 2: API Data Extraction (Jupyter Notebook)
**Notebook:** `jupyter/010_Question_Data_from_API_02-10-2026.ipynb`

**Cell 1: Setup**
```python
import requests
import pandas as pd
import time
from pathlib import Path
```

**Cell 2: Load Question List**
- Read run-question map CSV
- Get unique question numbers
- Print count

**Cell 3: Define API Fetch Function**
```python
def fetch_question_data(question_id: int) -> dict:
    """Fetch question data from Metaculus API."""
    url = f"https://www.metaculus.com/api2/questions/{question_id}/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

**Cell 4: Define Data Extraction Function**
```python
def extract_question_fields(data: dict) -> dict:
    """Extract relevant fields from API response."""
    # Extract top-level fields
    # Extract question sub-object fields
    # Extract aggregation data
    # Extract score data
    # Handle different question types
    # Return flat dictionary
```

**Cell 5: Batch Fetch with Rate Limiting**
```python
results = []
for i, qnum in enumerate(question_numbers):
    # Fetch data
    # Extract fields
    # Append to results
    # Print progress every 10 questions
    # Sleep 0.5s between requests (be respectful)
```

**Cell 6: Convert to DataFrame**
```python
df = pd.DataFrame(results)
# Display summary stats
# Display sample rows
```

**Cell 7: Data Quality Checks**
- Count by question_type
- Count by status
- Check resolution completeness
- Check score/coverage availability

**Cell 8: Save to CSV**
```python
output = OUTPUT_DIR / f"Question_Data_from_API_{date.today()}.csv"
df.to_csv(output, index=False)
```

---

### Step 3: Output Schema

**Proposed CSV columns** (30+ fields):

**Identifiers:**
- `question_id` — integer
- `title` — full question title
- `short_title`
- `slug`

**Metadata:**
- `question_type` — binary, numeric, multiple_choice, date, group
- `status` — open, closed, resolved, etc.
- `resolved` — boolean
- `resolution` — resolution value (if resolved)
- `author_username`
- `curation_status`

**Dates:**
- `created_at`
- `published_at`
- `open_time`
- `actual_close_time`
- `actual_resolve_time`
- `resolution_set_time`

**Counts:**
- `comment_count`
- `nr_forecasters` — total forecasters
- `forecasts_count` — total forecasts submitted
- `community_forecaster_count` — from aggregations

**Tournament:**
- `tournament_id` — from projects.default_project.id
- `tournament_name` — from projects.default_project.name
- `tournament_slug`
- `question_weight` — from question.question_weight

**Community Forecast:**
- `community_forecast` — formatted string (probability or range)
- `community_forecast_mean` — numeric mean
- `community_interval_lower` — lower bound
- `community_interval_upper` — upper bound

**Score Data (if available):**
- `coverage` — 0.0 to 1.0
- `peer_score`
- `baseline_score`
- `spot_peer_score`
- `spot_baseline_score`

**Question-type specific:**
- `mc_options` — JSON array for MC questions
- `numeric_range_min` — for numeric
- `numeric_range_max` — for numeric
- `open_upper_bound` — boolean
- `open_lower_bound` — boolean

**Text (optional, for reference):**
- `description` — full question text
- `resolution_criteria`
- `fine_print`

---

### Step 4: Enhancements (Optional)

**A. Bot-Specific Forecasts (if authenticated)**
- Add METACULUS_TOKEN authentication
- Fetch `/api2/questions/{id}/forecast/` for bot's predictions
- Extract: `my_forecast`, `my_forecast_time`, `my_latest_forecast`

**B. Tournament Leaderboard**
- Endpoint: `/api2/leaderboards/?project=32916`
- Extract: username, rank, score, coverage, contribution_count
- Save to separate CSV

**C. Forecast History**
- Endpoint: `/api2/questions/{id}/prediction_timeseries/`
- Get community prediction over time
- Could plot or analyze trends

**D. Merge with Run Data**
- Join API data with run-question map (008a)
- Add columns: `run_id`, `run_timestamp`, `github_run_url`
- Track which runs processed which questions

---

## Advantages Over HTML Parsing

| Feature | HTML (009a) | API (010) |
|---|---|---|
| **Resolution values** | 6 of 13 (46%) | All resolved Qs (100%) |
| **Forecaster counts** | 0 (broken) | All questions |
| **Comment counts** | 0 (broken) | All questions |
| **Status reliability** | Inferred from score | Authoritative |
| **Coverage/scores** | Via script parsing | Direct from API |
| **Tournament info** | Generic | Full metadata |
| **Question types** | Inferred from HTML | Explicit field |
| **Dates** | Not available | All timestamps |
| **Community forecasts** | Partial | Complete with intervals |
| **Stability** | Breaks with HTML changes | Stable API contract |
| **Bot forecasts** | Not available | Available with auth |

---

## Rate Limiting & Ethics

**Respectful API Usage:**
- Sleep 0.5-1 second between requests (~145 questions = ~2-3 minutes)
- Use exponential backoff on errors
- Cache responses to avoid re-fetching
- Consider batch endpoints if available

**Error Handling:**
- Catch HTTP errors (404, 500, etc.)
- Log failed requests
- Continue on individual failures
- Report summary at end

---

## Testing Strategy

**Phase 1: Single Question Test**
1. Fetch Q41451 (resolved MC question with score)
2. Verify all fields extract correctly
3. Check data matches HTML extraction

**Phase 2: Small Batch**
1. Test on 10 questions of mixed types
2. Verify binary, numeric, MC, group handling
3. Check resolved vs open questions

**Phase 3: Full Run**
1. Process all ~145 questions
2. Compare with 009a HTML output for overlap
3. Verify completeness

---

## Deliverables

**Primary Output:**
- `products/Question_Data_from_API_2026-02-10.csv` — comprehensive question data

**Supporting Files:**
- `jupyter/010_Question_Data_from_API_02-10-2026.ipynb` — extraction notebook
- `conversation and context docs/Metaculus API Question Data Extraction Session 02-10-2026.md` — session notes

**Optional Outputs:**
- `products/Tournament_Leaderboard_from_API_2026-02-10.csv` — if leaderboard endpoint works
- `products/Question_Data_Comparison_HTML_vs_API.xlsx` — side-by-side comparison

---

## Timeline Estimate

**Development:**
- Setup & single question test: 15 min
- Data extraction function: 30 min
- Batch processing: 15 min
- Output formatting: 15 min
**Total:** ~1.5 hours

**Execution:**
- API calls (145 questions @ 0.5s): ~3 minutes
- Data processing: ~1 minute
**Total:** ~5 minutes per run

---

## Next Steps

1. ✅ API investigation (completed)
2. ⬜ Create notebook 010
3. ⬜ Test single question extraction
4. ⬜ Develop full extraction pipeline
5. ⬜ Run on complete question list
6. ⬜ Compare with HTML output (009a)
7. ⬜ Document findings

---

## References

**API Documentation:**
- [Metaculus API 2.0.0 OAS3](https://www.metaculus.com/api/)
- [Metaculus Forecasting Tools (GitHub)](https://github.com/Metaculus/forecasting-tools)
- [API Updates Notebook](https://www.metaculus.com/notebooks/28595/)

**Related Project Files:**
- `products/Run_Question_Map_2026-02-09_v02.csv` — input question list
- `products/Question_Data_from_HTML_2026-02-10.csv` — HTML extraction for comparison
- `jupyter/008a_Run_Question_Number_Map_02-09-2026.ipynb` — source of question list
- `jupyter/009a_Question_Data_from_HTML_02-10-2026.ipynb` — HTML extraction notebook

---

## Open Questions

1. **Authentication:** Do we need METACULUS_TOKEN to access bot's own forecasts?
2. **Rate limits:** What are the actual API rate limits?
3. **Batch endpoints:** Is there a bulk question fetch endpoint?
4. **Historical data:** Can we get bot's forecast history over time?
5. **MiniBench questions:** Are the 79 non-Spring questions accessible via API?
