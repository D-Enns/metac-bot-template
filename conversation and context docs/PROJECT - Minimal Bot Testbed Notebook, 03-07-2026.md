# Minimal Bot Testbed Notebook Project
Make a jupyter notebook that performs the minimal viable forecasting functions outlined in this repo, given provided news summaries. 

## Details
My Metaculus Bot forecasts events in Metaculus forecasting tournaments. The purpose of this notebook is to improve my forecasting bot by serving as a testbed to try new forecasting approaches. The notebook should:
- Accept outside news summaries for analysis (they will be provided)
- Run in a jupyter notebood named: "012_Metaculus_Bot_Testbed_03-07-2026"
- Consist of code distilled and summarized from the local repo at "/c/Users/Donni/projects/metac_bot_Spring_2026"
- Use the OpenRouter API and my key to access necessary models (Key is in my Environment)
- Use my latest prompt for numeric questions (we will make seperate notebooks for different question types)

## Code Basis

### Strategy
- Other than LLM access, **all code must be local** and contained in the jupyter notebook. For instance, it should not be necessary to install metaculus forecasting-tools
- Necessary functions from from https://github.com/Metaculus/metac-bot-template or https://github.com/Metaculus/forecasting-tools should be replicated, streamlined, and placed in the notebook.
- No news gathering code should be in the notebook. News summaries will be an input to the notebook.

### Primary Sources
- main.py and dre_forecasting tools in "C:\Users\Donni\projects\metac_bot_Spring_2026"
- https://github.com/Metaculus/metac-bot-template
- https://github.com/Metaculus/forecasting-tools 

### Updating Mechanisms
- In the future it will be necessary to capture code updates from the Metaculus sources. Make a cell that outlines a procedure to do this on a regular basis.