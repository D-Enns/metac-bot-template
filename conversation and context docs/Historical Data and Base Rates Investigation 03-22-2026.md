# Historical Data and Base Rates Investigation
**Date**: 2026-03-22
**Project**: Metaculus AI Forecasting Bot — Base Rate Research Enhancement
**Related**: `PROJECT - Investigate Historical Data and Baserates Approaches 03-22-2026.md`

---

## Executive Summary

The bot's forecast prompts already instruct the LLM to "consider base rates and analogs," but provide **no actual base rate data** — the LLM relies entirely on training data. The `forecasting-tools` library (already installed as a dependency) ships with a full suite of base rate research tools (`BaseRateResearcher`, `NicheListResearcher`, `Estimator`, `KeyFactorsResearcher`) that are publicly exported but **completely unused** in our bot.

Analysis of top-performing bots from the EA Forum's [Q2 AI Benchmark Results](https://forum.effectivealtruism.org/posts/F2stjK9wHSy3HPEC9/q2-ai-benchmark-results-pros-maintain-clear-lead) shows that **research infrastructure is the #2 differentiator** after model quality (which we already address with GPT-5.2). Our aggregation pipeline (Skew-T, majority-vote validation, 6 runs) is already strong. **Base rate research is the most impactful area we're not yet exploiting.**

LLMs have reasonable base rate knowledge from training data for well-documented domains (mortality, elections, GDP growth), but are weak on niche/recent events, precise counts, correct denominators, and tail-event calibration — exactly the areas where Metaculus tournament questions tend to live. Prompt-only improvements help with the well-documented cases; tool-based research (web-grounded via Perplexity Sonar or Exa) is needed to fill the gap on niche and current-event questions.

Eleven pathways are proposed below, ranging from **no-cost prompt improvements** (implementable today) to a **custom historical data pipeline** (significant engineering investment). The recommended approach is phased: start with free prompt enhancements, then layer on library-based tools as Exa API access is established.

All library-based tools share one critical dependency: **`EXA_API_KEY`** (Exa.ai web search API), which would need to be obtained and added to GitHub Actions secrets.

### Recommended Next Step: Notebook 013d — Multi-Model Base Rate Researcher Prototype

The highest-value next action is to build and test **Option 3: the Multi-Model LLM Base Rate Researcher** in a Jupyter notebook (`jupyter/013d_MultiModel_BaseRate_Researcher_03-22-2026.ipynb`). This approach independently queries GPT-5.2 and Claude 4.6 for base rate analysis on a question, then uses o4-mini to synthesize their responses into a consensus report with confidence levels.

**Why this is the recommended starting point:**
- **No new API keys** — uses existing OpenRouter credits for models we already pay for
- **Web search built in** — both GPT-5.2 and Claude 4.6 support native web search via the `:online` suffix (e.g., `"openrouter/openai/gpt-5.2:online"`), so the researcher can find real-time historical data, not just training-data knowledge
- **Model diversity catches errors** — different training data means different knowledge gaps; when both models agree on a rate, confidence is high; when they disagree, the disagreement is itself useful signal for the forecaster
- **Clean integration path** — the output is a markdown string that appends directly to the existing research context, exactly like AskNews does today. No changes to method signatures, aggregation, or the framework
- **Directly addresses the #1 gap** — the EA Forum analysis shows research infrastructure is the biggest remaining lever, and our forecast prompts already ask about base rates but provide no data to work with

The notebook will test this on 5-6 representative questions across all types (binary, numeric, multiple choice), compare training-data-only vs `:online` web-search variants, and measure cost, latency, and output quality. See Part 7 (Notebook 013d) for the full test plan.

---

## Part 1: Status of Available Tools

### Tools Already in `forecasting-tools` (Installed, Not Used)

| Tool | What It Does | Maturity | Cost per Question |
|------|-------------|----------|-------------------|
| **BaseRateResearcher** | Converts a question into reference classes (numerator/denominator), searches the web for historical counts, computes a historical rate, and extrapolates to future probability | Experimental | ~$0.01-0.05 (Exa search + LLM) |
| **NicheListResearcher** | Exhaustively lists all instances of a thing (max 30 items), deduplicates via semantic similarity + LLM, fact-checks each item with criteria and citations | Experimental | ~$0.05-0.15 |
| **Estimator** | Fermi-style size estimation with cited reasoning steps — useful for denominator estimation in base rates | Experimental | ~$0.01-0.03 |
| **KeyFactorsResearcher** | Finds & scores pros/cons/base-rates for a question using a 10-criteria scorecard (recency, relevance, specificity, predictive power, source reputation, etc.) | Experimental | ~$0.05-0.15 |
| **SmartSearcher** | Web search + LLM synthesis with inline citations via Exa.ai. More configurable than Perplexity. Already imported in main.py but only used for general research | Stable | ~$0.01-0.03 |
| **DataAnalyzer** | Runs code-based data analysis via OpenAI code interpreter agent. Could analyze datasets relevant to forecasting questions | Experimental | ~$0.05-0.20 |
| **ResearchCoordinator** (deprecated) | Orchestrates multi-stage research: brainstorms background + base-rate questions, researches each, produces combined report | Deprecated but functional | ~$0.10-0.30 |

**Import paths** (all publicly exported):
```python
from forecasting_tools import (
    BaseRateResearcher,
    NicheListResearcher,
    Estimator,  # Listed as FermiEstimator in some docs
    KeyFactorsResearcher,
    ScoredKeyFactor,
    SmartSearcher,
    DataAnalyzer,
    FactCheckedItem,
)
```

### BaseRateResearcher — Detailed Capabilities

The `BaseRateResearcher` implements an end-to-end pipeline:

1. **Validates** whether a question is suitable for base rate analysis (LLM check)
2. **Determines** appropriate time window (start/end dates) via LLM
3. **Conducts** general background research on the topic
4. **Identifies numerator** reference class — "the thing being counted" (e.g., "successful SpaceX launches")
5. **Decides** whether to measure per-day or per-event (LLM decision with reasoning)
6. **Identifies denominator** reference class (e.g., "total SpaceX launch attempts")
7. **Searches** for actual counts via SmartSearcher/Exa
8. **Calculates** historical rate = numerator / denominator
9. **Extrapolates** to future (if per-day model)
10. **Produces** markdown report with all reasoning and citations

**Strengths**: Fully automated, produces structured output, handles both frequency-based and event-based rates
**Weaknesses**: Experimental, relies on Exa search quality for count accuracy, may fail on questions without clear reference classes, no built-in validation of count accuracy

### KeyFactorsResearcher — Detailed Capabilities

Produces scored, ranked evidence factors:

1. **Brainstorms** background questions (half the research budget)
2. **Brainstorms** base-rate-specific questions (other half)
3. **Researches** each question via SmartSearcher
4. **Scores** every factor on 10 criteria:
   - Recency, relevance, specificness, predictive power, source reputation
   - Is outdated? Includes a number? Includes a date? Key person quote? Overall quality
5. **Ranks** by weighted score (0-45+ scale)
6. **Deduplicates** across all factors
7. **Returns** top-N scored factors with citations and dates

**Strengths**: Structured, scored, prioritized evidence — directly useful for forecast reasoning
**Weaknesses**: Higher cost and latency (multiple Exa searches per question)

---

## Part 1b: Web Search Capabilities Available via OpenRouter

### Key Finding: Claude and OpenAI Models Can Search the Web Directly

Both major model families now offer **native web search** as a built-in capability, all accessible through the OpenRouter platform we already use and pay for. This is directly relevant to base rate research — these models can search Wikipedia, news archives, and historical data sources in real-time.

### OpenRouter Platform

OpenRouter provides a unified interface for web search across multiple providers ([docs](https://openrouter.ai/docs/guides/features/plugins/web-search)). Two equivalent methods to enable search:
- Append `:online` to any model slug: `"openrouter/openai/gpt-5.2:online"`
- Or use plugins explicitly: `"plugins": [{"id": "web"}]`

Domain filtering is supported across all search-enabled models: `include_domains` (e.g., `["wikipedia.org", "*.gov"]`), `exclude_domains`, with wildcard and subpath support.

#### Claude (Anthropic) — Native Web Search

Claude models have robust native web search via Anthropic's search tool ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)):

**Supported models**: Claude Opus 4.6, Opus 4.5, Opus 4.1, Opus 4, Sonnet 4.6, Sonnet 4.5, Sonnet 4, Haiku 4.5

**Dynamic filtering** (Opus 4.6 and Sonnet 4.6 only): Claude writes and executes code to filter search results before they reach the context window, keeping only relevant data and reducing token consumption. Particularly effective for technical documentation and research tasks.

**Cost impact**:
- **$10 per 1,000 searches** (~$0.01 per individual search)
- Plus standard token costs for search-generated content (search results count as input tokens)
- Estimated per-question cost for base rate research: **~$0.01-0.03 additional** (1-3 searches)

**Automatic citations**: Responses include source URLs, titles, and cited text — directly useful for grounding base rate claims.

**Via OpenRouter**: Append `:online` suffix — native Anthropic search pricing is passed through.

#### OpenAI — Native Web Search

OpenAI provides native web search on multiple model families ([docs](https://developers.openai.com/api/docs/guides/tools-web-search)):

**Search-enabled models**:
- `gpt-5`, `gpt-5.2` — via `:online` suffix or `web_search` tool
- `o4-mini`, `o3-deep-research`, `o4-mini-deep-research`
- Dedicated always-search models: `gpt-5-search-api`, `gpt-4o-search-preview` — these **always** retrieve web data before responding

**Cost impact**:
- Native OpenAI search pricing passed through from provider
- Via OpenRouter's `:online` suffix: approximately **$4 per 1,000 search results** (default 5 results per request = ~$0.02 per search-augmented call)
- Estimated per-question cost for base rate research: **~$0.02-0.06 additional** (1-3 search-augmented calls)

#### Perplexity Sonar Models

Built-in web search is Perplexity's core feature — available via OpenRouter:
- `openrouter/perplexity/sonar-pro` — advanced search with citations
- `openrouter/perplexity/sonar-reasoning` — reasoning + search (based on DeepSeek R1)
- `openrouter/perplexity/sonar-pro-search` — agentic deep search (exclusive to OpenRouter)
- Top-ranked in Search Arena evaluations (tied for #1 with Gemini 2.5 Pro Grounding)

#### Exa Search

For models without native search, OpenRouter falls back to **Exa-powered search** using keyword + embeddings-based retrieval. Cost: $4 per 1,000 results. Exa is also the backend for the `forecasting-tools` library's `SmartSearcher` (requires separate `EXA_API_KEY` when used directly outside OpenRouter).

### Integration via `GeneralLlm` (forecasting-tools)

The `GeneralLlm` class already supports web search:
- Accepts `web_search_options` kwarg (passes through to litellm)
- Has a built-in `GeneralLlm.search_context_model(model, search_context_size="high")` classmethod
- Accepts `**kwargs` that pass through to litellm, so OpenRouter's `:online` suffix should work in the model name
- The `:online` suffix via OpenRouter is the simplest integration path — just change the model string

### What This Means for Option 3 (Multi-Model Base Rate Researcher)

The multi-model LLM base rate researcher can be **significantly enhanced** by using web-search-enabled models instead of (or alongside) training-data-only models:

| Configuration | What It Does | Cost per Question |
|--------------|-------------|-------------------|
| GPT-5.2 + Claude 4.6 (training data only) | Cross-validates base rates from training data | ~$0.02-0.08 |
| GPT-5.2`:online` + Claude 4.6`:online` | Both models search the web for real-time base rate data | ~$0.04-0.12 |
| GPT-5.2 + Perplexity Sonar Pro | Training data + web-grounded search | ~$0.03-0.10 |
| GPT-5.2`:online` + Perplexity Sonar Pro | Two independent web-search-enabled models | ~$0.04-0.12 |

**Recommended**: Use the `:online` suffix on the existing GPT-5.2 model for the first test — it's a one-character change (`"openrouter/openai/gpt-5.2:online"`) and gives web search grounding with zero code changes.

---

## Part 2: External Sources Investigated

| Source | Description | API Available? | Usefulness for Base Rates |
|--------|-------------|---------------|--------------------------|
| **Exa.ai** | Web search API — primary backend for all forecasting-tools research tools | Yes, via `EXA_API_KEY` | High — required for all library-based tools |
| **AskNews** (already integrated) | Current news research via API | Yes, already in use | Low for base rates — good for recency, not historical data |
| **newsminimalist.com** | AI-curated daily news summaries | No documented API found | Low — no programmatic access |
| **abstraction.substack.com** | "Forecasting and the future of AI" newsletter by Jonathan Mann | N/A (content, not a tool) | Low — thought pieces, not data tools |
| **NewsAPI.org, NewsAPI.ai, GNews** | Various news APIs with historical search | Yes, various pricing | Medium — could supplement Exa for news-based base rates |
| **API Ninjas Historical Events API** | Historical events database | Yes | Low-Medium — limited to well-known events |
| **Wikipedia** | Comprehensive historical reference | API available (free) | Medium — good for reference class counts if queried well |

---

## Part 3: Insights from Top-Performing Bots

**Source**: [Q2 AI Benchmark Results: Pros Maintain Clear Lead (EA Forum)](https://forum.effectivealtruism.org/posts/F2stjK9wHSy3HPEC9/q2-ai-benchmark-results-pros-maintain-clear-lead)

### What Differentiates Better Bots

| Factor | Impact | Our Status |
|--------|--------|-----------|
| **Base model quality** | Highest impact — "the most important factor" | Strong (GPT-5.2) |
| **Aggregation of multiple forecasts** | +1,799 points average | Strong (6 runs + Skew-T/majority-vote) |
| **Manual review + custom test questions** | +2,216 points (largest effect) | Not systematic |
| **Research infrastructure** (web scraping, multiple search APIs, multi-step agentic research) | High — top bots use "6-7 step agentic approach" | **Gap** — single AskNews call only |
| **Multi-model diversity** | Moderate — top bots use 2-3 different LLMs | Not used (single model) |
| **Prediction market extraction** | Negative for some bots | Not used (correctly) |

### Key Takeaway
Our bot is well-optimized on aggregation and model quality. **Research depth is the biggest remaining lever**, and base rate research is a specific, high-value component of research infrastructure.

---

## Part 4: Current Bot Integration Points

### How Research Flows Into Forecasting

```
run_research(question)          →  research string
    ↓
_make_prediction(question, research)  ×6 calls
    ↓
_run_forecast_on_{binary|numeric|mc}(question, research)
    ↓
Prompt includes: "## Your research assistant says: {research}"
    +
"### Consider base rates and analogs" section (asks LLM to reason about base rates)
    ↓
aggregate_predictions()         →  final forecast
```

**The integration point is clear**: enrich the `research` string with base rate data before it reaches the forecast prompts. The prompts already have a section asking about base rates — providing actual data makes this section much more effective.

### Three Integration Options (Increasing Complexity)

1. **Append to `run_research()`**: Add base rate research call after existing AskNews call, concatenate results. ~20 lines of code, zero signature changes.
2. **Override `_make_prediction()`**: In `SpringTemplateBotExtended`, enrich the research string with base rate data before dispatching to forecast methods. Clean separation, slightly more code.
3. **Override `_research_and_make_predictions()`**: Full control over research pipeline, can run base rate research in parallel with AskNews. Most flexible, most complex.

---

## Part 5: Proposed Pathways

### No-Cost Options

#### Option 1: Enhanced Base Rate Prompting (No Cost, No Dependencies)

**What**: Improve the "Consider base rates and analogs" section in all three forecast prompt types to elicit better base rate reasoning from the LLM using only its training data.

**Current prompt section** (identical across all question types):
```
### Consider base rates and analogs
- Are there analogs that suggest what the probability should be...
- Could this be a question dominated by simple probability...
- How should base rates anchor or adjust your interpretation...
- Note your observations on base rates
```

**Proposed enhancement**: Add explicit Fermi decomposition steps, reference class identification, and structured base rate estimation:
```
### Consider base rates and analogs
1. Identify the most relevant reference class for this question
2. Estimate the historical base rate: how often has [event type] occurred in [relevant time period]?
3. Break down the estimate: what is the numerator (events of interest) and denominator (total opportunities)?
4. Note any key differences between the reference class and this specific question
5. State your base rate estimate and how it anchors your scenario estimates
```

**Files to modify**: `main.py` (3 prompt sections: binary ~line 254, MC ~line 562, numeric ~line 713)
**Effort**: ~30 minutes
**Risk**: None
**Expected impact**: Modest — better-structured reasoning, but still limited by LLM training data

#### Option 2: Research Prompt Enhancement (No Cost, No Dependencies)

**What**: Modify the research prompt to explicitly request base rate and historical frequency information from the existing AskNews researcher.

**Current research prompt**:
```
You are an assistant to a superforecaster.
...generate a concise but detailed rundown of the most relevant news...
```

**Proposed addition**:
```
In addition to current news, identify:
- Historical base rates: how frequently has this type of event occurred in the past?
- Reference classes: what similar events or categories provide relevant frequency data?
- Trend data: is the rate of occurrence increasing, decreasing, or stable?
```

**Files to modify**: `main.py` (research prompt ~line 150)
**Effort**: ~15 minutes
**Risk**: AskNews may not surface historical data well (it's optimized for current news)
**Expected impact**: Low-Modest — depends on researcher's ability to find historical data

---

### Low-Cost Options (No New API Keys)

#### Option 3: Multi-Model LLM Base Rate Researcher (No New API Keys)

**What**: A standalone base rate research tool that independently queries two frontier models (GPT-5.2 and Claude 4.6) for base rate analysis on a question, then uses a third model (o4-mini) to synthesize and reconcile their responses. Accessed in the bot the same way the AskNews researcher works — as a callable tool that returns a research string appended to the forecast context.

**Why multi-model?**
- GPT-5.2 and Claude 4.6 have **different training data** and different knowledge strengths/gaps
- When both models agree on a base rate, confidence is high
- When they disagree, o4-mini can flag the uncertainty — disagreement is itself useful signal
- Cross-checking catches confabulated or hallucinated rates that a single model might produce unchallenged

**Architecture**:
```
Question text
    ├──→ GPT-5.2: "What are the historical base rates for [question]?"
    │         → Identify reference class, count occurrences, estimate rate, note trends
    │
    ├──→ Claude 4.6: Same prompt
    │         → Independent analysis with potentially different data/perspective
    │
    └──→ o4-mini (summarizer):
              Input: Both base rate analyses
              Task: Synthesize into single report, flag agreements/disagreements,
                    produce final base rate estimate with confidence level
              Output: Structured markdown section
```

**Implementation sketch**:
```python
async def get_base_rate_research(self, question_text: str) -> str:
    """Multi-model base rate researcher. Returns markdown string."""
    base_rate_prompt = (
        "You are a base rate analyst for a forecasting team.\n"
        "Given the following question, provide a detailed base rate analysis:\n"
        "1. Identify the most relevant reference class(es)\n"
        "2. Estimate historical frequency: how often has this type of event occurred?\n"
        "3. Provide the numerator (events of interest) and denominator (opportunities)\n"
        "4. Note any trend (increasing, decreasing, stable)\n"
        "5. State key caveats or differences between the reference class and this specific question\n\n"
        f"Question: {question_text}"
    )

    # Query two frontier models in parallel
    # Use :online suffix for web-grounded search, or omit for training-data-only
    gpt = GeneralLlm(model="openrouter/openai/gpt-5.2:online", temperature=0.3, timeout=60)
    claude = GeneralLlm(model="openrouter/anthropic/claude-opus-4-6:online", temperature=0.3, timeout=60)

    analysis_gpt, analysis_claude = await asyncio.gather(
        gpt.invoke(base_rate_prompt),
        claude.invoke(base_rate_prompt),
    )

    # Synthesize with o4-mini
    synthesizer = GeneralLlm(model="openrouter/openai/o4-mini", temperature=0.2, timeout=40)
    synthesis = await synthesizer.invoke(
        "You are synthesizing two independent base rate analyses for a forecasting question.\n"
        "Produce a concise summary that:\n"
        "- States the consensus base rate estimate (if both agree)\n"
        "- Flags disagreements with both perspectives\n"
        "- Provides a final best-estimate rate with confidence (high/medium/low)\n"
        "- Notes key caveats\n\n"
        f"## Analysis A (GPT-5.2):\n{analysis_gpt}\n\n"
        f"## Analysis B (Claude 4.6):\n{analysis_claude}"
    )

    return f"\n\n## Base Rate Research (Multi-Model)\n{synthesis}"
```

**Integration into `run_research()`**:
```python
async def run_research(self, question):
    research = await super().run_research(question)  # AskNews (existing)
    try:
        base_rates = await self.get_base_rate_research(question.question_text)
        research += base_rates
    except Exception as e:
        logger.info(f"Base rate research unavailable: {e}")
    return research
```

**Cost**: ~$0.02-0.08 per question without `:online`; ~$0.04-0.12 with `:online` web search (3 LLM calls via OpenRouter — two frontier + one summarizer)
**Latency**: +10-20 seconds (two frontier calls run in parallel, then one summarizer call)
**New dependency**: None — uses existing `OPENROUTER_API_KEY` with existing credits
**Files to modify**: `main.py` or `dre_forecasting_tools.py` (new method + `run_research()` modification)
**Risk**: Low — uses stable production models; try/except fallback for safety
**Expected impact**: Moderate without `:online` (training data only). **High with `:online`** — models actively search the web for historical data, Wikipedia, news archives before answering. The `:online` variant addresses the main weakness of LLM-only approaches (niche/recent events) while keeping zero new API keys.

**Key insight**: Adding `:online` to the model string (e.g., `"openrouter/openai/gpt-5.2:online"`) is a one-token change that transforms training-data-only base rate analysis into web-grounded research. This should be tested in Notebook 013d as a variant.

---

#### Option 4: DIY Base Rate Research via Perplexity Sonar (No New API Keys)

**What**: Similar to Option 3 but uses Perplexity Sonar (via OpenRouter) which has **built-in web search**. Trades model diversity for web-grounded data.

**Tradeoff vs Option 3**: Option 3 gives model diversity + cross-validation from training data. Option 4 gives web-grounded current data from a single model. These could also be **combined** — use Option 3's multi-model approach but replace one of the two frontier models with Perplexity Sonar to get both diversity and web grounding.

---

---

### Options Requiring `EXA_API_KEY`

#### Option 5: SmartSearcher for Targeted Historical Queries

**What**: Use `SmartSearcher` directly (not the full BaseRateResearcher pipeline) to ask targeted historical questions generated from the forecast question.

**Approach**:
1. Use LLM to generate 2-3 historical/base-rate questions from the forecast question
2. Run `SmartSearcher` on each
3. Append cited answers to research string

**Cost**: ~$0.02-0.06 per question
**Advantage over Options 3-4**: Structured search results with scoring, deduplication, and source metadata
**Files to modify**: `main.py` or `dre_forecasting_tools.py`
**New dependency**: `EXA_API_KEY`

#### Option 6: BaseRateResearcher Integration

**What**: Call `BaseRateResearcher` in `run_research()`, append structured base rate report to research output. Full automated pipeline (reference class identification → count search → rate calculation).

**Cost**: ~$0.01-0.05 per question via Exa API
**New dependency**: `EXA_API_KEY`

#### Option 7: KeyFactorsResearcher Integration

**What**: Run `KeyFactorsResearcher` to produce scored, ranked evidence factors (pros, cons, and base rates) with citations.

**Cost**: ~$0.05-0.15 per question
**Latency**: +30-60 seconds per question
**Advantage**: Produces structured, scored evidence — most useful format for forecast reasoning
**Files to modify**: `main.py` or `dre_forecasting_tools.py`
**Expected impact**: Moderate-High — addresses both base rates and broader evidence quality

#### Option 8: Combined BaseRate + KeyFactors Pipeline

**What**: Run both tools in parallel, combine outputs into a structured research supplement.

**Cost**: ~$0.06-0.20 per question
**Expected impact**: High — comprehensive evidence base

---

### Higher-Cost / Higher-Effort Options

#### Option 9: NicheListResearcher for Countable Events

**What**: For numeric questions about countable events, enumerate and fact-check all historical instances.

**Best for**: Questions like "How many X will happen by Y?" where historical instances can be listed
**Cost**: ~$0.05-0.15 per applicable question
**Limitation**: Max 30 items, high latency, only applicable to certain question types
**Effort**: Medium — need question-type detection logic

#### Option 10: Multi-Model Research Diversification

**What**: Run research through multiple LLMs (GPT-5.2 + Claude + o4-mini) and aggregate research findings, not just forecast outputs.

**Cost**: 2-3x current research cost
**Effort**: Medium
**Expected impact**: Moderate — EA Forum data shows multi-model diversity helps

#### Option 11: Custom Historical Data Pipeline

**What**: Build a custom research agent that queries Wikipedia API, historical events databases, and statistical data sources for time series data relevant to forecast questions.

**Cost**: Development time + API costs vary
**Effort**: High (weeks of development)
**Expected impact**: Potentially highest for numeric questions, but uncertain ROI

---

## Part 6: Recommended Phasing

| Phase | Option | Cost | Effort | New API Keys? |
|-------|--------|------|--------|---------------|
| **1 (Now)** | Options 1 + 2: Prompt enhancements | Free | ~1 hour | No |
| **2 (Next)** | Option 3: Multi-model LLM base rate researcher | ~$0.02-0.08/q | ~3-4 hours | No |
| **3 (Enhance)** | Option 4: Add Perplexity Sonar for web-grounded base rates | ~$0.01-0.05/q | ~2-3 hours | No |
| **4 (If Exa obtained)** | Options 5-8: Library-based tools (SmartSearcher, BaseRateResearcher, KeyFactors) | ~$0.01-0.15/q | ~3-4 hours | Yes (`EXA_API_KEY`) |
| **5 (Future)** | Options 9-11 as performance data dictates | Varies | Days-weeks | Various |

### Recommended First Steps
1. **Start with Options 1 + 2** (prompt improvements). Free, fast, and provides a baseline to measure improvement against.
2. **Move to Option 3** (multi-model LLM base rate researcher). Uses existing OpenRouter credits for GPT-5.2, Claude 4.6, and o4-mini. Cross-validation between models catches hallucinated rates. Prototype in Notebook 013d first.
3. **Layer on Option 4** (Perplexity Sonar) to add web-grounded data. Can replace one of the two frontier models in Option 3, or run as a third independent source.
4. **Evaluate Exa access** only if Options 3+4 prove insufficient — the library tools are more structured but require a paid API key with no documented free tier.

### Before Phase 4 (Exa-based tools)
- Obtain `EXA_API_KEY` (check if free credits available via Metaculus partnership or Exa.ai directly)
- Test `BaseRateResearcher` standalone in Notebook 012 on 5-10 representative questions
- Compare quality against multi-model approach from Phase 2 to determine if Exa is worth the cost

---

## Part 7: Jupyter Notebook Testing Plan

Each major tool and integration approach should be prototyped and evaluated in a Jupyter notebook before any production integration. Notebooks follow the project convention: `jupyter/NNN_Description_MM-DD-YYYY.ipynb`, with iterations as `a`, `b`, `c` suffixes.

### Important: Exa API Dependency

Most `forecasting-tools` research tools (`SmartSearcher`, `KeyFactorsResearcher`, `NicheListResearcher`) **hard-depend on Exa API** (`EXA_API_KEY`). There is no free tier documented. The notebooks below are organized into two tracks:

- **Track 1 (No new API keys)**: Uses only `OPENROUTER_API_KEY` and optionally `ASKNEWS_CLIENT_ID`/`ASKNEWS_SECRET` — tools we already have and pay for.
- **Track 2 (Requires `EXA_API_KEY`)**: Tests the library's built-in research tools. Only pursue if Exa access is obtained (check Metaculus partnership, Exa free trial, or paid plan).

---

### Track 1: No New API Keys Required

#### Notebook 013: Prompt Enhancement A/B Test
**File**: `jupyter/013_Prompt_BaseRate_AB_Test_03-22-2026.ipynb`

**Purpose**: Test the no-cost prompt improvements (Options 1 + 2) by comparing forecast quality before and after.

**Cells**:
1. **Setup**: Import `GeneralLlm`, load the current forecast prompts from `main.py`
2. **Define test questions**: 3 binary, 2 numeric, 2 multiple choice — use questions with known community forecasts for comparison
3. **Baseline run**: Run each question through the current forecast prompt (with generic "consider base rates" section), capture:
   - Raw scenario outputs (9 scenarios per run)
   - Final aggregated forecast
   - Quality of base rate reasoning (manual 1-5 score)
4. **Enhanced run**: Run each question through the enhanced prompt (with Fermi decomposition steps, explicit reference class identification), capture same metrics
5. **Comparison table**: Side-by-side — question, baseline forecast, enhanced forecast, community forecast, baseline reasoning score, enhanced reasoning score
6. **Analysis**: Does the enhanced prompt produce more specific base rate reasoning? Are forecasts closer to community median?

**Success criteria**: Enhanced prompts produce more structured base rate reasoning in at least 60% of test questions.

**Dependency**: `OPENROUTER_API_KEY` (already have)

---

#### Notebook 013d: Multi-Model LLM Base Rate Researcher
**File**: `jupyter/013d_MultiModel_BaseRate_Researcher_03-22-2026.ipynb`

**Purpose**: Build and test the multi-model base rate researcher (Option 3) — independently query GPT-5.2 and Claude 4.6 for base rate analysis, then synthesize with a summarizer model.

**Cells**:
1. **Setup**: Import `GeneralLlm`, configure models via OpenRouter:
   - GPT-5.2 (`openrouter/openai/gpt-5.2`, temperature=0.3)
   - Claude 4.6 (`openrouter/anthropic/claude-opus-4-6`, temperature=0.3)
   - Summarizer models (test both):
     - o4-mini (`openrouter/openai/o4-mini`, temperature=0.2) — reasoning model, strong at analytical comparison
     - Claude Sonnet 4.6 (`openrouter/anthropic/claude-sonnet-4-6`, temperature=0.2) — excellent synthesis and structured writing, different provider from GPT-5.2
2. **Design the base rate prompt**: Craft the structured prompt that asks for reference class identification, historical frequency, numerator/denominator, trends, and caveats
3. **Test on 5-6 representative questions**:
   - Binary with clear reference class (e.g., SpaceX launch success)
   - Binary with ambiguous reference class (e.g., geopolitical event)
   - Numeric with historical trend data (e.g., age records, economic metric)
   - Multiple choice (e.g., "how many new AI labs")
   - Edge case: novel event with no clear historical precedent
4. **For each question, capture and display**:
   - GPT-5.2 raw analysis (full text)
   - Claude 4.6 raw analysis (full text)
   - Summarizer synthesis (consensus, disagreements, confidence level)
   - Agreement score: did both models identify the same reference class? Same rate?
5. **Summarizer A/B test**: Run the same two frontier analyses through both summarizer models and compare:
   - **o4-mini**: Reasoning model — does it catch logical inconsistencies between the two analyses? Does it accurately identify which source is more credible?
   - **Claude Sonnet 4.6**: Synthesis model — does it produce clearer, more concise output? Does being from a different provider than GPT-5.2 result in more balanced treatment?
   - Score each on: conciseness (1-5), accuracy of comparison (1-5), usefulness as forecast context (1-5), neutrality toward both sources (1-5)
   - Note: o4-mini is same provider as GPT-5.2 (potential subtle bias); Sonnet 4.6 is same provider as the Claude 4.6 source (same concern in reverse). The question is whether this matters in practice for factual synthesis.
6. **Quality assessment matrix**:
   - Reference class quality (1-5)
   - Rate accuracy (spot-check against known data)
   - Disagreement informativeness (did disagreements reveal genuine uncertainty?)
   - Synthesis quality — best summarizer (1-5)
7. **Cost and latency tracking**: Record per-question costs for all calls (both summarizer variants), wall time
8. **`:online` variant testing** (critical test): Re-run the same questions with `:online` suffix on both frontier models (`openrouter/openai/gpt-5.2:online` + `openrouter/anthropic/claude-opus-4-6:online`). Compare:
   - Do the models now cite real web sources?
   - Are base rate counts more specific and accurate?
   - How much does cost increase?
   - Side-by-side: training-data-only vs `:online` on the same question
9. **Perplexity Sonar variant**: Try replacing one frontier model with `openrouter/perplexity/sonar-pro` — does dedicated search-model improve accuracy vs `:online` suffix?
10. **Summary**: Compile results into recommendations:
    - Best summarizer model (o4-mini vs Claude Sonnet 4.6)
    - Best frontier configuration (training-data-only vs `:online` vs Perplexity Sonar swap)
    - Overall: which configuration maximizes quality per dollar?

**Success criteria**: Multi-model synthesis produces base rate estimates that are (a) more reliable than either model alone, and (b) usefully flag uncertainty when models disagree.

**Dependency**: `OPENROUTER_API_KEY` (already have)

**Cost estimate**: ~$0.25-0.75 total for full test run (5-6 questions × 3 LLM calls × 2 summarizer variants, plus `:online` reruns)

---

#### Notebook 013a: DIY Base Rate Research via OpenRouter + Perplexity
**File**: `jupyter/013a_DIY_BaseRate_Research_03-22-2026.ipynb`

**Purpose**: Build and test a custom base rate research function using models we already have access to (via OpenRouter), without Exa. Uses Perplexity Sonar models (available through OpenRouter) for web-grounded historical research.

**Approach**: Perplexity Sonar models (`openrouter/perplexity/sonar-pro`, `openrouter/perplexity/sonar-deep-research`) have built-in web search and return cited answers. We can use them as a search-capable LLM to answer base rate questions directly.

**Cells**:
1. **Setup**: Import `GeneralLlm`, configure Perplexity Sonar via OpenRouter
2. **Base rate question generator**: Given a Metaculus question, use the default LLM (GPT-5.2) to generate 2-3 base-rate-specific sub-questions:
   - "How many times has [event type] occurred in the past N years?"
   - "What is the historical frequency of [reference class]?"
   - "What trend data exists for [metric]?"
3. **Run Perplexity Sonar** on each sub-question — it will search the web and return cited answers
4. **Format results**: Combine into a structured "Base Rate Research" section
5. **Test on 4-5 questions** from each type (binary, numeric, MC)
6. **Quality assessment**: Are answers specific, cited, and useful for anchoring forecasts?
7. **Cost tracking**: Monitor OpenRouter costs for Perplexity Sonar calls

**Success criteria**: Perplexity Sonar returns specific, cited historical data on at least 60% of base rate sub-questions.

**Dependency**: `OPENROUTER_API_KEY` (already have — Perplexity models available via OpenRouter)

**Cost estimate**: ~$0.01-0.05 per question (Sonar Pro pricing via OpenRouter)

---

#### Notebook 013b: AskNews Deep Research for Historical Context
**File**: `jupyter/013b_AskNews_DeepResearch_BaseRate_03-22-2026.ipynb`

**Purpose**: Test whether AskNews deep research mode (already available) can surface useful historical/base rate information when given base-rate-specific queries.

**Cells**:
1. **Setup**: Import `AskNewsSearcher` or use `asknews/deep-research/medium-depth` via GeneralLlm
2. **Generate base rate queries**: Same question-to-sub-question approach as 013a
3. **Run AskNews deep research** on each sub-question
4. **Compare**: Side-by-side with Perplexity Sonar results from 013a on the same questions
5. **Evaluate**: AskNews is news-focused — does it find historical frequency data, or only recent events?

**Success criteria**: Determine whether AskNews deep research adds value for base rates, or if it's better reserved for current-news research only.

**Dependency**: `ASKNEWS_CLIENT_ID` + `ASKNEWS_SECRET` (already have)

---

#### Notebook 013c: Custom Base Rate Pipeline Prototype
**File**: `jupyter/013c_Custom_BaseRate_Pipeline_03-22-2026.ipynb`

**Purpose**: Combine the best-performing approach from 013a/013b into an end-to-end prototype that can be dropped into the bot's `run_research()` method.

**Cells**:
1. **Setup**: Import best-performing search tool from 013a/013b testing
2. **Build `get_base_rate_research(question)` function**:
   - Step 1: LLM generates 2-3 base rate sub-questions from the Metaculus question
   - Step 2: Search tool answers each sub-question with citations
   - Step 3: Format as structured markdown section
   - Step 4: Try/except wrapper for graceful fallback
3. **Simulate enriched research pipeline**: AskNews (existing) + base rate research (new) → combined research string
4. **Run forecast prompt** with enriched research on 3-4 test questions
5. **Compare**: Forecast with standard research vs. enriched research
6. **Measure**: Total latency, total cost, forecast quality delta
7. **Production readiness**: Does it stay within the 80s LLM timeout? Does the combined context fit?

**Success criteria**: Enriched pipeline produces better-informed forecasts without breaking latency or cost budgets, using only existing API keys.

**Dependency**: `OPENROUTER_API_KEY` + `ASKNEWS_CLIENT_ID`/`ASKNEWS_SECRET` (already have)

---

### Track 2: Requires `EXA_API_KEY`

Only pursue these notebooks if Exa API access is obtained.

#### Notebook 012: BaseRateResearcher Evaluation
**File**: `jupyter/012_BaseRateResearcher_Eval_03-22-2026.ipynb`

**Purpose**: Test the library's `BaseRateResearcher` standalone on representative questions.

**Cells**:
1. **Setup**: Import `BaseRateResearcher`, load `EXA_API_KEY`
2. **Test questions**: 3-4 questions from each type (binary, numeric, MC), plus edge cases
3. **Run BaseRateResearcher** on each, capture: markdown report, reference classes, counts, historical rate, execution time, cost, errors
4. **Quality assessment**: Are reference classes sensible? Are counts accurate? Is the rate plausible?
5. **Summary table**: DataFrame of results with quality scores (1-5)

**Dependency**: `EXA_API_KEY`

---

#### Notebook 012a: SmartSearcher for Targeted Historical Queries
**File**: `jupyter/012a_SmartSearcher_Historical_03-22-2026.ipynb`

**Purpose**: Test `SmartSearcher` directly for targeted historical/base-rate questions, compare to DIY approach from 013a.

**Cells**:
1. **Setup**: Import `SmartSearcher`, configure with Exa API
2. **Run on same base rate sub-questions** used in Notebook 013a for direct comparison
3. **Compare**: SmartSearcher (Exa) vs. Perplexity Sonar (OpenRouter) — quality, cost, latency
4. **Verdict**: Is Exa worth the additional API key and cost?

**Dependency**: `EXA_API_KEY`

---

#### Notebook 012b: KeyFactorsResearcher Evaluation
**File**: `jupyter/012b_KeyFactorsResearcher_Eval_03-22-2026.ipynb`

**Purpose**: Test `KeyFactorsResearcher` on representative questions, evaluate scored evidence quality.

**Cells**:
1. **Setup**: Import `KeyFactorsResearcher`, `ScoredKeyFactor`
2. **Run on 3-4 test questions**: Call `find_and_sort_key_factors()`, inspect scored factors
3. **Quality assessment**: Are top-ranked factors useful? Do base_rate-typed factors have accurate data?
4. **Cost/latency tracking**: Record total API calls, wall time, estimated cost

**Dependency**: `EXA_API_KEY`

---

#### Notebook 012c: NicheListResearcher for Countable Events
**File**: `jupyter/012c_NicheListResearcher_Eval_03-22-2026.ipynb`

**Purpose**: Test `NicheListResearcher` on numeric questions about countable, enumerable events.

**Cells**:
1. **Setup**: Import `NicheListResearcher`, `FactCheckedItem`
2. **Select 2-3 numeric questions** where past instances can be listed
3. **Run and evaluate**: Completeness, accuracy, usefulness of enumerated lists
4. **Edge cases**: Question with >30 expected items (should reject), question with very few items

**Dependency**: `EXA_API_KEY`

---

### Notebook Execution Order

| Order | Notebook | Track | Dependency | Blocks |
|-------|----------|-------|------------|--------|
| 1 | **013** (Prompt A/B) | 1 - Free | `OPENROUTER_API_KEY` | Nothing — start here |
| 2 | **013d** (Multi-Model LLM Researcher) | 1 - Free | `OPENROUTER_API_KEY` | 013c — **primary prototype** |
| 3 | **013a** (Perplexity Sonar) | 1 - Free | `OPENROUTER_API_KEY` | 013c |
| 4 | **013b** (AskNews Deep) | 1 - Free | `ASKNEWS` keys | 013c |
| 5 | **013c** (Custom Pipeline) | 1 - Free | Results from 013d/013a/013b | Production integration |
| 6 | **012** (BaseRateResearcher) | 2 - Exa | `EXA_API_KEY` | 012a |
| 7 | **012a** (SmartSearcher) | 2 - Exa | `EXA_API_KEY` | Comparison with 013d |
| 8 | **012b** (KeyFactorsResearcher) | 2 - Exa | `EXA_API_KEY` | — |
| 9 | **012c** (NicheListResearcher) | 2 - Exa | `EXA_API_KEY` | — |

**Track 1 can proceed immediately** with existing API keys. Notebook 013d (multi-model LLM researcher) is the recommended primary prototype. Track 2 is deferred until Exa access is obtained and serves as a comparison/upgrade path.

---

## Part 8: Key Files Reference

| File | What to Modify | For Which Options |
|------|---------------|-------------------|
| `main.py` ~line 150 | Research prompt | Options 2, 3, 4 |
| `main.py` ~lines 254, 562, 713 | Forecast prompt base rate sections | Option 1 |
| `main.py` ~line 150-200 | `run_research()` method | Options 3, 4, 5, 6 |
| `dre_forecasting_tools.py` | `SpringTemplateBotExtended` overrides | Options 4, 5, 6, 7 |
| `.env` / GitHub Actions secrets | Add `EXA_API_KEY` | Options 3-9 |

---

## Sources

- [forecasting-tools GitHub Repository](https://github.com/Metaculus/forecasting-tools) — library source and documentation
- [Q2 AI Benchmark Results: Pros Maintain Clear Lead (EA Forum)](https://forum.effectivealtruism.org/posts/F2stjK9wHSy3HPEC9/q2-ai-benchmark-results-pros-maintain-clear-lead) — performance analysis of top forecasting bots
- [Q2 Template Bot source](https://github.com/Metaculus/forecasting-tools/blob/5e21a4f96ab84086b2f84b1c4e31b95ce289c6f2/forecasting_tools/forecast_bots/official_bots/q2_template_bot.py) — official Metaculus template bot architecture
- [Abstraction Substack](https://abstraction.substack.com/) — forecasting methodology newsletter by Jonathan Mann
- Installed `forecasting-tools` library source code (v0.2.80+) — direct code analysis of BaseRateResearcher, KeyFactorsResearcher, NicheListResearcher, Estimator, SmartSearcher
