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

### Recommended Next Step: Notebook 013a — Multi-Model Base Rate Researcher Prototype

The highest-value next action is to build and test **Option 3: the Multi-Model LLM Base Rate Researcher** in a Jupyter notebook (`jupyter/013a_MultiModel_BaseRate_Researcher_03-22-2026.ipynb`). This approach independently queries GPT-5.2 and Claude 4.6 for base rate analysis on a question, then uses o4-mini to synthesize their responses into a consensus report with confidence levels.

**Why this is the recommended starting point:**
- **No new API keys** — uses existing OpenRouter credits for models we already pay for
- **Web search built in** — both GPT-5.2 and Claude 4.6 support native web search via the `:online` suffix (e.g., `"openrouter/openai/gpt-5.2:online"`), so the researcher can find real-time historical data, not just training-data knowledge
- **Model diversity catches errors** — different training data means different knowledge gaps; when both models agree on a rate, confidence is high; when they disagree, the disagreement is itself useful signal for the forecaster
- **Clean integration path** — the output is a markdown string that appends directly to the existing research context, exactly like AskNews does today. No changes to method signatures, aggregation, or the framework
- **Directly addresses the #1 gap** — the EA Forum analysis shows research infrastructure is the biggest remaining lever, and our forecast prompts already ask about base rates but provide no data to work with

The notebook will test this on 5-6 representative questions across all types (binary, numeric, multiple choice), compare training-data-only vs `:online` web-search variants, and measure cost, latency, and output quality. See Part 7 (Notebook 013a) for the full test plan.

**Option 3a: Multi-Model News Researcher** follows the identical architecture — two frontier models queried in parallel, then synthesized by a third — but with a news-focused prompt instead of a base-rate prompt. Where the base rate researcher asks "how often has this happened historically?", the news researcher asks "what's happening right now that changes the probability?" Both are standalone async functions in `research.py` that share the same internal helpers (`_query_model()`, `_synthesize_analyses()`), and both run **in parallel** in the bot's `run_research()` override, so the combined latency cost is roughly the same as running either one alone. Together they address both sides of the forecasting equation: the historical anchor (base rates) and the update signal (current news). See Notebook 013b for the test plan.

### Notebook Map

| Notebook | Name | Purpose |
|----------|------|---------|
| **013** | Prompt A/B Test | Baseline — test enhanced prompt wording |
| **013a** | Multi-Model Base Rate Researcher | Primary prototype — builds `research.py` core functions |
| **013b** | Multi-Model News Researcher | Second researcher — builds `get_news_research()` |
| **013c** | Integration Pipeline | End-to-end test — wires both into `run_research()` override |

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

**Key insight**: Adding `:online` to the model string (e.g., `"openrouter/openai/gpt-5.2:online"`) is a one-token change that transforms training-data-only base rate analysis into web-grounded research. This should be tested in Notebook 013a as a variant.

---

#### Option 3a: Multi-Model News Researcher (No New API Keys)

**What**: A standalone news and current-events research tool that follows the same multi-model pattern as Option 3, but with a **news-focused prompt**. Independently queries two web-search-enabled frontier models for current news, recent developments, and expert commentary on a question, then synthesizes into a structured news briefing. Complements the base rate researcher — base rates provide the historical anchor, the news researcher provides the update signal.

**Why separate from base rates?**
- Different prompt, different objective: base rates ask "how often has this happened?" while news asks "what's happening now that changes the probability?"
- The current AskNews researcher is a single-source, single-model call. Multi-model news research cross-validates current events the same way Option 3 cross-validates historical rates
- Can run **in parallel** with base rate research (both are independent of each other), keeping total latency low

**Architecture**:
```
Question text
    ├──→ GPT-5.2:online: "What recent news and developments are relevant to [question]?"
    │         → Key events, policy changes, expert statements, market signals
    │
    ├──→ Claude 4.6:online: Same prompt
    │         → Independent news search with potentially different sources/perspective
    │
    └──→ o4-mini (synthesizer):
              Input: Both news analyses
              Task: Synthesize into single briefing, flag agreements/disagreements,
                    note recency and reliability of sources
              Output: Structured markdown section
```

**Implementation sketch**:
```python
async def get_news_research(
    question_text: str,
    resolution_criteria: str = "",
    fine_print: str = "",
    model_a: str = "openrouter/openai/gpt-5.2",
    model_b: str = "openrouter/anthropic/claude-opus-4-6",
    synthesizer_model: str = "openrouter/openai/o4-mini",
    use_web_search: bool = True,  # Default True — news research needs web
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """
    Multi-model news researcher. Independently queries two frontier
    models for current news analysis, then synthesizes.
    Returns a markdown string to append to research context.
    """
    ...
```

**Relationship to existing AskNews**: This could **replace** or **supplement** the existing AskNews researcher in `run_research()`. AskNews has a dedicated news API but is a single source; multi-model `:online` search covers broader web sources. Testing will determine whether to:
- Replace AskNews entirely (simpler pipeline, fewer API dependencies)
- Run both and concatenate (maximum coverage, higher cost)
- Use AskNews as a fast default, multi-model news as an upgrade for important questions

**Integration into `run_research()`**:
```python
async def run_research(self, question):
    # Run all research sources in parallel
    asknews_task = super().run_research(question)  # AskNews (existing)
    base_rate_task = get_base_rate_research(
        question.question_text, ...)
    news_task = get_news_research(
        question.question_text, ...)

    research, base_rates, news = await asyncio.gather(
        asknews_task,
        base_rate_task,
        news_task,
        return_exceptions=True,
    )

    # Append successful results, skip failures
    result = research if not isinstance(research, Exception) else ""
    if not isinstance(base_rates, Exception):
        result += base_rates
    if not isinstance(news, Exception):
        result += news
    return result
```

**Cost**: ~$0.04-0.12 per question with `:online` (3 LLM calls — same as Option 3)
**Latency**: +10-20 seconds, but runs **in parallel** with base rate research, so net latency increase is ~0 if both run concurrently
**New dependency**: None — uses existing `OPENROUTER_API_KEY`
**Files to modify**: `research.py` (new function) + `dre_forecasting_tools.py` (`run_research()` override)
**Risk**: Low — same pattern as Option 3; try/except fallback
**Expected impact**: High — addresses the #1 gap (research infrastructure depth) identified in the EA Forum analysis. Multi-model news cross-validation catches single-source blind spots.

**Key difference from Option 3**: `use_web_search` defaults to `True` (news research is inherently about current information, not training data). The news prompt focuses on recency, developments, and signals rather than reference classes and frequencies.

---

## Part 6: Recommended Phasing

| Phase | Option | Cost | Effort | New API Keys? |
|-------|--------|------|--------|---------------|
| **1 (Now)** | Options 1 + 2: Prompt enhancements | Free | ~1 hour | No |
| **2 (Next)** | Option 3: Multi-model LLM base rate researcher | ~$0.02-0.08/q | ~3-4 hours | No |
| **3 (Next)** | Option 3a: Multi-model news researcher | ~$0.04-0.12/q | ~2-3 hours | No |
| **4 (Integrate)** | Combine Options 3 + 3a into `research.py`, integrate into bot | ~$0.06-0.20/q total | ~2-3 hours | No |

### Recommended First Steps
1. **Start with Options 1 + 2** (prompt improvements). Free, fast, and provides a baseline to measure improvement against.
2. **Move to Option 3** (multi-model LLM base rate researcher). Uses existing OpenRouter credits for GPT-5.2, Claude 4.6, and o4-mini. Cross-validation between models catches hallucinated rates. Prototype in Notebook 013a first.
3. **Move to Option 3a** (multi-model news researcher). Same architecture, news-focused prompt. Prototype in Notebook 013b. Runs in parallel with base rate research.
4. **Integrate both** into `research.py` and wire into the bot's `run_research()` override. Both run in parallel alongside existing AskNews for maximum coverage.

See Appendix A for additional options (Perplexity Sonar, Exa-based library tools, custom pipelines) that can be evaluated if Options 1-3a prove insufficient.

---

## Part 7: Jupyter Notebook Testing Plan

Each major tool and integration approach should be prototyped and evaluated in a Jupyter notebook before any production integration. Notebooks follow the project convention: `jupyter/NNN_Description_MM-DD-YYYY.ipynb`, with iterations as `a`, `b`, `c` suffixes.

---

## Part 7a: Production Code Architecture

All notebook code must be structured for **direct transfer** to production files. This section defines the target module, integration points, and coding conventions that every notebook in the 013 series must follow.

### A. Target Module: `research.py`

A new standalone module at the repo root (same level as `main.py` and `dre_forecasting_tools.py`). Contains all research functions as **async standalone functions** — no bot class dependency, pure functions that accept question data and return markdown strings. Designed to grow: base rates first, then news, then time series and other data research.

**Module structure**:
```python
# research.py
"""
Multi-model research tools for the Metaculus forecasting bot.
Provides base rate analysis, news research, and (future) time series
and historical data research. All functions are async and return
markdown strings suitable for appending to the research context
passed to forecast prompts.
"""
import asyncio
import logging
from forecasting_tools import GeneralLlm

logger = logging.getLogger(__name__)

# ── Model configuration ──────────────────────────────────────────────
# These match the OpenRouter model strings used in main.py llms dict.
# Override via function parameters for notebook experimentation.
DEFAULT_RESEARCHER_MODEL_A = "openrouter/openai/gpt-5.2"
DEFAULT_RESEARCHER_MODEL_B = "openrouter/anthropic/claude-opus-4-6"
DEFAULT_SYNTHESIZER_MODEL = "openrouter/openai/o4-mini"


# ── Public entry points ───────────────────────────────────────────────
async def get_base_rate_research(
    question_text: str,
    resolution_criteria: str = "",
    fine_print: str = "",
    model_a: str = DEFAULT_RESEARCHER_MODEL_A,
    model_b: str = DEFAULT_RESEARCHER_MODEL_B,
    synthesizer_model: str = DEFAULT_SYNTHESIZER_MODEL,
    use_web_search: bool = False,
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """
    Multi-model base rate researcher. Independently queries two frontier
    models for base rate analysis, then synthesizes with a third model.
    Returns a markdown string to append to research context.
    """
    ...


async def get_news_research(
    question_text: str,
    resolution_criteria: str = "",
    fine_print: str = "",
    model_a: str = DEFAULT_RESEARCHER_MODEL_A,
    model_b: str = DEFAULT_RESEARCHER_MODEL_B,
    synthesizer_model: str = DEFAULT_SYNTHESIZER_MODEL,
    use_web_search: bool = True,   # Default True — news needs web search
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """
    Multi-model news researcher. Independently queries two web-search-enabled
    frontier models for current news and developments, then synthesizes.
    Returns a markdown string to append to research context.
    """
    ...


# ── Shared internal helpers ───────────────────────────────────────────
def _build_base_rate_prompt(
    question_text: str,
    resolution_criteria: str = "",
    fine_print: str = "",
) -> str:
    """Build the structured prompt for base rate analysis."""
    ...


def _build_news_prompt(
    question_text: str,
    resolution_criteria: str = "",
    fine_print: str = "",
) -> str:
    """Build the structured prompt for news research."""
    ...


async def _query_model(
    prompt: str,
    model: str,
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """Query a single model via GeneralLlm and return its response."""
    ...


async def _synthesize_analyses(
    analysis_a: str,
    analysis_b: str,
    question_text: str,
    section_heading: str,
    model: str,
    temperature: float = 0.2,
    timeout: int = 40,
) -> str:
    """Synthesize two independent analyses into a consensus report."""
    ...
```

**Key design decisions**:
- **`GeneralLlm` for all LLM calls** — matches production exactly, supports OpenRouter routing, `:online` suffix, timeouts, and retries
- **No bot class dependency** — functions accept strings, return strings. This makes them testable in notebooks without instantiating `SpringTemplateBotExtended`
- **Model strings as parameters with defaults** — notebooks can experiment with different models (`:online` variants, Perplexity Sonar, etc.) while production uses defaults
- **`use_web_search` flag** — when `True`, appends `:online` suffix to model strings for web-grounded research
- **Shared helpers** — `_query_model()` and `_synthesize_analyses()` are used by both base rate and news researchers (and future research functions). `_synthesize_analyses()` takes a `section_heading` parameter so the output heading varies by research type
- **Parallel-friendly** — `get_base_rate_research()` and `get_news_research()` are independent and can be `asyncio.gather()`'d in the bot's `run_research()` override

### B. Integration Point: `dre_forecasting_tools.py`

`SpringTemplateBotExtended` overrides `run_research()` to call the new module. Base rate and news research run **in parallel** with each other (and alongside the existing AskNews call via `super()`):

```python
# In dre_forecasting_tools.py — addition to SpringTemplateBotExtended
from research import get_base_rate_research, get_news_research

async def run_research(self, question):
    q_text = question.question_text
    q_criteria = getattr(question, 'resolution_criteria', '')
    q_fine_print = getattr(question, 'fine_print', '')

    # Run all research sources in parallel
    asknews_result, base_rate_result, news_result = await asyncio.gather(
        super().run_research(question),        # AskNews (existing)
        get_base_rate_research(                 # Base rate (new)
            question_text=q_text,
            resolution_criteria=q_criteria,
            fine_print=q_fine_print,
            use_web_search=True,
        ),
        get_news_research(                      # News (new)
            question_text=q_text,
            resolution_criteria=q_criteria,
            fine_print=q_fine_print,
        ),
        return_exceptions=True,
    )

    # Assemble: start with AskNews, append successful results
    research = asknews_result if not isinstance(asknews_result, Exception) else ""
    if isinstance(asknews_result, Exception):
        logger.info(f"AskNews research failed for {question.page_url}: {asknews_result}")
    if not isinstance(base_rate_result, Exception):
        research += base_rate_result
    else:
        logger.info(f"Base rate research unavailable for {question.page_url}: {base_rate_result}")
    if not isinstance(news_result, Exception):
        research += news_result
    else:
        logger.info(f"News research unavailable for {question.page_url}: {news_result}")

    return research
```

**Why `dre_forecasting_tools.py` and not `main.py`?** The extended bot class is the one actually instantiated at runtime. Overriding `run_research()` there keeps `main.py` closer to the upstream Metaculus template and isolates our custom research pipeline.

### C. Notebook Code Conventions for Transferability

All notebooks in the 013 series must follow these conventions so code can be copied directly to `research.py`:

| Convention | Rationale |
|-----------|-----------|
| Use `GeneralLlm` for all LLM calls (not raw `AsyncOpenAI`) | Matches production; handles OpenRouter routing, retries, timeouts |
| Use `nest_asyncio.apply()` + `await` in notebooks | Allows async code in Jupyter cells |
| Functions use the **exact same signatures** as the production module | Zero refactoring needed when transferring |
| Mark production functions with `# PRODUCTION TARGET: research.py::function_name` | Clear which cells contain transferable code vs exploration |
| Mark exploration-only cells with `# EXPLORATION ONLY` | These cells (visualizations, comparisons, cost tracking) stay in the notebook |
| Use `SimpleNamespace` for question objects | Established pattern from 012 series; maps API dict fields to bot-framework attribute names |
| Model strings use full OpenRouter paths (e.g., `"openrouter/openai/gpt-5.2:online"`) | Matches `main.py` llms dict format |
| `temperature`, `timeout` as function parameters with defaults | Notebooks can experiment; production uses defaults |

**SimpleNamespace pattern** (from 012 series testbed notebooks):
```python
from types import SimpleNamespace

question = SimpleNamespace(
    question_text=q["title"],
    resolution_criteria=q.get("resolution_criteria", ""),
    fine_print=q.get("fine_print", ""),
    background_info=q.get("description", ""),
)
```

This lets notebooks test with real Metaculus question data while using the same attribute names the bot framework expects.

---

All notebooks below use only existing API keys (`OPENROUTER_API_KEY`). For deferred options requiring `EXA_API_KEY` or other new dependencies, see Appendix A.

#### Notebook 013: Prompt Enhancement A/B Test
**File**: `jupyter/013_Prompt_BaseRate_AB_Test_03-22-2026.ipynb`

**Purpose**: Test the no-cost prompt improvements (Options 1 + 2) by comparing forecast quality before and after.

**Production target**: `main.py` — enhanced prompt text for the "Consider base rates and analogs" sections (~lines 254, 562, 713)
**Functions to extract**: None (prompt text only — copy directly into `main.py` forecast prompt strings)

**Cells**:
1. **Setup**: Import `GeneralLlm`, load the current forecast prompts from `main.py`
2. **Define test questions**: 3 binary, 2 numeric, 2 multiple choice — use questions with known community forecasts for comparison
3. **Baseline run**: Run each question through the current forecast prompt (with generic "consider base rates" section), capture:
   - Raw scenario outputs (9 scenarios per run)
   - Final aggregated forecast
   - Quality of base rate reasoning (manual 1-5 score)
4. **Enhanced run**: Run each question through the enhanced prompt (with Fermi decomposition steps, explicit reference class identification), capture same metrics
5. **Comparison table**: Side-by-side — question, baseline forecast, enhanced forecast, community forecast, baseline reasoning score, enhanced reasoning score `# EXPLORATION ONLY`
6. **Analysis**: Does the enhanced prompt produce more specific base rate reasoning? Are forecasts closer to community median? `# EXPLORATION ONLY`

**Success criteria**: Enhanced prompts produce more structured base rate reasoning in at least 60% of test questions.

**Dependency**: `OPENROUTER_API_KEY` (already have)

**Transfer notes**: The only production artifact is the improved prompt text. Copy the winning prompt wording into the three `### Consider base rates and analogs` sections in `main.py` (binary ~line 254, MC ~line 562, numeric ~line 713).

---

#### Notebook 013a: Multi-Model LLM Base Rate Researcher (**Primary Prototype**)
**File**: `jupyter/013a_MultiModel_BaseRate_Researcher_03-22-2026.ipynb`

**Purpose**: Build and test the multi-model base rate researcher (Option 3) — independently query GPT-5.2 and Claude 4.6 for base rate analysis, then synthesize with a summarizer model. **This is the primary notebook — it produces the production functions for `research.py`.**

**Production target**: `research.py` (new file)
**Functions to extract**:
| Function | Signature | Cell |
|----------|-----------|------|
| `get_base_rate_research()` | `async def get_base_rate_research(question_text, resolution_criteria, fine_print, model_a, model_b, synthesizer_model, use_web_search, temperature, timeout) -> str` | 6 |
| `_build_base_rate_prompt()` | `def _build_base_rate_prompt(question_text, resolution_criteria, fine_print) -> str` | 3 |
| `_query_model()` | `async def _query_model(prompt, model, temperature, timeout) -> str` | 4 |
| `_synthesize_analyses()` | `async def _synthesize_analyses(analysis_a, analysis_b, question_text, model, temperature, timeout) -> str` | 5 |

**Cells** (detailed, production-oriented):

1. **Setup & imports** `# EXPLORATION ONLY`
   ```python
   import nest_asyncio, asyncio, os, time
   from types import SimpleNamespace
   from dotenv import load_dotenv
   from forecasting_tools import GeneralLlm
   nest_asyncio.apply()
   load_dotenv()
   ```

2. **Test question definitions** `# EXPLORATION ONLY`
   - Fetch 5-6 questions from Metaculus API using `MetaculusClient.get_question_by_url()`
   - Or use `SimpleNamespace` with hardcoded question data for reproducibility
   - Questions:
     - Binary with clear reference class (e.g., SpaceX launch success)
     - Binary with ambiguous reference class (e.g., geopolitical event)
     - Numeric with historical trend data (e.g., age records, economic metric)
     - Multiple choice (e.g., "how many new AI labs")
     - Edge case: novel event with no clear historical precedent

3. **`_build_base_rate_prompt()`** `# PRODUCTION TARGET: research.py::_build_base_rate_prompt`
   ```python
   def _build_base_rate_prompt(
       question_text: str,
       resolution_criteria: str = "",
       fine_print: str = "",
   ) -> str:
       """Build the structured prompt for base rate analysis."""
       context_parts = [f"Question: {question_text}"]
       if resolution_criteria:
           context_parts.append(f"Resolution criteria: {resolution_criteria}")
       if fine_print:
           context_parts.append(f"Fine print: {fine_print}")
       context = "\n".join(context_parts)

       return (
           "You are a base rate analyst for a professional forecasting team.\n"
           "Given the following question, provide a detailed base rate analysis:\n\n"
           "1. Identify the most relevant reference class(es)\n"
           "2. Estimate historical frequency: how often has this type of event occurred?\n"
           "3. Provide the numerator (events of interest) and denominator (opportunities)\n"
           "4. Note any trend (increasing, decreasing, stable)\n"
           "5. State key caveats or differences between the reference class and "
           "this specific question\n\n"
           f"{context}"
       )
   ```
   Test: Run on each question, print prompt, verify it looks reasonable.

4. **`_query_model()`** `# PRODUCTION TARGET: research.py::_query_model`
   ```python
   async def _query_model(
       prompt: str,
       model: str,
       temperature: float = 0.3,
       timeout: int = 60,
   ) -> str:
       """Query a single model via GeneralLlm and return its response."""
       llm = GeneralLlm(model=model, temperature=temperature, timeout=timeout)
       return await llm.invoke(prompt)
   ```
   Test: Call with one question on GPT-5.2, print response.

5. **`_synthesize_analyses()`** `# PRODUCTION TARGET: research.py::_synthesize_analyses`
   ```python
   async def _synthesize_analyses(
       analysis_a: str,
       analysis_b: str,
       question_text: str,
       model: str,
       temperature: float = 0.2,
       timeout: int = 40,
   ) -> str:
       """Synthesize two independent analyses into a consensus report."""
       prompt = (
           "You are synthesizing two independent base rate analyses "
           "for a forecasting question.\n"
           "Produce a concise summary that:\n"
           "- States the consensus base rate estimate (if both agree)\n"
           "- Flags disagreements with both perspectives\n"
           "- Provides a final best-estimate rate with confidence "
           "(high/medium/low)\n"
           "- Notes key caveats\n\n"
           f"Question: {question_text}\n\n"
           f"## Analysis A:\n{analysis_a}\n\n"
           f"## Analysis B:\n{analysis_b}"
       )
       llm = GeneralLlm(model=model, temperature=temperature, timeout=timeout)
       return await llm.invoke(prompt)
   ```
   Test: Feed two raw analyses from cell 4, print synthesis.

6. **`get_base_rate_research()`** `# PRODUCTION TARGET: research.py::get_base_rate_research`
   ```python
   async def get_base_rate_research(
       question_text: str,
       resolution_criteria: str = "",
       fine_print: str = "",
       model_a: str = "openrouter/openai/gpt-5.2",
       model_b: str = "openrouter/anthropic/claude-opus-4-6",
       synthesizer_model: str = "openrouter/openai/o4-mini",
       use_web_search: bool = False,
       temperature: float = 0.3,
       timeout: int = 60,
   ) -> str:
       """
       Multi-model base rate researcher. Independently queries two frontier
       models for base rate analysis, then synthesizes with a third model.
       Returns a markdown string to append to research context.
       """
       # Append :online suffix for web-grounded search
       if use_web_search:
           model_a = model_a + ":online" if ":online" not in model_a else model_a
           model_b = model_b + ":online" if ":online" not in model_b else model_b

       prompt = _build_base_rate_prompt(question_text, resolution_criteria, fine_print)

       # Query two frontier models in parallel
       analysis_a, analysis_b = await asyncio.gather(
           _query_model(prompt, model_a, temperature, timeout),
           _query_model(prompt, model_b, temperature, timeout),
       )

       # Synthesize with summarizer
       synthesis = await _synthesize_analyses(
           analysis_a, analysis_b, question_text,
           synthesizer_model, temperature=0.2, timeout=40,
       )

       return f"\n\n## Base Rate Research (Multi-Model)\n{synthesis}"
   ```
   Test: Run end-to-end on each test question, print full output.

7. **Single-question deep dive** `# EXPLORATION ONLY`
   - For each test question, display side-by-side:
     - GPT-5.2 raw analysis (full text)
     - Claude 4.6 raw analysis (full text)
     - Synthesizer output (consensus, disagreements, confidence level)
     - Agreement score: did both models identify the same reference class? Same rate?

8. **Summarizer A/B test** `# EXPLORATION ONLY`
   - Run the same two frontier analyses through both summarizer models:
     - **o4-mini** (`openrouter/openai/o4-mini`, temperature=0.2) — reasoning model, strong at analytical comparison
     - **Claude Sonnet 4.6** (`openrouter/anthropic/claude-sonnet-4-6`, temperature=0.2) — excellent synthesis and structured writing
   - Score each on: conciseness (1-5), accuracy of comparison (1-5), usefulness as forecast context (1-5), neutrality toward both sources (1-5)
   - Note: o4-mini is same provider as GPT-5.2 (potential subtle bias); Sonnet 4.6 is same provider as the Claude 4.6 source (same concern in reverse). The question is whether this matters in practice for factual synthesis.

9. **Quality assessment matrix** `# EXPLORATION ONLY`
   - Reference class quality (1-5)
   - Rate accuracy (spot-check against known data)
   - Disagreement informativeness (did disagreements reveal genuine uncertainty?)
   - Synthesis quality — best summarizer (1-5)

10. **Cost and latency tracking** `# EXPLORATION ONLY`
    - Record per-question costs for all calls (both summarizer variants), wall time
    - Use `time.time()` around each call, capture token counts from response metadata if available

11. **`:online` variant testing** (critical test) `# EXPLORATION ONLY`
    - Re-run the same questions with `use_web_search=True` (which appends `:online` suffix)
    - Compare: Do models now cite real web sources? Are base rate counts more specific? Cost increase?
    - Side-by-side: training-data-only vs `:online` on the same question

12. **Perplexity Sonar variant** `# EXPLORATION ONLY`
    - Try replacing one frontier model with `openrouter/perplexity/sonar-pro`
    - Call: `await get_base_rate_research(..., model_b="openrouter/perplexity/sonar-pro")`
    - Does dedicated search-model improve accuracy vs `:online` suffix?

13. **Summary & recommendations** `# EXPLORATION ONLY`
    - Best summarizer model (o4-mini vs Claude Sonnet 4.6)
    - Best frontier configuration (training-data-only vs `:online` vs Perplexity Sonar swap)
    - Overall: which configuration maximizes quality per dollar?
    - Final recommended defaults for `research.py` constants

**Success criteria**: Multi-model synthesis produces base rate estimates that are (a) more reliable than either model alone, and (b) usefully flag uncertainty when models disagree.

**Dependency**: `OPENROUTER_API_KEY` (already have)

**Cost estimate**: ~$0.25-0.75 total for full test run (5-6 questions × 3 LLM calls × 2 summarizer variants, plus `:online` reruns)

**Transfer notes**: Cells 3-6 copy directly to `research.py` with no changes. Update the module-level default model constants based on cell 13 recommendations (best summarizer, best frontier config, `use_web_search` default).

---

#### Notebook 013b: Multi-Model News Researcher
**File**: `jupyter/013b_MultiModel_News_Researcher_03-23-2026.ipynb`

**Purpose**: Build and test the multi-model news researcher (Option 3a) — same architecture as 013a but with a news-focused prompt. Independently queries two web-search-enabled frontier models for current news and developments, then synthesizes.

**Production target**: `research.py`
**Functions to extract**:
| Function | Signature | Cell |
|----------|-----------|------|
| `get_news_research()` | `async def get_news_research(question_text, resolution_criteria, fine_print, model_a, model_b, synthesizer_model, use_web_search, temperature, timeout) -> str` | 5 |
| `_build_news_prompt()` | `def _build_news_prompt(question_text, resolution_criteria, fine_print) -> str` | 3 |

**Note**: `_query_model()` and `_synthesize_analyses()` are shared with 013a — reuse from that notebook, do not redefine.

**Cells**:
1. **Setup & imports** `# EXPLORATION ONLY`
   ```python
   import nest_asyncio, asyncio, os, time
   from types import SimpleNamespace
   from dotenv import load_dotenv
   from forecasting_tools import GeneralLlm
   nest_asyncio.apply()
   load_dotenv()
   ```

2. **Test question definitions** `# EXPLORATION ONLY`
   - Use the **same test questions** as 013a for direct comparison of base rate vs news research
   - Fetch via `MetaculusClient.get_question_by_url()` or hardcoded `SimpleNamespace`

3. **`_build_news_prompt()`** `# PRODUCTION TARGET: research.py::_build_news_prompt`
   ```python
   def _build_news_prompt(
       question_text: str,
       resolution_criteria: str = "",
       fine_print: str = "",
   ) -> str:
       """Build the structured prompt for news research."""
       context_parts = [f"Question: {question_text}"]
       if resolution_criteria:
           context_parts.append(f"Resolution criteria: {resolution_criteria}")
       if fine_print:
           context_parts.append(f"Fine print: {fine_print}")
       context = "\n".join(context_parts)

       return (
           "You are a news research analyst for a professional forecasting team.\n"
           "Given the following forecasting question, search for and summarize the most "
           "relevant recent news, developments, and expert commentary:\n\n"
           "1. Key recent events or announcements directly relevant to this question\n"
           "2. Policy changes, regulatory actions, or institutional decisions\n"
           "3. Expert statements, analyst reports, or credible forecasts\n"
           "4. Market signals, data releases, or trend changes\n"
           "5. Note the recency and reliability of each source\n\n"
           f"{context}"
       )
   ```
   Test: Run on each question, print prompt, verify it asks for news (not base rates).

4. **Reuse shared helpers from 013a** `# EXPLORATION ONLY`
   - Copy or import `_query_model()` and `_synthesize_analyses()` from 013a
   - These are identical — the only difference is the prompt and section heading

5. **`get_news_research()`** `# PRODUCTION TARGET: research.py::get_news_research`
   ```python
   async def get_news_research(
       question_text: str,
       resolution_criteria: str = "",
       fine_print: str = "",
       model_a: str = "openrouter/openai/gpt-5.2",
       model_b: str = "openrouter/anthropic/claude-opus-4-6",
       synthesizer_model: str = "openrouter/openai/o4-mini",
       use_web_search: bool = True,   # Default True — news needs web
       temperature: float = 0.3,
       timeout: int = 60,
   ) -> str:
       """
       Multi-model news researcher. Independently queries two web-search-enabled
       frontier models for current news and developments, then synthesizes.
       Returns a markdown string to append to research context.
       """
       if use_web_search:
           model_a = model_a + ":online" if ":online" not in model_a else model_a
           model_b = model_b + ":online" if ":online" not in model_b else model_b

       prompt = _build_news_prompt(question_text, resolution_criteria, fine_print)

       analysis_a, analysis_b = await asyncio.gather(
           _query_model(prompt, model_a, temperature, timeout),
           _query_model(prompt, model_b, temperature, timeout),
       )

       synthesis = await _synthesize_analyses(
           analysis_a, analysis_b, question_text,
           section_heading="News Research (Multi-Model)",
           model=synthesizer_model, temperature=0.2, timeout=40,
       )

       return f"\n\n## News Research (Multi-Model)\n{synthesis}"
   ```

6. **Single-question deep dive** `# EXPLORATION ONLY`
   - For 2-3 test questions, display side-by-side: GPT-5.2 news, Claude 4.6 news, synthesis
   - Compare: Do the two models surface different news sources? Different angles?

7. **Compare vs AskNews** `# EXPLORATION ONLY`
   - Run AskNews on the same questions (using existing `AskNewsSearcher`)
   - Side-by-side: AskNews output vs multi-model news output
   - Evaluate: coverage breadth, source diversity, recency, citation quality

8. **Cost and latency tracking** `# EXPLORATION ONLY`
   - Per-question cost breakdown, wall time for parallel calls
   - Compare to AskNews cost (~free with existing subscription)

9. **Summary & recommendations** `# EXPLORATION ONLY`
   - Does multi-model news add value over AskNews alone?
   - Recommended: replace AskNews, supplement AskNews, or skip?
   - Best model configuration for news (same as base rates, or different?)

**Success criteria**: Multi-model news synthesis provides broader or more accurate news coverage than AskNews alone on at least 50% of test questions.

**Dependency**: `OPENROUTER_API_KEY` (already have)

**Cost estimate**: ~$0.15-0.40 total for test run (5-6 questions × 3 LLM calls with `:online`)

**Transfer notes**: Cells 3 and 5 copy directly to `research.py`. The shared helpers (`_query_model`, `_synthesize_analyses`) are already there from 013a. Note that `_synthesize_analyses()` uses a `section_heading` parameter — make sure the 013a version includes this (or update it during 013b development).

---

#### Notebook 013c: Integration Pipeline Prototype
**File**: `jupyter/013c_Integration_Pipeline_03-23-2026.ipynb`

**Purpose**: Combine base rate research (from 013a) and news research (from 013b) into an end-to-end prototype that simulates the full production research pipeline: AskNews (existing) + base rate research + news research → enriched forecast.

**Production target**: `dre_forecasting_tools.py` — the `run_research()` override in `SpringTemplateBotExtended`
**Functions to extract**:
| Function | Target File | Notes |
|----------|------------|-------|
| `run_research()` override | `dre_forecasting_tools.py` | Calls `super().run_research()` + `get_base_rate_research()` + `get_news_research()` in parallel |

**Cells**:
1. **Setup**: Import `get_base_rate_research`, `get_news_research` from cells (or from `research.py` if already created), import `GeneralLlm`, `AskNewsSearcher`
2. **Simulate `run_research()` override** `# PRODUCTION TARGET: dre_forecasting_tools.py::run_research`:
   ```python
   async def enriched_run_research(question) -> str:
       """Simulates the production run_research() override."""
       # Run all three research sources in parallel
       asknews_result, base_rate_result, news_result = await asyncio.gather(
           AskNewsSearcher().call_preconfigured_version(
               "asknews/news-summaries", prompt),
           get_base_rate_research(
               question_text=question.question_text,
               resolution_criteria=getattr(question, 'resolution_criteria', ''),
               fine_print=getattr(question, 'fine_print', ''),
               use_web_search=True,
           ),
           get_news_research(
               question_text=question.question_text,
               resolution_criteria=getattr(question, 'resolution_criteria', ''),
               fine_print=getattr(question, 'fine_print', ''),
           ),
           return_exceptions=True,
       )
       # Assemble: start with AskNews, append successful results
       research = asknews_result if not isinstance(asknews_result, Exception) else ""
       if not isinstance(base_rate_result, Exception):
           research += base_rate_result
       if not isinstance(news_result, Exception):
           research += news_result
       return research
   ```
3. **Run enriched pipeline** on 3-4 test questions, print combined research string
4. **Run forecast prompt** with enriched research — use the actual binary/numeric/MC prompt from `main.py` `# EXPLORATION ONLY`
5. **Compare**: Forecast with standard research vs. enriched research `# EXPLORATION ONLY`
6. **Measure**: Total latency, total cost, forecast quality delta `# EXPLORATION ONLY`
7. **Production readiness**: Does total pipeline time stay under ~2 minutes? Does the combined context fit within token limits? `# EXPLORATION ONLY`

**Success criteria**: Enriched pipeline produces better-informed forecasts without breaking latency or cost budgets, using only existing API keys.

**Dependency**: `OPENROUTER_API_KEY` + `ASKNEWS_CLIENT_ID`/`ASKNEWS_SECRET` (already have)

**Transfer notes**: Cell 2's `enriched_run_research()` becomes the `run_research()` override in `SpringTemplateBotExtended`. The only adaptation: replace `AskNewsSearcher()` call with `await super().run_research(question)` (which already handles AskNews). See Part 7a Section B for the exact production integration code.

Only pursue these notebooks if Exa API access is obtained.

---

### Notebook Execution Order

| Order | Notebook | Dependency | Purpose |
|-------|----------|------------|---------|
| 1 | **013** (Prompt A/B) | `OPENROUTER_API_KEY` | Baseline — test prompt improvements |
| 2 | **013a** (Multi-Model Base Rate Researcher) | `OPENROUTER_API_KEY` | **Primary prototype** — builds `research.py` core functions |
| 3 | **013b** (Multi-Model News Researcher) | `OPENROUTER_API_KEY` | Second researcher — builds `get_news_research()` |
| 4 | **013c** (Integration Pipeline) | Results from 013a + 013b | End-to-end test — builds `run_research()` override |

All notebooks use only existing API keys (`OPENROUTER_API_KEY`). See Appendix A for deferred options (Perplexity Sonar, Exa-based library tools, etc.).

---

## Part 7b: Code Transfer Checklist

Step-by-step process for moving validated notebook code to production. Execute after Notebook 013c confirms the pipeline works end-to-end.

### Prerequisites
- [ ] Notebook 013a completed: best model configuration identified, base rate functions validated
- [ ] Notebook 013b completed: news researcher validated, best config identified
- [ ] Notebook 013c completed: full pipeline tested within latency/cost budgets
- [ ] Recommended defaults documented (best summarizer, `use_web_search` setting, timeout values)

### Step 1: Create `research.py`
- [ ] Create new file at repo root: `research.py`
- [ ] Copy cells marked `# PRODUCTION TARGET: research.py::*` from Notebook 013a (cells 3-6): `_build_base_rate_prompt()`, `_query_model()`, `_synthesize_analyses()`, `get_base_rate_research()`
- [ ] Copy cells marked `# PRODUCTION TARGET: research.py::*` from Notebook 013b (cells 3, 5): `_build_news_prompt()`, `get_news_research()`
- [ ] Add module docstring, imports (`asyncio`, `logging`, `GeneralLlm`)
- [ ] Set module-level default constants based on 013a/013b recommendations
- [ ] Verify: `python -c "from research import get_base_rate_research, get_news_research"` imports cleanly

### Step 2: Integrate into `dre_forecasting_tools.py`
- [ ] Add import: `from research import get_base_rate_research, get_news_research`
- [ ] Override `run_research()` in `SpringTemplateBotExtended` (see Part 7a Section B for exact code)
- [ ] All three research sources run in parallel via `asyncio.gather()` with `return_exceptions=True`

### Step 3: Update prompt text in `main.py` (if Notebook 013 validated improvements)
- [ ] Replace "Consider base rates and analogs" sections (~lines 254, 562, 713) with enhanced prompt text from Notebook 013

### Step 4: Environment and CI
- [ ] No new env vars needed (uses existing `OPENROUTER_API_KEY`)
- [ ] If `:online` models are used, verify OpenRouter account supports web search (should work by default)
- [ ] No changes to `pyproject.toml` (no new dependencies)
- [ ] No changes to GitHub Actions workflows (existing `OPENROUTER_API_KEY` secret suffices)

### Step 5: Test locally
- [ ] Run: `poetry run python main.py --mode test_questions` with a binary and numeric question
- [ ] Verify: base rate and news research sections appear in `forecast_summaries/` output files
- [ ] Verify: total per-question time stays under ~2.5 minutes (current AskNews + forecast is ~60-90s; parallel base rate + news research adds ~15-25s)
- [ ] Verify: forecast quality is at least as good as without base rates (manual spot-check)

### Step 6: Deploy
- [ ] Commit `research.py` + modified `dre_forecasting_tools.py` + modified `main.py`
- [ ] Push to `bot-dev` branch
- [ ] Monitor first few GitHub Actions runs for errors in `run_diagnostics.json`
- [ ] Check OpenRouter usage dashboard for cost impact

---

## Part 8: Key Files Reference

| File | What to Modify | For Which Options |
|------|---------------|-------------------|
| **`research.py`** (new) | `get_base_rate_research()`, `get_news_research()`, shared helpers | Options 3, 3a |
| `main.py` ~line 150 | Research prompt | Option 2 |
| `main.py` ~lines 254, 562, 713 | Forecast prompt base rate sections | Option 1 |
| `dre_forecasting_tools.py` | `run_research()` override — parallel calls to `research.py` functions | Options 3, 3a |

---

## Sources

- [forecasting-tools GitHub Repository](https://github.com/Metaculus/forecasting-tools) — library source and documentation
- [Q2 AI Benchmark Results: Pros Maintain Clear Lead (EA Forum)](https://forum.effectivealtruism.org/posts/F2stjK9wHSy3HPEC9/q2-ai-benchmark-results-pros-maintain-clear-lead) — performance analysis of top forecasting bots
- [Q2 Template Bot source](https://github.com/Metaculus/forecasting-tools/blob/5e21a4f96ab84086b2f84b1c4e31b95ce289c6f2/forecasting_tools/forecast_bots/official_bots/q2_template_bot.py) — official Metaculus template bot architecture
- [Abstraction Substack](https://abstraction.substack.com/) — forecasting methodology newsletter by Jonathan Mann
- Installed `forecasting-tools` library source code (v0.2.80+) — direct code analysis of BaseRateResearcher, KeyFactorsResearcher, NicheListResearcher, Estimator, SmartSearcher

---

## Appendix A: Other Options (Deferred)

These options were investigated but are deferred in favor of the multi-model approach (Options 3 + 3a) which requires no new API keys. Revisit if the primary approach proves insufficient.

### Option 4: DIY Base Rate Research via Perplexity Sonar (No New API Keys)

**What**: Similar to Option 3 but uses Perplexity Sonar (via OpenRouter) which has **built-in web search**. Trades model diversity for web-grounded data.

**Tradeoff vs Option 3**: Option 3 gives model diversity + cross-validation from training data. Option 4 gives web-grounded current data from a single model. These could also be **combined** — use Option 3's multi-model approach but replace one of the two frontier models with Perplexity Sonar to get both diversity and web grounding.

**Note**: The `:online` suffix on Option 3's frontier models largely subsumes this option's value. Perplexity Sonar can still be tested as a `model_a` or `model_b` swap within the existing `get_base_rate_research()` function — no new code needed, just pass `model_b="openrouter/perplexity/sonar-pro"`.

---

### Options Requiring `EXA_API_KEY`

Most `forecasting-tools` research tools (`SmartSearcher`, `KeyFactorsResearcher`, `NicheListResearcher`) **hard-depend on Exa API** (`EXA_API_KEY`). There is no free tier documented. Only pursue if Exa access is obtained (check Metaculus partnership, Exa free trial, or paid plan).

#### Option 5: SmartSearcher for Targeted Historical Queries

**What**: Use `SmartSearcher` directly (not the full BaseRateResearcher pipeline) to ask targeted historical questions generated from the forecast question.

**Approach**:
1. Use LLM to generate 2-3 historical/base-rate questions from the forecast question
2. Run `SmartSearcher` on each
3. Append cited answers to research string

**Cost**: ~$0.02-0.06 per question
**Advantage over Options 3-4**: Structured search results with scoring, deduplication, and source metadata
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
**New dependency**: `EXA_API_KEY`

#### Option 10: Multi-Model Research Diversification

**What**: Run research through multiple LLMs (GPT-5.2 + Claude + o4-mini) and aggregate research findings, not just forecast outputs.

**Cost**: 2-3x current research cost
**Expected impact**: Moderate — EA Forum data shows multi-model diversity helps
**Note**: Options 3 + 3a partially implement this idea for base rates and news specifically.

#### Option 11: Custom Historical Data Pipeline

**What**: Build a custom research agent that queries Wikipedia API, historical events databases, and statistical data sources for time series data relevant to forecast questions.

**Cost**: Development time + API costs vary
**Effort**: High (weeks of development)
**Expected impact**: Potentially highest for numeric questions, but uncertain ROI
