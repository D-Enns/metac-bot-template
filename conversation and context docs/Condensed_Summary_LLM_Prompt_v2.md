# Condensed Summary LLM Prompt - Version 2

This is the prompt that will be sent to `openrouter/openai/gpt-oss-120b:exacto` to generate condensed forecast summaries.

## Prompt Template

```python
async def _create_condensed_summary(
    self,
    full_explanation: str,
    aggregated_prediction: PredictionTypes,
    question: MetaculusQuestion,
    final_cost: float,
    time_spent_in_minutes: float
) -> str:
    """Use LLM to create intelligent condensed summary"""
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
    condensed = await summarizer_llm.invoke(prompt)

    return condensed
```

## Key Features

1. **Metadata Preserved**: All question metadata included at top
2. **Target Length**: 5,000-10,000 characters (50-80% reduction from full)
3. **Structured Output**: Clear sections that LLM must follow
4. **Consensus/Outliers**: Emphasizes showing agreement vs disagreement
5. **Links Preserved**: Instructs LLM to maintain website URLs
6. **Question Type Agnostic**: Works for binary, numeric, multiple choice, etc.
7. **Model**: Uses `openrouter/openai/gpt-oss-120b:exacto` for cost efficiency

## Cost Estimate

- Input: ~20k tokens (truncated full explanation) = $0.001
- Output: ~2,000 tokens (condensed summary at 10k chars) = $0.0048
- **Total per summary: ~$0.006** (very affordable)

## Next Steps

1. Review and approve this prompt
2. Add `"summarizer": "openrouter/openai/gpt-oss-120b:exacto"` to llms config in main.py
3. Implement `_create_condensed_summary()` method in dre_forecasting_tools.py
4. Modify `_create_comment()` to be async and use condensed version for posting
5. Test on a sample question
