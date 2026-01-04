# Forecast Summaries - Complete Implementation Plan

**Date:** January 4, 2026
**Status:** Planning Phase

---

## Overview

Transform the basic forecast summary saving into a complete system with:
1. ✅ Automated local storage (no manual download)
2. ✅ Enhanced metadata in saved files
3. ✅ Condensed summaries for Metaculus posting
4. ✅ Production-ready workflow

---

## Architecture Decision: Automated Download (Goal 1)

### Problem
Artifacts require manual download from GitHub Actions UI - not ideal for automation.

### Solution Options Evaluated

| Option | Approach | Pros | Cons | Decision |
|--------|----------|------|------|----------|
| A | Download artifact via GitHub API | Works across runs | Complex, needs auth, timing issues | ❌ No |
| B | Second workflow downloads artifact | Automated | Complex dependencies, timing issues | ❌ No |
| **C** | **Auto-commit to repo** | **Simple, reliable, fully automated** | **Adds commits to history** | **✅ YES** |

### Selected Architecture: Auto-Commit

**How it works:**
1. Bot runs and creates forecast summaries in `forecast_summaries/`
2. Workflow automatically commits files back to repo
3. Files appear in your local directory on next `git pull`
4. No manual download needed!

**Implementation:**
- Add git commit step to workflow after bot runs
- Configure git user for commits
- Only commit `forecast_summaries/` directory
- Use meaningful commit message with question ID

---

## Goal 1: Automated Local Storage

### Current State
- ✅ Files created on GitHub Actions runner
- ✅ Files uploaded as artifacts
- ❌ Requires manual download and extraction

### Target State
- ✅ Files automatically committed to repo
- ✅ Files appear locally after `git pull`
- ✅ No zip extraction needed

### Implementation Steps

**Step 1.1: Modify Workflow - Add Auto-Commit**

Add to `dre_test_bot.yaml` after "Run bot" step:

```yaml
      - name: Commit forecast summaries
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add forecast_summaries/
          git diff --staged --quiet || git commit -m "Add forecast summaries from run ${{ github.run_number }}"
          git push
```

**Step 1.2: Update Workflow Permissions**

Add at top of workflow (after `concurrency:`):

```yaml
permissions:
  contents: write
```

**Step 1.3: Remove Artifact Upload (Optional)**

Since files are now committed, artifact upload is redundant. Can remove the "Upload forecast summaries" step.

**Result:**
- Files automatically appear in repo
- Local `git pull` gets latest forecasts
- Fully automated!

---

## Goal 2: Enhanced Metadata in Saved Files

### Current File Contents
```markdown
# SUMMARY
*Question*: Will XYZ happen?
*Final Prediction*: 75.0%
...
```

### Target File Contents
```markdown
# FORECAST METADATA
**Forecast ID**: q14333
**Question URL**: https://www.metaculus.com/questions/14333/
**Tournament**: Spring 2026 AI Forecasting Competition
**Forecast Date**: 2026-01-04 14:23:15 UTC
**Bot Version**: SpringTemplateBot2026

---

# SUMMARY
*Question*: Will XYZ happen?
*Final Prediction*: 75.0%
...
```

### Implementation Steps

**Step 2.1: Extract Tournament Name**

Add helper method to `SpringTemplateBot2026`:

```python
def _get_tournament_name(self, question: MetaculusQuestion) -> str:
    """Extract human-readable tournament name from question"""
    if hasattr(question, 'tournament_slugs') and question.tournament_slugs:
        slug = question.tournament_slugs[0]

        # Map common tournament slugs to readable names
        tournament_map = {
            'ai-forecasting-benchmark-2024': 'AI Forecasting Benchmark 2024',
            'ai-forecasting-benchmark-2025': 'AI Forecasting Benchmark 2025',
            'ai-forecasting-benchmark-2026': 'Spring 2026 AI Forecasting Competition',
            'current-ai-competition': 'Spring 2026 AI Forecasting Competition',
            'minibench': 'MiniBench',
            'metaculus-cup': 'Metaculus Cup',
        }

        return tournament_map.get(slug, slug.replace('-', ' ').title())

    return "Unknown Tournament"
```

**Step 2.2: Modify `_save_full_forecast_copy()`**

Update to add metadata header:

```python
def _save_full_forecast_copy(
    self,
    full_explanation: str,
    question: MetaculusQuestion,
) -> None:
    """Save complete forecast explanation with enhanced metadata"""
    from datetime import datetime, timezone

    # Create directory
    reports_dir = Path("forecast_summaries")
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Extract question ID and tournament
    question_id = question.page_url.rstrip('/').split('/')[-1]
    tournament_name = self._get_tournament_name(question)
    tournament_slug = question.tournament_slugs[0] if hasattr(question, 'tournament_slugs') and question.tournament_slugs else "unknown"

    # Find next counter
    counter = 1
    while True:
        filename = f"{question_id}_{tournament_slug}_full_{counter}.md"
        filepath = reports_dir / filename
        if not filepath.exists():
            break
        counter += 1

    # Create metadata header
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    metadata_header = clean_indents(
        f"""
        # FORECAST METADATA
        **Forecast ID**: q{question_id}
        **Question URL**: {question.page_url}
        **Tournament**: {tournament_name}
        **Forecast Date**: {timestamp}
        **Bot Version**: {self.__class__.__name__}

        ---

        """
    )

    # Combine metadata + original explanation
    complete_content = metadata_header + full_explanation

    # Save file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(complete_content)

    logger.info(f"Saved full forecast to {filepath}")
```

**Result:**
- Every saved forecast has rich metadata header
- Easy to identify which question and tournament
- Includes timestamp and bot version for tracking

---

## Goal 3: Condensed Summary for Metaculus API

### Current Behavior
- Full explanation (10,000-50,000 chars) posted to Metaculus
- Contains ALL research, ALL forecaster reasoning
- Can be overwhelming for readers

### Target Behavior
- **Full version**: Saved locally with all details
- **Condensed version**: Posted to Metaculus (3,000-5,000 chars)
- Condensed includes:
  - Question and prediction
  - Key reasoning from first forecaster (truncated)
  - Brief research highlights
  - Note that full analysis is available

### Implementation Approach: LLM-Based Summarization

**Decision:** Use an LLM to intelligently summarize rather than programmatic truncation.

**Why LLM approach:**
- ✅ Intelligent extraction of key insights (not blind truncation)
- ✅ Maintains coherent narrative flow
- ✅ Better readability
- ✅ Preserves most important reasoning

### Model Selection for Summarization

| Model | Input Cost | Output Cost | Best For | Recommendation |
|-------|------------|-------------|----------|----------------|
| **oss-120b (exacto)** | $0.05/1M | $0.24/1M | Cost efficiency | ⭐ **Recommended** |
| gpt-4o-mini | $0.15/1M | $0.60/1M | Speed | Good alternative |

**Cost per condensed summary (estimated):**
- Input: ~10k tokens (full explanation) = $0.0005-0.0015
- Output: ~2k tokens (condensed) = $0.0048-0.0120
- **Total: ~$0.005-0.013 per summary**

**Recommended:** `openrouter/openai/gpt-oss-120b:exacto` (cheaper + high quality)

### Implementation Steps

**Step 3.1: Configure Summarizer LLM**

In bot initialization, add or update:

```python
template_bot = SpringTemplateBot2026(
    # ... existing config ...
    llms={
        "default": GeneralLlm(...),
        "summarizer": "openrouter/openai/gpt-oss-120b:exacto",  # For condensed summaries
        "parser": "openrouter/openai/o4-mini",
        # ... other llms ...
    },
)
```

**Alternative models:**
- `"openrouter/openai/gpt-4o-mini"` - If you prefer faster response
- `"openrouter/openai/gpt-oss-120b"` - Non-exacto version (slightly cheaper, less curated)

**Step 3.2: Create LLM-Based Condensed Summary Method**

Add to `SpringTemplateBot2026`:

```python
async def _create_condensed_summary(
    self,
    full_explanation: str,
    aggregated_prediction: PredictionTypes,
    question: MetaculusQuestion,
    final_cost: float,
    time_spent_in_minutes: float
) -> str:
    """Use LLM to create intelligent condensed summary"""
    from forecasting_tools.data_models.data_organizer import DataOrganizer

    # Get readable prediction for reference
    report_type = DataOrganizer.get_report_type_for_question_type(type(question))
    readable_prediction = report_type.make_readable_prediction(aggregated_prediction)

    # Get summarizer LLM
    summarizer_llm = self.get_llm("summarizer", "llm")

    # Create summarization prompt
    prompt = clean_indents(
        f"""
        Create a condensed forecast summary for posting to Metaculus.

        **Requirements:**
        - Target length: 3,000-5,000 characters
        - Include the final prediction clearly
        - Extract and present the 2-3 most important reasons for this forecast
        - Highlight the most critical research findings that support the prediction
        - Maintain clarity and readability
        - Keep the professional tone
        - End with a brief methodology note

        **Question:** {question.question_text}
        **Final Prediction:** {readable_prediction}

        **Original Full Forecast Analysis:**
        {full_explanation[:15000]}

        Create a condensed version that captures the essence of the reasoning while being significantly shorter.
        Start directly with a header like "# Forecast Summary" and organize the content clearly.
        """
    )

    # Generate condensed summary
    condensed = await summarizer_llm.invoke(prompt)

    # Add metadata footer
    footer = clean_indents(
        f"""

        ---
        *Methodology: Multi-world scenario analysis with GPR aggregation*
        *Cost: ${round(final_cost, 4)} | Time: {round(time_spent_in_minutes, 2)} minutes*
        *Full analysis archived with complete research and all forecaster reasoning*
        """
    )

    return condensed + footer
```

**Step 3.3: Modify `_create_comment()` to Use Condensed Version**

Update existing override to be async:

```python
async def _create_comment(
    self,
    question: MetaculusQuestion,
    research_prediction_collections: list[ResearchWithPredictions],
    aggregated_prediction: PredictionTypes,
    final_cost: float,
    time_spent_in_minutes: float,
) -> str:
    """
    Override to:
    1. Save full report locally with metadata
    2. Return condensed version for Metaculus API
    """
    # Generate full explanation using parent method
    full_explanation = super()._create_comment(
        question,
        research_prediction_collections,
        aggregated_prediction,
        final_cost,
        time_spent_in_minutes
    )

    # Save full version locally with metadata (Goal 2)
    self._save_full_forecast_copy(full_explanation, question)

    # Create condensed version using LLM (Goal 3)
    condensed_explanation = await self._create_condensed_summary(
        full_explanation,
        aggregated_prediction,
        question,
        final_cost,
        time_spent_in_minutes
    )

    # Return condensed version for API submission
    return condensed_explanation
```

**Important:** Check if parent's `_create_comment()` needs to be called with `await`. If the forecasting-tools library updates to make it async, add `await` before `super()._create_comment(...)`.

**Result:**
- Full detailed analysis saved locally
- Clean, readable summary posted to Metaculus
- Users can see key reasoning without overwhelming detail

---

## Goal 4: Production Workflow for Tournament Forecasting

### Current Workflows
- `run_bot_on_tournament.yaml` - Production tournament forecasting
- `test_bot.yaml` - Original test workflow
- `dre_test_bot.yaml` - Test workflow with our changes

### Target: New Production Workflow

Create `forecast_with_summaries.yaml` that:
- Runs on AI Competition and MiniBench tournaments
- Saves forecast summaries automatically
- Commits summaries to repo
- Can run on schedule or manual trigger

### Implementation Steps

**Step 4.1: Create Production Workflow**

New file: `.github/workflows/forecast_with_summaries.yaml`

```yaml
name: Forecast with Summaries

on:
  workflow_dispatch:
    inputs:
      tournament:
        description: 'Tournament to forecast on'
        required: true
        type: choice
        options:
          - both
          - ai_competition
          - minibench
  schedule:
    # Run daily at 9 AM UTC (adjust as needed)
    - cron: '0 9 * * *'

permissions:
  contents: write

concurrency:
  group: forecast-tournament-${{ github.ref }}
  cancel-in-progress: false

jobs:
  forecast_job:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install poetry
        uses: snok/install-poetry@v1
        with:
          virtualenvs-create: true
          virtualenvs-in-project: true
          installer-parallel: true

      - name: Install dependencies
        run: poetry install --no-interaction --no-root

      - name: Run bot on tournaments
        run: |
          poetry run python main.py --mode tournament
        env:
          METACULUS_TOKEN: ${{ secrets.METACULUS_TOKEN }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ASKNEWS_CLIENT_ID: ${{ secrets.ASKNEWS_CLIENT_ID }}
          ASKNEWS_SECRET: ${{ secrets.ASKNEWS_SECRET }}

      - name: Commit forecast summaries
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add forecast_summaries/
          if ! git diff --staged --quiet; then
            git commit -m "Add forecast summaries from run ${{ github.run_number }} [skip ci]"
            git push
          else
            echo "No new forecast summaries to commit"
          fi
```

**Notes:**
- `[skip ci]` in commit message prevents infinite loop
- `if ! git diff --staged --quiet` only commits if there are changes
- Supports manual trigger with tournament selection
- Optional: Schedule for automatic daily runs

**Step 4.2: Test Before Production**

Test sequence:
1. Test with `dre_test_bot.yaml` first
2. Verify auto-commit works
3. Verify condensed summaries post correctly
4. Then deploy `forecast_with_summaries.yaml`

---

## Implementation Order

### Phase 1: Enhanced Metadata (Goal 2) ⭐ START HERE
**Why first:** Simple, low risk, immediate value
1. Add `_get_tournament_name()` method
2. Modify `_save_full_forecast_copy()` to add metadata header
3. Test on `dre_test_bot.yaml`
4. Verify metadata appears correctly

**Estimated time:** 30 minutes
**Risk:** Low

---

### Phase 2: Auto-Commit (Goal 1)
**Why second:** Enables automation before adding complexity
1. Add permissions to `dre_test_bot.yaml`
2. Add git commit step to workflow
3. Test workflow run
4. Verify files appear in repo after push
5. Test local `git pull` to get files

**Estimated time:** 45 minutes
**Risk:** Medium (git config, permissions)

---

### Phase 3: Condensed Summaries (Goal 3)
**Why third:** Most complex, builds on previous phases
1. Implement `_create_condensed_summary()` method
2. Modify `_create_comment()` to use condensed version
3. Test with one question
4. Compare full (saved) vs condensed (posted) versions
5. Adjust truncation logic if needed

**Estimated time:** 1-2 hours
**Risk:** Medium (need to tune truncation, verify posting works)

---

### Phase 4: Production Workflow (Goal 4)
**Why last:** Combines all features, needs thorough testing
1. Create `forecast_with_summaries.yaml`
2. Test on test_questions mode first
3. Dry run on tournament (with posting disabled)
4. Production run with posting enabled
5. Monitor first few runs closely

**Estimated time:** 1 hour (mostly testing)
**Risk:** Low (using proven components)

---

## Testing Strategy

### Test After Each Phase

**Phase 1 Test:**
```bash
# Run bot locally
poetry run python main.py --mode test_questions

# Check file
cat forecast_summaries/[latest_file]

# Verify:
# - Metadata header present
# - Question URL correct
# - Tournament name readable
# - Timestamp correct
```

**Phase 2 Test:**
```bash
# Run workflow in GitHub Actions
# After completion:
git pull

# Check directory
ls -la forecast_summaries/

# Verify:
# - New files appeared automatically
# - No manual download needed
```

**Phase 3 Test:**
```bash
# Run bot
poetry run python main.py --mode test_questions

# Compare:
# - Local file (full version)
# - Metaculus post (condensed version)

# Verify:
# - Both have same prediction
# - Condensed is significantly shorter
# - Key reasoning preserved
# - Condensed is readable
```

**Phase 4 Test:**
```bash
# Manual trigger in GitHub Actions
# Select "test_questions" first

# Verify:
# - All goals working together
# - Files committed automatically
# - Metaculus posts are condensed
# - Full files have metadata
```

---

## File Structure After Implementation

```
metac_bot_Spring_2026/
├── .github/
│   └── workflows/
│       ├── test_bot.yaml                      # Original (unchanged)
│       ├── dre_test_bot.yaml                  # Testing workflow
│       ├── forecast_with_summaries.yaml       # NEW: Production workflow
│       ├── run_bot_on_tournament.yaml         # OLD: Can deprecate
│       └── run_bot_on_metaculus_cup.yaml      # Keep as-is
├── forecast_summaries/
│   ├── {qid}_ai_forecasting_full_1.md        # Full reports with metadata
│   ├── {qid}_ai_forecasting_full_2.md        # Multiple runs tracked
│   ├── {qid}_minibench_full_1.md             # Per tournament
│   └── ...
├── main.py                                    # Updated with all methods
└── FORECAST_SUMMARIES_IMPLEMENTATION_PLAN.md # This file
```

---

## Expected Outcomes

### Automated Workflow
1. Bot runs on schedule or manual trigger
2. Generates forecasts with full analysis
3. Posts condensed summaries to Metaculus
4. Saves full reports with metadata locally
5. Auto-commits to repo
6. Files available on next `git pull`

### No Manual Steps Required
- ✅ No artifact downloads
- ✅ No file extraction
- ✅ No copy/paste
- ✅ Fully automated archival

### Better User Experience
- **On Metaculus:** Clean, readable condensed summaries
- **In Archive:** Complete detailed analysis
- **For Analysis:** Rich metadata for tracking

---

## Rollback Plan

If issues arise:

**Phase 1 Issue:**
```python
# Comment out metadata header in _save_full_forecast_copy()
# Files will save without metadata header
```

**Phase 2 Issue:**
```yaml
# Remove git commit step from workflow
# Falls back to artifact upload
```

**Phase 3 Issue:**
```python
# In _create_comment(), return full_explanation instead of condensed
# Posts full version to Metaculus (current behavior)
```

**Phase 4 Issue:**
```bash
# Use original run_bot_on_tournament.yaml
# New workflow disabled until issues resolved
```

---

## Success Metrics

After full implementation, verify:

- ✅ Files appear in `forecast_summaries/` without manual download
- ✅ Each file has metadata header with question info
- ✅ Metaculus posts are ~3000-5000 chars (vs 10000-50000 before)
- ✅ Full analysis preserved in local files
- ✅ Multiple forecasts on same question increment counter
- ✅ Tournament names are human-readable
- ✅ Workflow runs without errors
- ✅ No git conflicts or permission issues

---

## Questions to Resolve Before Starting

1. **Condensed summary length:** Confirm 3000-5000 chars is good target
2. **Git commits:** OK to have bot commits in history?
3. **Schedule:** Should production workflow run daily? What time?
4. **Tournament focus:** Both AI Competition + MiniBench, or one?
5. **File retention:** Keep all forecast files indefinitely, or prune old ones?

---

**Ready to begin?**

Recommend starting with **Phase 1 (Enhanced Metadata)** as it's:
- Low risk
- Immediate value
- Foundation for later phases
- Easy to test and verify

---

*Last Updated: January 4, 2026*
*Status: Planning complete, ready for implementation*
