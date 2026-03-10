# News Gathering System for Forecasting Bot
## Planning Report

> **Current Plan:** Let bot run for about 1 week, tentatively implement the News Gathering System on February 1.

**Date:** January 25, 2026
**Author:** Claude (Planning Session with Dre)
**Status:** Planning Phase
**Project:** Alternative to AskNews for Independent Source Gathering

---

# Executive Summary

## Purpose

Develop a news gathering system that collects **independent, high-quality news sources** relevant to probabilistic forecasting questions. Unlike AskNews which provides aggregated summaries, this system will retrieve and present **individual sources separately** with links, enabling forecasters to evaluate source quality and draw their own conclusions.

## Feasibility Assessment

### Search API Options

The critical component is web search capability. Two options have been identified:

#### OPTION A: OpenAI o4-mini-deep-research (PROVISIONAL - Funded)

**Status: ✅ PROVISIONALLY SELECTED** - Uses existing OpenRouter funding

| Model | Input | Output | Web Search | Context |
|-------|-------|--------|------------|---------|
| `openrouter/openai/o4-mini-deep-research` | $2/M | $8/M | **$10/K calls** | 200K |

**Key Characteristics:**
- Model "always uses web_search tool" - search is built-in
- Designed for "complex, multi-step research tasks"
- Supports structured outputs
- Available via OpenRouter (funded)

**⚠️ PROVISIONAL STATUS:** The exact behavior needs testing:
- How many web searches per API call?
- Does it return individual source URLs?
- What format are results returned in?

**Estimated Cost per Question:**
| Component | Calculation | Cost |
|-----------|-------------|------|
| Input tokens (~3K) | 3K × $2/M | $0.006 |
| Output tokens (~2K) | 2K × $8/M | $0.016 |
| Web searches (~3-5 per call)* | 3-5 × $0.01 | $0.03-0.05 |
| **Subtotal per search call** | | **~$0.05-0.07** |
| Multiple calls (3-5 queries) | 3-5 × $0.06 | **$0.18-0.35** |

*Number of web searches per call is uncertain - requires testing.

**For Comparison - Other OpenAI Search Models:**
| Model | Input | Output | Web Search | Notes |
|-------|-------|--------|------------|-------|
| o3-deep-research | $10/M | $40/M | $10/K | More capable, 5x more expensive |
| gpt-4o-search-preview | $2.50/M | $10/M | $35/K | Higher search cost |
| gpt-4o-mini-search-preview | $0.15/M | $0.60/M | $27.50/K | Cheaper tokens, expensive search |

**o4-mini-deep-research has the lowest web search cost at $10/K ($0.01 per search).**

---

#### OPTION B: Exa API (Alternative - Out of Pocket)

**Status: ⚠️ ALTERNATIVE** - Requires separate funding (not covered by existing budget)

| Operation | Cost per 1,000 | Cost per Search |
|-----------|----------------|-----------------|
| Search (fast/auto/neural) | $5 | $0.005 |
| Results (1-25 per search) | $5 | $0.005 |
| Text extraction | $1/1K pages | $0.001/page |
| **Total per search + 10 pages** | | **~$0.02** |

**Exa Pricing Breakdown:**
- 5 searches with results: 5 × $0.01 = $0.05
- Text extraction (50 pages): 50 × $0.001 = $0.05
- **Total per question: ~$0.10**

**Exa Advantages:**
- Returns raw search results with URLs (guaranteed individual sources)
- Already integrated via SmartSearcher in forecasting-tools
- Well-documented API behavior
- Fine-grained control over search parameters

**Exa Disadvantages:**
- **OUT OF POCKET** - Not covered by existing funding
- Requires separate API key and billing
- $10 free credits available for testing

---

### Cost Comparison Summary

| Approach | Search Cost | LLM Processing | Total/Question | Funding |
|----------|-------------|----------------|----------------|---------|
| Current (AskNews) | ~$0.01 | Included | ~$0.01-0.02 | ✅ Funded |
| **o4-mini-deep-research** | ~$0.15-0.25* | Included | **~$0.15-0.25** | ✅ Funded |
| Exa + Claude | ~$0.10 | ~$0.05 | ~$0.15 | ❌ Out of pocket |

*o4-mini estimate is provisional pending testing of actual search behavior.

**Monthly Cost Impact (at 1,500-3,000 questions/month):**
- o4-mini approach: $225-750/month additional
- Exa approach: $225-450/month (out of pocket)

---

### OpenRouter Compatibility: ✅ FULLY FEASIBLE

The entire system can run through OpenRouter with models already in use:

| Component | Model | OpenRouter Available | Notes |
|-----------|-------|---------------------|-------|
| **Web search + research** | o4-mini-deep-research | ✅ Yes | **PROVISIONAL** |
| Source scoring | Claude / gpt-4o-mini | ✅ Yes | Post-processing |
| Source summarization | Claude / gpt-4o-mini | ✅ Yes | Per-source processing |
| Resolution detection | Claude / gpt-4o-mini | ✅ Yes | Single check per question |

**Key Point:** If o4-mini-deep-research works as expected, no new API integrations required.

---

### Show Stoppers Analysis

| Potential Blocker | Assessment | Mitigation |
|-------------------|------------|------------|
| **o4-mini search behavior unknown** | ⚠️ **HIGH PRIORITY** | **Must test before committing** |
| Rate limits (OpenRouter) | ⚠️ Low Risk | OpenRouter has generous limits |
| Paywall content | ⚠️ Medium Risk | Score based on available content |
| API costs higher than AskNews | ⚠️ Expected | Trade-off for independent sources |
| Latency | ⚠️ Medium Risk | Parallelize where possible |
| Source quality variance | ⚠️ Medium Risk | LLM scoring helps filter |

**VERDICT: CONDITIONALLY FEASIBLE**

**Before full implementation, MUST verify:**
1. o4-mini-deep-research returns individual source URLs (not just aggregated text)
2. Actual web search count per call matches cost estimates
3. Output format is compatible with downstream processing

**Recommendation:** Run a test with 2-3 questions to validate o4-mini behavior before proceeding.

## Success Metrics

1. **Breadth:** 5-10 independent sources per question from diverse outlets
2. **Quality:** Sources contain quantitative data relevant to outcome determination
3. **Reliability:** Established news sources preferred; source credibility noted
4. **Traceability:** Every piece of information linked to specific source URL

## Recommendation

**Proceed with phased implementation.** Start with Phase 1 (query generation) as a low-risk proof of concept, then evaluate before continuing to full implementation.

---

# Detailed Implementation Plan

## System Architecture Overview

### Option A: o4-mini-deep-research (PROVISIONAL - Funded)

```
┌─────────────────────────────────────────────────────────────────────┐
│              NEWS GATHERING PIPELINE (o4-mini-deep-research)        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌────────────────────────────────────┐        │
│  │   QUESTION   │───▶│     o4-mini-deep-research          │        │
│  │   INPUT      │    │  (OpenRouter - FUNDED)             │        │
│  └──────────────┘    │  • Generates search queries        │        │
│                      │  • Executes web searches           │        │
│                      │  • Returns results with URLs       │        │
│                      └──────────────┬─────────────────────┘        │
│                                     │                               │
│                      ┌──────────────▼─────────────────────┐        │
│                      │  EXTRACT INDIVIDUAL SOURCES        │        │
│                      │  (Parse URLs from o4-mini output)  │        │
│                      └──────────────┬─────────────────────┘        │
│                                     │                               │
│                      ┌──────────────▼─────────────────────┐        │
│                      │  Claude/gpt-4o-mini                │        │
│                      │  • Source scoring & filtering      │        │
│                      │  • Per-source summarization        │        │
│                      │  • Resolution detection            │        │
│                      └──────────────┬─────────────────────┘        │
│                                     │                               │
│                      ┌──────────────▼─────────────────────┐        │
│                      │  FINAL OUTPUT (to forecaster)      │        │
│                      │  5-10 independent source summaries │        │
│                      └────────────────────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Option B: Exa API (Alternative - Out of Pocket)

```
┌─────────────────────────────────────────────────────────────────────┐
│                NEWS GATHERING PIPELINE (Exa - OUT OF POCKET)        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   QUESTION   │───▶│    QUERY     │───▶│   EXA API    │          │
│  │   INPUT      │    │  GENERATOR   │    │  ($$$ OOP)   │          │
│  └──────────────┘    │ (Claude/GPT) │    └──────────────┘          │
│                      └──────────────┘           │                   │
│                                           ┌─────▼─────┐             │
│                                           │  RAW      │             │
│                                           │  RESULTS  │             │
│                                           │ (20-50)   │             │
│                                           └─────┬─────┘             │
│                                                 │                   │
│                      ┌──────────────────────────▼─────────────┐    │
│                      │  Claude/gpt-4o-mini                    │    │
│                      │  • Source scoring & filtering          │    │
│                      │  • Per-source summarization            │    │
│                      │  • Resolution detection                │    │
│                      └──────────────┬─────────────────────────┘    │
│                                     │                               │
│                      ┌──────────────▼─────────────────────┐        │
│                      │  FINAL OUTPUT (to forecaster)      │        │
│                      │  5-10 independent source summaries │        │
│                      └────────────────────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Models

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SearchQuery(BaseModel):
    """Generated search query with intent"""
    query_text: str
    search_intent: str  # e.g., "current status", "expert forecasts", "recent developments"
    priority: int = Field(..., ge=1, le=5)  # 1=highest priority

class RawSource(BaseModel):
    """Raw search result before scoring"""
    url: str
    title: str
    snippet: str
    source_name: str  # e.g., "Reuters", "NYT", "BBC"
    publication_date: Optional[datetime] = None
    query_origin: str  # Which search query found this

class ScoredSource(BaseModel):
    """Source with relevance scoring"""
    url: str
    title: str
    source_name: str
    publication_date: Optional[datetime]
    relevance_score: float = Field(..., ge=0, le=1)
    has_quantitative_data: bool
    quantitative_preview: Optional[str]  # Brief note on what quant data exists
    credibility_tier: str  # "high", "medium", "low", "unknown"

class SourceSummary(BaseModel):
    """Final structured summary of a single source"""
    source_url: str
    source_name: str
    publication_date: Optional[str]
    credibility_tier: str

    # Content summary
    summary: str  # 1-2 paragraphs

    # Forecasting-relevant extractions
    quantitative_findings: list[str]  # Specific numbers, dates, measurements
    current_status: Optional[str]  # What is the current state?
    trend_direction: Optional[str]  # "increasing", "decreasing", "stable", "volatile"
    outcome_implications: str  # What this source suggests about likely outcomes

    # Metadata
    relevance_score: float

class ResolutionCheck(BaseModel):
    """Check if question appears already resolved"""
    appears_resolved: bool
    resolution_evidence: Optional[str]
    suggested_outcome: Optional[str]
    confidence: float = Field(..., ge=0, le=1)

class ProcessedNewsOutput(BaseModel):
    """Final output for forecaster consumption"""
    question_text: str
    search_timestamp: str

    # Individual source summaries (NOT aggregated)
    sources: list[SourceSummary]

    # Resolution detection
    resolution_check: ResolutionCheck

    # Metadata
    total_sources_found: int
    sources_after_filtering: int
    search_queries_used: list[str]
```

## Phase 1: Query Generation Module

**Goal:** Generate 3-5 diverse search queries that cover different angles of the forecasting question.

**Implementation:**

```python
# news_gatherer/query_generator.py

from forecasting_tools import clean_indents, structure_output

QUERY_GENERATION_PROMPT = """
You are a research assistant helping a superforecaster gather news for a probabilistic forecast.

## Forecasting Question
{question_text}

## Question Background
{background_info}

## Resolution Criteria
{resolution_criteria}

## Today's Date
{current_date}

## Your Task
Generate 3-5 web search queries that will find the most useful news sources for forecasting this question.

## Query Design Principles
1. **Quantitative Focus:** Prioritize queries likely to find numbers, statistics, measurements
2. **Current Status:** At least one query should find the current state of affairs
3. **Expert/Market Views:** At least one query should find expert predictions or market indicators
4. **Recent Developments:** At least one query should find recent news (within last 30 days)
5. **Avoid Aggregators:** Design queries to find primary sources, not news aggregators

## Query Types to Include
- Current status/latest data query
- Trend/trajectory query
- Expert forecast/prediction query
- Recent news/developments query
- (Optional) Historical context if relevant

## Output Format
Provide 3-5 search queries, each with:
- The exact search query text
- The search intent (what type of information you expect to find)
- Priority (1-5, where 1 is highest priority)
"""

async def generate_search_queries(
    question: MetaculusQuestion,
    llm: GeneralLlm,
    num_queries: int = 5
) -> list[SearchQuery]:
    """Generate diverse search queries for a forecasting question."""

    prompt = clean_indents(QUERY_GENERATION_PROMPT.format(
        question_text=question.question_text,
        background_info=question.background_info or "Not provided",
        resolution_criteria=question.resolution_criteria or "Not provided",
        current_date=datetime.now().strftime("%Y-%m-%d")
    ))

    queries = await structure_output(
        prompt,
        list[SearchQuery],
        model=llm,
        num_validation_samples=2
    )

    # Sort by priority and limit
    queries.sort(key=lambda q: q.priority)
    return queries[:num_queries]
```

**Testing Strategy:**
- Run on 10 diverse questions from different domains
- Manually evaluate query quality and diversity
- Verify queries return relevant results in manual web search

**Estimated Time:** 2-3 hours

---

## Phase 2: Web Search Execution

**Goal:** Execute generated queries against web search APIs and collect raw results.

---

### OPTION A: o4-mini-deep-research (PROVISIONAL - Funded)

**Status:** ⚠️ REQUIRES TESTING before confirming this approach works.

```python
# news_gatherer/search_executor_o4.py

from forecasting_tools import GeneralLlm, clean_indents, structure_output
import asyncio

# Model for deep research with built-in web search
O4_DEEP_RESEARCH_MODEL = "openrouter/openai/o4-mini-deep-research"

DEEP_RESEARCH_PROMPT = """
You are a research assistant gathering news sources for a probabilistic forecast.

## Forecasting Question
{question_text}

## Search Query
{query_text}

## Search Intent
{search_intent}

## Your Task
Search the web for relevant, high-quality news sources that address this query.

## Requirements
1. Find 5-10 relevant news articles or data sources
2. Prioritize sources with QUANTITATIVE DATA (numbers, statistics, measurements)
3. Include the FULL URL for each source
4. Note the publication date if available
5. Extract a brief snippet of the most relevant content

## Output Format
For each source found, provide:
- url: The complete URL
- title: Article/page title
- source_name: Publication name (e.g., "Reuters", "NYT")
- publication_date: Date if known, null otherwise
- snippet: 2-3 sentence excerpt of relevant content
- has_quantitative_data: true/false
"""

async def execute_search_o4(
    query: SearchQuery,
    question_text: str,
    llm: GeneralLlm
) -> list[RawSource]:
    """
    Execute a single search using o4-mini-deep-research.

    ⚠️ PROVISIONAL: Actual behavior needs verification.
    The model "always uses web_search tool" but exact output format is unknown.
    """
    prompt = clean_indents(DEEP_RESEARCH_PROMPT.format(
        question_text=question_text,
        query_text=query.query_text,
        search_intent=query.search_intent
    ))

    # Use structured output to extract sources
    sources = await structure_output(
        prompt,
        list[RawSource],
        model=llm,
        num_validation_samples=1
    )

    # Tag each source with the query that found it
    for source in sources:
        source.query_origin = query.query_text

    return sources

async def execute_all_searches_o4(
    queries: list[SearchQuery],
    question_text: str
) -> list[RawSource]:
    """Execute multiple search queries using o4-mini-deep-research."""

    llm = GeneralLlm(
        model=O4_DEEP_RESEARCH_MODEL,
        temperature=0,
        timeout=120  # Deep research may take longer
    )

    all_results = []
    seen_urls = set()

    # Execute searches (can parallelize, but watch rate limits)
    for query in queries:
        try:
            sources = await execute_search_o4(query, question_text, llm)
            for source in sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    all_results.append(source)
        except Exception as e:
            logger.error(f"Search failed for query '{query.query_text}': {e}")

    return all_results
```

**⚠️ TESTING REQUIRED:**
Before relying on this approach, verify:
1. Does o4-mini-deep-research return individual source URLs?
2. How many web searches does it make per call?
3. What is the actual cost per call?

**Estimated Cost per Question:**
- 3-5 API calls × ~$0.05-0.07 each = **$0.15-0.35**

---

### OPTION B: Exa API (Alternative - Out of Pocket)

**Status:** ❌ OUT OF POCKET - Requires separate funding

```python
# news_gatherer/search_executor_exa.py

from forecasting_tools import SmartSearcher
import asyncio

async def execute_searches_exa(
    queries: list[SearchQuery],
    results_per_query: int = 10
) -> list[RawSource]:
    """
    Execute multiple search queries using Exa API.

    ⚠️ OUT OF POCKET: Exa requires separate API key and funding.
    Cost: ~$0.02 per search with content extraction.
    """
    all_results = []
    seen_urls = set()

    async def run_single_search(query: SearchQuery) -> list[RawSource]:
        searcher = SmartSearcher(
            model="openrouter/openai/gpt-4o-mini",  # For query enhancement
            temperature=0,
            num_searches_to_run=1,
            num_sites_per_search=results_per_query,
            use_advanced_filters=False
        )

        results = await searcher.get_search_results(query.query_text)

        sources = []
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                sources.append(RawSource(
                    url=result.url,
                    title=result.title,
                    snippet=result.text[:500] if result.text else "",
                    source_name=extract_source_name(result.url),
                    publication_date=result.published_date,
                    query_origin=query.query_text
                ))
        return sources

    # Execute all searches in parallel
    search_tasks = [run_single_search(q) for q in queries]
    results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

    for result_list in results_lists:
        if isinstance(result_list, list):
            all_results.extend(result_list)

    return all_results

def extract_source_name(url: str) -> str:
    """Extract publication name from URL."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    name = domain.replace("www.", "").split(".")[0]
    return name.title()
```

**Exa Cost Breakdown:**
| Operation | Cost |
|-----------|------|
| 5 searches | $0.025 |
| 50 results (10 per search) | $0.025 |
| Text extraction (50 pages) | $0.05 |
| **Total per question** | **~$0.10** |

---

### Search Executor Factory

```python
# news_gatherer/search_executor.py

from enum import Enum

class SearchBackend(Enum):
    O4_DEEP_RESEARCH = "o4_deep_research"  # Funded via OpenRouter
    EXA = "exa"  # Out of pocket

async def execute_searches(
    queries: list[SearchQuery],
    question_text: str,
    backend: SearchBackend = SearchBackend.O4_DEEP_RESEARCH
) -> list[RawSource]:
    """
    Execute searches using configured backend.

    Args:
        queries: List of search queries to execute
        question_text: The forecasting question (for context)
        backend: Which search API to use
    """
    if backend == SearchBackend.O4_DEEP_RESEARCH:
        return await execute_all_searches_o4(queries, question_text)
    elif backend == SearchBackend.EXA:
        return await execute_searches_exa(queries)
    else:
        raise ValueError(f"Unknown search backend: {backend}")
```

**Estimated Time:** 3-4 hours

---

## Phase 3: Source Scoring and Selection

**Goal:** Score each source for forecasting relevance and select top 5-10.

**Implementation:**

```python
# news_gatherer/source_scorer.py

SOURCE_SCORING_PROMPT = """
You are evaluating news sources for their usefulness in making a probabilistic forecast.

## Forecasting Question
{question_text}

## Source to Evaluate
**Title:** {title}
**URL:** {url}
**Source:** {source_name}
**Date:** {publication_date}
**Snippet:** {snippet}

## Scoring Criteria

### Relevance (0-1)
- 1.0: Directly addresses the forecast question with specific data
- 0.7-0.9: Highly relevant, contains useful context or related data
- 0.4-0.6: Somewhat relevant, tangentially related
- 0.1-0.3: Minimally relevant
- 0.0: Not relevant at all

### Quantitative Data
Does this source appear to contain specific numbers, statistics, dates, or measurements that could inform the forecast?
- Look for: percentages, counts, dollar amounts, dates, growth rates, etc.
- If yes, briefly note what quantitative data appears to be present

### Credibility Tier
Based on the source name and URL:
- "high": Major news outlets (Reuters, AP, BBC, NYT, WSJ, etc.), government sources, academic institutions
- "medium": Established industry publications, reputable blogs, regional news
- "low": Unknown sources, opinion sites, aggregators
- "unknown": Cannot determine from available information

## Output
Provide your assessment as a ScoredSource object.
"""

async def score_sources(
    sources: list[RawSource],
    question: MetaculusQuestion,
    llm: GeneralLlm,
    top_n: int = 10
) -> list[ScoredSource]:
    """Score and rank sources, returning top N."""

    scored = []

    # Process in batches to manage API calls
    for source in sources:
        prompt = clean_indents(SOURCE_SCORING_PROMPT.format(
            question_text=question.question_text,
            title=source.title,
            url=source.url,
            source_name=source.source_name,
            publication_date=source.publication_date or "Unknown",
            snippet=source.snippet
        ))

        scored_source = await structure_output(
            prompt,
            ScoredSource,
            model=llm
        )
        scored.append(scored_source)

    # Sort by relevance score, prefer sources with quantitative data
    scored.sort(key=lambda s: (s.relevance_score, s.has_quantitative_data), reverse=True)

    # Filter: minimum relevance threshold
    filtered = [s for s in scored if s.relevance_score >= 0.4]

    return filtered[:top_n]
```

**Optimization:** Batch multiple sources into single LLM call to reduce cost.

**Estimated Time:** 4-5 hours

---

## Phase 4: Per-Source Summarization

**Goal:** Create structured summaries for each selected source, extracting forecasting-relevant information.

**Implementation:**

```python
# news_gatherer/source_summarizer.py

SOURCE_SUMMARY_PROMPT = """
You are a research assistant creating a structured summary of a news source for a superforecaster.

## Forecasting Question Being Researched
{question_text}

## Source to Summarize
**URL:** {url}
**Title:** {title}
**Source:** {source_name}
**Publication Date:** {publication_date}
**Full Text or Excerpt:**
{content}

## Your Task
Create a structured summary that extracts all information relevant to forecasting this question.

## Summary Requirements

### 1. Summary (1-2 paragraphs)
Write a concise summary of the source focusing ONLY on information relevant to the forecasting question.
Ignore tangential information.

### 2. Quantitative Findings
List ALL specific numbers, statistics, dates, or measurements from this source that could inform the forecast:
- Include: percentages, counts, dollar amounts, dates, growth rates, polls, market data
- Format each as a standalone fact that can be understood without context
- If no quantitative data, return empty list

### 3. Current Status
What does this source say about the CURRENT state of affairs relevant to the question?
(Leave null if not addressed)

### 4. Trend Direction
Based on this source, what direction are things moving?
- "increasing" / "decreasing" / "stable" / "volatile" / "unclear"
(Leave null if not addressed)

### 5. Outcome Implications
In 1-2 sentences: What does this source suggest about the likely outcome of the forecast question?
Be specific about whether it points toward higher or lower probability, earlier or later dates, etc.

## Important
- Extract information, don't add interpretation beyond what the source states
- Include the source URL so forecasters can verify
- Note any caveats or limitations mentioned in the source
"""

async def summarize_source(
    source: ScoredSource,
    question: MetaculusQuestion,
    llm: GeneralLlm
) -> SourceSummary:
    """Create structured summary of a single source."""

    # Fetch full content if available (may need to use WebFetch or similar)
    content = await fetch_source_content(source.url)

    prompt = clean_indents(SOURCE_SUMMARY_PROMPT.format(
        question_text=question.question_text,
        url=source.url,
        title=source.title,
        source_name=source.source_name,
        publication_date=source.publication_date or "Unknown",
        content=content[:8000]  # Limit context size
    ))

    summary = await structure_output(
        prompt,
        SourceSummary,
        model=llm
    )

    # Preserve metadata from scoring
    summary.source_url = source.url
    summary.source_name = source.source_name
    summary.credibility_tier = source.credibility_tier
    summary.relevance_score = source.relevance_score

    return summary

async def summarize_all_sources(
    sources: list[ScoredSource],
    question: MetaculusQuestion,
    llm: GeneralLlm
) -> list[SourceSummary]:
    """Summarize all sources in parallel."""

    tasks = [summarize_source(s, question, llm) for s in sources]
    summaries = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failures
    valid_summaries = [s for s in summaries if isinstance(s, SourceSummary)]

    return valid_summaries
```

**Estimated Time:** 4-5 hours

---

## Phase 5: Resolution Detection

**Goal:** Check if any sources indicate the question has already resolved.

**Implementation:**

```python
# news_gatherer/resolution_detector.py

RESOLUTION_CHECK_PROMPT = """
You are checking whether a forecasting question appears to have already been resolved based on news sources.

## Forecasting Question
{question_text}

## Resolution Criteria
{resolution_criteria}

## Source Summaries
{source_summaries}

## Your Task
Determine if any of these sources indicate that the question's outcome is already known or determined.

### Signs of Resolution:
- Official announcements of outcomes
- Final vote counts, election results
- Confirmed events that satisfy resolution criteria
- Definitive statements from authoritative sources

### NOT Resolution:
- Predictions or forecasts (even confident ones)
- Preliminary or unofficial results
- Partial outcomes (unless resolution criteria accepts partial)

## Output
- appears_resolved: true/false
- resolution_evidence: Quote or describe the specific evidence (if resolved)
- suggested_outcome: What the resolution appears to be (if resolved)
- confidence: 0-1 how confident you are in this assessment
"""

async def check_resolution(
    summaries: list[SourceSummary],
    question: MetaculusQuestion,
    llm: GeneralLlm
) -> ResolutionCheck:
    """Check if sources indicate question is already resolved."""

    # Format summaries for prompt
    summaries_text = "\n\n".join([
        f"**{s.source_name}** ({s.source_url}):\n{s.summary}\nOutcome implications: {s.outcome_implications}"
        for s in summaries
    ])

    prompt = clean_indents(RESOLUTION_CHECK_PROMPT.format(
        question_text=question.question_text,
        resolution_criteria=question.resolution_criteria or "Not specified",
        source_summaries=summaries_text
    ))

    return await structure_output(
        prompt,
        ResolutionCheck,
        model=llm
    )
```

**Estimated Time:** 2-3 hours

---

## Phase 6: Integration with Forecast Bot

**Goal:** Replace or augment `run_research()` with new news gathering pipeline.

**Implementation:**

```python
# news_gatherer/main.py

class NewsGatherer:
    """
    Independent news gathering system for forecasting questions.
    Alternative to AskNews that preserves individual source independence.
    """

    def __init__(
        self,
        llm_model: str = "openrouter/openai/gpt-4o-mini",
        num_queries: int = 5,
        results_per_query: int = 10,
        top_sources: int = 7,
        min_relevance: float = 0.4
    ):
        self.llm = GeneralLlm(model=llm_model, temperature=0)
        self.num_queries = num_queries
        self.results_per_query = results_per_query
        self.top_sources = top_sources
        self.min_relevance = min_relevance

    async def gather_news(
        self,
        question: MetaculusQuestion
    ) -> ProcessedNewsOutput:
        """
        Full news gathering pipeline for a forecasting question.

        Returns structured output with independent source summaries.
        """
        logger.info(f"Starting news gathering for: {question.question_text[:50]}...")

        # Phase 1: Generate search queries
        queries = await generate_search_queries(
            question, self.llm, self.num_queries
        )
        logger.info(f"Generated {len(queries)} search queries")

        # Phase 2: Execute searches
        raw_sources = await execute_searches(
            queries, self.results_per_query
        )
        logger.info(f"Found {len(raw_sources)} raw sources")

        # Phase 3: Score and filter sources
        scored_sources = await score_sources(
            raw_sources, question, self.llm, self.top_sources
        )
        logger.info(f"Selected {len(scored_sources)} top sources")

        # Phase 4: Summarize each source
        summaries = await summarize_all_sources(
            scored_sources, question, self.llm
        )
        logger.info(f"Created {len(summaries)} source summaries")

        # Phase 5: Check for resolution
        resolution = await check_resolution(
            summaries, question, self.llm
        )
        if resolution.appears_resolved:
            logger.warning(f"Question may be resolved: {resolution.resolution_evidence}")

        # Assemble final output
        return ProcessedNewsOutput(
            question_text=question.question_text,
            search_timestamp=datetime.now(timezone.utc).isoformat(),
            sources=summaries,
            resolution_check=resolution,
            total_sources_found=len(raw_sources),
            sources_after_filtering=len(scored_sources),
            search_queries_used=[q.query_text for q in queries]
        )

    def format_for_forecaster(self, output: ProcessedNewsOutput) -> str:
        """
        Format ProcessedNewsOutput as markdown string for forecaster prompt.

        Preserves individual source independence - does NOT aggregate.
        """
        lines = [
            "# Research Summary",
            f"*Search conducted: {output.search_timestamp}*",
            f"*Sources found: {output.total_sources_found} → filtered to {len(output.sources)}*",
            ""
        ]

        # Resolution warning if applicable
        if output.resolution_check.appears_resolved:
            lines.extend([
                "## ⚠️ RESOLUTION ALERT",
                f"This question may already be resolved.",
                f"**Evidence:** {output.resolution_check.resolution_evidence}",
                f"**Suggested outcome:** {output.resolution_check.suggested_outcome}",
                f"**Confidence:** {output.resolution_check.confidence:.0%}",
                ""
            ])

        # Individual source summaries
        lines.append("## Independent Source Summaries")
        lines.append("*Each source summarized independently - not aggregated*")
        lines.append("")

        for i, source in enumerate(output.sources, 1):
            lines.extend([
                f"### Source {i}: {source.source_name}",
                f"**URL:** {source.source_url}",
                f"**Date:** {source.publication_date or 'Unknown'}",
                f"**Credibility:** {source.credibility_tier}",
                f"**Relevance Score:** {source.relevance_score:.2f}",
                "",
                source.summary,
                ""
            ])

            if source.quantitative_findings:
                lines.append("**Quantitative Data:**")
                for finding in source.quantitative_findings:
                    lines.append(f"- {finding}")
                lines.append("")

            if source.current_status:
                lines.append(f"**Current Status:** {source.current_status}")

            if source.trend_direction:
                lines.append(f"**Trend:** {source.trend_direction}")

            lines.append(f"**Outcome Implications:** {source.outcome_implications}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


# Integration with existing bot
class SpringTemplateBotWithNewsGatherer(SpringTemplateBotExtended):
    """Bot using new news gathering system instead of AskNews."""

    def __init__(self, *args, use_news_gatherer: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_news_gatherer = use_news_gatherer
        self.news_gatherer = NewsGatherer() if use_news_gatherer else None

    async def run_research(self, question: MetaculusQuestion) -> str:
        if self.use_news_gatherer and self.news_gatherer:
            # Use new system
            output = await self.news_gatherer.gather_news(question)
            return self.news_gatherer.format_for_forecaster(output)
        else:
            # Fall back to original AskNews-based research
            return await super().run_research(question)
```

**Estimated Time:** 4-6 hours

---

## Phase 7: Testing and Evaluation

**Goal:** Validate system quality against success metrics.

### Testing Protocol

1. **Unit Tests**
   - Query generation produces diverse, relevant queries
   - Source scoring correctly identifies relevant sources
   - Summarization extracts key forecasting information
   - Resolution detection catches obvious resolved questions

2. **Integration Tests**
   - Full pipeline runs without errors
   - Output format compatible with forecaster prompts
   - Cost tracking matches estimates

3. **Quality Evaluation** (Manual)
   - Run on 20 diverse questions across domains
   - Evaluate each output against success metrics:

| Metric | Evaluation Method | Target |
|--------|-------------------|--------|
| **Breadth** | Count unique sources; assess domain diversity | 5-10 sources from 3+ domains |
| **Quality** | % of sources with quantitative data | >60% have quant data |
| **Reliability** | % of sources from high-credibility tier | >50% high credibility |
| **Independence** | Verify sources are distinct (not aggregators) | 0% aggregator sources |

4. **A/B Comparison**
   - Run same questions through AskNews and NewsGatherer
   - Compare: source count, quantitative data presence, forecaster-rated usefulness
   - Track cost difference

**Estimated Time:** 6-8 hours

---

## Implementation Timeline

| Phase | Description | Est. Hours | Dependencies |
|-------|-------------|------------|--------------|
| 1 | Query Generation | 2-3 | None |
| 2 | Web Search Execution | 3-4 | Phase 1 |
| 3 | Source Scoring | 4-5 | Phase 2 |
| 4 | Per-Source Summarization | 4-5 | Phase 3 |
| 5 | Resolution Detection | 2-3 | Phase 4 |
| 6 | Bot Integration | 4-6 | Phases 1-5 |
| 7 | Testing & Evaluation | 6-8 | Phase 6 |
| **Total** | | **25-34 hours** | |

**Recommended Approach:** Implement phases sequentially with evaluation checkpoints after Phases 1, 4, and 7.

---

## File Structure

```
metac_bot_Spring_2026/
├── news_gatherer/
│   ├── __init__.py
│   ├── models.py              # Pydantic data models
│   ├── query_generator.py     # Phase 1
│   ├── search_executor.py     # Phase 2
│   ├── source_scorer.py       # Phase 3
│   ├── source_summarizer.py   # Phase 4
│   ├── resolution_detector.py # Phase 5
│   ├── main.py                # Pipeline orchestration
│   └── tests/
│       ├── test_query_generator.py
│       ├── test_source_scorer.py
│       └── test_integration.py
├── main.py                    # Existing bot (unchanged)
├── dre_forecasting_tools.py   # Existing extensions
└── ...
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **o4-mini doesn't return URLs** | **Medium** | **HIGH** | **Test before committing; fallback to Exa (OOP)** |
| **o4-mini cost higher than estimated** | **Medium** | **Medium** | **Test actual billing; adjust query count** |
| Search API rate limits | Low | High | Implement exponential backoff; cache results |
| LLM hallucination in summaries | Medium | Medium | Use structure_output validation; include source links for verification |
| Poor source quality | Medium | Medium | Credibility scoring; fallback to AskNews |
| Cost overrun | Low | Medium | Per-question cost tracking; configurable source limits |
| Latency too high | Medium | Low | Parallelize all independent operations; timeout handling |

---

## IMMEDIATE NEXT STEP: Test o4-mini-deep-research

**Before proceeding with full implementation, run this test:**

```python
# test_o4_deep_research.py
"""
Test script to verify o4-mini-deep-research behavior.
Run this BEFORE committing to the implementation plan.
"""

import asyncio
from forecasting_tools import GeneralLlm

async def test_o4_search():
    llm = GeneralLlm(
        model="openrouter/openai/o4-mini-deep-research",
        temperature=0,
        timeout=120
    )

    test_prompt = """
    Search the web for recent news about Federal Reserve interest rate decisions in 2026.

    For each relevant source you find, provide:
    1. The complete URL
    2. The article title
    3. The publication name
    4. A 2-3 sentence summary of the key information

    Find 5-7 high-quality sources from reputable news outlets.
    """

    print("Sending request to o4-mini-deep-research...")
    response = await llm.invoke(test_prompt)

    print("\n" + "="*60)
    print("RESPONSE:")
    print("="*60)
    print(response)
    print("\n" + "="*60)

    # Check for URLs in response
    import re
    urls = re.findall(r'https?://[^\s\)\"\']+', response)
    print(f"\nURLs found: {len(urls)}")
    for url in urls:
        print(f"  - {url}")

    return response

if __name__ == "__main__":
    asyncio.run(test_o4_search())
```

**Verify these questions:**
1. ✅/❌ Does the response include individual source URLs?
2. ✅/❌ Are the URLs real and accessible?
3. ✅/❌ How many web searches were billed? (Check OpenRouter dashboard)
4. ✅/❌ What was the actual cost?

**Decision Gate:**
- If o4-mini returns usable URLs → Proceed with Option A
- If o4-mini doesn't return URLs → Fall back to Option B (Exa, out of pocket)

---

## Success Criteria for Go/No-Go Decision

### Phase 0: o4-mini-deep-research Validation (MUST PASS FIRST)
- [ ] o4-mini returns individual source URLs (not just aggregated text)
- [ ] URLs are real and accessible (not hallucinated)
- [ ] Actual cost per call matches estimate (~$0.05-0.07)
- [ ] Response format is parseable for downstream processing

**If Phase 0 fails:** Fall back to Exa (out of pocket) or reconsider project scope.

---

After Phase 1 evaluation:
- [ ] Query generation produces 3-5 relevant, diverse queries
- [ ] Manual search with generated queries finds relevant sources

After Phase 4 evaluation:
- [ ] Source summaries capture key forecasting-relevant information
- [ ] Quantitative data extraction working (>50% of sources with quant data)
- [ ] Cost per question within 2x of estimate (~$0.30-0.50 for o4-mini approach)

After Phase 7 evaluation:
- [ ] Breadth: Average 5+ independent sources per question
- [ ] Quality: >60% of sources have quantitative data
- [ ] Reliability: >50% of sources from high-credibility tier
- [ ] User assessment: News gathering rated "useful" for >80% of questions

---

## Appendix: Example Output

**Question:** "Will the US Federal Reserve cut interest rates before July 2026?"

**Generated Queries:**
1. "Federal Reserve interest rate decision 2026" (current status)
2. "Fed funds rate forecast 2026 economists" (expert views)
3. "FOMC meeting schedule 2026 rate expectations" (upcoming events)
4. "US inflation data January 2026" (relevant indicators)
5. "Federal Reserve Powell testimony 2026" (official statements)

**Sample Source Summary:**

### Source 3: Reuters
**URL:** https://www.reuters.com/markets/us/fed-officials-signal-patience-on-rate-cuts-2026-01-20/
**Date:** January 20, 2026
**Credibility:** high
**Relevance Score:** 0.92

Fed officials indicated at the January FOMC meeting that they see no urgency to cut rates given persistent inflation above the 2% target. Governor Waller noted that the economy remains resilient and labor markets tight, suggesting the Fed can afford to wait for more data before adjusting policy.

**Quantitative Data:**
- Current Fed funds rate: 4.25-4.50%
- December 2025 CPI: 3.2% year-over-year
- Market pricing: 65% probability of first cut by June 2026 (CME FedWatch)
- Unemployment rate: 3.9%

**Current Status:** Fed funds rate unchanged since September 2025; no cuts announced

**Trend:** stable

**Outcome Implications:** This source suggests moderate probability (~65%) of a rate cut before July 2026, but Fed officials' cautious tone indicates it is not certain. The final decision likely depends on inflation data in Q1 2026.

---

*End of Planning Report*
