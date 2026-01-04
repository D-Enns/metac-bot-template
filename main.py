import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Any

# GPR aggregation imports
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C
from pydantic import BaseModel, Field


from forecasting_tools import (
    AskNewsSearcher,
    BinaryQuestion,
    ForecastBot,
    GeneralLlm,
    MetaculusClient,
    MetaculusQuestion,
    MultipleChoiceQuestion,
    NumericDistribution,
    NumericQuestion,
    DateQuestion,
    DatePercentile,
    Percentile,
    ConditionalQuestion,
    ConditionalPrediction,
    PredictionTypes,
    PredictionAffirmed,
    BinaryPrediction,
    PredictedOptionList,
    ReasonedPrediction,
    SmartSearcher,
    clean_indents,
    structure_output,
)
from forecasting_tools.data_models.forecast_report import ResearchWithPredictions

logger = logging.getLogger(__name__)


# Data model for multi-scenario predictions (flexible count)
class MultiScenarioPrediction(BaseModel):
    """Multiple scenario forecasts of arbitrary count from a single prompt"""
    scenarios: list[float] = Field(
        ...,
        description="List of forecast probabilities from low to high (0-100)",
        min_length=1
    )


# Data model for multiple choice scenario predictions (3x3 matrix = 9 distributions)
class MultipleChoiceScenarios(BaseModel):
    """Nine probability distributions from 3x3 world matrix approach.
    Each distribution is a list of probabilities (one per option) that sum to 100."""
    scenarios: list[list[float]] = Field(
        ...,
        description="List of 9 probability distributions. Each inner list contains probabilities (0-100) for all options in order. Each distribution must sum to 100.",
        min_length=9,
        max_length=9
    )


class SpringTemplateBot2026(ForecastBot):
    """
    This is the template bot for Spring 2026 Metaculus AI Tournament.
    This is a copy of what is used by Metaculus to run the Metac Bots in our benchmark, provided as a template for new bot makers.
    This template is given as-is, and is use-at-your-own-risk.
    We have covered most test cases in forecasting-tools it may be worth double checking key components locally.
    So far our track record has been 1 mentionable bug per season (affecting forecasts for 1-2% of total questions)

    Main changes since Fall:
    - Additional prompting has been added to numeric questions to emphasize putting pecentile values in the correct order.
    - Support for conditional and date questions has been added
    - Note: Spring AIB will not use date/conditional questions, so these are only for forecasting on the main site as you wish.

    The main entry point of this bot is `bot.forecast_on_tournament(tournament_id)` in the parent class.
    See the script at the bottom of the file for more details on how to run the bot.
    Ignoring the finer details, the general flow is:
    - Load questions from Metaculus
    - For each question
        - Execute run_research a number of times equal to research_reports_per_question
        - Execute respective run_forecast function `predictions_per_research_report * research_reports_per_question` times
        - Aggregate the predictions
        - Submit prediction (if publish_reports_to_metaculus is True)
    - Return a list of ForecastReport objects

    Alternatively, you can use the MetaculusClient to make a custom filter of questions to forecast on
    and forecast them with `bot.forecast_questions(questions)`

    Only the research and forecast functions need to be implemented in ForecastBot subclasses,
    though you may want to override other ForecastBot functions.
    In this example, you can change the prompts to be whatever you want since,
    structure_output uses an LLM to intelligently reformat the output into the needed structure.

    By default (i.e. 'tournament' mode), when you run this script, it will forecast on any open questions in the
    primary bot tournament and MiniBench. If you want to forecast on only one or the other, you can remove one
    of them from the 'tournament' mode code at the bottom of the file.

    You can experiment with what models work best with your bot by using the `llms` parameter when initializing the bot.
    You can initialize the bot with any number of models. For example,
    ```python
    my_bot = MyBot(
        ...
        llms={  # choose your model names or GeneralLlm llms here, otherwise defaults will be chosen for you
            "default": GeneralLlm(
                model="openrouter/openai/gpt-4o", # "anthropic/claude-sonnet-4-20250514", etc (see docs for litellm)
                temperature=0.3,
                timeout=40,
                allowed_tries=2,
            ),
            "summarizer": "openai/gpt-4o-mini",
            "researcher": "asknews/news-summaries",
            "parser": "openai/gpt-4o-mini",
        },
    )
    ```

    Then you can access the model in custom functions like this:
    ```python
    research_strategy = self.get_llm("researcher", "model_name"
    if research_strategy == "asknews/news-summaries":
        ...
    # OR
    summarizer = await self.get_llm("summarizer", "llm").invoke(prompt)
    # OR
    reasoning = await self.get_llm("default", "llm").invoke(prompt)
    ```

    If you end up having trouble with rate limits and want to try a more sophisticated rate limiter try:
    ```python
    from forecasting_tools import RefreshingBucketRateLimiter
    rate_limiter = RefreshingBucketRateLimiter(
        capacity=2,
        refresh_rate=1,
    ) # Allows 1 request per second on average with a burst of 2 requests initially. Set this as a class variable
    await self.rate_limiter.wait_till_able_to_acquire_resources(1) # 1 because it's consuming 1 request (use more if you are adding a token limit)
    ```
    Additionally OpenRouter has large rate limits immediately on account creation
    """

    _max_concurrent_questions = (
        1  # Set this to whatever works for your search-provider/ai-model rate limits
    )
    _concurrency_limiter = asyncio.Semaphore(_max_concurrent_questions)
    _structure_output_validation_samples = 2

    def __init__(self, *args, **kwargs):
        """Initialize bot with storage for multi-scenario predictions"""
        super().__init__(*args, **kwargs)
        self._binary_scenarios = []  # Storage for low/mid/high scenarios
        self._numeric_scenarios = []  # Storage for numeric outcome scenarios
        self._multiple_choice_scenarios = {}  # Storage for MC scenarios, dict of lists keyed by option name
        self._current_question_id = None  # Track question to know when to clear storage
        self._current_call_number = 0  # Track which LLM call we're on for current question

    ##################################### RESEARCH #####################################

    async def run_research(self, question: MetaculusQuestion) -> str:
        async with self._concurrency_limiter:
            research = ""
            researcher = self.get_llm("researcher")

            prompt = clean_indents(
                f"""
                You are an assistant to a superforecaster.
                The superforecaster will give you a question they intend to forecast on.
                To be a great assistant, you generate a concise but detailed rundown of the most relevant news, including if the question would resolve Yes or No based on current information.
                You do not produce forecasts yourself.

                Question:
                {question.question_text}

                This question's outcome will be determined by the specific criteria below:
                {question.resolution_criteria}

                {question.fine_print}
                """
            )

            if isinstance(researcher, GeneralLlm):
                research = await researcher.invoke(prompt)
            elif (
                researcher == "asknews/news-summaries"
                or researcher == "asknews/deep-research/low-depth"
                or researcher == "asknews/deep-research/medium-depth"
                or researcher == "asknews/deep-research/high-depth"
            ):
                research = await AskNewsSearcher().call_preconfigured_version(
                    researcher, prompt
                )
            elif researcher.startswith("smart-searcher"):
                model_name = researcher.removeprefix("smart-searcher/")
                searcher = SmartSearcher(
                    model=model_name,
                    temperature=0,
                    num_searches_to_run=2,
                    num_sites_per_search=10,
                    use_advanced_filters=False,
                )
                research = await searcher.invoke(prompt)
            elif not researcher or researcher == "None" or researcher == "no_research":
                research = ""
            else:
                research = await self.get_llm("researcher", "llm").invoke(prompt)
            logger.info(f"Found Research for URL {question.page_url}:\n{research}")
            return research

    ##################################### BINARY QUESTIONS #####################################

    async def _run_forecast_on_binary(
        self, question: BinaryQuestion, research: str
    ) -> ReasonedPrediction[float]:
        # Track which call number this is for the current question
        if self._current_question_id != question.page_url:
            self._current_call_number = 0
            logger.info(f"[GPR DEBUG] New question detected. Resetting counter. ID was: {self._current_question_id}, now: {question.page_url}")
        self._current_call_number = getattr(self, '_current_call_number', 0) + 1
        logger.info(f"[GPR DEBUG] Call number: {self._current_call_number}, Scenarios so far: {len(self._binary_scenarios)}, Question: {question.page_url}")

        # DRE 01-01-2026 Binary for Spring2026
        prompt = clean_indents(
            f"""
            # Make a Professional Forecast
            
            ## You are a professional forecaster interviewing for a job.

            ## Your interview question is:
            {question.question_text}

            ## Question background:
            {question.background_info}

            ## This question's outcome will be determined by the specific criteria below. These criteria have not yet 
            been satisfied:
            {question.resolution_criteria}

            {question.fine_print}

            ## Your research assistant says:
            {research}

            ## Today is {datetime.now().strftime("%Y-%m-%d")}.

            ## Your workflow

            ### Strategy
            Your general strategy is to consider multiple scenarios: given a subset of the evidence,
            what are low (most pessimistic given the selected evidence), mid (your baseline given the selected evidence), 
            and high (optimistic given the selected evidence) forecasts.
            
            ### Precision
            You do not preferentially choose forecast probabilities of 5%, 10%, 15%, 20% etc. Instead you make your best forecast, 
            allowing values such as 12%, 17%, 34%, 48%, 71%... Especially when forecasts are in the less than 10% and more than 90%, 
            allow for decimal forecasts (e.g. 2.3% or 95.7%), but you avoid forecasts below 1% or above 99%.
            
            ### Before answering you write:
            1. The time left until the outcome to the question is known.
            2. The status quo outcome if nothing changed.
            3. The expectations of experts and markets.
            4. A brief description of a scenario that results in a No outcome.
            5. A brief description of a scenario that results in a Yes outcome.
            
            ### You write your rationale remembering that good forecasters put extra weight on the status quo outcome 
            since the world changes slowly most of the time.

            ### Group the evidence
            Review the evidence from your research assistant and group it into three buckets of approximately the same size:
            - Bucket 1. Evidence that would indicate a relatively low forecast
            - Bucket 2. Evidence that would indicate a relatively central or baseline forecast
            - Bucket 3. Evidence that would indicate a high forecast
            
            ### Multi-world considerations
            You explore ranges of reasonable, possible forecasts.
            You consider three worlds, one world based on each bucket of evidence:
            1. Low_World: review the bucket 1 evidence from your research assistant that the forecast could be low, summarize.
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?

            2. Mid_World: review the bucket 2 evidence from your research assistant that the forecast could be around 
               the central views and trends, summarize.
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            
            3. High_World: review the bucket 3 evidence from your research assistant that the forecast could be high, summarize.
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?

            # Final Answer
            The last thing you write is your final answer as a list of values for the world scenarios. Written as a list: 
            
            [Low_World-Low, Low_World-Mid, Low_World-High, Mid_World-Low, Mid_World-Mid, Mid_World-High, High_World-Low,
            High_World-Mid, High_World-High]
            
            IMPORTANT: Write only the numbers without percent signs inside the brackets.
            """
        )

        result = await self._binary_prompt_to_forecast(question, prompt)

        # Don't aggregate here - let the framework call _aggregate_predictions instead
        # This avoids race conditions with async calls
        logger.info(f"[GPR DEBUG] Returning mid value. Scenarios stored: {len(self._binary_scenarios)}")
        return result

    async def _binary_prompt_to_forecast(
        self,
        question: BinaryQuestion,
        prompt: str,
    ) -> ReasonedPrediction[float]:
        # Clear storage if this is a new question
        logger.info(f"[GPR DEBUG] In _binary_prompt_to_forecast. Current ID: {self._current_question_id}, Question URL: {question.page_url}, Match: {self._current_question_id == question.page_url}")
        if self._current_question_id != question.page_url:
            self._binary_scenarios = []
            self._current_question_id = question.page_url
            logger.info(f"Starting new question {question.page_url}, cleared scenario storage")

        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        logger.info(f"Reasoning for URL {question.page_url}: {reasoning}")

        # Parse variable number of scenarios from prompt
        scenario_prediction: MultiScenarioPrediction = await structure_output(
            reasoning,
            MultiScenarioPrediction,
            model=self.get_llm("parser", "llm"),
            num_validation_samples=self._structure_output_validation_samples,
        )

        # Auto-correct decimal/percentage confusion: if all values < 1.0, LLM likely returned decimals
        if scenario_prediction.scenarios and max(scenario_prediction.scenarios) < 1.0:
            logger.warning(
                f"[DECIMAL DETECTED] Binary scenarios all < 1.0: {scenario_prediction.scenarios}. "
                f"LLM likely returned decimals (0-1) instead of percentages (0-100). Auto-correcting by ×100."
            )
            scenario_prediction.scenarios = [s * 100 for s in scenario_prediction.scenarios]
            logger.info(f"[RESCALED] Binary scenarios after correction: {scenario_prediction.scenarios}")

        # Convert all scenarios from 0-100 to 0-1 scale and clamp
        scenarios_decimal = [
            max(0.01, min(0.99, s / 100)) for s in scenario_prediction.scenarios
        ]

        # Store all scenarios
        self._binary_scenarios.extend(scenarios_decimal)

        # Warn if unusually few scenarios (likely LLM didn't follow prompt)
        if len(scenario_prediction.scenarios) < 2:
            logger.warning(
                f"Only {len(scenario_prediction.scenarios)} scenario(s) returned - check prompt clarity"
            )

        logger.info(
            f"Parsed {len(scenario_prediction.scenarios)} scenarios: {scenario_prediction.scenarios}"
        )
        logger.info(
            f"Total scenarios stored for question {question.page_url}: {len(self._binary_scenarios)} scenarios"
        )

        # Return median value to framework (framework will collect all predictions)
        median_decimal = float(np.median(scenarios_decimal))
        logger.info(
            f"Returning median forecast for URL {question.page_url}: {median_decimal:.4f}"
        )
        return ReasonedPrediction(prediction_value=median_decimal, reasoning=reasoning)

    def _gpr_aggregate_binary(self, scenarios: list[float]) -> float:
        """
        Aggregate multiple scenario forecasts using Gaussian Process Regression.

        Args:
            scenarios: List of forecast values in decimal (0-1 scale)

        Returns:
            Smoothed p50 forecast value (0-1 scale)
        """
        if len(scenarios) < 3:
            logger.warning(f"Too few scenarios ({len(scenarios)}), using median fallback")
            return float(np.median(scenarios))

        # Convert to percentage scale for GPR (0-100)
        scenarios_pct = [s * 100 for s in scenarios]

        # Sort scenarios
        sorted_data = sorted(scenarios_pct)

        # Create empirical CDF percentiles
        percentiles = self._make_percentiles(sorted_data)

        # Fit GPR model
        gpr_model = self._make_gpr_model(sorted_data, percentiles)

        # Extract p50 from the smooth curve
        p50_pct = gpr_model.predict(np.array([[50]]))[0]

        # Convert back to decimal and clamp
        p50_decimal = max(0.01, min(0.99, p50_pct / 100))

        logger.info(f"GPR aggregation: {len(scenarios)} scenarios → p50 = {p50_decimal:.4f}")

        return float(p50_decimal)

    def _gpr_aggregate_multiple_choice(
        self,
        scenarios_by_option: dict[str, list[float]]
    ) -> dict[str, float]:
        """
        Aggregate multiple choice scenarios using GPR per option, then normalize.

        Args:
            scenarios_by_option: Dict mapping option names to lists of probabilities (0-100 scale)

        Returns:
            Dict mapping option names to aggregated probabilities (0-1 scale, summing to 1.0)

        Example:
            Input:  {"A": [60, 65, 55, ...], "B": [30, 25, 28, ...], "C": [10, 10, 17, ...]}
            Output: {"A": 0.58, "B": 0.27, "C": 0.15}  # Sums to 1.0
        """
        if not scenarios_by_option:
            logger.warning("No scenarios provided for MC GPR aggregation")
            return {}

        # Get number of scenarios (assume all options have same count)
        first_option = list(scenarios_by_option.keys())[0]
        num_scenarios = len(scenarios_by_option[first_option])

        logger.info(
            f"[GPR DEBUG] MC GPR aggregation: {len(scenarios_by_option)} options × "
            f"{num_scenarios} scenarios each"
        )

        # Run GPR independently for each option
        gpr_results = {}
        for option_name, option_scenarios in scenarios_by_option.items():
            if len(option_scenarios) >= 9:
                # Convert to 0-1 scale for GPR
                scenarios_decimal = [s / 100 for s in option_scenarios]

                # Reuse binary GPR logic
                gpr_p50 = self._gpr_aggregate_binary(scenarios_decimal)

                # Convert back to 0-100 for normalization
                gpr_results[option_name] = gpr_p50 * 100

                logger.info(f"[GPR DEBUG] Option '{option_name}': GPR p50 = {gpr_p50*100:.2f}%")
            else:
                # Fallback to median for insufficient scenarios
                median_val = float(np.median(option_scenarios))
                gpr_results[option_name] = median_val
                logger.warning(
                    f"Option '{option_name}' has only {len(option_scenarios)} scenarios "
                    f"(need >=9 for GPR), using median: {median_val:.2f}%"
                )

        # Normalize to sum to 100
        total = sum(gpr_results.values())
        if total > 0:
            normalized = {opt: (val / total) for opt, val in gpr_results.items()}
        else:
            # Equal probability fallback
            normalized = {opt: 1.0 / len(gpr_results) for opt in gpr_results.keys()}

        logger.info(
            f"[GPR DEBUG] MC GPR final (normalized): "
            f"{', '.join(f'{opt}={prob*100:.1f}%' for opt, prob in normalized.items())}"
        )

        return normalized  # Returns 0-1 scale, summing to 1.0

    def _make_percentiles(self, sorted_data: list[float]) -> list[float]:
        """Create empirical CDF percentiles for sorted data"""
        percentiles = [100 * i / (1 + len(sorted_data)) for i in range(len(sorted_data))]
        return percentiles

    def _make_gpr_model(self, sorted_data: list[float], percentiles: list[float]):
        """
        Fit Gaussian Process Regression model to smooth through blocky forecast data.

        Uses inverted CDF approach: percentile (X) → forecast value (y)
        This allows direct querying of "what's the forecast at p50?"
        """
        X = np.array(percentiles).reshape(-1, 1)
        y = np.array(sorted_data)

        # Define kernel: smooth RBF + white noise for blockiness
        smooth_kernel = C(1.0, (1e-3, 1e5)) * RBF(20.0, (1e-2, 1e2))
        kernel = smooth_kernel + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))

        # Fit model with multiple restarts for better optimization
        gpr_model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
        gpr_model.fit(X, y)

        return gpr_model

    def _transpose_mc_scenarios(
        self,
        scenarios: list[list[float]],
        option_names: list[str]
    ) -> dict[str, list[float]]:
        """
        Convert list of distributions to per-option lists for aggregation.

        Args:
            scenarios: List of 9 distributions, each a list of probabilities (0-100)
            option_names: List of option names in order

        Returns:
            Dict mapping option names to lists of probabilities

        Example:
            Input:  [[60, 30, 10], [65, 25, 10], ...]
            Output: {"Opt A": [60, 65, ...], "Opt B": [30, 25, ...], "Opt C": [10, 10, ...]}
        """
        by_option = {name: [] for name in option_names}

        for i, distribution in enumerate(scenarios):
            if len(distribution) != len(option_names):
                logger.warning(
                    f"Scenario {i+1} has {len(distribution)} values but expected {len(option_names)} "
                    f"(options: {option_names}). Skipping this scenario."
                )
                continue

            for j, option_name in enumerate(option_names):
                by_option[option_name].append(distribution[j])

        logger.info(
            f"Transposed {len(scenarios)} distributions into per-option lists. "
            f"Each option now has {len(by_option[option_names[0]])} scenarios."
        )

        return by_option

    ##################################### AGGREGATION OVERRIDE #####################################
    # GPR aggregation moved to dre_forecasting_tools.py

    ##################################### MULTIPLE CHOICE QUESTIONS #####################################

    async def _run_forecast_on_multiple_choice(
        self, question: MultipleChoiceQuestion, research: str
    ) -> ReasonedPrediction[PredictedOptionList]:
        prompt = clean_indents(
            f"""
            # Make a Professional Forecast
  
            ## You are a professional forecaster interviewing for a job.
          
            ## Your interview question is:
            {question.question_text}
          
            ## The options are:
            {question.options}
          
            ## Question background:
            {question.background_info}
          
            ## This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
            {question.resolution_criteria}
          
            {question.fine_print}
          
            ## Your research assistant says:
            {research}
          
            ## Today is {datetime.now().strftime("%Y-%m-%d")}.
          
            ## Your workflow
          
            ### Strategy
            Your general strategy is to consider multiple scenarios across different interpretations of the evidence.
            For each interpretation, you will provide probability distributions under different
            conditions (trendline, baseline, chaos).
          
            ### Precision
            You do not preferentially choose round probabilities like 10%, 20%, 30%, etc. Instead you make your best forecast,
            allowing values such as 12%, 17%, 34%, 48%, 71%...  Avoid forecasts below 1% or above 99%. You ensure that 
            probabilities for all options sum to exactly 100% for each distribution you provide.
          
            ### Before answering you write:
            1. The time left until the outcome to the question is known.
            2. The status quo outcome - which option is most likely if nothing changed.
            3. The expectations of experts and markets about which options are favored.
            4. The outcome if the current trends continued.
            5. A brief description of a scenario that results in the status quo option.
            6. A brief description of a scenario that results in an unexpected or alternative option.
          
            ### You write your rationale remembering that:
            - Good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.
            - Good forecasters leave moderate probability on multiple options to account for unexpected outcomes.
          
            ### Group the evidence
            Review the evidence from your research assistant and group it into three buckets of approximately the same size:
            - Bucket 1. Evidence supporting the status quo or most expected outcome
            - Bucket 2. Evidence suggesting balanced uncertainty or multiple plausible outcomes
            - Bucket 3. Evidence favoring unexpected, alternative, or less conventional outcomes
          
            ### Multi-world considerations
            You explore ranges of reasonable probability distributions.
            You consider three worlds, one world based on each bucket of evidence:
          
            1. StatusQuo_World: review the bucket 1 evidence from your research assistant that
               supports the most expected outcome, summarize.
               - Trendline: probability distribution if trends present in this world continue
               - Baseline: probability distribution most supported by evidence in this world
               - Chaos: probability distribution given chaotic conditions that could occur in this world

            2. Balanced_World: review the bucket 2 evidence from your research assistant suggesting
               uncertainty across multiple outcomes, summarize.
               - Trendline: probability distribution if trends present in this world continue
               - Baseline: probability distribution most supported by evidence in this world
               - Chaos: probability distribution given chaotic conditions that could occur in this world

            3. Unexpected_World: review the bucket 3 evidence from your research assistant favoring
                less conventional outcomes, summarize.
               - Trendline: probability distribution if trends present in this world continue
               - Baseline: probability distribution most supported by evidence in this world
               - Chaos: probability distribution given chaotic conditions that could occur in this world
          
            # Final Answer
            The last thing you write is your final answer as 9 probability distributions for the world scenarios.
            Each distribution assigns a probability to every option in {question.options}, and all probabilities in each
            distribution must sum to exactly 100.

            Write them in order as a list of 9 lists:
            [[StatusQuo_World-Trendline], [StatusQuo_World-Baseline], [StatusQuo_World-Chaos],
            [Balanced_World-Trendline], [Balanced_World-Baseline], [Balanced_World-Chaos],
            [Unexpected_World-Trendline], [Unexpected_World-Baseline], [Unexpected_World-Chaos]]

            Each inner list contains probabilities for the options in this exact order: {question.options}

            IMPORTANT:
            - Write probabilities as numbers without percent signs
            - Each inner list must have exactly {len(question.options)} values
            - Each inner list must sum to exactly 100
            """
        )
        return await self._multiple_choice_prompt_to_forecast(question, prompt)

    async def _multiple_choice_prompt_to_forecast(
        self,
        question: MultipleChoiceQuestion,
        prompt: str,
    ) -> ReasonedPrediction[PredictedOptionList]:
        # Clear storage if this is a new question
        logger.info(f"[GPR DEBUG] In _multiple_choice_prompt_to_forecast. Current ID: {self._current_question_id}, Question URL: {question.page_url}, Match: {self._current_question_id == question.page_url}")
        if self._current_question_id != question.page_url:
            self._multiple_choice_scenarios = {}
            self._current_question_id = question.page_url
            logger.info(f"Starting new MC question {question.page_url}, cleared scenario storage")

        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        logger.info(f"Reasoning for URL {question.page_url}: {reasoning}")

        # Parse 9 probability distributions from prompt
        mc_scenario_prediction: MultipleChoiceScenarios = await structure_output(
            reasoning,
            MultipleChoiceScenarios,
            model=self.get_llm("parser", "llm"),
            num_validation_samples=self._structure_output_validation_samples,
        )

        # Auto-correct decimal/percentage confusion: if all values in all distributions < 1.0
        all_values = [val for dist in mc_scenario_prediction.scenarios for val in dist]
        if all_values and max(all_values) < 1.0:
            logger.warning(
                f"[DECIMAL DETECTED] MC distributions all have values < 1.0. "
                f"LLM likely returned decimals (0-1) instead of percentages (0-100). Auto-correcting by ×100."
            )
            mc_scenario_prediction.scenarios = [
                [val * 100 for val in dist] for dist in mc_scenario_prediction.scenarios
            ]
            logger.info(
                f"[RESCALED] MC distributions after correction. "
                f"Example first distribution: {mc_scenario_prediction.scenarios[0]}"
            )

        logger.info(
            f"Parsed {len(mc_scenario_prediction.scenarios)} distributions for MC question"
        )

        # Convert list of distributions to per-option lists
        scenarios_by_option = self._transpose_mc_scenarios(
            mc_scenario_prediction.scenarios,
            question.options
        )

        # Store scenarios (extend existing lists or create new ones)
        for option_name, probabilities in scenarios_by_option.items():
            if option_name not in self._multiple_choice_scenarios:
                self._multiple_choice_scenarios[option_name] = []
            self._multiple_choice_scenarios[option_name].extend(probabilities)

        logger.info(
            f"Total scenarios stored for MC question {question.page_url}: "
            f"{len(self._multiple_choice_scenarios.get(question.options[0], []))} scenarios per option"
        )

        # Return median value to framework (framework will collect all predictions)
        # Calculate median per option, then normalize
        median_probs = {}
        for option_name in question.options:
            if option_name in self._multiple_choice_scenarios:
                median_probs[option_name] = float(np.median(self._multiple_choice_scenarios[option_name]))
            else:
                median_probs[option_name] = 0.0

        # Normalize to sum to 100
        total = sum(median_probs.values())
        if total > 0:
            normalized_probs = {opt: (prob / total) * 100 for opt, prob in median_probs.items()}
        else:
            # Equal probability fallback
            normalized_probs = {opt: 100.0 / len(question.options) for opt in question.options}

        # Convert to 0-1 scale for PredictedOptionList
        from forecasting_tools.data_models.multiple_choice_report import PredictedOption
        predicted_options = [
            PredictedOption(option_name=opt, probability=normalized_probs[opt] / 100)
            for opt in question.options
        ]
        predicted_option_list = PredictedOptionList(predicted_options=predicted_options)

        logger.info(
            f"Returning median MC forecast for URL {question.page_url}: {normalized_probs}"
        )
        return ReasonedPrediction(
            prediction_value=predicted_option_list, reasoning=reasoning
        )

    ##################################### NUMERIC QUESTIONS #####################################

    async def _run_forecast_on_numeric(
        self, question: NumericQuestion, research: str
    ) -> ReasonedPrediction[NumericDistribution]:
        # Track which call number this is for the current question
        if self._current_question_id != question.page_url:
            self._current_call_number = 0
            logger.info(f"[GPR DEBUG] New numeric question detected. Resetting counter. ID was: {self._current_question_id}, now: {question.page_url}")
        self._current_call_number = getattr(self, '_current_call_number', 0) + 1
        logger.info(f"[GPR DEBUG] Numeric call number: {self._current_call_number}, Scenarios so far: {len(self._numeric_scenarios)}, Question: {question.page_url}")

        upper_bound_message, lower_bound_message = (
            self._create_upper_and_lower_bound_messages(question)
        )
        # DRE 01-01-2025 Numeric for Spring 2026
        prompt = clean_indents(
            f"""
            # Make a Professional Forecast
            
            ## You are a professional forecaster interviewing for a job.

            ## Your interview question is:
            {question.question_text}

            ## Question background:
            {question.background_info}

            {question.resolution_criteria}

            {question.fine_print}
    
            {lower_bound_message}
            {upper_bound_message}

            ## Units for answer:
            {question.unit_of_measure if question.unit_of_measure else "Not stated (please infer this)"}
            - You are careful to make sure you forecast units are consistent with the upper and lower bound units
            - You write Units for the answer are: (whatever units you determined)
        
            ## Your research assistant says:
            {research}

            ## Today is {datetime.now().strftime("%Y-%m-%d")}.
            {lower_bound_message}
            {upper_bound_message}
            
            ## Your workflow

            ### Formatting Instructions:
            - Please notice the units requested (e.g. whether you represent a number as 1,000,000 or 1 million).
            - Never use scientific notation.
            - Always start with a smaller number (more negative if negative) and then increase from there.

            ### Review some potential outcomes
            Before answering you write:
            1. The time left until the outcome to the question is known.
            2. The outcome if nothing changed (the current value).
            3. The outcome if the current trend continued.
            4. The expectations of experts and markets.
            5. The volatility history and expectations for the target measure.

            ### Group the evidence
            Review the evidence from your reseach assistant and group it into three buckets of approximately
            the same size:
            - Bucket 1. Evidence that would indicate a relatively low forecast
            - Bucket 2. Evidence that would indicate a relatively high forecast
            - Bucket 3. Evidence that would indicate a central forecast
            
            ### Multi-world considerations
            For this section, you are careful to report values in the confirmed units for answer. You want to
            explore ranges of reasonable possibilities. You consider possible worlds:
            1. Low_World: review the bucket 1 evidence from your reseach assistant that the forecast could be low.
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            2. High_World: review the bucket 3 evidence from your reseach assistant that the forecast could be high.
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            3. Mid_World: review the bucket 2 evidence from your reseach assistant that the forecast could be around
            the central views and trends.
            - What would be a low forecast estimate be for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate be for this world?
            
            ### Verify units
            With those values in mind, you are careful to use the units for answer that you determined earlier.
        
            # Final Answer
            The last thing you write is your final answer as a list of values for the world scenarios. Written as a list: 
            
            [Low_World-Low, Low_World-Mid, Low_World-High, Mid_World-Low, Mid_World-Mid, Mid_World-High, High_World_Low,
            High_World_Mid, High_World_High]
            """
        )

        result = await self._numeric_prompt_to_forecast(question, prompt)

        logger.info(f"[GPR DEBUG] Returning temporary distribution. Numeric scenarios stored: {len(self._numeric_scenarios)}")
        return result

    async def _numeric_prompt_to_forecast(
        self,
        question: NumericQuestion,
        prompt: str,
    ) -> ReasonedPrediction[NumericDistribution]:
        # Clear storage if this is a new question
        logger.info(f"[GPR DEBUG] In _numeric_prompt_to_forecast. Current ID: {self._current_question_id}, Question URL: {question.page_url}, Match: {self._current_question_id == question.page_url}")
        if self._current_question_id != question.page_url:
            self._numeric_scenarios = []
            self._current_question_id = question.page_url
            logger.info(f"Starting new numeric question {question.page_url}, cleared scenario storage")

        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        logger.info(f"Reasoning for URL {question.page_url}: {reasoning}")

        # Parse 9 scenarios from prompt using MultiScenarioPrediction
        scenario_prediction: MultiScenarioPrediction = await structure_output(
            reasoning,
            MultiScenarioPrediction,
            model=self.get_llm("parser", "llm"),
            num_validation_samples=self._structure_output_validation_samples,
        )

        # Store all scenarios (no scaling needed - already in question units)
        self._numeric_scenarios.extend(scenario_prediction.scenarios)

        # Warn if unusually few scenarios (likely LLM didn't follow prompt)
        if len(scenario_prediction.scenarios) < 9:
            logger.warning(
                f"Expected 9 scenarios, got {len(scenario_prediction.scenarios)} - check prompt clarity"
            )

        logger.info(
            f"Parsed {len(scenario_prediction.scenarios)} numeric scenarios: {scenario_prediction.scenarios}"
        )
        logger.info(
            f"Total numeric scenarios stored for question {question.page_url}: {len(self._numeric_scenarios)} scenarios"
        )

        # Return temporary distribution based on median (framework will aggregate later)
        # Create a simple distribution from the current scenarios for now
        median_value = float(np.median(scenario_prediction.scenarios))
        temp_percentiles = self._create_temp_distribution_from_scenarios(
            scenario_prediction.scenarios, question
        )

        logger.info(
            f"Returning temporary distribution for URL {question.page_url}, median: {median_value}"
        )
        return ReasonedPrediction(prediction_value=temp_percentiles, reasoning=reasoning)

    def _create_temp_distribution_from_scenarios(
        self, scenarios: list[float], question: NumericQuestion
    ) -> NumericDistribution:
        """Create a temporary distribution from scenarios (will be replaced by GPR aggregation)"""
        sorted_scenarios = sorted(scenarios)
        n = len(sorted_scenarios)

        # Map sorted scenarios to approximate percentiles
        # This is just a placeholder - GPR will create the final distribution
        if n >= 6:
            temp_percentiles = {
                10: sorted_scenarios[0],
                20: sorted_scenarios[1] if n > 1 else sorted_scenarios[0],
                40: sorted_scenarios[int(n * 0.4)] if n > 2 else sorted_scenarios[0],
                60: sorted_scenarios[int(n * 0.6)] if n > 3 else sorted_scenarios[-1],
                80: sorted_scenarios[-2] if n > 4 else sorted_scenarios[-1],
                90: sorted_scenarios[-1],
            }
        else:
            # Fallback for too few scenarios
            median = sorted_scenarios[n // 2]
            temp_percentiles = {10: median, 20: median, 40: median, 60: median, 80: median, 90: median}

        # Convert dict to list of Percentile objects (percentiles must be 0-1 scale)
        percentile_list = [Percentile(percentile=p/100, value=v) for p, v in sorted(temp_percentiles.items())]
        return NumericDistribution.from_question(percentile_list, question)

    def _validate_numeric_scenarios_majority_vote(self, scenarios: list[float]) -> list[float]:
        """
        Keep only scenarios from calls in the majority cluster. Bail if <3 calls agree.

        Detects unit interpretation errors by clustering call medians.
        Calls within 3× of each other are considered "agreeing".
        Returns scenarios from largest cluster, or raises ValueError if <3 calls agree.

        Args:
            scenarios: All scenarios from all LLM calls (typically 4 calls × 9 scenarios = 36)

        Returns:
            Validated scenarios from majority cluster

        Raises:
            ValueError: If <3 calls agree (insufficient consensus for reliable forecast)

        Example:
            Call medians: [1.0, 1.2, 120, 0.9]
            → Calls 0,1,3 agree (within 3×), Call 2 is 100× outlier
            → Returns 27 scenarios from calls 0,1,3
        """
        # Group by call (9 scenarios per call)
        num_calls = len(scenarios) // 9
        calls = [scenarios[i*9:(i+1)*9] for i in range(num_calls)]
        medians = [float(np.median(c)) for c in calls]

        # Find largest cluster of calls that agree (within 3× of each other)
        best_cluster = []
        for ref_idx in range(num_calls):
            cluster = [ref_idx]
            for other_idx in range(num_calls):
                if other_idx != ref_idx and medians[ref_idx] != 0:
                    ratio = medians[other_idx] / medians[ref_idx]
                    if 0.33 < ratio < 3.0:  # Within 3×
                        cluster.append(other_idx)
            if len(cluster) > len(best_cluster):
                best_cluster = cluster

        # Bail out if <3 calls agree
        if len(best_cluster) < 3:
            logger.error(
                f"❌ [BAIL OUT] Only {len(best_cluster)}/{num_calls} calls agree. "
                f"Call medians: {[f'{m:.2e}' for m in medians]}"
            )
            raise ValueError(
                f"Insufficient agreement: only {len(best_cluster)}/{num_calls} calls consistent. "
                f"Refusing to submit unreliable forecast."
            )

        # Keep scenarios from majority cluster
        valid_scenarios = []
        for idx in best_cluster:
            valid_scenarios.extend(calls[idx])

        excluded = num_calls - len(best_cluster)
        if excluded > 0:
            logger.warning(
                f"⚠️  [MAJORITY VOTE] Excluded {excluded} call(s). "
                f"Using {len(best_cluster)}/{num_calls} calls = {len(valid_scenarios)} scenarios."
            )
        else:
            logger.info(
                f"✅ [MAJORITY VOTE] All {num_calls} calls agree. "
                f"Using all {len(valid_scenarios)} scenarios."
            )

        return valid_scenarios

    def _gpr_aggregate_numeric(self, scenarios: list[float], question: NumericQuestion) -> NumericDistribution:
        """
        Aggregate numeric scenarios using GPR to create full CDF.

        Args:
            scenarios: List of numeric values from multiple world scenarios
            question: The NumericQuestion being forecasted

        Returns:
            NumericDistribution with smoothed percentiles at 5% increments

        Raises:
            ValueError: If majority vote validation fails (<3 calls agree)
        """
        # Validate scenarios for unit interpretation consistency
        # Keeps only scenarios from majority cluster, raises ValueError if <3 calls agree
        validated_scenarios = self._validate_numeric_scenarios_majority_vote(scenarios)

        if len(validated_scenarios) < 9:
            logger.warning(
                f"⚠️  FALLBACK TO EMPIRICAL METHOD: Only {len(validated_scenarios)} scenarios available. "
                f"GPR requires at least 9 scenarios for reliable aggregation. "
                f"Using empirical percentiles instead."
            )
            return self._empirical_distribution_fallback(validated_scenarios, question)

        # Sort scenarios to create empirical CDF
        sorted_scenarios = sorted(validated_scenarios)

        # Create empirical CDF percentiles
        n = len(sorted_scenarios)
        empirical_percentiles = [100 * i / (n + 1) for i in range(1, n + 1)]

        # Fit GPR model (same approach as binary)
        X = np.array(empirical_percentiles).reshape(-1, 1)
        y = np.array(sorted_scenarios)

        # Define kernel: smooth RBF + white noise
        smooth_kernel = C(1.0, (1e-3, 1e5)) * RBF(20.0, (1e-2, 1e2))
        kernel = smooth_kernel + WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e2))

        # Fit model with multiple restarts for better optimization
        gpr_model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
        gpr_model.fit(X, y)

        # Extract percentiles at 5% increments (19 percentiles: 5, 10, 15, ..., 90, 95)
        target_percentiles = list(range(5, 100, 5))  # [5, 10, 15, ..., 90, 95]
        percentile_list = []

        for p in target_percentiles:
            value = gpr_model.predict(np.array([[p]]))[0]
            percentile_list.append(Percentile(percentile=p/100, value=float(value)))

        logger.info(f"✅ GPR numeric aggregation: {len(validated_scenarios)} scenarios → {len(target_percentiles)} percentiles")
        logger.info(
            f"Distribution: p5={percentile_list[0].value:.2f}, "
            f"p50={percentile_list[9].value:.2f}, "
            f"p95={percentile_list[-1].value:.2f}"
        )

        return NumericDistribution.from_question(percentile_list, question)

    def _empirical_distribution_fallback(self, scenarios: list[float], question: NumericQuestion) -> NumericDistribution:
        """
        Fallback to empirical percentiles if too few scenarios for GPR.

        WARNING: This method is only used when GPR cannot be applied due to insufficient data.
        The resulting distribution will be less smooth than GPR.
        """
        sorted_scenarios = sorted(scenarios)
        n = len(sorted_scenarios)

        # Extract percentiles at 5% increments using empirical approach
        target_percentiles = list(range(5, 100, 5))
        percentile_list = []

        for p in target_percentiles:
            index = int(n * p / 100)
            index = min(max(0, index), n - 1)  # Clamp to valid range
            percentile_list.append(Percentile(percentile=p/100, value=sorted_scenarios[index]))

        logger.warning(
            f"📊 EMPIRICAL FALLBACK APPLIED: Used {n} scenarios to create distribution. "
            f"Distribution may be less smooth than GPR. "
            f"Range: [{percentile_list[0].value:.2f}, {percentile_list[-1].value:.2f}]"
        )

        return NumericDistribution.from_question(percentile_list, question)

    ##################################### DATE QUESTIONS #####################################

    async def _run_forecast_on_date(
        self, question: DateQuestion, research: str
    ) -> ReasonedPrediction[NumericDistribution]:
        upper_bound_message, lower_bound_message = (
            self._create_upper_and_lower_bound_messages(question)
        )
        prompt = clean_indents(
            f"""
            You are a professional forecaster interviewing for a job.

            Your interview question is:
            {question.question_text}

            Background:
            {question.background_info}

            {question.resolution_criteria}

            {question.fine_print}

            Your research assistant says:
            {research}

            Today is {datetime.now().strftime("%Y-%m-%d")}.

            {lower_bound_message}
            {upper_bound_message}

            Formatting Instructions:
            - This is a date question, and as such, the answer must be expressed in terms of dates.
            - The dates must be written in the format of YYYY-MM-DD. If hours matter, please append the date with the hour in UTC and military time: YYYY-MM-DDTHH:MM:SSZ.No other formatting is allowed.
            - Always start with a lower date chronologically and then increase from there.
            - Do NOT forget this. The dates must be written in chronological order starting at the earliest time at percentile 10 and increasing from there.

            Before answering you write:
            (a) The time left until the outcome to the question is known.
            (b) The outcome if nothing changed.
            (c) The outcome if the current trend continued.
            (d) The expectations of experts and markets.
            (e) A brief description of an unexpected scenario that results in a low outcome.
            (f) A brief description of an unexpected scenario that results in a high outcome.

            {self._get_conditional_disclaimer_if_necessary(question)}
            You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unknowns.

            The last thing you write is your final answer as:
            "
            Percentile 10: YYYY-MM-DD (oldest date)
            Percentile 20: YYYY-MM-DD
            Percentile 40: YYYY-MM-DD
            Percentile 60: YYYY-MM-DD
            Percentile 80: YYYY-MM-DD
            Percentile 90: YYYY-MM-DD (newest date)
            "
            """
        )
        forecast = await self._date_prompt_to_forecast(question, prompt)
        return forecast

    async def _date_prompt_to_forecast(
        self,
        question: DateQuestion,
        prompt: str,
    ) -> ReasonedPrediction[NumericDistribution]:
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        logger.info(f"Reasoning for URL {question.page_url}: {reasoning}")
        parsing_instructions = clean_indents(
            f"""
            The text given to you is trying to give a forecast distribution for a date question.
            - This text is trying to answer the question: "{question.question_text}".
            - As an example, someone else guessed that the answer will be between {question.lower_bound} and {question.upper_bound}, so the numbers parsed from an answer like this would be verbatim "{question.lower_bound}" and "{question.upper_bound}".
            - The output is given as dates/times please format it into a valid datetime parsable string. Assume midnight UTC if no hour is given.
            - If percentiles are not explicitly given (e.g. only a single value is given) please don't return a parsed output, but rather indicate that the answer is not explicitly given in the text.
            """
        )
        date_percentile_list: list[DatePercentile] = await structure_output(
            reasoning,
            list[DatePercentile],
            model=self.get_llm("parser", "llm"),
            additional_instructions=parsing_instructions,
            num_validation_samples=self._structure_output_validation_samples,
        )

        percentile_list = [
            Percentile(
                percentile=percentile.percentile,
                value=percentile.value.timestamp(),
            )
            for percentile in date_percentile_list
        ]
        prediction = NumericDistribution.from_question(percentile_list, question)
        logger.info(
            f"Forecasted URL {question.page_url} with prediction: {prediction.declared_percentiles}."
        )
        return ReasonedPrediction(prediction_value=prediction, reasoning=reasoning)

    def _create_upper_and_lower_bound_messages(
        self, question: NumericQuestion | DateQuestion
    ) -> tuple[str, str]:
        if isinstance(question, NumericQuestion):
            if question.nominal_upper_bound is not None:
                upper_bound_number = question.nominal_upper_bound
            else:
                upper_bound_number = question.upper_bound
            if question.nominal_lower_bound is not None:
                lower_bound_number = question.nominal_lower_bound
            else:
                lower_bound_number = question.lower_bound
            unit_of_measure = question.unit_of_measure
        elif isinstance(question, DateQuestion):
            upper_bound_number = question.upper_bound.date().isoformat()
            lower_bound_number = question.lower_bound.date().isoformat()
            unit_of_measure = ""
        else:
            raise ValueError()

        if question.open_upper_bound:
            upper_bound_message = f"The question creator thinks the number is likely not higher than {upper_bound_number} {unit_of_measure}."
        else:
            upper_bound_message = f"The outcome can not be higher than {upper_bound_number} {unit_of_measure}."

        if question.open_lower_bound:
            lower_bound_message = f"The question creator thinks the number is likely not lower than {lower_bound_number} {unit_of_measure}."
        else:
            lower_bound_message = f"The outcome can not be lower than {lower_bound_number} {unit_of_measure}."
        return upper_bound_message, lower_bound_message

    ##################################### CONDITIONAL QUESTIONS #####################################

    async def _run_forecast_on_conditional(
        self, question: ConditionalQuestion, research: str
    ) -> ReasonedPrediction[ConditionalPrediction]:
        parent_info, full_research = await self._get_question_prediction_info(
            question.parent, research, "parent"
        )
        child_info, full_research = await self._get_question_prediction_info(
            question.child, research, "child"
        )
        yes_info, full_research = await self._get_question_prediction_info(
            question.question_yes, full_research, "yes"
        )
        no_info, full_research = await self._get_question_prediction_info(
            question.question_no, full_research, "no"
        )
        full_reasoning = clean_indents(
            f"""
            ## Parent Question Reasoning
            {parent_info.reasoning}
            ## Child Question Reasoning
            {child_info.reasoning}
            ## Yes Question Reasoning
            {yes_info.reasoning}
            ## No Question Reasoning
            {no_info.reasoning}
        """
        )
        full_prediction = ConditionalPrediction(
            parent=parent_info.prediction_value,  # type: ignore
            child=child_info.prediction_value,  # type: ignore
            prediction_yes=yes_info.prediction_value,  # type: ignore
            prediction_no=no_info.prediction_value,  # type: ignore
        )
        return ReasonedPrediction(
            reasoning=full_reasoning, prediction_value=full_prediction
        )

    async def _get_question_prediction_info(
        self, question: MetaculusQuestion, research: str, question_type: str
    ) -> tuple[ReasonedPrediction[PredictionTypes | PredictionAffirmed], str]:
        from forecasting_tools.data_models.data_organizer import DataOrganizer

        previous_forecasts = question.previous_forecasts
        if (
            question_type in ["parent", "child"]
            and previous_forecasts
            and question_type not in self.force_reforecast_in_conditional
        ):
            # TODO: add option to not affirm current parent/child forecasts, create new forecast
            previous_forecast = previous_forecasts[-1]
            current_utc_time = datetime.now(timezone.utc)
            if (
                previous_forecast.timestamp_end is None
                or previous_forecast.timestamp_end > current_utc_time
            ):
                pretty_value = DataOrganizer.get_readable_prediction(previous_forecast) # type: ignore
                prediction = ReasonedPrediction(
                    prediction_value=PredictionAffirmed(),
                    reasoning=f"Already existing forecast reaffirmed at {pretty_value}.",
                )
                return (prediction, research)  # type: ignore
        info = await self._make_prediction(question, research)
        full_research = self._add_reasoning_to_research(research, info, question_type)
        return info, full_research  # type: ignore

    def _add_reasoning_to_research(
        self,
        research: str,
        reasoning: ReasonedPrediction[PredictionTypes],
        question_type: str,
    ) -> str:
        from forecasting_tools.data_models.data_organizer import DataOrganizer

        question_type = question_type.title()
        return clean_indents(
            f"""
            {research}
            ---
            ## {question_type} Question Information
            You have previously forecasted the {question_type} Question to the value: {DataOrganizer.get_readable_prediction(reasoning.prediction_value)}
            This is relevant information for your current forecast, but it is NOT your current forecast, but previous forecasting information that is relevant to your current forecast.
            The reasoning for the {question_type} Question was as such:
            ```
            {reasoning.reasoning}
            ```
            This is absolutely essential: do NOT use this reasoning to re-forecast the {question_type} question.
            """
        )

    def _get_conditional_disclaimer_if_necessary(
        self, question: MetaculusQuestion
    ) -> str:
        if question.conditional_type not in ["yes", "no"]:
            return ""
        return clean_indents(
            """
            As you are given a conditional question with a parent and child, you are to only forecast the **CHILD** question, given the parent question's resolution.
            You never re-forecast the parent question under any circumstances, but you use probabilistic reasoning, strongly considering the parent question's resolution, to forecast the child question.
            """
        )

    ##################################### FORECAST SUMMARY SAVING #####################################
    # Forecast saving functionality moved to dre_forecasting_tools.py


if __name__ == "__main__":
    # Import custom extensions here to avoid circular import
    from dre_forecasting_tools import SpringTemplateBotExtended

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Suppress LiteLLM logging
    litellm_logger = logging.getLogger("LiteLLM")
    litellm_logger.setLevel(logging.WARNING)
    litellm_logger.propagate = False

    parser = argparse.ArgumentParser(
        description="Run the TemplateBot forecasting system"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["tournament", "metaculus_cup", "test_questions"],
        default="tournament",
        help="Specify the run mode (default: tournament)",
    )
    args = parser.parse_args()
    run_mode: Literal["tournament", "metaculus_cup", "test_questions"] = args.mode
    assert run_mode in [
        "tournament",
        "metaculus_cup",
        "test_questions",
    ], "Invalid run mode"

    template_bot = SpringTemplateBotExtended(
        research_reports_per_question=1,
        predictions_per_research_report=4,  # 8 desired in production.
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=True,
        folder_to_save_reports_to=None,
        skip_previously_forecasted_questions=True,
        extra_metadata_in_explanation=True,
        llms={  # choose your model names or GeneralLlm llms here, otherwise defaults will be chosen for you
            "default": GeneralLlm(
                model= "openrouter/openai/gpt-5.2",  # "openrouter/openai/o3", # "anthropic/claude-sonnet-4-20250514", etc (see docs for litellm)
                temperature=1,
                timeout=80,  # Updated from 40 to 80. In test, one run failed due to exceeding 40.
                allowed_tries=2,
            ),
            "summarizer": "openrouter/openai/o4-mini",  # For summaries and condensed forecast summaries 
            "researcher": "asknews/news-summaries",
            "parser": "openrouter/openai/o4-mini",  # "metaculus/openai/o4-mini",
        },
    )

    client = MetaculusClient()
    if run_mode == "tournament":
        # You may want to change this to the specific tournament ID you want to forecast on
        seasonal_tournament_reports = asyncio.run(
            template_bot.forecast_on_tournament(
                client.CURRENT_AI_COMPETITION_ID, return_exceptions=True
            )
        )
        minibench_reports = asyncio.run(
            template_bot.forecast_on_tournament(
                client.CURRENT_MINIBENCH_ID, return_exceptions=True
            )
        )
        forecast_reports = seasonal_tournament_reports + minibench_reports
    elif run_mode == "metaculus_cup":
        # The Metaculus cup is a good way to test the bot's performance on regularly open questions. You can also use AXC_2025_TOURNAMENT_ID = 32564 or AI_2027_TOURNAMENT_ID = "ai-2027"
        # The Metaculus cup may not be initialized near the beginning of a season (i.e. January, May, September)
        template_bot.skip_previously_forecasted_questions = False
        forecast_reports = asyncio.run(
            template_bot.forecast_on_tournament(
                client.CURRENT_METACULUS_CUP_ID, return_exceptions=True
            )
        )
    elif run_mode == "test_questions":
        # Example questions are a good way to test the bot's performance on a single question
        EXAMPLE_QUESTIONS = [
            # "https://www.metaculus.com/questions/578/human-extinction-by-2100/",  # Binary
            # "https://www.metaculus.com/questions/22427/number-of-new-leading-ai-labs/",  # Multiple Choice
            "https://www.metaculus.com/questions/14333/age-of-oldest-human-as-of-2100/",  # Numeric
            # "https://www.metaculus.com/c/diffusion-community/38880/how-many-us-labor-strikes-due-to-ai-in-2029/",  # Discrete Numeric
        ]
        template_bot.skip_previously_forecasted_questions = False
        questions = [
            client.get_question_by_url(question_url)
            for question_url in EXAMPLE_QUESTIONS
        ]
        forecast_reports = asyncio.run(
            template_bot.forecast_questions(questions, return_exceptions=True)
        )
    template_bot.log_report_summary(forecast_reports)
