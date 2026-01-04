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

    def _create_comment(
        self,
        question: MetaculusQuestion,
        research_prediction_collections: list[ResearchWithPredictions],
        aggregated_prediction: PredictionTypes,
        final_cost: float,
        time_spent_in_minutes: float,
    ) -> str:
        """
        Override to save full forecast locally before posting to Metaculus.
        The posted forecast remains unchanged.
        """
        full_explanation = super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        self._save_full_forecast_copy(full_explanation, question)

        return full_explanation
