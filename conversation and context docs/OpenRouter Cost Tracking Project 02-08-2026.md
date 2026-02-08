# OpenRouter Costing via Colab

## Current Status
https://colab.research.google.com/drive/1B3Ziof5MDraMH9pwWMYP8q5dQU-lgkyD#scrollTo=WcSY449zhfoY
- Tool gets a statistics json from OpenRouter api
- Then it displays available statisics
- The main value of interest is limit_remaining

## Desired Behavior
- Read a history spread sheet (probably google sheets, maybe excel)
    - get the prior balance (old limit_remaining)
	- get prior number of questions run (may have to track manually)
- Get new balance from api (limit_remaining)
- Optionally ask for number of questions forecast
- Calculate usage from last access
- Calculate cost per questions
- Report on screen: 
	- usage since last access
	- number of questions
	- average cost per questions
- Write to spreadsheet a new line with:
    - date-time
	- original balance 
	- remaining balance
	- total cost since inception
	- cost since last access
	- new question count since last session
	- avg cost/question since last access
	- question count since inception
	- avg cost/question since inception
	
## Notes
- need storarge spreadsheet, preferably on google drive
	
	