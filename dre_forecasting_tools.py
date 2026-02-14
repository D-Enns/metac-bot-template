"""
Custom extensions to Metaculus forecasting-tools library
Author: Dre
Date: January 4, 2026
"""

import json
import logging
import sys
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
    - Probit aggregation for numeric, framework defaults for binary/MC
    - Enhanced forecast summary saving with metadata
    - Question pipeline diagnostics for missed forecast investigation
    """

    # Stores diagnostics from all tournament runs in a session
    _run_diagnostics: list[dict] = []

    ##################################### QUESTION PIPELINE DIAGNOSTICS #####################################

    async def forecast_on_tournament(
        self,
        tournament_id: int | str,
        return_exceptions: bool = False,
    ):
        """
        Override framework's forecast_on_tournament to add question pipeline diagnostics.

        Wraps the standard flow with detailed logging of:
        - How many questions the API returns (and their types)
        - Which are marked already_forecasted
        - Which will actually be attempted
        - Results: successes vs failures
        """
        from forecasting_tools.helpers.metaculus_api import MetaculusApi

        # Fetch questions (same as framework)
        questions = MetaculusApi.get_all_open_questions_from_tournament(tournament_id)

        # Build per-question diagnostic data
        question_details = []
        by_type = {}
        for q in questions:
            q_type = type(q).__name__
            by_type[q_type] = by_type.get(q_type, 0) + 1
            q_id = getattr(q, 'id_of_post', '?')
            q_text = (q.question_text or "")[:80]
            question_details.append({
                "id": q_id,
                "type": q_type,
                "already_forecasted": q.already_forecasted,
                "text": q_text,
            })

        unforecasted = [q for q in questions if not q.already_forecasted]
        skipped = [q for q in questions if q.already_forecasted]

        # Log diagnostic summary
        logger.info(f"{'='*60}")
        logger.info(f"QUESTION PIPELINE: Tournament {tournament_id}")
        logger.info(f"Total open questions from API: {len(questions)}")
        logger.info(f"By type: {by_type}")
        for d in question_details:
            logger.info(f"  Q{d['id']} [{d['type']}] forecasted={d['already_forecasted']} | {d['text']}")
        logger.info(f"Already forecasted (will skip): {len(skipped)}")
        logger.info(f"Unforecasted (will attempt): {len(unforecasted)}")
        for q in unforecasted:
            q_id = getattr(q, 'id_of_post', '?')
            logger.info(f"  ATTEMPT: Q{q_id} [{type(q).__name__}]")
        logger.info(f"{'='*60}")

        # Run the standard forecast pipeline
        results = await self.forecast_questions(questions, return_exceptions)

        # Inspect results
        result_details = self._inspect_results(results, tournament_id)

        # Store diagnostics for this tournament run
        run_diag = {
            "tournament_id": str(tournament_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_open_questions": len(questions),
            "by_type": by_type,
            "already_forecasted": len(skipped),
            "attempted": len(unforecasted),
            "questions": question_details,
            "results": result_details,
        }
        self._run_diagnostics.append(run_diag)

        return results

    def _inspect_results(
        self,
        results: list,
        tournament_id: int | str,
    ) -> dict:
        """
        Inspect forecast results, separating successes from failures.
        Logs summary with GitHub Actions annotations for failures.
        """
        from forecasting_tools.data_models.forecast_report import ForecastReport

        successes = []
        failures = []
        for r in results:
            if isinstance(r, BaseException):
                failures.append({
                    "type": type(r).__name__,
                    "message": str(r)[:500],
                })
            elif isinstance(r, ForecastReport):
                q_id = getattr(r.question, 'id_of_post', '?')
                successes.append({
                    "question_id": q_id,
                    "question_type": type(r.question).__name__,
                })

        logger.info(f"RESULTS for tournament {tournament_id}: "
                     f"{len(successes)} successes, {len(failures)} failures")

        for s in successes:
            logger.info(f"  SUCCESS: Q{s['question_id']} [{s['question_type']}]")

        for f in failures:
            logger.warning(f"  FAILURE: {f['type']}: {f['message']}")
            # GitHub Actions annotation
            print(f"::warning::Forecast failure in tournament {tournament_id}: "
                  f"{f['type']}: {f['message'][:200]}")

        return {
            "successes": successes,
            "failures": failures,
        }

    def write_diagnostics_json(self) -> Path:
        """
        Write accumulated diagnostics to forecast_summaries/run_diagnostics.json.
        Called at end of script to capture all tournament runs.
        """
        reports_dir = Path("forecast_summaries")
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / "run_diagnostics.json"

        output = {
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "tournaments": self._run_diagnostics,
            "summary": self._build_diagnostics_summary(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, default=str)

        logger.info(f"Wrote run diagnostics to {filepath}")
        return filepath

    def _build_diagnostics_summary(self) -> dict:
        """Build a summary across all tournament runs."""
        total_open = sum(d["total_open_questions"] for d in self._run_diagnostics)
        total_already = sum(d["already_forecasted"] for d in self._run_diagnostics)
        total_attempted = sum(d["attempted"] for d in self._run_diagnostics)
        total_successes = sum(len(d["results"]["successes"]) for d in self._run_diagnostics)
        total_failures = sum(len(d["results"]["failures"]) for d in self._run_diagnostics)

        return {
            "total_open_questions": total_open,
            "total_already_forecasted": total_already,
            "total_attempted": total_attempted,
            "total_successes": total_successes,
            "total_failures": total_failures,
        }

    def get_exit_code(self) -> int:
        """
        Determine exit code based on diagnostics.
        Returns 1 if questions were attempted and ALL failed, 0 otherwise.
        """
        summary = self._build_diagnostics_summary()
        if summary["total_attempted"] > 0 and summary["total_successes"] == 0:
            logger.error(
                f"ALL {summary['total_failures']} forecast attempts failed. Exiting with code 1."
            )
            return 1
        return 0

    ##################################### AGGREGATION OVERRIDE #####################################

    async def _aggregate_predictions(
        self,
        predictions: list,
        question: MetaculusQuestion,
    ):
        """
        Override framework's aggregation to use Probit for numeric questions.

        For binary questions: Use default framework median aggregation.
        For numeric questions: Apply Probit aggregation on all stored scenarios to get full distribution.
        For multiple choice questions: Use default framework per-option mean with normalization.
        For other question types: Use default framework aggregation.
        """
        from forecasting_tools.data_models.questions import BinaryQuestion, NumericQuestion, MultipleChoiceQuestion
        from forecasting_tools.data_models.multiple_choice_report import PredictedOption

        # Numeric questions: Probit aggregation for full distribution
        if isinstance(question, NumericQuestion) and len(self._numeric_scenarios) >= 9:
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

        # Fallback: Use default framework aggregation for binary, multiple choice, and other question types
        logger.info(f"[AGG DEBUG] Using default aggregation for {type(question).__name__}")
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

            # [HEADLINE]
            A 3–6 word tabloid-style headline. Usually breathless, often ends with an exclamation point.
            Example: "WHO Declaration Looks Unlikely!"

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
            *Total Cost*: ${round(final_cost, 4)} (estimated)
            *Time Spent*: {round(time_spent_in_minutes, 2)} minutes
            *Bot Name*: {self.__class__.__name__}

            ## Research Summary
            Compress the research findings into **3 headings with 2-3 bullet points each**. Focus on the most important facts and insights. **Include website links** from the original research.
            If base rates or historical analogs are discussed anywhere in the full analysis, include the values and any range in this section (or as a short note just below the headline). If none are discussed, omit entirely.

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
            8. **Use proper markdown formatting throughout** — `#` for headers, `**text**` for bold, bullet lists with `-`, etc.

            **FULL FORECAST ANALYSIS TO CONDENSE:**

            {full_explanation[:20000]}

            ---

            Generate the condensed summary now, following the structure exactly as shown above.
            """
        )

        # Generate condensed summary
        condensed = await summarizer_llm.invoke(prompt)

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

    def _get_aggregation_method_info(self, question: MetaculusQuestion) -> str:
        """
        Get aggregation method string with R² for numeric questions.

        Returns string like:
        - "Probit (R²=0.94)" for good fits
        - "Probit (R²=0.72 LOW FIT)" for poor fits
        - "Median" for binary, "per Option Mean, (normalized)" for multiple choice
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
            return "Median"
        elif isinstance(question, MultipleChoiceQuestion):
            return "per Option Mean, (normalized)"
        else:
            return "N/A"

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
        self._save_full_forecast_copy(full_explanation, question)

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

            # Post-generation validation: warn if condensation may not have occurred
            if len(condensed_explanation) > 0.75 * len(full_explanation):
                logger.warning(
                    f"Condensation may not have occurred: condensed={len(condensed_explanation)} chars, "
                    f"full={len(full_explanation)} chars (ratio={len(condensed_explanation)/len(full_explanation):.2f})"
                )
            if "# " not in condensed_explanation:
                logger.warning(
                    f"Condensed summary missing markdown headers (no '# ' found in {len(condensed_explanation)} chars)"
                )
        except Exception as e:
            logger.error(f"Error generating condensed summary: {e}")
            logger.warning("Falling back to full explanation for posting")
            condensed_explanation = full_explanation

        # Save condensed forecast locally
        self._save_condensed_forecast_copy(condensed_explanation, question)

        # Return condensed version (this gets posted to Metaculus)
        logger.info("Returning condensed summary for Metaculus posting")
        return condensed_explanation
