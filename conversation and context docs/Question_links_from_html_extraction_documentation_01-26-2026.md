# Terminal Commands to Extract Websites from HTML

## Project Overview

This document describes the process used to extract Metaculus question URLs from a large HTML text file (`spring_tournament_text.txt`, 296.3KB) and generate output files in multiple formats.

## Session Summary

**Date:** 2026-01-26
**Source File:** `C:\Users\Donni\projects\metac_ques_pages\spring_tournament_text.txt`
**Output Directory:** `C:\Users\Donni\projects\metac_ques_pages\product\`

### Challenge

The source file was too large (296.3KB) to read directly in a single operation, requiring alternative approaches using pattern matching and command-line tools.

## Extraction Process

### Step 1: Pattern Discovery

Initial attempts to find complete URLs with domain:
```bash
grep -oP 'https://www\.metaculus\.com/questions/[0-9]+/[^"]*' spring_tournament_text.txt
```
This returned no results, indicating URLs were stored as relative paths.

### Step 2: Successful Extraction

Found question URLs using relative path pattern:
```bash
grep -oP '/questions/[0-9]+' /mnt/c/Users/Donni/projects/metac_ques_pages/spring_tournament_text.txt | head -20
```

This successfully identified patterns like `/questions/41190`, `/questions/41191`, etc.

### Step 3: Complete URL Generation

Extracted all unique question IDs, sorted them, and prepended the domain:
```bash
grep -oP '/questions/[0-9]+' /mnt/c/Users/Donni/projects/metac_ques_pages/spring_tournament_text.txt | sort -u | sed 's|^|https://www.metaculus.com|'
```

**Result:** 31 unique Metaculus question URLs identified.

## Output Files Created

### 1. Simple Text File (`links.txt`)
One URL per line, generated using:
```bash
grep -oP '/questions/[0-9]+' /mnt/c/Users/Donni/projects/metac_ques_pages/spring_tournament_text.txt | sort -u | sed 's|^|https://www.metaculus.com|' > /mnt/c/Users/Donni/projects/metac_ques_pages/product/links.txt
```

**Use case:** Easy copy-paste, scripting, or import into other tools.

### 2. CSV File (`links.csv`)
Two columns: ID and URL

**Format:**
```csv
ID,URL
123,https://www.metaculus.com/questions/123
41190,https://www.metaculus.com/questions/41190
...
```

**Use case:** Import into spreadsheet applications, databases, or data analysis tools.

### 3. HTML File (`links.html`)
Formatted webpage with clickable links that open in new tabs.

**Features:**
- Clean, responsive design
- Hover effects on links
- Question ID labels
- Total question count displayed
- Opens directly in web browser

**Use case:** Quick navigation, sharing with team members, visual reference.

## Key Commands Reference

### Extract URL Patterns from Large Files
```bash
grep -oP 'pattern' filename
```
- `-o`: Only show matching part
- `-P`: Use Perl-compatible regex
- `pattern`: Regular expression to match

### Remove Duplicates and Sort
```bash
sort -u
```
- `-u`: Unique entries only

### String Replacement with sed
```bash
sed 's|original|replacement|'
```
- `s`: Substitute command
- `|`: Delimiter (alternative to `/`)

### Combine Commands with Pipes
```bash
command1 | command2 | command3
```
Each command processes the output of the previous one.

## Results

**Total Questions Found:** 31

**Question ID Range:**
- Question #123 (appears to be a template/placeholder)
- Questions #41190 - #41836 (actual tournament questions)

**Files Created:**
1. `product/links.txt` - Plain text list
2. `product/links.csv` - CSV format with headers
3. `product/links.html` - Interactive HTML page

## Lessons Learned

1. **Large Files:** When files exceed tool size limits, use grep/sed for pattern extraction
2. **Relative vs Absolute URLs:** HTML often contains relative paths that need domain prepending
3. **Regex Patterns:** `[0-9]+` matches one or more digits for capturing question IDs
4. **Multiple Formats:** Providing txt, csv, and html formats serves different use cases
5. **WSL Path Conversion:** Windows paths (C:\) must be converted to WSL format (/mnt/c/)

## Future Enhancements

Potential improvements for similar tasks:
- Fetch actual question titles using the Metaculus API
- Add scraping to get question metadata (dates, status, etc.)
- Automate periodic updates if tournament questions change
- Generate markdown format with question titles as link text
