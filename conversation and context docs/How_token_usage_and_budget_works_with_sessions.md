# How Token Usage and Budget Works with Sessions

**Date:** December 27, 2025
**Topic:** Understanding Claude Code token budgets, context windows, and working over extended periods

---

## Conversation Summary

This document explains how token budgets work in Claude Code, the difference between token budget and context window, and strategies for working on long-term projects over weeks or months.

---

## Q&A Session

### User Question 1
```
how many tokens have I used today?
```

### Response
Based on the current session, you've used **51,570 tokens** out of your 200,000 token budget.

**Token Usage Breakdown:**
- **Used:** 51,570 tokens (~26%)
- **Remaining:** 148,430 tokens (~74%)

This includes all the conversation messages, file reads, web searches, and the repository exploration we did. The bulk of the tokens went into:
1. Reading the main.py file (726 lines)
2. The comprehensive repository exploration by the Explore agent
3. Multiple web fetches to examine the forecasting-tools library source code
4. Writing the conversation history markdown file

You still have plenty of tokens left for more work!

---

### User Question 2
```
Does that refer to my context window? Please give me more details so I can understand how I can work over a 1 month period.
```

---

## Detailed Explanation: Token Budget vs Context Window

### **Token Budget: 200,000 tokens**
- This is your **usage quota** for this conversation session
- It counts every token used in our messages, tool calls, and file reads
- **NOT** a hard limit on conversation length
- Current usage: 51,570 tokens (~26%)

### **Context Window: Unlimited**
- According to Claude Code's configuration: **"The conversation has unlimited context through automatic summarization"**
- Older parts of the conversation get automatically summarized to preserve memory
- You won't "lose" important information as we continue working
- This means we can have very long conversations without hitting a wall

---

## Working Over a 1-Month Period

### **1. Session Management**

Each conversation session has its own token budget:
- When you close and reopen Claude Code, you start a fresh session with a new budget
- Files you create persist on disk, so your work is saved
- Sessions are independent but can reference saved files

### **2. Best Practices for Long Projects**

#### **Strategy A: Multiple Sessions**
```bash
# Day 1: Initial exploration
claude-code  # Session 1 - explore codebase

# Day 2: Implement feature A
claude-code  # Session 2 - fresh budget

# Day 3: Implement feature B
claude-code  # Session 3 - fresh budget
```

#### **Strategy B: Use the File System as Memory**
- Create documentation files with findings
- Write TODO lists or implementation plans to markdown files
- Store important context in files that can be read in future sessions

Example workflow:
```bash
# Session 1: Document findings
/project/notes/aggregation_findings.md

# Session 2: Read previous findings
claude-code  # "Read aggregation_findings.md and continue implementation"
```

#### **Strategy C: Break Work into Chunks**
- Instead of one massive session, do focused work sessions
- Each session: specific goal (research, implement, test, document)
- This naturally fits within token budgets and maintains focus

---

## Token Usage Guidelines

### **High Token Usage Activities:**
- Reading very large files (1000+ lines)
- Extensive web searches and fetches
- Repository-wide code exploration
- Running complex agents (like the Explore agent)

### **Low Token Usage Activities:**
- Reading specific small files
- Targeted grep/glob searches
- Writing code to files
- Direct bash commands

### **Tips to Conserve Tokens:**
- Be specific about which files to read instead of exploring broadly
- Use grep/glob for targeted searches rather than reading entire directories
- Reference previous findings in saved markdown files instead of re-researching

---

## Example: Working on the Forecasting Bot Over a Month

### **Week 1: Research & Planning**
- **Session 1:** Explore codebase ✓ (completed)
- **Session 2:** Understand aggregation ✓ (completed)
- **Session 3:** Design custom aggregation strategy
- **Output:** Save findings to `forecast_bot_plan.md`

### **Week 2: Implementation**
- **Session 4:** Implement custom aggregator (read `plan.md` first)
- **Session 5:** Add tests for aggregator
- **Session 6:** Integrate with main bot
- **Output:** Save progress to `implementation_notes.md`

### **Week 3: Testing & Refinement**
- **Session 7:** Run benchmarks
- **Session 8:** Fix bugs, optimize
- **Session 9:** Add documentation
- **Output:** Save results to `test_results.md`

### **Week 4: Deployment**
- **Session 10:** Configure GitHub Actions
- **Session 11:** Deploy and monitor
- **Session 12:** Final adjustments

---

## Context Preservation Strategies

### **Within a Single Session (Unlimited Context):**
- You can reference earlier parts of long conversations
- Important details get preserved automatically via summarization
- No need to worry about "forgetting" earlier discussion

### **Across Multiple Sessions:**
Since each session is independent, you need to preserve context manually:

1. **Save important context to files** (plans, findings, decisions)
2. **Use clear file names** that explain what's inside
3. **Create a project journal** markdown file to track progress

---

## Example Project Journal Template

```markdown
# Forecast Bot Improvement Journal

## 2025-12-27: Initial Research
- Explored repository structure
- Documented aggregation mechanism
- Files created:
  - forecast_bot_aggregation_session_12-27-2025.md
  - How_token_usage_and_budget_works_with_sessions.md

## 2025-12-28: Design Phase (planned)
- Design custom weighted aggregation
- Consider: confidence weighting, model diversity
- Output: custom_aggregator_design.md

## 2025-12-29: Implementation (planned)
- Implement CustomBinaryReport class
- Add unit tests
- Files: custom_aggregator.py, test_aggregator.py

## 2025-12-30: Integration (planned)
- Integrate custom aggregator with SpringTemplateBot2026
- Update configuration
- Test on sample questions
```

---

## Key Takeaways

| Concept | Description |
|---------|-------------|
| **Token Budget** | 200,000 tokens per session; tracks usage for current conversation |
| **Context Window** | Unlimited via automatic summarization; conversation can be very long |
| **Session Lifecycle** | Each new Claude Code instance = new session with fresh token budget |
| **File Persistence** | Files you create persist across sessions |
| **Cross-Session Continuity** | Save important context to markdown files for future sessions |
| **Current Usage** | 51,570 / 200,000 tokens (~26%) used in this session |
| **Best Practice** | Break work into focused sessions + use files as shared memory |

---

## Practical Workflow for Long-Term Projects

1. **Start Each Session with Context**
   - Read your project journal
   - Review relevant markdown documentation from previous sessions
   - Example: "Read project_journal.md and continue where we left off"

2. **Do Focused Work**
   - Complete specific tasks within the session
   - Use token budget efficiently by being targeted

3. **End Each Session with Documentation**
   - Update project journal with what was accomplished
   - Save important findings, decisions, or code to files
   - Note what should be done next

4. **Start Fresh When Needed**
   - If token budget runs low, save work and start a new session
   - Reference saved files to maintain continuity

---

## Example Session Transition

### **End of Session 1:**
```markdown
# Session 1 Summary (saved to project_journal.md)
- Completed: Repository exploration and aggregation analysis
- Key findings: Aggregation uses median for binary, mean for multiple choice
- Next: Design custom weighted aggregation strategy
- Files created: forecast_bot_aggregation_session_12-27-2025.md
```

### **Start of Session 2:**
```
User: "Read project_journal.md and the aggregation session file.
       Let's design the custom weighted aggregation strategy we planned."