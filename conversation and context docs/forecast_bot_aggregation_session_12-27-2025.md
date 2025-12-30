# Forecast Bot Aggregation Session - December 27, 2025

## Conversation Summary
This session explored the Metaculus forecasting bot repository, specifically focusing on how forecast aggregation works in the forecasting-tools library.

---

## Full Conversation History

### User
```
login
```

### Assistant
I can see you've typed "login" but I need more context to help you effectively. Could you clarify what you'd like to do?

For example:
- Are you trying to implement a login feature in an application?
- Do you need help with SSH/system login?
- Are you looking to authenticate with a service or API?
- Do you want to log into a specific platform or tool?

Please provide more details about what you're trying to accomplish.

---

### User
```
Can you review a git repo and summarize it for me?
```

### Assistant
I'd be happy to review and summarize a git repository for you! However, I need a bit more information:

The current working directory (`/home/dre_ubuntu`) is not a git repository. Could you please:

1. **Provide the path** to the git repository on your system, or
2. **Share the git URL** if you'd like me to clone it first, or
3. Let me know if you need to **navigate to a different directory** where the repo exists

Also, what kind of summary would be most helpful?
- Overall purpose and functionality
- Technology stack and architecture
- File/directory structure
- Key features and components
- Recent activity and commits
- All of the above

Let me know and I'll get started!

---

### User
```
C:\Users\Donni\projects\metac_bot_Spring_2026
```

### Assistant
I'll review the git repository for you. Since you're on a Windows system and I'm running in WSL, I'll convert the path to `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026`.

Let me explore the repository and provide you with a comprehensive summary.

**[Explored repository using Task tool with Explore agent]**

---

## Comprehensive Exploration Report: Metac Bot Spring 2026

### 1. Overall Purpose and What the Project Does

This is a **Metaculus AI Forecasting Bot template** designed for the Metaculus AI Benchmark (AIB) tournament for Spring 2026. The bot automatically forecasts predictions on questions from the Metaculus forecasting platform, specifically for the AI Forecasting Tournament.

Key purposes:
- Provides a working template for building custom forecasting bots that participate in Metaculus's AI Benchmarking tournaments
- Automates the process of researching and forecasting on open questions
- Handles multiple types of predictions: binary (yes/no), multiple choice, numeric/continuous, and conditional questions
- Designed to run continuously via GitHub Actions automation every 20 minutes or on demand

The bot leverages AI/LLMs to conduct research and generate probabilistic forecasts on complex, time-sensitive forecasting questions related to AI and other topics.

---

### 2. Technology Stack and Frameworks Used

**Core Technologies:**
- **Python 3.11+** - Primary programming language
- **Poetry** - Python package/dependency manager (production-grade)
- **asyncio** - For asynchronous concurrent operations

**Key Dependencies:**
- **forecasting-tools** (v0.2.80) - Metaculus's framework providing:
  - `ForecastBot` - Base class for building bots
  - `MetaculusClient` - API client for Metaculus platform
  - Question types: `BinaryQuestion`, `MultipleChoiceQuestion`, `NumericQuestion`, `DateQuestion`, `ConditionalQuestion`
  - Search and research tools: `AskNewsSearcher`, `SmartSearcher`
  - LLM abstraction: `GeneralLlm`
  - Utility functions: `structure_output`, `clean_indents`

- **LLM/API Integration:**
  - **OpenAI** - GPT models (OpenAI API)
  - **OpenRouter** - Multi-provider LLM API (recommended for variety)
  - **AskNews SDK** - News research and deep research capabilities
  - **Perplexity API** - Alternative search and reasoning
  - **Exa API** - Web search capability

- **Utilities:**
  - `requests` - HTTP requests for API calls
  - `numpy` - Numerical computations
  - `python-decouple` & `python-dotenv` - Environment variable management
  - `pydantic` - Data validation and modeling

**CI/CD:**
- **GitHub Actions** - Workflow automation for scheduled bot runs
- **Ubuntu Latest** - Runtime environment

---

### 3. Directory and File Structure

```
/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/
├── .git/                                  # Git repository metadata
├── .github/
│   └── workflows/
│       ├── run_bot_on_tournament.yaml    # Main scheduled bot job (every 20 min)
│       ├── run_bot_on_metaculus_cup.yaml # Secondary tournament (every 2 days)
│       └── test_bot.yaml                 # Manual test workflow
├── metac-bot-template/                   # Nested template directory (v0)
│   ├── main.py
│   ├── main_with_no_framework.py
│   ├── community_benchmark.py
│   ├── .git/, .github/
│   ├── README.md
│   ├── pyproject.toml
│   └── poetry.lock
├── main.py                               # Primary bot implementation (726 lines)
├── main_with_no_framework.py             # Minimal dependency version (1547 lines)
├── README.md                             # Documentation (13.5 KB)
├── pyproject.toml                        # Poetry configuration
├── poetry.lock                           # Locked dependencies (489 KB)
├── .env.template                         # Environment variables template
├── .gitignore                            # Git exclusion rules
└── [Total: ~4,200 lines of Python code]
```

**Total Project Size:** ~1.4 MB for entire directory including nested template

---

### 4. Key Components and Features

#### A. **Main Bot Implementation (`main.py` - 726 lines)**

**Core Class:** `SpringTemplateBot2026` (extends `ForecastBot`)

**Research Phase:**
- `run_research()` - Conducts online research using:
  - AskNews with news summaries or deep-research capabilities
  - Smart Searcher (web search + LLM analysis)
  - Perplexity API (fallback)
  - Can run with no research mode

**Forecasting Functions by Question Type:**
1. **Binary Questions** (`_run_forecast_on_binary`)
   - Analyzes Yes/No outcomes
   - Considers status quo, scenarios for both outcomes
   - Outputs probability 0-100%

2. **Multiple Choice Questions** (`_run_forecast_on_multiple_choice`)
   - Predicts probabilities for N options
   - Considers status quo and unexpected outcomes
   - Handles option name parsing and normalization

3. **Numeric Questions** (`_run_forecast_on_numeric`)
   - Generates distribution estimates using percentiles (10, 20, 40, 60, 80, 90)
   - Respects unit conversions and bounds
   - Encourages humble, wide confidence intervals

4. **Date Questions** (`_run_forecast_on_date`)
   - Forecasts timing of events
   - Outputs dates in YYYY-MM-DD format
   - Respects chronological ordering

5. **Conditional Questions** (`_run_forecast_on_conditional`)
   - Handles complex multi-part questions
   - Forecasts parent, child, yes, and no components
   - Prevents re-forecasting of already-predicted parts

**Key Features:**
- **Concurrency Control:** Single concurrent question processing (`_max_concurrent_questions = 1`)
- **Rate Limiting:** Async semaphore for API rate limiting
- **Multi-Run Aggregation:** 5 predictions per research report, aggregates median
- **LLM-Based Parsing:** Uses `structure_output()` for intelligent extraction
- **Flexible LLM Configuration:** Can use any model via OpenRouter/LiteLLM
- **Validation Sampling:** Double-checks parsing with multiple LLM samples
- **Skip Already Forecasted:** Avoids re-forecasting same questions

#### B. **No-Framework Implementation (`main_with_no_framework.py` - 1547 lines)**

A self-contained version with minimal dependencies, showing:
- Raw API interactions with Metaculus
- Direct LLM calls to OpenAI
- Custom research implementations (Perplexity, Exa, AskNews)
- Manual parsing of predictions
- Useful for understanding internals or custom implementations

Key components:
- `list_posts_from_tournament()` - Fetches tournament questions
- `call_llm()` - Direct OpenAI API interaction with rate limiting
- `run_research()` - Handles multiple research providers
- `call_perplexity()`, `call_exa_smart_searcher()`, `call_asknews()` - Research methods
- `parse_binary_prediction()`, `parse_numeric_forecast()`, etc. - Custom parsers
- Direct submission to Metaculus API

#### C. **Benchmark Tool (`community_benchmark.py` - 132 lines)**

Evaluates bot performance:
- Compares bot forecasts against community predictions
- Runs on random question samples
- Tracks monetary costs of API calls
- Generates benchmark reports (Brier score, etc.)

---

### 5. Dependencies and Configuration

**Python Package Requirements:**
```
python = "^3.11"
forecasting-tools = "^0.2.80"
openai = "^2.0.0"
asknews = "^0.13.0"
requests = "^2.32.3"
numpy = "^2.3.0"
python-dotenv = "^1.0.1"
python-decouple = "^3.8"

[dev]
ipykernel = "^6.29.5"
```

**Environment Variables Required:**
```
METACULUS_TOKEN=<your_token>          # Required - bot account token
OPENROUTER_API_KEY=<key>              # Optional but recommended
PERPLEXITY_API_KEY=<key>              # Optional - alternative search
OPENAI_API_KEY=<key>                  # Optional - for models
EXA_API_KEY=<key>                     # Optional - for smart search
ASKNEWS_CLIENT_ID=<id>                # Optional - for news research
ASKNEWS_SECRET=<secret>               # Optional - for news research
ANTHROPIC_API_KEY=<key>               # Optional - for Claude models
```

**Configuration Parameters (in main.py):**
```python
research_reports_per_question = 1
predictions_per_research_report = 5
use_research_summary_to_forecast = False
publish_reports_to_metaculus = True
skip_previously_forecasted_questions = True
extra_metadata_in_explanation = True
```

---

### 6. Recent Git Activity

**Latest Commits (as of Dec 21, 2025):**

| Commit | Author | Date | Message |
|--------|--------|------|---------|
| 234f515 | Ben Wilson | Dec 17 | Update main_with_no_framework.py (#95) |
| 4ff8ab8 | Ben Wilson | Dec 17 | Update main_with_no_framework.py (#94) |
| aa2c111 | Ben Wilson | Dec 17 | Feat/spring no framework (#93) |
| f46e3dd | Ben Wilson | Dec 17 | New spring template bot for main.py (#91) |
| 9643174 | Ben Wilson | Aug 22 | Changed concurrency to 1 (#80) |

**Branches:**
- `bot-dev` (current) - Development branch
- `main` - Main production branch
- Multiple upstream branches from Metaculus official repo

**Remotes:**
- `origin` - User's fork: github.com/D-Enns/metac-bot-template
- `upstream` - Metaculus official: github.com/Metaculus/metac-bot-template

**Activity:** Active maintenance with Spring 2026 updates (mid-December 2025), focusing on no-framework implementation and bot improvements.

---

### 7. Documentation and README

**README.md Highlights:**

**Quick Start Options:**
1. **GitHub Actions (Easiest):**
   - Fork the repo
   - Set repository secrets (API keys)
   - Enable GitHub Actions workflow
   - Bot runs automatically every 20 minutes
   - Can be toggled on/off via Actions menu

2. **Local Development:**
   - Install Poetry package manager
   - Run `poetry install`
   - Create `.env` file from `.env.template`
   - Execute: `poetry run python main.py --mode test_questions`

**Run Modes:**
- `tournament` (default) - Forecasts on AI Benchmarking tournament + MiniBench
- `metaculus_cup` - Forecasts on regular Metaculus Cup questions
- `test_questions` - Tests on 4 example questions for debugging

**API Key Setup:**
- Instructions provided for obtaining tokens from:
  - Metaculus.com/aib - Bot account creation
  - OpenRouter.ai - Free credits available (form-based)
  - Perplexity, Exa, AskNews - Multiple search/research options

**Improvement Ideas:**
The README lists 14+ potential enhancements:
- Finetuned LLMs on Metaculus data
- Dataset explorers and analysis tools
- Question decomposer
- Meta-Forecast researcher aggregation
- Base rate researchers
- Key factor analysis
- Monte Carlo simulations
- Personality diversity (multiple experts/LLMs)
- Worldbuilding scenarios
- Consistency forecasting
- Extremization & calibration
- Evidence point systems
- Search provider benchmarking
- Timeline researchers

**Useful Resources:**
- 30-minute video tutorial (Loom)
- Detailed Discord community support
- Example code for AskNews /news and /deepnews endpoints
- Contact: ben@metaculus.com

---

### 8. GitHub Actions Automation

**Three Workflows:**

1. **run_bot_on_tournament.yaml** (Primary)
   - Trigger: Every 20 minutes via cron
   - Manual: Can trigger manually
   - Concurrency: Single concurrent run (prevents overlaps)
   - Runs: `poetry run python main.py` (tournament mode)
   - Runs on: Ubuntu Latest, Python 3.11
   - Installs dependencies via Poetry
   - Reads secrets for: METACULUS_TOKEN, OPENROUTER_API_KEY, OPENAI_API_KEY, PERPLEXITY_API_KEY, EXA_API_KEY, ASKNEWS keys, ANTHROPIC_API_KEY

2. **run_bot_on_metaculus_cup.yaml** (Secondary)
   - Trigger: Every 2 days at midnight via cron
   - Runs: `poetry run python main.py --mode metaculus_cup`
   - Same setup as primary workflow

3. **test_bot.yaml** (Testing)
   - Trigger: Manual only (workflow_dispatch)
   - Runs: `poetry run python main.py --mode test_questions`
   - Used for debugging with 4 example questions

---

### Summary

This is a **production-ready AI forecasting bot** that automates predictions on the Metaculus platform. It's:
- **Well-structured** with two implementation approaches (framework-based and minimal-dependency)
- **Actively maintained** by the Metaculus team and community
- **Flexible** supporting multiple LLM providers and research tools
- **Automated** via GitHub Actions for continuous forecasting
- **Documented** with tutorials and detailed README
- **Battle-tested** with known 1-2% bug rate from previous seasons
- **Designed for Spring 2026 AIB** with recent updates to date and conditional question support

The project demonstrates best practices in async Python, rate limiting, LLM integration, and production automation for AI systems.

---

### User
```
The code aggregates several forecasts from a selected LLM. It uses a public Git repo called something like "forecast tools". I want to know where the forecast aggregation happens, how it works, and a general idea of how I could make my own aggregation tool.
```

### Assistant
I'll investigate the forecast aggregation mechanism for you. Let me start by examining the main bot implementation and then trace how the aggregation works.

**[Read main.py file - 726 lines]**

**[Searched for forecasting-tools GitHub repository]**

**[Found repository at https://github.com/Metaculus/forecasting-tools]**

**[Explored repository structure and found:]**
- `forecasting_tools/forecast_bots/forecast_bot.py` - Base ForecastBot class
- `forecasting_tools/data_models/` - Contains report types with aggregation logic
  - `binary_report.py`
  - `numeric_report.py`
  - `multiple_choice_report.py`

**[Fetched aggregation implementations from each report type]**

---

## Where Forecast Aggregation Happens

The aggregation happens in two layers:

### 1. **ForecastBot Class** (`forecast_bot.py`)
The base `ForecastBot` class has an `_aggregate_predictions()` method that:
- Collects predictions from multiple runs (5 in your case from `predictions_per_research_report=5`)
- Delegates to the appropriate report type based on question type
- Calls `report_type.aggregate_predictions(predictions, question)`

### 2. **Report Type Classes** (in `data_models/`)
Each question type has its own aggregation implementation:
- **Binary**: `binary_report.py`
- **Numeric**: `numeric_report.py`
- **Multiple Choice**: `multiple_choice_report.py`

---

## How Aggregation Works

### **Binary Questions** (median)
```python
@classmethod
async def aggregate_predictions(
    cls, predictions: list[float], question: BinaryQuestion
) -> float:
    for prediction in predictions:
        assert 0 <= prediction <= 1, "Predictions must be between 0 and 1"
    return float(statistics.median(predictions))
```

**Example:** If you have 5 predictions `[0.65, 0.70, 0.68, 0.72, 0.69]`, the aggregated forecast is `0.69` (the median).

**Why median?** It's robust to outliers - if one LLM gives a wild prediction, it won't skew the result.

### **Numeric Questions** (median of CDFs)
More sophisticated - it:
1. **Converts each prediction to a full CDF** (Cumulative Distribution Function) with 201 points
2. **Aligns all CDFs** to the same x-axis values
3. **Calculates median** across all percentile heights at each point:
   ```python
   np.median(np.array(all_percentiles_of_cdf), axis=0)
   ```
4. **Reconstructs the distribution** from the median CDF

**Example:** If you have 5 distributions each with percentiles (10th, 20th, 40th, 60th, 80th, 90th), it takes the median value at each percentile point.

### **Multiple Choice Questions** (mean)
```python
# For each option:
average_probability = sum(probabilities_of_current_option) / len(probabilities_of_current_option)
```

Takes the **arithmetic mean** of probabilities for each option across all predictions, then normalizes to ensure they sum to 1.0.

**Example:**
- Prediction 1: `{A: 0.6, B: 0.3, C: 0.1}`
- Prediction 2: `{A: 0.5, B: 0.4, C: 0.1}`
- Aggregated: `{A: 0.55, B: 0.35, C: 0.1}`

---

## How to Make Your Own Aggregation Tool

Here's a framework for building a custom aggregation system:

### **Option 1: Modify the existing framework**

Create your own report class that overrides `aggregate_predictions()`:

```python
from forecasting_tools.data_models.binary_report import BinaryReport
import statistics

class CustomBinaryReport(BinaryReport):
    @classmethod
    async def aggregate_predictions(
        cls, predictions: list[float], question: BinaryQuestion
    ) -> float:
        # Your custom logic here
        # Examples:

        # 1. Use mean instead of median
        return statistics.mean(predictions)

        # 2. Weighted average (give more weight to extreme predictions)
        weights = [abs(p - 0.5) for p in predictions]  # Higher weight for confident predictions
        if sum(weights) == 0:
            return statistics.mean(predictions)
        weighted_sum = sum(p * w for p, w in zip(predictions, weights))
        return weighted_sum / sum(weights)

        # 3. Trimmed mean (remove outliers)
        sorted_preds = sorted(predictions)
        trimmed = sorted_preds[1:-1]  # Remove highest and lowest
        return statistics.mean(trimmed) if trimmed else statistics.mean(predictions)

        # 4. Bayesian aggregation
        # Prior belief + evidence combination
        prior = 0.5
        posterior = prior
        for pred in predictions:
            # Simple Bayesian update (you'd want a more sophisticated version)
            likelihood_ratio = pred / (1 - pred) if pred < 1 else 10
            prior_odds = posterior / (1 - posterior)
            posterior_odds = prior_odds * likelihood_ratio
            posterior = posterior_odds / (1 + posterior_odds)
        return posterior
```

### **Option 2: Standalone aggregation tool**

Build an independent aggregator that doesn't depend on the framework:

```python
import statistics
import numpy as np
from typing import List, Dict

class CustomForecastAggregator:
    """Standalone aggregation tool for multiple forecasts"""

    @staticmethod
    def aggregate_binary(predictions: List[float], method: str = "median") -> float:
        """
        Aggregate binary predictions (0-1 probabilities)

        Args:
            predictions: List of probability values
            method: 'median', 'mean', 'trimmed_mean', 'geometric_mean'
        """
        if method == "median":
            return statistics.median(predictions)

        elif method == "mean":
            return statistics.mean(predictions)

        elif method == "trimmed_mean":
            # Remove top and bottom 10%
            n = len(predictions)
            trim = int(n * 0.1)
            sorted_preds = sorted(predictions)
            trimmed = sorted_preds[trim:-trim] if trim > 0 else sorted_preds
            return statistics.mean(trimmed)

        elif method == "geometric_mean":
            # Convert to log-odds, average, convert back
            log_odds = [np.log(p / (1 - p)) for p in predictions if 0 < p < 1]
            avg_log_odds = np.mean(log_odds)
            return 1 / (1 + np.exp(-avg_log_odds))

        else:
            raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def aggregate_multiple_choice(
        predictions: List[Dict[str, float]],
        method: str = "mean"
    ) -> Dict[str, float]:
        """
        Aggregate multiple choice predictions

        Args:
            predictions: List of dictionaries {option_name: probability}
            method: 'mean', 'median', 'product' (multiplicative)
        """
        # Get all option names
        options = list(predictions[0].keys())

        result = {}
        for option in options:
            probs = [pred[option] for pred in predictions]

            if method == "mean":
                result[option] = np.mean(probs)
            elif method == "median":
                result[option] = np.median(probs)
            elif method == "product":
                # Multiplicative aggregation (good for independent forecasters)
                result[option] = np.prod(probs) ** (1/len(probs))

        # Normalize to sum to 1
        total = sum(result.values())
        return {k: v/total for k, v in result.items()}

    @staticmethod
    def aggregate_numeric_distributions(
        predictions: List[Dict[int, float]],  # {percentile: value}
        method: str = "median"
    ) -> Dict[int, float]:
        """
        Aggregate numeric distributions represented as percentiles

        Args:
            predictions: List of {percentile: value} dictionaries
            method: 'median', 'mean'
        """
        percentiles = sorted(predictions[0].keys())
        result = {}

        for pct in percentiles:
            values = [pred[pct] for pred in predictions]

            if method == "median":
                result[pct] = np.median(values)
            elif method == "mean":
                result[pct] = np.mean(values)

        return result

# Usage example:
if __name__ == "__main__":
    aggregator = CustomForecastAggregator()

    # Binary example
    binary_preds = [0.65, 0.70, 0.68, 0.72, 0.69]
    print(f"Binary (median): {aggregator.aggregate_binary(binary_preds, 'median')}")
    print(f"Binary (mean): {aggregator.aggregate_binary(binary_preds, 'mean')}")

    # Multiple choice example
    mc_preds = [
        {"A": 0.6, "B": 0.3, "C": 0.1},
        {"A": 0.5, "B": 0.4, "C": 0.1},
        {"A": 0.55, "B": 0.35, "C": 0.1},
    ]
    print(f"Multiple choice: {aggregator.aggregate_multiple_choice(mc_preds)}")

    # Numeric distribution example
    numeric_preds = [
        {10: 100, 50: 150, 90: 200},
        {10: 110, 50: 155, 90: 210},
        {10: 105, 50: 152, 90: 205},
    ]
    print(f"Numeric: {aggregator.aggregate_numeric_distributions(numeric_preds)}")
```

### **Key Considerations for Your Own Tool:**

1. **Robustness**: Use median for resistance to outliers
2. **Independence**: If forecasts are independent, multiplicative aggregation can work well
3. **Calibration**: Track performance and adjust (e.g., extremize predictions by pushing them away from 50%)
4. **Weighting**: Give more weight to better-performing models/forecasters
5. **Diversity**: Aggregate predictions from different model types for better coverage

---

## Sources:
- [Metaculus forecasting-tools GitHub Repository](https://github.com/Metaculus/forecasting-tools)
- [Binary Report Implementation](https://github.com/Metaculus/forecasting-tools/blob/main/forecasting_tools/data_models/binary_report.py)
- [Numeric Report Implementation](https://github.com/Metaculus/forecasting-tools/blob/main/forecasting_tools/data_models/numeric_report.py)
- [Multiple Choice Report Implementation](https://github.com/Metaculus/forecasting-tools/blob/main/forecasting_tools/data_models/multiple_choice_report.py)

---

### User
```
Write the entire conversation history into a new file named forecast_bot_aggregation_session_12-27-2025.md and make it downloadable
```

---

## End of Conversation

**Session Date:** December 27, 2025
**Working Directory:** `/home/dre_ubuntu`
**Repository Analyzed:** `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026`
**Key Topic:** Forecast aggregation in Metaculus forecasting-tools library

---

## Key Findings Summary

1. **Aggregation Location**:
   - Base class: `ForecastBot._aggregate_predictions()` in `forecast_bot.py`
   - Implementation: Delegated to report types in `data_models/` directory

2. **Aggregation Methods by Question Type**:
   - Binary: Median of probabilities
   - Numeric: Median of CDFs (201-point distributions)
   - Multiple Choice: Mean of probabilities per option (normalized)

3. **Configuration**:
   - `predictions_per_research_report = 5` (generates 5 predictions)
   - `research_reports_per_question = 1` (1 research cycle per question)
   - Total predictions per question: 5 × 1 = 5

4. **Custom Aggregation Options**:
   - Override report class methods
   - Build standalone aggregation tool
   - Alternative methods: trimmed mean, weighted average, Bayesian updates, geometric mean

---

## Technical Details

**Main Repository:**
- GitHub: https://github.com/Metaculus/forecasting-tools
- Version: 0.2.80
- Language: Python 3.11+
- Framework: Poetry

**Key Files Analyzed:**
- `/mnt/c/Users/Donni/projects/metac_bot_Spring_2026/main.py` (726 lines)
- `forecasting_tools/forecast_bots/forecast_bot.py`
- `forecasting_tools/data_models/binary_report.py`
- `forecasting_tools/data_models/numeric_report.py`
- `forecasting_tools/data_models/multiple_choice_report.py`

---

*This document was generated by Claude Code on December 27, 2025*
