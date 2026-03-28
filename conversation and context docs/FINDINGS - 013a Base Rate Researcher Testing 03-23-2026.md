# Findings: 013a Base Rate Researcher Testing
**Date**: 2026-03-23
**Notebooks**: `013a_MultiModel_BaseRate_Researcher_03-22-2026.ipynb`, `013a01_Online_Model_Times_03-23-2026.ipynb`

---

## Key Findings

### 1. Training-Data-Only Pipeline Works Well (013a, Cells 4–9)

The core multi-model base rate pipeline — GPT-5.2 + Claude Opus 4.6 queried in parallel, synthesized by o4-mini — runs successfully end-to-end.

- **GPT-5.2** and **Claude Opus 4.6** both produce substantive base rate analyses from training data alone
- **o4-mini synthesizer** produces a coherent consensus report that flags agreements and disagreements
- Synthesis correctly identified that both models agreed on the direction (modest drift downward in employment share) while differing on specific rate estimates
- Total wall time for training-data pipeline: parallel query time + synthesis time (well within 60s timeout)

### 2. `:online` Web Search Is Reliable for Claude, Broken for GPT-5.2 (013a01)

Tested each model with the `:online` suffix (web-grounded search via OpenRouter) 3 times on the same question with a 150s timeout.

| Model | Success Rate | Latency (mean) | Notes |
|-------|-------------|----------------|-------|
| `openai/gpt-5.2:online` | **0/3** | All timed out at 150s | Completely non-functional through OpenRouter |
| `anthropic/claude-opus-4-6:online` | **3/3** | **64.9s** (59–72s range) | Reliable, ~7K chars output |

**Conclusion**: GPT-5.2:online is not viable through OpenRouter. This is not run-to-run variability — it's a consistent failure pattern. Claude Opus:online works reliably with ~65s latency.

### 3. Research Context Integration

The `_build_base_rate_prompt()` function now accepts a `research_context` parameter that embeds externally provided news/research (e.g., from AskNews) directly into the base rate prompt. Both models use this context to ground their analysis in current evidence rather than relying solely on training data.

---

## Recommended Architecture Update

Based on these findings, the original 2-model architecture should be revised to **3 models**:

### Original (Planning Doc)
```
GPT-5.2 ──────────┐
                   ├──> Synthesizer (o4-mini) ──> Output
Claude Opus 4.6 ──┘
```

### Revised
```
GPT-5.2 (training data) ──────────────┐
                                       ├──> Synthesizer (o4-mini) ──> Output
Claude Opus 4.6 (training data) ──────┤
                                       │
Claude Opus 4.6:online (web search) ──┘
```

**Why 3 models**:
- Two training-data analyses provide diverse anchoring from different training corpora
- One web-grounded analysis finds current data that post-dates training cutoffs
- All three run in parallel via `asyncio.gather()`, so wall time ≈ slowest leg (~65s)
- The synthesizer gets three perspectives: two historical anchors + one current-evidence view
- Cost increase is one additional Claude Opus call (the most expensive model), but the information gain from web search is significant

**Production implications for `research.py`**:
- `get_base_rate_research()` signature needs a third model parameter (or `online_model`)
- Default timeout should be ≥ 80s to accommodate `:online` latency with margin
- `asyncio.gather(return_exceptions=True)` should be used so one model timing out doesn't kill the others

---

## Summarizer A/B Test (013a, Cell 8) — Pending

The o4-mini vs Claude Sonnet 4.6 synthesizer comparison was run but not yet scored. Manual quality assessment needed on:
- Conciseness (1-5)
- Accuracy of comparison (1-5)
- Usefulness as forecast context (1-5)
- Neutrality toward both sources (1-5)

---

## Cost Observations

- Training-data queries are cheap and fast
- Claude Opus 4.6 is the most expensive model (~$15/M input, $75/M output) — adding an `:online` call doubles the Opus cost per question
- Exact per-question cost TBD from the cost tracking cell (013a, Cell 12)

---

## Open Questions

1. **Is GPT-5.2:online broken only for this prompt/question, or universally?** — Could test with a shorter prompt or different question, but 0/3 at 150s suggests a systemic OpenRouter issue
2. **Best synthesizer**: o4-mini vs Claude Sonnet 4.6 — needs manual scoring
3. **Does the third leg (Opus:online) add enough value over just passing research context to the training-data models?** — The training-data models already receive the AskNews research via `research_context`. The `:online` model does its own independent web search, which may find different/better sources. Worth comparing quality.
4. **Timeout strategy for production**: 80s covers the mean (65s) + ~1 std dev, but the max observed was 72s. 90s may be safer. The bot's current default LLM timeout is 80s.

---

## Files

| File | Purpose |
|------|---------|
| `jupyter/013a_MultiModel_BaseRate_Researcher_03-22-2026.ipynb` | Primary prototype — production functions + exploration |
| `jupyter/013a01_Online_Model_Times_03-23-2026.ipynb` | Latency/reliability test for `:online` models |
| `conversation and context docs/PLAN - Historical Data and Base Rates Investigation 03-22-2026.md` | Master planning doc (needs update to reflect 3-model architecture) |
