# Fix Missed Questions Part 2
Between 10% and 30% of questions do not receive a forecast.

## Previous session
C:\Users\Donni\projects\metac_bot_Spring_2026\conversation and context docs\Diagnostic Results and Fixes Session 02-14-2026.md

### Questions are still missed, but not as frequently
As of 03/06/2026

## Comments from other Users\Donni\projects\metac_bot_Spring_2026\conversation

- "i've started getting lots of 429 errors hitting the api just to see if there are open questions that i haven't forecast in the two bot tournaments - as such i missed basically all the minibot questions until i noticed the problem and started doing manual runs. is anyone else experiencing this?"

- "Nope you must be accidentally hitting the api way too much"

- "fine for me (polling both tournaments every 5 minutes)"

- "i don't see anything unusual or excessive in what i'm doing, when I read my logs on GH actions, almost every time I call the API I get a 429"

- **"do you have sleep? 1 second between calls is enough; maybe mock it and measure some statistics (max calls per second etc)"**

- **"@smingers that would be my first thought. The bots we are running in production are doing fine, and it seems other bot makers aren't experiencing a problem, so I'm guessing that you are not waiting long enough between calls. Our rate limit is 8 requests per 10 seconds. The MetaculusCllient from forecasting-tools handles this automatically."**

### The solution may be in MetaculusCllient from https://github.com/Metaculus/forecasting-tools
One of the tournament runners suggested this in the comment above

## Investigate other possibilities
Could there be other issues causing the missed question problem?
