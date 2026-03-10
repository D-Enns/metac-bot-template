# Metaculus API Data Extraction - Session Summary

**Date:** 2026-01-26
**Project:** Extracting forecast question data from Metaculus AI Benchmark
**Status:** Planning phase - Ready to begin API implementation

---

## Objective

Extract data from hundreds of Metaculus forecast question pages from the Spring AIB 2026 tournament. Each page contains a different forecast question with associated metadata (question text, resolution criteria, dates, forecasts, etc.).

---

## Problem & Approach Evolution

### Initial Attempts (FAILED)
1. **WebFetch tool** - Returned 403 Forbidden
2. **curl command** - Blocked by Cloudflare challenge page ("Just a moment...")
   - Cloudflare requires JavaScript execution to verify not a bot
   - Simple HTTP requests cannot bypass this

### Considered Approaches (ABANDONED)
1. **Screenshot + OCR Pipeline**
   - Use headless Chrome to screenshot pages
   - Apply OCR (Tesseract/pytesseract) to extract text
   - Issues:
     - Accuracy concerns with OCR
     - Processing hundreds of images would be slow
     - Text extraction from images less reliable than structured data

2. **Browser Automation (Playwright/Selenium)**
   - Would work to bypass Cloudflare
   - But raised ToS concerns about scraping

---

## SOLUTION: Official Metaculus API ✅

### Key Discovery
Found the AI Benchmark Resources page (saved locally):
- **Location:** `/mnt/c/Users/Donni/projects/metac_ques_pages/materials/AIB Resources Page_save 01-26-2026.html`

### Important Resources Identified

**1. Metaculus API**
- **URL:** https://metaculus.com/api
- Official API endpoint for programmatic access
- This is the ToS-compliant way to access data

**2. Official Bot Templates & Tools**
- **Bot Template:** https://github.com/Metaculus/metac-bot-template
- **Forecasting Tools:** https://github.com/Metaculus/forecasting-tools
  - Contains `run_bots.py` for interacting with questions
- These show how to properly interact with Metaculus API

**3. Authentication**
- Requires Metaculus token for API access
- Bot account creation is supported and documented

---

## Tournament Context

**Spring AIB 2026 Tournament**
- URL pattern: `https://www.metaculus.com/tournament/spring-aib-2026/?order_by=-open_time&page=10`
- Multiple pages of questions
- Question formats: Binary, Numeric, Discrete, Multiple-choice
- Scored using Brier score
- Community of bot makers already using API access

**Why This Approach is Legitimate:**
1. Metaculus explicitly provides API access
2. They offer bot templates for automated interaction
3. AI Benchmark tournaments are designed for programmatic access
4. They provide free LLM/API credits for participants

---

## System Environment

**Working Directory:** `/mnt/c/Users/Donni/projects/metac_ques_pages`

**Directory Structure:**
- `conversations/` - Session summaries and notes
- `materials/` - Saved HTML resources
- `html_as_text/` - Extracted text output
- `product/` - Final output
- `skills/` - Custom scripts/tools

**Available Tools:**
- Python 3.12.3 installed
- pip NOT currently installed (but can be added)
- WSL2 environment (Linux on Windows)
- Chrome available on Windows side

---

## Next Steps

### 1. Investigate Metaculus API
- [ ] Access and read API documentation at https://metaculus.com/api
- [ ] Identify endpoints for:
  - Listing tournament questions
  - Fetching individual question details
  - Getting question metadata (title, description, resolution criteria, dates)

### 2. Review Bot Template Code
- [ ] Clone or examine https://github.com/Metaculus/metac-bot-template
- [ ] Study how it authenticates with API
- [ ] Understand data structures returned by API
- [ ] Identify relevant code for fetching question lists

### 3. Authentication Setup
- [ ] Create bot account on Metaculus (if not already done)
- [ ] Generate Metaculus API token
- [ ] Store credentials securely

### 4. Develop Extraction Script
- [ ] Install required Python packages (requests, etc.)
- [ ] Write script to:
  - Authenticate with Metaculus API
  - Fetch list of questions from Spring AIB 2026 tournament
  - Extract relevant fields from each question
  - Save data in structured format (JSON/CSV)
  - Handle pagination (multiple pages of questions)
  - Implement rate limiting/delays to be respectful

### 5. Data Structure Planning
Determine what fields to extract from each question:
- Question ID
- Question title/text
- Question type (binary, numeric, discrete, multiple-choice)
- Resolution criteria
- Open/close dates
- Current community prediction
- Background information
- Related questions
- Tags/categories

---

## Questions to Resolve

1. **API Rate Limits:** What are the API rate limits? Need to implement appropriate delays.
2. **Authentication:** Do we already have a Metaculus account/token?
3. **Data Format:** What output format is preferred? (JSON, CSV, database, etc.)
4. **Question Filtering:** Should we extract ALL questions or filter by:
   - Status (open/closed/resolved)
   - Date range
   - Question type
   - Specific pages
5. **Historical Data:** Do we need historical forecast data or just current question details?

---

## Useful Links for Reference

- **AI Benchmark Resources:** https://www.metaculus.com/notebooks/38928/ai-benchmark-resources/
- **API Docs:** https://metaculus.com/api
- **Bot Template Repo:** https://github.com/Metaculus/metac-bot-template
- **Forecasting Tools Repo:** https://github.com/Metaculus/forecasting-tools
- **Tournament Page:** https://www.metaculus.com/tournament/spring-aib-2026/

---

## Technical Notes

- Cloudflare protection prevents simple HTTP scraping
- API access is the intended method for programmatic interaction
- Bot makers community is active and supported
- Free credits available for participants
- Discord channel: "build-a-forecasting-bot" for questions
- Contact: ben [at] metaculus [.com]

---

## Summary

We've confirmed that Metaculus provides official API access for extracting question data, making web scraping unnecessary and ensuring ToS compliance. The next phase involves setting up API authentication and developing a Python script to systematically extract question data from the Spring AIB 2026 tournament.
