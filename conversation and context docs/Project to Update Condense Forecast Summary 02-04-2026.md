# Project to Update Condensed Forecast Summary

## Project Purpose
After revising forecast methods, **Condensed Summaries** have behaved inconsistently. For example,
for some questions report the wrong aggregation method. Others don't condense the **full summary** at all.

## Purpose of the Condensed Forecast Summay
The condensed forecast provides a more digestible summary of key forecast elements than the
full summary.

## Background Documents (ask for these if not included in the prompt)

### /conversation and context docs/Forecast Bot Code Reorganization and Forecast Summary Customization Session 01-04-2026.md

### /conversation and context docs/Condensed_Summary_LLM_Prompt_v2.md


## Desired behavior

### Make a true condensed summary for all question types

### Include correct type of aggregation
If the metaculus

### Additional Desired Behavior

#### Brief headline at very top of summary
Aim for 3 to 6 word, tabloid style headline. Usually breathless and often with exclamation point.

#### Base rates
If base rate is discussed in the full summary, report base rate values here. Include range of
potential base rates discussed.

## Current issues
- Incorrect aggregation type reported
- Intermittent failure to condense the full summary (just returns the full summary)

## Code exploration
Please review code on https://github.com/D-Enns/metac-bot-template and https://github.com/Metaculus/forecasting-tools to determine for each question
type, where the full summaries reside, condensed summaries are made, and where aggregation occurs.
How will you determine the type of aggregation used? The likely locations are:
- main.py
- dre_forecasting_tools.py
- and the metaculus framework forecasting_tools.py


## Example Condensed Summary Issues

### Example 1

This **Binary** question summary reports **GPR** as the aggregation type. But the type used is **Median**.
If the metaculus forecast-tools framework is used, the method is **Median** for Binary questions. The additional
desire is to start with a **Headline** and add **base rate discussion** (if found in the full summary).
Note that the markdown style is not applied, but should be.
<br>
q_forc+bot's Prediction
11.4%
Feb 2, 2026
FORECAST METADATA
Forecast ID: q41908
Question URL: https://www.metaculus.com/questions/41908
Question Type: Binary
Units: N/A
Tournament: Spring Aib 2026
Forecast Date: 2026-02-02 17:07:42 UTC
Bot Version: SpringTemplateBotExtended
Aggregation Method: GPR

SUMMARY FORECAST VALUES
Question: Will the WHO Director-General declare a PHEIC for H5N1 before May 1, 2026?
Final Prediction: 11.4%
Total Cost: $0.3176 (estimated)
Time Spent: 1.59 minutes
Bot Name: SpringTemplateBotExtended

Research Summary
Recent WHO Achievements
In 2025, WHO secured over 900 million doses of influenza vaccines and responded to multiple health emergencies (source).
WHO managed to effectively coordinate responses despite severe funding cuts, emphasizing the need for robust global health systems (source).
Technological Advances in Health Security
Notable advancements include a promising nasal avian influenza vaccine, which has shown efficacy in animal trials (source).
WHO stressed on the importance of continuous investment in health infrastructure and pandemic preparedness, learning from experiences during the COVID-19 pandemic.
Future Considerations
Experts highlight the necessity for international collaboration to improve health security and equitable vaccine access.
The current global health landscape reflects efforts to enhance surveillance and response mechanisms, requiring constant vigilance.
Forecaster Reasoning Part 1: Key Dimensions
Time left until resolution: Consensus is low urgency as PHEIC declarations are infrequent; some forecasters believe the threat period is limited.
Outcome if nothing changed (current value): Most agree on a minimal chance (below 20%) for a declaration unless a significant outbreak occurs.
Outcome if current trend continued: Predominant belief that continued advancements in vaccine technology may mitigate severe avian flu threats.
Expectations of experts and markets: Experts generally align on low immediate risk; some disagree on the speed of WHO's decision-making process.
Volatility history and expectations: Forecasts indicate low volatility in decision-making; outliers caution about unexpected outbreaks influencing responses.
Forecaster Reasoning Part 2: Scenario Analysis
Scenario Group 1: Optimistic
Rapid development and deployment of the nasal vaccine lead to better control of H5N1 outbreaks.
Assumes enhanced international cooperation and funding for health crises.
Probability weight: 2-5%.
Scenario Group 2: Baseline
Moderate public health response with existing measures in place to monitor and control H5N1 sporadic cases.
Assumes WHO continues current operational status amidst funding challenges.
Probability weight: 10-15%.
Scenario Group 3: Pessimistic
An unexpected outbreak leads to increased WHO scrutiny and potential lockdowns; PHEIC is declared.
Relies on the emergence of virulent strains not adequately prepared for by current vaccine technology.
Probability weight: 20-35%.
Forecaster Reasoning Part 3: Final Synthesis
The final prediction predominantly reflects expert confidence in current vaccine effectiveness and global preparedness.
Funding cuts to WHO have strained operations but have not drastically altered the overall capacity to respond.
Consensus that without a significant event, prognosis for PHEIC declaration remains low (11.4%).
Collective vigilance on H5N1 remains crucial, yet current circumstances do not prompt immediate alarm.
Continuous advancements in technology are viewed as key to mitigating outbreak risks effectively.


### Example 2
This **Multiple Choice** question summary reports **GPR** as the aggregation type. But the type used is **Median**.
If the metaculus forecast-tools framework is used, the method is. Try to identify where that is defined
in the code. The additional desire is to start with a **Headline** and add **base rate discussion** (if found
in the full summary).
Note that the markdown style is not applied, but should be.
<br>
q_forc+bot's Prediction
Doesn't change: 45.2%
Decreases: 33.3%
...show full forecast
Feb 4, 2026
FORECAST METADATA
Forecast ID: q41995
Question URL: https://www.metaculus.com/questions/41995
Question Type: Multiple Choice
Units: N/A
Tournament: Unknown
Forecast Date: 2026-02-04 07:33:33 UTC
Bot Version: SpringTemplateBotExtended
Aggregation Method: GPR

SUMMARY FORECAST VALUES
Question: Will the interest in “opm” change between 2026-02-04 and 2026-02-15 according to Google Trends?
Final Prediction:

Increases: 21.5%
Doesn't change: 45.17%
Decreases: 33.33%
Total Cost: $0.3375 (estimated)
Time Spent: 1.62 minutes
Bot Name: SpringTemplateBotExtended

Research Summary
Generative Engine Optimization (GEO) Importance
GEO is essential due to the shift from traditional SEO to optimizing for AI-generated content summaries.
Key strategies involve creating structured, semantic content that is referenced by AI systems, essential for online visibility.
Google's AI Overview Influence
The rise of AI-generated overviews is leading to reduced user engagement with traditional search links, affecting publishers significantly.
Tools like SerpApi help track visibility in AI contexts, emphasizing the emerging need for specialized tracking and content optimization.
Impact on Publishers
A projected 43% traffic decline for publishers in three years, attributed to Google's transition to answer-focused interfaces.
Publishers must adapt to diversification across platforms to mitigate traffic losses and secure revenue streams.
Forecaster Reasoning Part 1: Key Dimensions
Time left until resolution: Consensus leans toward stability in trends over the next week, with some forecasters anticipating slight fluctuations.
Outcome if nothing changed (current value): Majority forecast no change; outliers expect a decrease due to external factors.
Outcome if current trend continued: Consensus suggests a widespread belief in maintaining current levels of interest without major shifts.
Expectations of experts and markets: General agreement on moderate growth; negligible disagreement on potential decreases.
Volatility history and expectations: Consensus on low volatility, although a minority see potential for external factors to induce changes.
Forecaster Reasoning Part 2: Scenario Analysis
Scenario Group 1: Positive Trends
Characterized by increased engagement driven by new marketing strategies.
Assumes effective use of GEO principles leading to higher search interest.
Estimated probability: 21.5%.
Scenario Group 2: Stagnation
Represents maintaining current interest levels amidst a backdrop of changing digital landscapes.
Relies on current user behavior not drastically adjusting.
Estimated probability: 45.17%.
Scenario Group 3: Negative Trends
Indicates declining interest due to oversaturation or shifts in user search behavior.
Assumes adverse effects from AI integration, jeopardizing traditional content visibility.
Estimated probability: 33.33%.
Forecaster Reasoning Part 3: Final Synthesis
Adoption of GEO strategies is critical as traditional SEO yields diminishing returns.
The rise of AI-driven search interfaces is diminishing direct website traffic, prompting a need for adaptive content strategies.
Forecasters exhibit concern over the implications of AI Overviews, suggesting a significant shift is underway in content visibility priorities.
Consensus on current interest levels indicates a balanced expectation of stability with cautious notes on potential declines.
Methodology: Multi-world scenario analysis with GPR aggregation

### Example 3: From https://www.metaculus.com/questions/41843/co2-emission-change-from-transport-2020-25/
**This Numeric Question is Correct.** It has a true condensed summary, and documents the correct 
type of aggregation. The additional desire is to start with a **Headline** and add **base rate discussion** (if found in the full summary).
Note that the markdown style is not applied, but should be.
<br>
 q_forc+bot's Prediction
7.39% (-6.76 - 21.5)
Feb 4, 2026
FORECAST METADATA
Forecast ID: q41843
Question URL: https://www.metaculus.com/questions/41843
Question Type: Numeric
Units: %
Tournament: Spring Aib 2026
Forecast Date: 2026-02-04 08:07:55 UTC
Bot Version: SpringTemplateBotExtended
Aggregation Method: Probit (R²=0.99)

SUMMARY FORECAST VALUES
Question: By how much will carbon dioxide emissions change from ground transportation globally between 2020 and 2025?
Final Prediction: Probability distribution:

1.00% chance of value below -40.967752
25.00% chance of value below -6.605097
50.00% chance of value below 7.425926
75.00% chance of value below 21.456949
99.00% chance of value below 50.009097
Total Cost: $0.3184 (estimated)
Time Spent: 1.54 minutes
Bot Name: SpringTemplateBotExtended

Research Summary
Trends in CO2 Emissions
Global CO2 emissions fell in 2020 due to the COVID-19 pandemic but require sustained efforts to meet Paris Agreement goals.
A concentration of emissions exists, with 32 companies responsible for over 50% of global fossil fuel emissions One Green Planet.
EU Regulations Impacting Emissions
Revised EU vehicle emissions regulations could allow up to 15% of high-emission internal combustion vehicles post-2035, increasing potential emissions.
The European Commission's new approach may lead to a 10% rise in CO2 emissions from vehicles between 2025 and 2050 de.marketscreener.com.
China's Coal Expansion
Despite a significant increase in renewable energy, China continues to expand coal-fired power capacity, risking climate goals for carbon neutrality by 2060.
Reports indicate a surge in coal projects, complicating efforts to stabilize emissions The Straits Times.
Forecaster Reasoning Part 1: Key Dimensions
Time left until resolution: Consensus is that the timeframe (2020-2025) is short for significant change; a few outliers believe 2025 will see substantial shifts accelerating emissions.
Outcome if nothing changed (current value): Most forecasters think emissions could stay stable, while a minority expects increases in certain regions due to regulatory rollbacks.
Outcome if current trend continued: Consensus views a potential moderate increase while some predict sharp declines, citing heightened green initiatives.
Expectations of experts and markets: General expectations anticipate a push towards reduced emissions, though several forecasters note push-back from traditional energy sectors.
Volatility history and expectations: Agreement exists on increasing volatility in emissions estimates, with divergent views on the role of individual countries and companies in future trends.
Forecaster Reasoning Part 2: Scenario Analysis
Scenario Group 1: Optimistic Scenario
The global emissions from transport could decrease, driven by aggressive green policies and shifts toward electric vehicles. Probability: 30% chance for decrease of more than 10%.

Scenario Group 2: Baseline Scenario
Moderate changes in emissions reflecting current regulations and expected market adaptations. Probability: 50% chance in the range of +5% to -5%.

Scenario Group 3: Pessimistic Scenario
A significant increase in emissions is anticipated due to regulatory rollbacks and continued reliance on fossil fuels. Probability: 20% chance for an increase above +10%.

Forecaster Reasoning Part 3: Final Synthesis
Key policies such as EU emissions regulations significantly influence transportation emissions forecasts.
Global economic activities post-pandemic may stabilize or increase emissions, contingent on governmental action.
Significant concentration of emissions sources emphasizes the need for accountability and policy reform, especially among major firms.
The interplay between renewable energy expansion and coal reliance in China complicates global emissions trajectories.
Regional variations in emissions trends require tailored policy responses to effectively mitigate climate impacts.
Methodology: Multi-world scenario analysis with Probit (R²=0.99) aggregation
