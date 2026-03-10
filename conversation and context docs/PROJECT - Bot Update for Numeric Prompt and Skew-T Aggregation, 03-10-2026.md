# Metaculus Forecasting Bot Update for Numeric Prompt and Skew-T Aggregation, 03-10-2026

## Background
The Metaculus forecasting bot handles questions of different types (Binary, Multiple Choice, and Numeric). This update is focused on updating the Numeric Forecasts.

### Numeric Forecasts
Numeric forecasts assign produce a forecast distribution of potential outcomes. Assumption of the correct or compatible distribution improves the forecast quality. (And improper choice decreases the quality).

## Update 1: improve the forecast with model judgement
- The current prompt causes the LLM Model to explore multiple scenarios that could be reasonable outcomes
- The new prompt to be installed here asks the Model to use its own judgement about the potential shape of the distribution, before providing percentile values of the forecast that are subsequently fit with a Skew-T distribution.

### Task
Put the new Numeric prompt in place in main.py. The vetted and tested prompt is contained in "C:\Users\Donni\projects\metac_bot_Spring_2026\prompts\NUMERIC_prompt_NV03_03-09-2026.md

## Update 2: implement the new Skew-T Aggregation
- The current aggregation method is Probit, which assumes a normal distribution
- In this project, replace probit aggregation with Skew-T aggregation, which is more flexible

### Task 
Implement Skew-T aggregation in main.py, using code from C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter\012b_Metaculus_Bot_Testbed_NUMERIC_Probit_and_Skew-TNV03_03-10-2026.ipynb