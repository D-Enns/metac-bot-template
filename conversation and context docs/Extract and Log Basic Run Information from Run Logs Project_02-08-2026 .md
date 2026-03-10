# Make Run and Question Log from Workflow Runs in GitHub Actions

## Background
- I have a bot in the Spring 2026 AI Forecasting Benchmark Tournament 
	- https://www.metaculus.com/tournament/spring-aib-2026/ TL;DR
- The bot runs periodically (currently every 20 minutes) in GitHub Actions
    - https://github.com/D-Enns/metac-bot-template/actions
- For each workflow run, a forecast_job file is available
- Within forecast_job, "Run bot" contains most or all of the information that we need
	- an exception may be the run number. It is part of the run name, e.g. Dre Tournament Bot #1220

## Desired Behavior
Summarize key data in an excel "log" containing one row for each Run.

### Excel Log Contents (columns)
- workflow run number (from workflow run title?)
- time-date: from "Run bot"
	- first time date present in file, usually aroun line 21
- **Is there a question to forecast? Y/N**	
	- Runs without a question to forecast are more common than those with questions 
	- There will not be a line saying "Found Research for URL" in "Run bot"
- question number: from "Run bot"
	- typical form: https://www.metaculus.com/questions/41851:
	- question number for this example is 41851
	- "None" if there is no question
- forecast value (if there is a question, "None" if not)
	- "None" if there is no question
		- there will not be a line that says 
	- May be a single probability (for question type "Binary"), e.g.:
        - **Probability: 1.8%**
	- A list of values (for Multiple Choice questions), e.g.:
		- Immediately below "# Final Answer": [2.45, 2.60, 2.75, 2.75, 2.88, 3.05, 3.05, 3.30, 3.90]
	- For Numeric questions
	    - Immediately below "# Final Answer": [2.45, 2.60, 2.75, 2.75, 2.88, 3.05, 3.05, 3.30, 3.90]
- error? If there is error flag that prevents the forecast.
    - Watch for "Error: Process completed with exit code 1." in Run bot
	
### Write the results excel file to 
"C:/Users/Donni/projects/metac_bot_Spring_2026/products" folder with name "Runs and Question Numbers.xlsx"



