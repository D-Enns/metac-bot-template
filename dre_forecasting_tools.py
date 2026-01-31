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
from scipy.integrate import quad
from scipy.interpolate import splrep, splev
from scipy.stats import linregress

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
from forecasting_tools.data_models.numeric_report import Percentile
from forecasting_tools.data_models.forecast_report import ResearchWithPredictions

# Import base bot class from main
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import SpringTemplateBot2026

logger = logging.getLogger(__name__)


##################################### PROBIT TRANSFORMATION FUNCTIONS #####################################

def _pdf_normal(z: float) -> float:
    """Standard normal probability density function."""
    return (1 / ((2 * np.pi))**0.5) * np.exp(-0.5 * (z**2))


def _pcntl_from_z(z: float) -> float:
    """Convert z-score to percentile by integrating normal PDF from -inf to z."""
    return quad(_pdf_normal, -np.inf, z)[0]


# Precompute z-spline lookup table at module load for performance
_Z_VALUES = np.arange(-7, 7.01, 0.01)
_PCNTL_VALUES = [_pcntl_from_z(z) for z in _Z_VALUES]
_Z_SPLINE = splrep(_PCNTL_VALUES, _Z_VALUES)


def _z_from_pcntl(percentile: float | np.ndarray) -> float | np.ndarray:
    """
    Convert percentile (0-1 scale) to z-score using precomputed spline.

    Args:
        percentile: Value(s) between 0 and 1

    Returns:
        Corresponding z-score(s)
    """
    return splev(percentile, _Z_SPLINE)


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

            # Save scenario data before clearing
            try:
                self._save_scenario_data(
                    scenarios=self._binary_scenarios,
                    question=question,
                    aggregated_result=gpr_result,
                    question_type="binary"
                )
            except Exception as e:
                logger.error(f"Error saving binary scenario data: {e}")

            # Clear scenarios after aggregation
            self._binary_scenarios = []
            self._current_question_id = None
            self._current_call_number = 0

            logger.info(f"[GPR DEBUG] Aggregation complete. Returning GPR result: {gpr_result:.4f}")
            return gpr_result

        # Numeric questions: Probit aggregation for full distribution
        elif isinstance(question, NumericQuestion) and len(self._numeric_scenarios) >= 9:
            logger.info(f"[PROBIT DEBUG] _aggregate_predictions called for numeric question with {len(predictions)} predictions")
            logger.info(f"[PROBIT DEBUG] Using Probit aggregation on {len(self._numeric_scenarios)} stored numeric scenarios")

            probit_distribution, r_squared = self._probit_aggregate_numeric(self._numeric_scenarios, question)

            # Save scenario data before clearing
            try:
                self._save_scenario_data(
                    scenarios=self._numeric_scenarios,
                    question=question,
                    aggregated_result=probit_distribution,
                    question_type="numeric"
                )
            except Exception as e:
                logger.error(f"Error saving numeric scenario data: {e}")

            # Clear scenarios after aggregation
            self._numeric_scenarios = []
            self._current_question_id = None
            self._current_call_number = 0

            logger.info(f"[PROBIT DEBUG] Numeric aggregation complete. Returning distribution with {len(probit_distribution.declared_percentiles)} percentiles (R²={r_squared:.4f})")
            return probit_distribution

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

                # Save scenario data before clearing
                try:
                    self._save_scenario_data(
                        scenarios=self._multiple_choice_scenarios,
                        question=question,
                        aggregated_result=result,
                        question_type="multiple_choice"
                    )
                except Exception as e:
                    logger.error(f"Error saving multiple choice scenario data: {e}")

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

    ##################################### PROBIT AGGREGATION FOR NUMERIC #####################################

    def _probit_aggregate_numeric(
        self,
        scenarios: list[float],
        question: NumericQuestion,
    ) -> tuple[NumericDistribution, float]:
        """
        Aggregate numeric scenarios using probit (normal) regression to create full CDF.

        The probit method fits a normal distribution by performing linear regression
        in z-score space, enabling smooth extrapolation to extreme percentiles (p01, p99)
        without edge artifacts.

        Args:
            scenarios: List of numeric values from multiple world scenarios
            question: The NumericQuestion being forecasted

        Returns:
            Tuple of (NumericDistribution with 21 percentiles, R² fit quality)
        """
        # Validate scenarios using parent class method (majority vote validation)
        validated_scenarios = self._validate_numeric_scenarios_majority_vote(scenarios)

        if len(validated_scenarios) < 9:
            logger.warning(
                f"⚠️  PROBIT FALLBACK: Only {len(validated_scenarios)} scenarios available. "
                f"Using empirical percentiles instead."
            )
            return self._empirical_distribution_fallback(validated_scenarios, question), 0.0

        # Sort scenarios and assign empirical percentiles
        data_sorted = np.sort(np.array(validated_scenarios))
        n = len(data_sorted)
        empirical_pctl = np.array(range(1, n + 1)) / (n + 1)  # 0-1 scale

        # Transform to z-space
        z_values = _z_from_pcntl(empirical_pctl)

        # Linear regression: value = slope * z + intercept
        slope, intercept, r_value, _, _ = linregress(z_values, data_sorted)
        r_squared = r_value ** 2

        # Store R² for use in summary
        self._last_probit_r2 = r_squared

        # Output percentiles: 1, 2, 3, ..., 97, 98, 99 (99 total) for smooth CDF
        output_pctls = list(range(1, 100))  # [1, 2, 3, ..., 97, 98, 99]

        # Generate output distribution
        output_z = _z_from_pcntl(np.array(output_pctls) / 100)
        output_values = [z * slope + intercept for z in output_z]

        # Get question bounds for clamping
        lower_bound = getattr(question, 'lower_bound', None)
        upper_bound = getattr(question, 'upper_bound', None)

        # Clamp values to question bounds if they exist
        if lower_bound is not None:
            output_values = [max(v, lower_bound) for v in output_values]
        if upper_bound is not None:
            output_values = [min(v, upper_bound) for v in output_values]

        # Create percentile list
        percentile_list = [
            Percentile(percentile=p/100, value=float(v))
            for p, v in zip(output_pctls, output_values)
        ]

        # Ensure strictly increasing values (required by NumericDistribution)
        percentile_list = self._ensure_strictly_increasing_percentiles(percentile_list)

        # Log fit quality
        fit_quality = "✓" if r_squared >= 0.85 else "⚠️ LOW FIT"
        logger.info(
            f"✅ Probit numeric aggregation: {len(validated_scenarios)} scenarios → {len(output_pctls)} percentiles"
        )
        logger.info(
            f"   Probit fit: slope={slope:.4f}, intercept={intercept:.4f}, R²={r_squared:.4f} {fit_quality}"
        )
        logger.info(
            f"   Distribution: p1={percentile_list[0].value:.2f}, "
            f"p50={percentile_list[49].value:.2f}, "
            f"p99={percentile_list[-1].value:.2f}"
        )

        if r_squared < 0.85:
            logger.warning(
                f"⚠️  LOW PROBIT FIT (R²={r_squared:.4f}): Data may not be normally distributed. "
                f"Consider reviewing scenarios for multimodality or skewness."
            )

        return NumericDistribution.from_question(percentile_list, question), r_squared

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

        # Get concise submitted forecast format
        submitted_forecast = self._format_submitted_forecast(aggregated_prediction, question)

        # Get summarizer LLM
        summarizer_llm = self.get_llm("summarizer", "llm")

        # Get question metadata
        question_id = question.page_url.rstrip('/').split('/')[-1]
        units = getattr(question, 'unit_of_measure', None) or "N/A"
        tournament_slug, tournament_readable = self._get_tournament_name(question)
        question_type = self._get_question_type(question)
        aggregation_method = self._get_aggregation_method_info(question)
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
            **Aggregation Method**: {aggregation_method}

            ---

            # SUMMARY FORECAST VALUES
            *Question*: {question.question_text}
            *Final Prediction*: {readable_prediction}
            *Submitted Forecast*: {submitted_forecast}
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
            *Methodology: Multi-world scenario analysis with {aggregation_method} aggregation*

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
        condensed = await summarizer_llm.invoke(prompt)

        return condensed

    def _format_submitted_forecast(
        self,
        aggregated_prediction: PredictionTypes,
        question: MetaculusQuestion
    ) -> str:
        """
        Format the submitted forecast in a concise, easy-to-scan format.

        Args:
            aggregated_prediction: The final aggregated prediction
            question: MetaculusQuestion object

        Returns:
            Formatted string like:
            - Binary: "65.32% probability"
            - Numeric: "p1=13.635; p5=13.955; p10=14.126; p25=14.412; p50=14.729; p75=15.047; p90=15.332; p95=15.503; p99=15.824"
            - Multiple Choice: "Option A: 43.21%; Option B: 37.45%; Option C: 19.34%"
        """
        from forecasting_tools.ai_models.basic_model_interfaces import BinaryQuestion, NumericQuestion, MultipleChoiceQuestion

        # Binary question
        if isinstance(question, BinaryQuestion):
            prob_percentage = float(aggregated_prediction) * 100
            return f"{prob_percentage:.4g}% probability"

        # Numeric question
        elif isinstance(question, NumericQuestion):
            # Extract key percentiles
            key_percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            percentile_parts = []

            if hasattr(aggregated_prediction, 'declared_percentiles'):
                for p in aggregated_prediction.declared_percentiles:
                    p_int = int(p.percentile * 100)
                    if p_int in key_percentiles:
                        # Format with 5 significant figures
                        value = float(p.value)
                        formatted_value = float(f"{value:.5g}")
                        percentile_parts.append(f"p{p_int}={formatted_value}")

            if percentile_parts:
                return "; ".join(percentile_parts)
            else:
                # Fallback if percentiles not available
                return str(aggregated_prediction)

        # Multiple choice question
        elif isinstance(question, MultipleChoiceQuestion):
            option_parts = []

            if hasattr(aggregated_prediction, 'predicted_options'):
                for opt in aggregated_prediction.predicted_options:
                    prob_percentage = float(opt.probability) * 100
                    option_parts.append(f"{opt.option_name}: {prob_percentage:.4g}%")

            if option_parts:
                return "; ".join(option_parts)
            else:
                # Fallback if options not available
                return str(aggregated_prediction)

        # Unknown question type
        else:
            return str(aggregated_prediction)

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

    def _get_aggregation_method_info(self, question: MetaculusQuestion) -> str:
        """
        Get aggregation method string with R² for numeric questions.

        Returns string like:
        - "Probit (R²=0.94)" for good fits
        - "Probit (R²=0.72 LOW FIT)" for poor fits
        - "GPR" for binary/multiple choice
        - "N/A" for other question types
        """
        from forecasting_tools.data_models.questions import (
            BinaryQuestion,
            NumericQuestion,
            MultipleChoiceQuestion,
        )

        if isinstance(question, NumericQuestion):
            r2 = getattr(self, '_last_probit_r2', None)
            if r2 is not None:
                if r2 >= 0.85:
                    return f"Probit (R²={r2:.2f})"
                else:
                    return f"Probit (R²={r2:.2f} LOW FIT)"
            return "Probit"
        elif isinstance(question, BinaryQuestion):
            return "GPR"
        elif isinstance(question, MultipleChoiceQuestion):
            return "GPR"
        else:
            return "N/A"

    def _save_full_forecast_copy(
        self,
        full_explanation: str,
        question: MetaculusQuestion,
        aggregated_prediction: PredictionTypes,
    ) -> None:
        """Save complete forecast explanation with enhanced metadata"""
        reports_dir = Path("forecast_summaries")
        reports_dir.mkdir(parents=True, exist_ok=True)

        question_id = question.page_url.rstrip('/').split('/')[-1]
        tournament_slug, tournament_readable = self._get_tournament_name(question)
        question_type = self._get_question_type(question)
        aggregation_method = self._get_aggregation_method_info(question)

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
            **Aggregation Method**: {aggregation_method}

            ---

            """
        )

        # Add submitted forecast after metadata
        submitted_forecast = self._format_submitted_forecast(aggregated_prediction, question)
        submitted_forecast_section = f"\n**Submitted Forecast**: {submitted_forecast}\n\n"

        complete_content = metadata_header + submitted_forecast_section + full_explanation

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

    def _save_scenario_data(
        self,
        scenarios: list | dict,
        question: MetaculusQuestion,
        aggregated_result: Any,
        question_type: str
    ) -> None:
        """
        Save individual scenario data from LLM runs as JSON.

        Args:
            scenarios: Raw scenario data (list for binary/numeric, dict for MC)
            question: MetaculusQuestion object
            aggregated_result: Final aggregated prediction
            question_type: Type of question (binary, numeric, multiple_choice)
        """
        import json

        reports_dir = Path("forecast_summaries")
        reports_dir.mkdir(parents=True, exist_ok=True)

        question_id = question.page_url.rstrip('/').split('/')[-1]
        tournament_slug, tournament_readable = self._get_tournament_name(question)

        # Find counter for this question (match the forecast summary counter)
        counter = 1
        while True:
            test_filename = f"{question_id}_{tournament_slug}_full_{counter}.md"
            test_filepath = reports_dir / test_filename
            if not test_filepath.exists():
                # Use this counter for scenarios file too
                break
            counter += 1

        # Create scenarios filename
        scenarios_filename = f"{question_id}_{tournament_slug}_scenarios_{counter}.json"
        scenarios_filepath = reports_dir / scenarios_filename

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Determine actual scenario count
        if question_type == "multiple_choice":
            # For MC, count scenarios per option (should be same for all)
            actual_count = len(next(iter(scenarios.values()))) if scenarios else 0
        else:
            actual_count = len(scenarios)

        # Calculate expected scenarios
        scenarios_per_prediction = 9  # Standard for 3x3 world matrix
        expected_count = self.predictions_per_research_report * scenarios_per_prediction

        # Build scenario data structure
        scenario_data = {
            "metadata": {
                "forecast_id": f"q{question_id}",
                "question_url": question.page_url,
                "question_text": question.question_text,
                "question_type": question_type,
                "tournament": tournament_readable,
                "tournament_slug": tournament_slug,
                "forecast_date": timestamp,
                "bot_version": self.__class__.__name__,
                "run_config": {
                    "predictions_per_research_report": self.predictions_per_research_report,
                    "scenarios_per_prediction": scenarios_per_prediction,
                    "expected_total_scenarios": expected_count,
                    "actual_total_scenarios": actual_count,
                    "all_scenarios_generated": (actual_count == expected_count)
                }
            },
            "scenarios": {},
            "aggregated_result": None,
            "summary": {}
        }

        # Add type-specific scenario data
        if question_type == "binary":
            scenario_data["scenarios"]["raw_values"] = scenarios  # List of probabilities (0-1)
            scenario_data["scenarios"]["num_scenarios"] = len(scenarios)
            scenario_data["aggregated_result"] = {
                "type": "probability",
                "value": float(aggregated_result),
                "percentage": f"{float(aggregated_result) * 100:.2f}%"
            }
            scenario_data["summary"] = {
                "min_probability": float(min(scenarios)),
                "max_probability": float(max(scenarios)),
                "mean_probability": float(np.mean(scenarios)),
                "median_probability": float(np.median(scenarios)),
                "std_probability": float(np.std(scenarios))
            }

            # Add submitted forecast
            prob_percentage = float(aggregated_result) * 100
            scenario_data["submitted_forecast"] = {
                "format": "probability",
                "value": float(aggregated_result),
                "display": f"{prob_percentage:.4g}% probability"
            }

        elif question_type == "numeric":
            scenario_data["scenarios"]["raw_values"] = scenarios  # List of numeric values
            scenario_data["scenarios"]["num_scenarios"] = len(scenarios)
            scenario_data["metadata"]["units"] = getattr(question, 'unit_of_measure', 'N/A')
            scenario_data["metadata"]["aggregation_method"] = "probit"

            # Add probit R² if available
            probit_r2 = getattr(self, '_last_probit_r2', None)
            if probit_r2 is not None:
                scenario_data["metadata"]["probit_r_squared"] = round(probit_r2, 4)
                scenario_data["metadata"]["probit_fit_quality"] = "good" if probit_r2 >= 0.85 else "low"

            # Get percentiles from aggregated result
            if hasattr(aggregated_result, 'declared_percentiles'):
                percentiles_dict = {
                    f"p{int(p.percentile * 100)}": float(p.value)
                    for p in aggregated_result.declared_percentiles
                }
                scenario_data["aggregated_result"] = {
                    "type": "distribution",
                    "aggregation_method": "probit",
                    "percentiles": percentiles_dict
                }
            else:
                scenario_data["aggregated_result"] = {
                    "type": "distribution",
                    "value": str(aggregated_result)
                }

            scenario_data["summary"] = {
                "min_value": float(min(scenarios)),
                "max_value": float(max(scenarios)),
                "mean_value": float(np.mean(scenarios)),
                "median_value": float(np.median(scenarios)),
                "std_value": float(np.std(scenarios))
            }

            # Add submitted forecast
            key_percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            submitted_dict = {}
            if hasattr(aggregated_result, 'declared_percentiles'):
                for p in aggregated_result.declared_percentiles:
                    p_int = int(p.percentile * 100)
                    if p_int in key_percentiles:
                        # Format with 5 significant figures
                        submitted_dict[f"p{p_int}"] = float(f"{float(p.value):.5g}")

            scenario_data["submitted_forecast"] = {
                "format": "percentiles",
                "percentiles": submitted_dict,
                "display": "; ".join([f"{k}={v}" for k, v in submitted_dict.items()])
            }

        elif question_type == "multiple_choice":
            # scenarios is a dict mapping option names to lists of probabilities
            scenario_data["scenarios"]["by_option"] = {
                option: {
                    "raw_probabilities": probs,
                    "num_scenarios": len(probs)
                }
                for option, probs in scenarios.items()
            }

            # Get aggregated result per option
            if hasattr(aggregated_result, 'predicted_options'):
                aggregated_probs = {
                    opt.option_name: float(opt.probability)
                    for opt in aggregated_result.predicted_options
                }
            else:
                aggregated_probs = {}

            scenario_data["aggregated_result"] = {
                "type": "multiple_choice",
                "probabilities": aggregated_probs
            }

            # Summary stats per option
            scenario_data["summary"]["by_option"] = {
                option: {
                    "min_probability": float(min(probs)),
                    "max_probability": float(max(probs)),
                    "mean_probability": float(np.mean(probs)),
                    "median_probability": float(np.median(probs)),
                    "std_probability": float(np.std(probs))
                }
                for option, probs in scenarios.items()
            }

            # Add submitted forecast
            submitted_dict = {}
            if hasattr(aggregated_result, 'predicted_options'):
                submitted_dict = {
                    opt.option_name: f"{float(opt.probability) * 100:.4g}%"
                    for opt in aggregated_result.predicted_options
                }

            scenario_data["submitted_forecast"] = {
                "format": "multiple_choice",
                "probabilities": submitted_dict,
                "display": "; ".join([f"{k}: {v}" for k, v in submitted_dict.items()])
            }

        # Save to JSON file
        with open(scenarios_filepath, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved scenario data to {scenarios_filepath}")

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

        logger.info("Creating forecast comment with condensed summary generation")

        # Generate full explanation
        full_explanation = super()._create_comment(
            question,
            research_prediction_collections,
            aggregated_prediction,
            final_cost,
            time_spent_in_minutes
        )

        # Save full forecast locally
        self._save_full_forecast_copy(full_explanation, question, aggregated_prediction)

        # Generate condensed summary using LLM (run async function synchronously)
        logger.info("Generating condensed summary...")
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
            logger.info(f"Condensed summary generated ({len(condensed_explanation)} chars)")
        except Exception as e:
            logger.error(f"Error generating condensed summary: {e}")
            logger.warning("Falling back to full explanation for posting")
            condensed_explanation = full_explanation

        # Save condensed forecast locally
        self._save_condensed_forecast_copy(condensed_explanation, question)

        # Return condensed version (this gets posted to Metaculus)
        logger.info("Returning condensed summary for Metaculus posting")
        return condensed_explanation
