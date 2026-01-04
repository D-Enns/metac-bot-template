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

# Import base bot class from main
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import SpringTemplateBot2026

logger = logging.getLogger(__name__)


class SpringTemplateBotExtended(SpringTemplateBot2026):
    """
    Extended version of ForecastBot with custom aggregation and forecast saving.

    Extensions:
    - GPR-based prediction aggregation
    - Enhanced forecast summary saving with metadata
    - Future: Condensed summary generation
    """

    ##################################### AGGREGATION OVERRIDE #####################################

    async def _aggregate_predictions(
        self,
        predictions: list,
        question: MetaculusQuestion,
    ):
        """
        Override framework's aggregation to use GPR for binary, numeric, and multiple choice questions.

        For binary questions: Apply GPR on all stored scenarios to get p50.
        For numeric questions: Apply GPR on all stored scenarios to get full distribution.
        For multiple choice questions: Apply GPR per option, then normalize.
        For other question types: Use default framework aggregation.
        """
        from forecasting_tools.data_models.questions import BinaryQuestion, NumericQuestion, MultipleChoiceQuestion
        from forecasting_tools.data_models.multiple_choice_report import PredictedOption

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

        # Multiple choice questions: GPR aggregation per option
        elif isinstance(question, MultipleChoiceQuestion) and self._multiple_choice_scenarios:
            # Check if we have enough scenarios (at least 9 per option)
            first_option = list(self._multiple_choice_scenarios.keys())[0]
            num_scenarios = len(self._multiple_choice_scenarios[first_option])

            logger.info(f"[GPR DEBUG] _aggregate_predictions called for MC question with {len(predictions)} predictions")
            logger.info(f"[GPR DEBUG] Using GPR aggregation on {num_scenarios} scenarios per option")

            if num_scenarios >= 9:
                # Run GPR aggregation
                gpr_results = self._gpr_aggregate_multiple_choice(self._multiple_choice_scenarios)

                # Convert to PredictedOptionList
                predicted_options = [
                    PredictedOption(option_name=opt, probability=prob)
                    for opt, prob in gpr_results.items()
                ]
                result = PredictedOptionList(predicted_options=predicted_options)

                # Clear scenarios after aggregation
                self._multiple_choice_scenarios = {}
                self._current_question_id = None
                self._current_call_number = 0

                logger.info(f"[GPR DEBUG] MC aggregation complete. Returning GPR result")
                return result
            else:
                logger.warning(
                    f"MC question has only {num_scenarios} scenarios per option (need >=9), "
                    f"using default framework aggregation"
                )

        # Fallback: Use default framework aggregation for other question types or insufficient scenarios
        logger.info(f"[GPR DEBUG] Using default aggregation for {type(question).__name__}")
        return await super()._aggregate_predictions(predictions, question)

    ##################################### FORECAST SUMMARY SAVING #####################################

    async def _create_condensed_summary(
        self,
        full_explanation: str,
        aggregated_prediction: PredictionTypes,
        question: MetaculusQuestion,
        final_cost: float,
        time_spent_in_minutes: float
    ) -> str:
        """Use LLM to create intelligent condensed summary (5-10k chars)"""
        from forecasting_tools.data_models.data_organizer import DataOrganizer

        # Get readable prediction for reference
        report_type = DataOrganizer.get_report_type_for_question_type(type(question))
        readable_prediction = report_type.make_readable_prediction(aggregated_prediction)

        # Get summarizer LLM
        summarizer_llm = self.get_llm("summarizer", "llm")

        # Get question metadata
        question_id = question.page_url.rstrip('/').split('/')[-1]
        units = getattr(question, 'unit_of_measure', None) or "N/A"
        tournament_slug, tournament_readable = self._get_tournament_name(question)
        question_type = self._get_question_type(question)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Create summarization prompt
        prompt = clean_indents(
            f"""
            You are an expert at condensing AI forecasting analyses into clear, concise summaries for Metaculus readers.

            **TASK:** Create a condensed forecast summary that preserves the key insights while being significantly shorter than the full analysis.

            **TARGET LENGTH:** 5,000-10,000 characters

            **OUTPUT STRUCTURE:**

            # FORECAST METADATA
            **Forecast ID**: q{question_id}
            **Question URL**: {question.page_url}
            **Question Type**: {question_type}
            **Units**: {units}
            **Tournament**: {tournament_readable}
            **Forecast Date**: {timestamp}
            **Bot Version**: {self.__class__.__name__}

            ---

            # SUMMARY FORECAST VALUES
            *Question*: {question.question_text}
            *Final Prediction*: {readable_prediction}
            *Total Cost*: ${round(final_cost, 4)} (estimated)
            *Time Spent*: {round(time_spent_in_minutes, 2)} minutes
            *Bot Name*: {self.__class__.__name__}

            ## Research Summary
            Compress the research findings into **3 headings with 2-3 bullet points each**. Focus on the most important facts and insights. **Include website links** from the original research.

            Example structure:
            ### [Topic Area 1]
            - Key finding with [link](url)
            - Supporting data point

            ### [Topic Area 2]
            - Important trend or pattern
            - Relevant context

            ### [Topic Area 3]
            - Critical consideration
            - Notable exception or caveat

            ## Forecaster Reasoning Part 1: Key Dimensions
            Concisely summarize the forecasters' analysis across these dimensions. For each, note **consensus** and any **outliers/disagreements**:

            1. **Time left until resolution:** [Consensus view and any disagreements]

            2. **Outcome if nothing changed (current value):** [Consensus and outliers]

            3. **Outcome if current trend continued:** [Consensus and outliers]

            4. **Expectations of experts and markets:** [Consensus and outliers]

            5. **Volatility history and expectations:** [Consensus and outliers]

            ## Forecaster Reasoning Part 2: Scenario Analysis
            Identify and summarize the main scenario groups/buckets that forecasters considered. Typically 3 groups (e.g., optimistic/baseline/pessimistic or low/medium/high). For each group, provide **~3 lines** covering:
            - Key characteristics of the scenario
            - Main assumptions
            - Probability weight or outcome range

            ### Scenario Group 1: [Name/Description]
            [3-line summary]

            ### Scenario Group 2: [Name/Description]
            [3-line summary]

            ### Scenario Group 3: [Name/Description]
            [3-line summary]

            ## Forecaster Reasoning Part 3: Final Synthesis
            Concisely summarize the **key points** that drove the final forecast across all forecasters. What were the most important considerations in arriving at the final prediction? (3-5 bullet points)

            ---
            *Methodology: Multi-world scenario analysis with Gaussian Process Regression aggregation*

            ---

            **IMPORTANT INSTRUCTIONS:**

            1. **Extract, don't fabricate:** Only use information present in the full analysis below
            2. **Preserve links:** Include all website URLs from the research section
            3. **Consensus vs Outliers:** Always note where forecasters agreed vs disagreed
            4. **Be specific:** Include numbers, dates, and concrete facts where available
            5. **Maintain technical accuracy:** Don't oversimplify to the point of losing meaning
            6. **Target 5,000-10,000 characters:** Be concise but complete
            7. **Use the exact metadata header shown above**

            **FULL FORECAST ANALYSIS TO CONDENSE:**

            {full_explanation[:20000]}

            ---

            Generate the condensed summary now, following the structure exactly as shown above.
            """
        )

        # Generate condensed summary
        logger.info("[CONDENSED] Generating condensed summary with LLM...")
        condensed = await summarizer_llm.invoke(prompt)
        logger.info(f"[CONDENSED] Generated condensed summary ({len(condensed)} characters)")

        return condensed

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

    def _get_question_type(self, question: MetaculusQuestion) -> str:
        """Get human-readable question type"""
        from forecasting_tools.data_models.questions import (
            BinaryQuestion,
            NumericQuestion,
            MultipleChoiceQuestion,
            DateQuestion,
            ConditionalQuestion
        )

        if isinstance(question, BinaryQuestion):
            return "Binary"
        elif isinstance(question, MultipleChoiceQuestion):
            return "Multiple Choice"
        elif isinstance(question, NumericQuestion):
            # Check if it's discrete (has specific options) or continuous
            if hasattr(question, 'options') and question.options:
                return "Discrete Numeric"
            return "Numeric"
        elif isinstance(question, DateQuestion):
            return "Date"
        elif isinstance(question, ConditionalQuestion):
            return "Conditional"
        else:
            return "Unknown"

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
        question_type = self._get_question_type(question)

        # Get units if available
        units = getattr(question, 'unit_of_measure', None) or "N/A"

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
            **Question Type**: {question_type}
            **Units**: {units}
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

    def _save_condensed_forecast_copy(
        self,
        condensed_explanation: str,
        question: MetaculusQuestion,
    ) -> None:
        """Save condensed forecast explanation"""
        reports_dir = Path("forecast_summaries")
        reports_dir.mkdir(parents=True, exist_ok=True)

        question_id = question.page_url.rstrip('/').split('/')[-1]
        tournament_slug, _ = self._get_tournament_name(question)

        counter = 1
        while True:
            filename = f"{question_id}_{tournament_slug}_condensed_{counter}.md"
            filepath = reports_dir / filename
            if not filepath.exists():
                break
            counter += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(condensed_explanation)

        logger.info(f"Saved condensed forecast to {filepath}")

    def _create_comment(
        self,
        question: MetaculusQuestion,
        research_prediction_collections: list[ResearchWithPredictions],
        aggregated_prediction: PredictionTypes,
        final_cost: float,
        time_spent_in_minutes: float,
    ) -> str:
        """
        Override to save both full and condensed forecasts locally.
        Posts condensed version to Metaculus, keeps full version in local storage.
        """
        import asyncio

        print("="*80)
        print("DEBUG: _create_comment in SpringTemplateBotExtended called!")
        print("="*80)
        logger.info("="*80)
        logger.info("CONDENSED SUMMARY: Starting _create_comment override")
        logger.info("="*80)

        # Generate full explanation
        full_explanation = super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        # Save full forecast locally
        print(f"DEBUG: Saving full forecast, length={len(full_explanation)}")
        logger.info(f"Saving full forecast, length={len(full_explanation)}")
        self._save_full_forecast_copy(full_explanation, question)

        # Generate condensed summary using LLM (run async function synchronously)
        print("DEBUG: Starting condensed summary generation...")
        logger.info("Starting condensed summary generation...")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._create_condensed_summary(
                            full_explanation,
                            aggregated_prediction,
                            question,
                            final_cost,
                            time_spent_in_minutes
                        )
                    )
                    condensed_explanation = future.result()
            else:
                # No event loop running, use asyncio.run
                condensed_explanation = asyncio.run(
                    self._create_condensed_summary(
                        full_explanation,
                        aggregated_prediction,
                        question,
                        final_cost,
                        time_spent_in_minutes
                    )
                )
            print(f"DEBUG: Condensed summary generated, length={len(condensed_explanation)}")
            logger.info(f"Condensed summary generated successfully, length={len(condensed_explanation)}")
        except Exception as e:
            print(f"DEBUG: ERROR generating condensed summary: {e}")
            logger.error(f"[CONDENSED] Error generating condensed summary: {e}")
            logger.info("[CONDENSED] Falling back to full explanation")
            condensed_explanation = full_explanation

        # Save condensed forecast locally
        print(f"DEBUG: Saving condensed forecast, length={len(condensed_explanation)}")
        logger.info(f"Saving condensed forecast, length={len(condensed_explanation)}")
        self._save_condensed_forecast_copy(condensed_explanation, question)

        # Return condensed version (this gets posted to Metaculus)
        print("DEBUG: Returning condensed version for Metaculus posting")
        logger.info("[CONDENSED] Returning condensed version for Metaculus posting")
        return condensed_explanation
