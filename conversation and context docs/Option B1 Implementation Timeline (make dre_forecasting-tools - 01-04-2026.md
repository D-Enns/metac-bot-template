# Option B1 Implementation Timeline - Tournament Deadline

**Date:** January 4, 2026
**Deadline:** 5:00 PM Denver Time
**Objective:** Move all forecasting-tools extensions to new file + implement Phase 1 metadata

---

## Time Budget Analysis

**Total estimated time:** 50-70 minutes
**Recommended buffer:** 30 minutes for unexpected issues
**Total time needed:** 80-100 minutes (~1.5 hours)

**Current time check needed:** Run this to see how much time you have:
```bash
TZ='America/Denver' date
```

---

## Detailed Implementation Steps

### Phase A: Create New File Structure (15 minutes)

#### Step A1: Create dre_forecasting_tools.py (3 min)
**Action:** Create new file with base class structure

**File:** `dre_forecasting_tools.py`

**Content:**
```python
"""
Custom extensions to Metaculus forecasting-tools library
Author: Dre
Date: January 4, 2026
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C

from forecasting_tools import (
    BinaryQuestion,
    MetaculusQuestion,
    MultipleChoiceQuestion,
    NumericQuestion,
    NumericDistribution,
    PredictedOptionList,
    PredictionTypes,
    ForecastBot,
    clean_indents,
)
from forecasting_tools.data_models.forecast_report import ResearchWithPredictions

logger = logging.getLogger(__name__)


class SpringTemplateBotExtended(ForecastBot):
    """
    Extended version of ForecastBot with custom aggregation and forecast saving.

    Extensions:
    - GPR-based prediction aggregation
    - Enhanced forecast summary saving with metadata
    - Future: Condensed summary generation
    """

    # Methods will be added here
    pass
```

**Verification:**
```bash
poetry run python -m py_compile dre_forecasting_tools.py
```

---

#### Step A2: Update main.py imports (2 min)
**Action:** Add import at top of main.py

**Add after existing imports:**
```python
from dre_forecasting_tools import SpringTemplateBotExtended
```

**Change bot initialization (find line ~1415):**
```python
# OLD:
template_bot = SpringTemplateBot2026(

# NEW:
template_bot = SpringTemplateBotExtended(
```

**Verification:**
```bash
poetry run python -c "from dre_forecasting_tools import SpringTemplateBotExtended; print('Import successful')"
```

---

### Phase B: Move GPR Aggregation Code (10 minutes)

#### Step B1: Copy _aggregate_predictions() method (5 min)

**From main.py (lines 539-621):**
Copy the entire `async def _aggregate_predictions()` method

**To dre_forecasting_tools.py:**
Paste inside `SpringTemplateBotExtended` class

**Code to move:**
```python
    async def _aggregate_predictions(
        self,
        predictions: list,
        question: MetaculusQuestion,
    ) -> PredictionTypes:
        """
        Custom GPR-based aggregation for predictions.
        Overrides the default aggregation in ForecastBot.
        """
        # [Full method - 83 lines]
```

**Important:** Keep exact indentation (4 spaces for class methods)

---

#### Step B2: Remove from main.py (2 min)

**Action:** Delete lines 537-621 from main.py

**Leave this comment in its place:**
```python
    # GPR aggregation moved to dre_forecasting_tools.py
```

---

#### Step B3: Test GPR code compiles (3 min)

```bash
poetry run python -m py_compile dre_forecasting_tools.py
```

If error, check:
- Indentation (should be 4 spaces)
- All imports present at top of file
- Class structure correct

---

### Phase C: Move Forecast Saving Code (15 minutes)

#### Step C1: Add _get_tournament_name() helper (5 min)

**To dre_forecasting_tools.py:**

Add inside `SpringTemplateBotExtended` class:

```python
    def _get_tournament_name(self, question: MetaculusQuestion) -> tuple[str, str]:
        """
        Extract human-readable tournament name from question.
        Returns: (slug, readable_name)
        """
        slug = "unknown"
        readable_name = "Unknown Tournament"

        if hasattr(question, 'tournament_slugs') and question.tournament_slugs:
            slug = question.tournament_slugs[0]
        elif hasattr(question, 'post') and hasattr(question.post, 'projects'):
            if question.post.projects:
                slug = str(question.post.projects[0])

        tournament_map = {
            'ai-forecasting-benchmark-2024': 'AI Forecasting Benchmark 2024',
            'ai-forecasting-benchmark-2025': 'AI Forecasting Benchmark 2025',
            'ai-forecasting-benchmark-2026': 'Spring 2026 AI Forecasting Competition',
            'current-ai-competition': 'Spring 2026 AI Forecasting Competition',
            'spring-2026-ai-forecasting-competition': 'Spring 2026 AI Forecasting Competition',
            'minibench': 'MiniBench',
            'metaculus-cup': 'Metaculus Cup',
            'ai-2027': 'AI 2027 Tournament',
        }

        readable_name = tournament_map.get(slug, slug.replace('-', ' ').title())
        slug_clean = slug.replace('-', '_')

        return slug_clean, readable_name
```

---

#### Step C2: Update _save_full_forecast_copy() with metadata (7 min)

**To dre_forecasting_tools.py:**

```python
    def _save_full_forecast_copy(
        self,
        full_explanation: str,
        question: MetaculusQuestion,
    ) -> None:
        """Save complete forecast explanation with enhanced metadata"""
        reports_dir = Path("forecast_summaries")
        reports_dir.mkdir(parents=True, exist_ok=True)

        question_id = question.page_url.rstrip('/').split('/')[-1]
        tournament_slug, tournament_readable = self._get_tournament_name(question)

        counter = 1
        while True:
            filename = f"{question_id}_{tournament_slug}_full_{counter}.md"
            filepath = reports_dir / filename
            if not filepath.exists():
                break
            counter += 1

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        metadata_header = clean_indents(
            f"""
            # FORECAST METADATA
            **Forecast ID**: q{question_id}
            **Question URL**: {question.page_url}
            **Tournament**: {tournament_readable}
            **Forecast Date**: {timestamp}
            **Bot Version**: {self.__class__.__name__}

            ---

            """
        )

        complete_content = metadata_header + full_explanation

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(complete_content)

        logger.info(f"Saved full forecast to {filepath}")
```

---

#### Step C3: Copy _create_comment() override (3 min)

**From main.py (lines 1427-1452):**

**To dre_forecasting_tools.py:**

```python
    def _create_comment(
        self,
        question: MetaculusQuestion,
        research_prediction_collections: list[ResearchWithPredictions],
        aggregated_prediction: PredictionTypes,
        final_cost: float,
        time_spent_in_minutes: float,
    ) -> str:
        """
        Override to save full forecast locally before posting to Metaculus.
        The posted forecast remains unchanged.
        """
        full_explanation = super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        self._save_full_forecast_copy(full_explanation, question)

        return full_explanation
```

---

### Phase D: Clean Up main.py (5 minutes)

#### Step D1: Remove moved code from main.py (3 min)

**Delete these sections:**
1. Lines 1388-1452 (entire "FORECAST SUMMARY SAVING" section)
2. Keep the section comment as placeholder:

```python
    ##################################### FORECAST SUMMARY SAVING #####################################
    # Forecast saving functionality moved to dre_forecasting_tools.py
```

---

#### Step D2: Verify main.py structure (2 min)

**What should remain in SpringTemplateBot2026 class:**
- ✅ `run_research()`
- ✅ `_run_forecast_on_binary()`
- ✅ `_run_forecast_on_multiple_choice()`
- ✅ `_run_forecast_on_numeric()`
- ✅ `_run_forecast_on_date()`
- ✅ `_run_forecast_on_conditional()`
- ❌ NO `_aggregate_predictions()` (moved)
- ❌ NO forecast saving methods (moved)

**Check class ends properly:**
```python
class SpringTemplateBot2026(ForecastBot):
    # ... methods ...

    def _get_conditional_disclaimer_if_necessary(
        self, question: MetaculusQuestion
    ) -> str:
        # ... (last method in class)


if __name__ == "__main__":
    # ... initialization ...
```

---

### Phase E: Testing & Verification (20 minutes)

#### Step E1: Syntax check (2 min)

```bash
poetry run python -m py_compile dre_forecasting_tools.py
poetry run python -m py_compile main.py
```

**Expected:** Both compile without errors

---

#### Step E2: Import test (2 min)

```bash
poetry run python -c "from dre_forecasting_tools import SpringTemplateBotExtended; print('Success')"
```

**Expected:** "Success" printed

---

#### Step E3: Test bot initialization (3 min)

**Create test script:** `test_import.py`

```python
from dre_forecasting_tools import SpringTemplateBotExtended
from forecasting_tools import GeneralLlm

bot = SpringTemplateBotExtended(
    research_reports_per_question=1,
    predictions_per_research_report=2,
    publish_reports_to_metaculus=False,
)

print("Bot initialized successfully")
print(f"Bot class: {bot.__class__.__name__}")
print(f"Has _aggregate_predictions: {hasattr(bot, '_aggregate_predictions')}")
print(f"Has _save_full_forecast_copy: {hasattr(bot, '_save_full_forecast_copy')}")
print(f"Has _get_tournament_name: {hasattr(bot, '_get_tournament_name')}")
```

**Run:**
```bash
poetry run python test_import.py
```

**Expected output:**
```
Bot initialized successfully
Bot class: SpringTemplateBotExtended
Has _aggregate_predictions: True
Has _save_full_forecast_copy: True
Has _get_tournament_name: True
```

---

#### Step E4: Test on dre_test_bot.yaml (10 min)

**Commit and push:**
```bash
git add dre_forecasting_tools.py main.py
git commit -m "Refactor: Move forecasting extensions to dre_forecasting_tools.py"
git push
```

**Run workflow:**
1. Go to GitHub Actions
2. Run "Dre Test Bot" workflow
3. Wait for completion

**Check workflow logs for:**
- ✅ No import errors
- ✅ Bot runs successfully
- ✅ "Saved full forecast to..." message appears
- ✅ Forecast posted to Metaculus

---

#### Step E5: Verify output (3 min)

**After workflow completes:**

1. **Download artifact** or **git pull** (if auto-commit enabled)

2. **Check forecast file:**
   - File exists: `forecast_summaries/q{id}_{tournament}_full_1.md`
   - Has metadata header with all fields
   - Has full forecast after metadata

3. **Check Metaculus:**
   - Forecast posted successfully
   - Prediction value correct

---

### Phase F: Final Verification (10 minutes)

#### Step F1: Verify metadata content (5 min)

**Open saved forecast file and verify:**

```markdown
# FORECAST METADATA
**Forecast ID**: q14333
**Question URL**: https://www.metaculus.com/questions/14333/
**Tournament**: MiniBench (or Spring 2026 AI Forecasting Competition)
**Forecast Date**: 2026-01-04 14:23:15 UTC
**Bot Version**: SpringTemplateBotExtended

---

# SUMMARY
*Question*: ...
```

**Check:**
- ✅ Forecast ID matches question
- ✅ URL is correct and clickable
- ✅ Tournament name is readable (not slug)
- ✅ Timestamp is recent and in UTC
- ✅ Bot version shows "SpringTemplateBotExtended"

---

#### Step F2: Verify GPR still works (5 min)

**Check workflow logs:**

Search for aggregation logs (if any exist)

**Or check prediction value:**
- Should be GPR-aggregated (not simple average)
- Compare to individual forecaster values in summary
- GPR should smooth outliers

**If you have multiple forecasters with predictions like:**
- Forecaster 1: 0.45
- Forecaster 2: 0.55
- Forecaster 3: 0.50
- Forecaster 4: 0.52

**Final prediction should be:**
- GPR result: ~0.50-0.51 (smoothed)
- NOT simple average: 0.505

---

## Risk Mitigation Plan

### If Something Breaks

**Symptom:** Import error in workflow

**Fix:**
```bash
# Check exact error in logs
# Likely missing import in dre_forecasting_tools.py
# Add missing import and push
```

---

**Symptom:** Bot initialization fails

**Fix:**
```bash
# Verify SpringTemplateBotExtended inherits from ForecastBot
# Check class definition:
class SpringTemplateBotExtended(ForecastBot):
```

---

**Symptom:** Forecasts don't save

**Fix:**
```bash
# Check _save_full_forecast_copy is being called
# Add debug log at start of method:
logger.info("_save_full_forecast_copy called")
```

---

**Symptom:** GPR aggregation not working

**Fix:**
```bash
# Verify _aggregate_predictions signature matches parent
# Check it's async:
async def _aggregate_predictions(...)
```

---

### Emergency Rollback Plan

**If major issues and running out of time:**

```bash
# Revert to previous commit
git log --oneline -5
git revert HEAD
git push

# Or restore main.py from git
git checkout HEAD~1 main.py
git commit -m "Rollback to working version"
git push
```

---

## Success Criteria Checklist

Before 5 PM, verify ALL of these:

- [ ] `dre_forecasting_tools.py` exists and compiles
- [ ] `main.py` imports `SpringTemplateBotExtended` successfully
- [ ] Bot initializes without errors
- [ ] Workflow runs successfully
- [ ] Forecast is saved with metadata header
- [ ] Metadata shows readable tournament name
- [ ] Forecast is posted to Metaculus
- [ ] GPR aggregation still functions
- [ ] No errors in workflow logs

---

## Timeline Summary

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| A1 | Create dre_forecasting_tools.py | 3 min | 3 min |
| A2 | Update main.py imports | 2 min | 5 min |
| B1 | Copy GPR aggregation | 5 min | 10 min |
| B2 | Remove from main.py | 2 min | 12 min |
| B3 | Test GPR compiles | 3 min | 15 min |
| C1 | Add tournament helper | 5 min | 20 min |
| C2 | Update save method | 7 min | 27 min |
| C3 | Copy _create_comment | 3 min | 30 min |
| D1 | Clean up main.py | 3 min | 33 min |
| D2 | Verify structure | 2 min | 35 min |
| E1 | Syntax check | 2 min | 37 min |
| E2 | Import test | 2 min | 39 min |
| E3 | Bot init test | 3 min | 42 min |
| E4 | Workflow test | 10 min | 52 min |
| E5 | Verify output | 3 min | 55 min |
| F1 | Check metadata | 5 min | 60 min |
| F2 | Verify GPR | 5 min | 65 min |
| **Buffer** | Unexpected issues | 15-30 min | **80-95 min** |

**Total time needed: 80-95 minutes (1.3-1.6 hours)**

---

## Next Steps After Tournament Starts

With working code in place, you can:

1. **Phase 2:** Add auto-commit to workflow
2. **Phase 3:** Implement LLM-based condensed summaries
3. **Phase 4:** Create production workflow
4. **Future:** Continue refactoring and improvements

---

*Created: January 4, 2026*
*Deadline: 5:00 PM Denver Time*
*Status: Ready to execute*
