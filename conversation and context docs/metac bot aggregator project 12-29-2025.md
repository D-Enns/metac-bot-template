# Background: forecast_bot_aggregation_session_12-27-2025.md

# Project Overview

## Goal: Better performance in Metaculus Spring 2026 AI forecasting tournament by improving aggregation methods of multiple-scenario based forecasts on questions of different types (Binary, Numeric, Discrete, Multiple Choice)

### Scenarios are simply reasonable low-mid-high forecasts for a given set of news summaries.

### The scenarios are based on a prompt that differs by question type, resulting in a few forecasts per LLM run.

### Those multiple forecasts per LLM run are passed to an aggregator method to do something more sophisticated than the standard median, probably formation of a probability density function.


## Development Tactics

### Investigate and iterate the general multi-scenario approach using jupyter notebooks.

### Our development jupyter notebooks should be located at C:\Users\Donni\projects\metac_bot_Spring_2026\jupyter

### Our initial development will demand lower resources than the eventual production forecast bot. (e.g. Start with Binomial question type; 4 LLM runs instead of 5 or more; 3 scenarios per LLM run instead of 9; less verbose prompts)

### Testing and proof of concept in jupyter until near production.