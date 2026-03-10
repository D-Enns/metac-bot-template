forecast_prompt = f"""
# Make a Professional Forecast

## You are a professional forecaster interviewing for a job.

## Your interview question is:
{question['title']}

## Question background:
{question['description']}

{question['resolution_criteria']}

{question['fine_print']}

{lower_bound_message}
{upper_bound_message}

## Units for answer:
{question['unit'] if question['unit'] else 'Not stated (please infer this)'}
- You are careful to make sure you forecast units are consistent with the upper and lower bound units
- You write Units for the answer are: (whatever units you determined)

## Your research assistant says:
{news_summary}

## Today is {datetime.now().strftime('%Y-%m-%d')}.
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