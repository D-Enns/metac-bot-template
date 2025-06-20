import argparse
import asyncio
import logging
import os
from datetime import datetime
from typing import Literal

from forecasting_tools import (
    AskNewsSearcher,
    BinaryQuestion,
    ForecastBot,
    GeneralLlm,
    MetaculusApi,
    MetaculusQuestion,
    MultipleChoiceQuestion,
    NumericDistribution,
    NumericQuestion,
    PredictedOptionList,
    PredictionExtractor,
    ReasonedPrediction,
    SmartSearcher,
    clean_indents,
)

logger = logging.getLogger(__name__)


class TemplateForecaster(ForecastBot):
    """
    This is a copy of the template bot for Q2 2025 Metaculus AI Tournament.
    The official bots on the leaderboard use AskNews in Q2.
    Main template bot changes since Q1
    - Support for new units parameter was added
    - You now set your llms when you initialize the bot (making it easier to switch between and benchmark different models)

    The main entry point of this bot is `forecast_on_tournament` in the parent class.
    See the script at the bottom of the file for more details on how to run the bot.
    Ignoring the finer details, the general flow is:
    - Load questions from Metaculus
    - For each question
        - Execute run_research a number of times equal to research_reports_per_question
        - Execute respective run_forecast function `predictions_per_research_report * research_reports_per_question` times
        - Aggregate the predictions
        - Submit prediction (if publish_reports_to_metaculus is True)
    - Return a list of ForecastReport objects

    Only the research and forecast functions need to be implemented in ForecastBot subclasses.

    If you end up having trouble with rate limits and want to try a more sophisticated rate limiter try:
    ```
    from forecasting_tools.ai_models.resource_managers.refreshing_bucket_rate_limiter import RefreshingBucketRateLimiter
    rate_limiter = RefreshingBucketRateLimiter(
        capacity=2,
        refresh_rate=1,
    ) # Allows 1 request per second on average with a burst of 2 requests initially. Set this as a class variable
    await self.rate_limiter.wait_till_able_to_acquire_resources(1) # 1 because it's consuming 1 request (use more if you are adding a token limit)
    ```
    Additionally OpenRouter has large rate limits immediately on account creation
    """

    _max_concurrent_questions = 2  # Set this to whatever works for your search-provider/ai-model rate limits
    _concurrency_limiter = asyncio.Semaphore(_max_concurrent_questions)

    async def run_research(self, question: MetaculusQuestion) -> str:
        async with self._concurrency_limiter:
            research = ""
            if os.getenv("ASKNEWS_CLIENT_ID") and os.getenv("ASKNEWS_SECRET"):
                research = await AskNewsSearcher().get_formatted_news_async(
                    question.question_text
                )
            elif os.getenv("EXA_API_KEY"):
                research = await self._call_exa_smart_searcher(
                    question.question_text
                )
            elif os.getenv("PERPLEXITY_API_KEY"):
                research = await self._call_perplexity(question.question_text)
            elif os.getenv("OPENROUTER_API_KEY"):
                research = await self._call_perplexity(
                    question.question_text, use_open_router=True
                )
            else:
                logger.warning(
                    f"No research provider found when processing question URL {question.page_url}. Will pass back empty string."
                )
                research = ""
            logger.info(
                f"Found Research for URL {question.page_url}:\n{research}"
            )
            return research

    async def _call_perplexity(
        self, question: str, use_open_router: bool = False
    ) -> str:
        prompt = clean_indents(
            f"""
            You are an assistant to a superforecaster.
            The superforecaster will give you a question they intend to forecast on.
            To be a great assistant, you generate a concise but detailed rundown of the most relevant news, including if the question would resolve Yes or No based on current information.
            You do not produce forecasts yourself.

            Question:
            {question}
            """
        )  # NOTE: The metac bot in Q1 put everything but the question in the system prompt.
        if use_open_router:
            model_name = "openrouter/perplexity/sonar-reasoning"
        else:
            model_name = "perplexity/sonar-pro"  # perplexity/sonar-reasoning and perplexity/sonar are cheaper, but do only 1 search
        model = GeneralLlm(
            model=model_name,
            temperature=0.1,
        )
        response = await model.invoke(prompt)
        return response

    async def _call_exa_smart_searcher(self, question: str) -> str:
        """
        SmartSearcher is a custom class that is a wrapper around an search on Exa.ai
        """
        searcher = SmartSearcher(
            model=self.get_llm("default", "llm"),
            temperature=0,
            num_searches_to_run=2,
            num_sites_per_search=10,
        )
        prompt = (
            "You are an assistant to a superforecaster. The superforecaster will give"
            "you a question they intend to forecast on. To be a great assistant, you generate"
            "a concise but detailed rundown of the most relevant news, including if the question"
            "would resolve Yes or No based on current information. You do not produce forecasts yourself."
            f"\n\nThe question is: {question}"
        )  # You can ask the searcher to filter by date, exclude/include a domain, and run specific searches for finding sources vs finding highlights within a source
        response = await searcher.invoke(prompt)
        return response

    # Revised DRE 5/31/2025 encourage forecast and probability precision of 1%
    # Modified from DRE 5/17/2025 prompt
    async def _run_forecast_on_binary(
        self, question: BinaryQuestion, research: str
    ) -> ReasonedPrediction[float]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster interviewing for a job.

            Your interview question is:
            {question.question_text}

            Question background:
            {question.background_info}


            This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
            {question.resolution_criteria}

            {question.fine_print}


            Your research assistant says:
            {research}

            Today is {datetime.now().strftime("%Y-%m-%d")}.
            
            1% precision
            You commit to forecast with 1% precision. This means you do not preferentially choose forecast probabilities
            of 5%, 10%, 15%, 20% etc. Instead you make your best forecast, allowing values such as 12%, 17%, 34%, 48%, 71%... 
            Particularly when aggregating several forecasts, this may result in a more accurate overall forecast.
            
            Before answering you write:
            (a) The time left until the outcome to the question is known.
            (b) The status quo outcome if nothing changed.
            (c) The expectations of experts and markets.
            (d) A brief description of a scenario that results in a No outcome.
            (e) A brief description of a scenario that results in a Yes outcome.

            You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.
            
            ************
            Group the evidence
            Review the evidence from your reseach assistant and group it into three buckets of approximately the same size:
            Bucket 1) Evidence that would indicate a relatively low forecast
            Bucket 2) Evidence that would indicate a relatively high forecast
            Bucket 3) Evidence that would indicate a central forecast
            
            ************
            Multi-world considerations
            Now you want to explore ranges of reasonable, possible forecasts, aiming for 1% precision. 
            You consider three worlds:
            1) Low_World: review the bucket 1 evidence from your reseach assistant that the forecast could be low.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            2) High_World: review the bucket 3 evidence from your reseach assistant that the forecast could be high.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            3) Mid_World: review the bucket 3 evidence from your reseach assistant that the forecast could be around the central views and trends.
            - What would an appropriate base rate be for this world:
            - What would be a low forecast estimate be for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate be for this world?
            
            ************
            Reference CSV
            Now, for future reference, make a CSV based on values from your multi-world reasoning.
            Headings: World_name, Base rate, Low Forecast, Mid Forecast, High Forecast
            Rows: Low_World, Mid_World, High_World
            
            ************
            Final expected distribution of reasonable forecasts
            You order the 9 estimates from low to high because you know that these values represent a range of resonable forecasts.
            
            Considering the 9 estimates ordered from low to high:
            - Project a distribution of reasonable forecasts
            - Make a CSV with percentiles of probability from P10 to p90 on increments of 10
            - Reflect on the 50th percentile and adjust as necessary
            - The 50th percentile is a good estimate of forecast probability, but you modify your final answer based on your analysis
            ************

            The last thing you write is your final answer as: "Probability: ZZ%", 0-100
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        prediction: float = PredictionExtractor.extract_last_percentage_value(
            reasoning, max_prediction=1, min_prediction=0
        )
        logger.info(
            f"Forecasted URL {question.page_url} as {prediction} with reasoning:\n{reasoning}"
        )
        return ReasonedPrediction(
            prediction_value=prediction, reasoning=reasoning
        )
    
    # DRE 6/1/2025 prompt: Multiworld, 1% precision
    # Built from Binary 5/31/2025 and Multiple Choice 5/17/2025 (revised)
    async def _run_forecast_on_multiple_choice(
        self, question: MultipleChoiceQuestion, research: str
    ) -> ReasonedPrediction[PredictedOptionList]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster interviewing for a job.

            Your interview question is:
            {question.question_text}

            The options are: 
            {question.options}


            Background:
            {question.background_info}

            {question.resolution_criteria}

            {question.fine_print}
            

            Your research assistant says:
            {research}

            Today is {datetime.now().strftime("%Y-%m-%d")}.
            
            1% precision
            You commit to forecast with 1% precision. This means you do not preferentially choose forecast probabilities
            of 5%, 10%, 15%, 20% etc. Instead you make your best forecast, allowing values such as 12%, 17%, 34%, 48%, 71%... 
            Particularly when aggregating several forecasts, this may result in a more accurate overall forecast.
            
            Before answering you write:
            (a) The time left until the outcome to the question is known.
            (b) The status quo outcome if nothing changed.
            (c) The expectations of experts and markets.
            
            You write your rationale remembering that (1) good forecasters put extra weight on the status quo outcome 
            since the world changes slowly most of the time, and (2) good forecasters leave some moderate probability
            on most options to account for unexpected outcomes.
            
            ************
            There are N options in this question, in this order:
            {question.options}
            
            At this stage, you treat each option as an independent, binary question. 
            
            For each option you conduct the following steps:
            
            You write:
            - The status quo outcome if nothing changed for the option.
            - The expectations of experts and markets for the option.
            - A brief description of a scenario that results in a No outcome for the option.
            - A brief description of a scenario that results in a Yes outcome for the option.
            
            Group the evidence for the option
            Review the evidence from your reseach assistant and group it into three buckets of approximately the same size:
            Bucket 1) Evidence that would indicate a relatively low forecast
            Bucket 2) Evidence that would indicate a relatively high forecast
            Bucket 3) Evidence that would indicate a central forecast
            
            Multi-world considerations for the option
            Now you want to explore ranges of reasonable possible forecasts. You consider three worlds:
            1) Low_World: review the bucket 1 evidence from your reseach assistant that the forecast could be low.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            2) High_World: review the bucket 3 evidence from your reseach assistant that the forecast could be high.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            3) Mid_World: review the bucket 3 evidence from your reseach assistant that the forecast could be around the central views and trends.
            - What would an appropriate base rate be for this world:
            - What would be a low forecast estimate be for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate be for this world?
            
            Reference Table for the option
            Now, for future reference, make a CSV based on values from your multi-world reasoning around the option.
            Headings: World_name, Base rate, Low Forecast, Mid Forecast, High Forecast
            Rows: Low_World, Mid_World, High_World
            
            You order the 9 estimates for the option from low to high because you know that these values represent a 
            range of resonable forecasts.
            
            Considering the 9 estimates ordered from low to high for the option
            - You use your judgment to make a table of with percentiles of probability
              from P10 to p90 on increments of 10
            - The 50th percentile is your preliminary estimate of probability for the option
            
            ************
            Consolidate and adjust the multiple choice option forecasts
            
            Sort the option probabilities from highest to lowest and reflect on:
            - The options should sum to 100%
            - Does the relative probability of each option make sense?
            - Does the status quo impact the probability?
            - Does evidence suggest moving away from the status quo?
            - Does the evidence indicate the preliminary probability should be adjusted?
            
            ************
            Final forecast
            
            You make your final and best forecast using any adjustments after reflection and remembering to report at 1% or 
            better precision.
            
            The last thing you write is your final probabilities for the N options in this order {question.options} as:
            Option_A: Probability_A
            Option_B: Probability_B
            ...
            Option_N: Probability_N
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        prediction: PredictedOptionList = (
            PredictionExtractor.extract_option_list_with_percentage_afterwards(
                reasoning, question.options
            )
        )
        logger.info(
            f"Forecasted URL {question.page_url} as {prediction} with reasoning:\n{reasoning}"
        )
        return ReasonedPrediction(
            prediction_value=prediction, reasoning=reasoning
        )
        
    # DRE 5/31/2025 Numeric enforcement building on 5/17/2025 prompt
    async def _run_forecast_on_numeric(
        self, question: NumericQuestion, research: str
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

            Units for answer: {question.unit_of_measure if question.unit_of_measure else "Not stated (please infer this)"}
            You write Units for the answer are: (whatever units you determined)

            Your research assistant says:
            {research}

            Today is {datetime.now().strftime("%Y-%m-%d")}.

            {lower_bound_message}
            {upper_bound_message}

            Formatting Instructions:
            - Please notice the units requested (e.g. whether you represent a number as 1,000,000 or 1 million).
            - Never use scientific notation.
            - Always start with a smaller number (more negative if negative) and then increase from there

            Before answering you write:
            (a) The time left until the outcome to the question is known.
            (b) The outcome if nothing changed.
            (c) The outcome if the current trend continued.
            (d) The expectations of experts and markets.
            (e) A brief description of an unexpected scenario that results in a low outcome.
            (f) A brief description of an unexpected scenario that results in a high outcome.

            You remind yourself that good forecasters are humble and set wide 90/10 confidence intervals to account for unknown unknowns.
            
            ************
            Group the evidence
            Review the evidence from your reseach assistant and group it into three buckets of approximately the same size:
            Bucket 1) Evidence that would indicate a relatively low forecast
            Bucket 2) Evidence that would indicate a relatively high forecast
            Bucket 3) Evidence that would indicate a central forecast
            
            ************
            Verify the Units for the answer, and write them here
            You check that those are the same units used above in questions (a), (b), (c), (d), (e), and (f)
            If the units are in agreement write "units confirmed"
            
            ************
            Multi-world considerations
            For this section, you are careful to report values in the confirmed units for answer
            You want to explore ranges of reasonable possibilities. You consider three worlds:
            1) Low_World: review the bucket 1 evidence from your reseach assistant that the forecast could be low.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            2) High_World: review the bucket 3 evidence from your reseach assistant that the forecast could be high.
            - What would an appropriate base rate be for this world?
            - What would be a low forecast estimate for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate for this world?
            3) Mid_World: review the bucket 3 evidence from your reseach assistant that the forecast could be around the central views and trends.
            - What would an appropriate base rate be for this world:
            - What would be a low forecast estimate be for this world?
            - What would be a mid forecast estimate for this world?
            - What would be a high forecast estimate be for this world? 

            ************
            Reference CSV
            Now, for future reference, make a CSV based on values from your multi-world reasoning.
            Headings: World_name, Base rate, Low Forecast, Mid Forecast, High Forecast
            Rows: Low_World, Mid_World, High_World
            
            ************
            You order the 9 estimates from low to high because you know that these values represent a reasonable range of outcomes.
            
            ************
            With those values in mind, you are careful to use the units for answer
            
            ************
            The last thing you write is your final answer as:
            "
            Percentile 10: XX
            Percentile 20: XX
            Percentile 40: XX
            Percentile 50: XX
            Percentile 60: XX
            Percentile 80: XX
            Percentile 90: XX
            "
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        prediction: NumericDistribution = (
            PredictionExtractor.extract_numeric_distribution_from_list_of_percentile_number_and_probability(
                reasoning, question
            )
        )
        logger.info(
            f"Forecasted URL {question.page_url} as {prediction.declared_percentiles} with reasoning:\n{reasoning}"
        )
        return ReasonedPrediction(
            prediction_value=prediction, reasoning=reasoning
        )
    
    def _create_upper_and_lower_bound_messages(
        self, question: NumericQuestion
    ) -> tuple[str, str]:
        if question.open_upper_bound:
            upper_bound_message = ""
        else:
            upper_bound_message = (
                f"The outcome can not be higher than {question.upper_bound}."
            )
        if question.open_lower_bound:
            lower_bound_message = ""
        else:
            lower_bound_message = (
                f"The outcome can not be lower than {question.lower_bound}."
            )
        return upper_bound_message, lower_bound_message


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
        description="Run the Q1TemplateBot forecasting system"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["tournament", "quarterly_cup", "test_questions"],
        default="tournament",
        help="Specify the run mode (default: tournament)",
    )
    args = parser.parse_args()
    run_mode: Literal["tournament", "quarterly_cup", "test_questions"] = (
        args.mode
    )
    assert run_mode in [
        "tournament",
        "quarterly_cup",
        "test_questions",
    ], "Invalid run mode"

    template_bot = TemplateForecaster(
        research_reports_per_question=1,
        predictions_per_research_report=8, #predictions_per_research_report=8,  # predictions_per_research_report=5
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=True,
        folder_to_save_reports_to=None,
        skip_previously_forecasted_questions=True,
        llms={  # choose your model names or GeneralLlm llms here, otherwise defaults will be chosen for you
                # naming style reminder: "metaculus/{anthropic or openai}/{model_name}".
            "default": GeneralLlm(
                model="metaculus/openai/o4-mini", #model="metaculus/openai/o4-mini",
                temperature=1,  # change to 1 because o4-mini only takes (1) temperature... error on run
                timeout=200,  #timeout=40
                allowed_tries=2,
            ),
            "summarizer": "metaculus/openai/o4-mini",  #"metaculus/openai/o4-mini", #"summarizer": "openai/gpt-4o-mini",
        },
    )

    if run_mode == "tournament":
        forecast_reports = asyncio.run(
            template_bot.forecast_on_tournament(
                MetaculusApi.CURRENT_AI_COMPETITION_ID, return_exceptions=True
            )
        )
    elif run_mode == "quarterly_cup":
        # The quarterly cup is a good way to test the bot's performance on regularly open questions. You can also use AXC_2025_TOURNAMENT_ID = 32564
        # The new quarterly cup may not be initialized near the beginning of a quarter
        template_bot.skip_previously_forecasted_questions = False
        forecast_reports = asyncio.run(
            template_bot.forecast_on_tournament(
                MetaculusApi.CURRENT_QUARTERLY_CUP_ID, return_exceptions=True
            )
        )
    elif run_mode == "test_questions":
        # Example questions are a good way to test the bot's performance on a single question
        EXAMPLE_QUESTIONS = [
            "https://www.metaculus.com/questions/3245/what-will-be-the-us-average-weekly-hours-of-all-employees-total-non-farm-private-in-october-2025/", # numeric
            #"https://www.metaculus.com/questions/36934/tariff-disappear-from-nyt-and-wsj-front-pages-before-jul-2025/", # binary
            #"https://www.metaculus.com/questions/36440/tour-de-france-2025-winner/", # multiple choice
            #"https://www.metaculus.com/questions/37522/control-of-gaza-strip-on-august-31-2025/", # multiple choice
            #"https://www.metaculus.com/questions/18677/member-country-leaves-brics-by-2035/", # binary
            #"https://www.metaculus.com/questions/578/human-extinction-by-2100/",  # Human Extinction - Binary
            #"https://www.metaculus.com/questions/14333/age-of-oldest-human-as-of-2100/",  # Age of Oldest Human - Numeric
            #"https://www.metaculus.com/questions/22427/number-of-new-leading-ai-labs/",  # Number of New Leading AI Labs - Multiple Choice
            #"https://www.metaculus.com/questions/36295/us-tariff-rate-on-goods-imported-into-us-at-yearend-2026/",  # new question chosen by me
        ]
        template_bot.skip_previously_forecasted_questions = False
        questions = [
            MetaculusApi.get_question_by_url(question_url)
            for question_url in EXAMPLE_QUESTIONS
        ]
        forecast_reports = asyncio.run(
            template_bot.forecast_questions(questions, return_exceptions=True)
        )
    TemplateForecaster.log_report_summary(forecast_reports)  # type: ignore
