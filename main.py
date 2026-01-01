import argparse
import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

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

logger = logging.getLogger(__name__)


# Data model for multi-scenario predictions (flexible count)
class MultiScenarioPrediction(BaseModel):
    """Multiple scenario forecasts of arbitrary count from a single prompt"""
    scenarios: list[float] = Field(
        ...,
        description="List of forecast probabilities from low to high (0-100)",
        min_length=1
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
            what are low (pessimistic), mid (baseline), and high (optimistic) forecasts.
            
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
            Review the evidence from your reseach assistant and group it into three buckets of approximately the same size:
            - Bucket 1. Evidence that would indicate a relatively low forecast
            - Bucket 2. Evidence that would indicate a relatively high forecast
            - Bucket 3. Evidence that would indicate a central forecast
            
            #### Multi-world considerations
            You explore ranges of reasonable, possible forecasts.
            You consider three worlds:
            1. Low_World: review the bucket 1 evidence from your reseach assistant that the forecast could be low, summarize.
            - What would be a low (pessimistic) forecast estimate for this world?
            - What would be a mid (your baseline) forecast estimate for this world?
            - What would be a high (optimistic) forecast estimate for this world?

            2. Mid_World: review the bucket 2 evidence from your reseach assistant that the forecast could be around 
               the central views and trends, summarize.
            - What would be a low (pessimistic) forecast estimate be for this world?
            - What would be a mid (your baseline) forecast estimate for this world?
            - What would be a high (optimistic) forecast estimate be for this world?
            
            3. High_World: review the bucket 3 evidence from your reseach assistant that the forecast could be high, summarize.
            - What would be a low (pessimistic) forecast estimate for this world?
            - What would be a mid (your baseline) forecast estimate for this world?
            - What would be a high (optimistic) forecast estimate for this world?

            # Final Answer
            The last thing you write is your final answer as a list of values for the world scenarios. Written as a list: 
            
            [Low_World-Low, Low_World-Mid, Low_World-High, Mid_World-Low, Mid_World-Mid, Mid_World-High, High_World_Low,
            High_World_Mid, High_World_High]
            
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

    ##################################### AGGREGATION OVERRIDE #####################################

    async def _aggregate_predictions(
        self,
        predictions: list,
        question: MetaculusQuestion,
    ):
        """
        Override framework's aggregation to use GPR for binary and numeric questions.

        For binary questions: Apply GPR on all stored scenarios to get p50.
        For numeric questions: Apply GPR on all stored scenarios to get full distribution.
        For other question types: Use default framework aggregation.
        """
        from forecasting_tools.data_models.questions import BinaryQuestion, NumericQuestion

        # Binary questions: GPR aggregation
        if isinstance(question, BinaryQuestion) and len(self._binary_scenarios) >= 3:
            logger.info(f"[GPR DEBUG] _aggregate_predictions called with {len(predictions)} predictions")
            logger.info(f"[GPR DEBUG] Using GPR aggregation on {len(self._binary_scenarios)} stored scenarios")

            gpr_result = self._gpr_aggregate_binary(self._binary_scenarios)

            # Clear scenarios after aggregation
            self._binary_scenarios = []
            self._current_question_id = None
            self._current_call_number = 0

            logger.info(f"[GPR DEBUG] Aggregation complete. Returning GPR result: {gpr_result:.4f}")
            return gpr_result

        # Numeric questions: GPR aggregation for full distribution
        elif isinstance(question, NumericQuestion) and len(self._numeric_scenarios) >= 9:
            logger.info(f"[GPR DEBUG] _aggregate_predictions called for numeric question with {len(predictions)} predictions")
            logger.info(f"[GPR DEBUG] Using GPR aggregation on {len(self._numeric_scenarios)} stored numeric scenarios")

            gpr_distribution = self._gpr_aggregate_numeric(self._numeric_scenarios, question)

            # Clear scenarios after aggregation
            self._numeric_scenarios = []
            self._current_question_id = None
            self._current_call_number = 0

            logger.info(f"[GPR DEBUG] Numeric aggregation complete. Returning distribution with {len(gpr_distribution.declared_percentiles)} percentiles")
            return gpr_distribution

        else:
            # Use default framework aggregation for other question types or insufficient scenarios
            logger.info(f"[GPR DEBUG] Using default aggregation for {type(question).__name__}")
            return await super()._aggregate_predictions(predictions, question)

    ##################################### MULTIPLE CHOICE QUESTIONS #####################################

    async def _run_forecast_on_multiple_choice(
        self, question: MultipleChoiceQuestion, research: str
    ) -> ReasonedPrediction[PredictedOptionList]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster interviewing for a job.

            Your interview question is:
            {question.question_text}

            The options are: {question.options}


            Background:
            {question.background_info}

            {question.resolution_criteria}

            {question.fine_print}


            Your research assistant says:
            {research}

            Today is {datetime.now().strftime("%Y-%m-%d")}.

            Before answering you write:
            (a) The time left until the outcome to the question is known.
            (b) The status quo outcome if nothing changed.
            (c) A description of an scenario that results in an unexpected outcome.

            {self._get_conditional_disclaimer_if_necessary(question)}
            You write your rationale remembering that (1) good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time, and (2) good forecasters leave some moderate probability on most options to account for unexpected outcomes.

            The last thing you write is your final probabilities for the N options in this order {question.options} as:
            Option_A: Probability_A
            Option_B: Probability_B
            ...
            Option_N: Probability_N
            """
        )
        return await self._multiple_choice_prompt_to_forecast(question, prompt)

    async def _multiple_choice_prompt_to_forecast(
        self,
        question: MultipleChoiceQuestion,
        prompt: str,
    ) -> ReasonedPrediction[PredictedOptionList]:
        parsing_instructions = clean_indents(
            f"""
            Make sure that all option names are one of the following:
            {question.options}

            The text you are parsing may prepend these options with some variation of "Option" which you should remove if not part of the option names I just gave you.
            Additionally, you may sometimes need to parse a 0% probability. Please do not skip options with 0% but rather make it an entry in your final list with 0% probability.
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        logger.info(f"Reasoning for URL {question.page_url}: {reasoning}")
        predicted_option_list: PredictedOptionList = await structure_output(
            text_to_structure=reasoning,
            output_type=PredictedOptionList,
            model=self.get_llm("parser", "llm"),
            num_validation_samples=self._structure_output_validation_samples,
            additional_instructions=parsing_instructions,
        )

        logger.info(
            f"Forecasted URL {question.page_url} with prediction: {predicted_option_list}."
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

        # Check for unit interpretation issues
        if self._detect_unit_inconsistency(scenario_prediction.scenarios):
            logger.warning(
                f"Possible unit interpretation error detected in call {self._current_call_number}! "
                f"Scenarios: {scenario_prediction.scenarios}"
            )

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

    def _detect_unit_inconsistency(self, scenarios: list[float]) -> bool:
        """
        Detect if scenarios suggest unit interpretation errors.

        Returns True if scenarios span >2 orders of magnitude,
        suggesting some forecaster interpreted units differently.
        """
        if len(scenarios) < 3:
            return False

        sorted_scenarios = sorted(scenarios)
        min_val = sorted_scenarios[0]
        max_val = sorted_scenarios[-1]

        # Can't check ratio with negative/zero values
        if min_val <= 0:
            return False

        ratio = max_val / min_val

        # If max is >100× min, likely unit confusion
        if ratio > 100:
            logger.warning(
                f"Scenarios span {ratio:.1f}× range: {min_val} to {max_val}. "
                f"Possible unit interpretation error."
            )
            return True

        return False

    def _gpr_aggregate_numeric(self, scenarios: list[float], question: NumericQuestion) -> NumericDistribution:
        """
        Aggregate numeric scenarios using GPR to create full CDF.

        Args:
            scenarios: List of numeric values from multiple world scenarios
            question: The NumericQuestion being forecasted

        Returns:
            NumericDistribution with smoothed percentiles at 5% increments
        """
        if len(scenarios) < 9:
            logger.warning(
                f"⚠️  FALLBACK TO EMPIRICAL METHOD: Only {len(scenarios)} scenarios available. "
                f"GPR requires at least 9 scenarios for reliable aggregation. "
                f"Using empirical percentiles instead."
            )
            return self._empirical_distribution_fallback(scenarios, question)

        # Sort scenarios to create empirical CDF
        sorted_scenarios = sorted(scenarios)

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

        logger.info(f"✅ GPR numeric aggregation: {len(scenarios)} scenarios → {len(target_percentiles)} percentiles")
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


if __name__ == "__main__":
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

    template_bot = SpringTemplateBot2026(
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
                timeout=40,
                allowed_tries=2,
            ),
            "summarizer": "openrouter/openai/o4-mini",  # "summarizer": "metaculus/openai/o4-mini",
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
            "https://www.metaculus.com/questions/578/human-extinction-by-2100/",  # Human Extinction - Binary
            # "https://www.metaculus.com/questions/14333/age-of-oldest-human-as-of-2100/",  # Age of Oldest Human - Numeric
            # "https://www.metaculus.com/questions/22427/number-of-new-leading-ai-labs/",  # Number of New Leading AI Labs - Multiple Choice
            # "https://www.metaculus.com/c/diffusion-community/38880/how-many-us-labor-strikes-due-to-ai-in-2029/",  # Number of US Labor Strikes Due to AI in 2029 - Discrete
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
