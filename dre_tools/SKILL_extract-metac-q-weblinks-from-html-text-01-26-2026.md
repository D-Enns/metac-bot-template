# AI Skill: Extract URLs from HTML Files

## Skill Name
URL Extraction and Multi-Format Export

## Description
Extract specific URL patterns from large HTML text files and generate output in multiple formats (txt, csv, html). Particularly useful when files are too large for direct reading or when URLs are stored as relative paths.

## Use Cases
- Extract question URLs from tournament pages
- Compile link lists from scraped web content
- Generate shareable URL collections
- Create navigation pages from raw HTML
- Parse relative URLs and convert to absolute URLs

## Prerequisites
- Access to bash/terminal commands (Linux/WSL environment)
- Basic regex pattern matching knowledge
- Source HTML file location

## Input Parameters

### Required:
1. **source_file_path**: Full path to HTML text file
2. **url_pattern**: Regex pattern to match URLs (e.g., `/questions/[0-9]+`)
3. **base_domain**: Base domain to prepend for relative URLs (e.g., `https://www.metaculus.com`)
4. **output_directory**: Directory path for generated files

### Optional:
5. **output_basename**: Base name for output files (default: `links`)
6. **page_title**: Title for HTML output (default: `Extracted URLs`)

## Step-by-Step Process

### Step 1: Verify File Accessibility
Check if file exists and note its size:
```bash
ls -lh /path/to/source/file.txt
```

**Decision Point:** If file is over 256KB, proceed with grep-based extraction rather than attempting to read entire file.

### Step 2: Test Pattern Matching
Test regex pattern on first few matches:
```bash
grep -oP 'pattern' /path/to/file.txt | head -20
```

Example:
```bash
grep -oP '/questions/[0-9]+' /path/to/file.txt | head -20
```

**Validate:** Ensure pattern captures expected URL structures.

### Step 3: Extract All Unique URLs
Extract, deduplicate, and sort URLs:
```bash
grep -oP 'pattern' /path/to/file.txt | sort -u
```

**Key Flags:**
- `-o`: Output only matching parts
- `-P`: Perl-compatible regex
- `-u`: Sort unique entries only

### Step 4: Convert to Absolute URLs (if needed)
Prepend base domain to relative paths:
```bash
grep -oP 'pattern' /path/to/file.txt | sort -u | sed 's|^|base_domain|'
```

Example:
```bash
grep -oP '/questions/[0-9]+' /path/to/file.txt | sort -u | sed 's|^|https://www.metaculus.com|'
```

### Step 5: Generate Output Files

#### A. Plain Text File
```bash
grep -oP 'pattern' /path/to/file.txt | sort -u | sed 's|^|base_domain|' > /output/dir/links.txt
```

**Use:** Simple list, one URL per line.

#### B. CSV File
Create structured CSV with headers:
```bash
echo "ID,URL" > /output/dir/links.csv
grep -oP 'pattern' /path/to/file.txt | sort -u | while read path; do
  id=$(echo "$path" | grep -oP '[0-9]+$')
  echo "$id,base_domain$path"
done >> /output/dir/links.csv
```

**Alternative:** Generate CSV programmatically with proper formatting.

#### C. HTML File
Create interactive HTML page with:
- Styled layout
- Clickable links (target="_blank")
- Hover effects
- Question count
- Question ID labels

**Template Structure:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Page Title</title>
    <style>
        /* Responsive, clean styling */
        /* Hover effects for better UX */
    </style>
</head>
<body>
    <h1>Title</h1>
    <div class="count">Total: X URLs</div>
    <ul>
        <li><span class="question-id">#ID</span><a href="URL" target="_blank">URL</a></li>
        <!-- Repeat for each URL -->
    </ul>
</body>
</html>
```

### Step 6: Verification
Confirm all files created successfully:
```bash
ls -lh /output/dir/
```

Count URLs in each file to verify consistency:
```bash
wc -l /output/dir/links.txt
grep -c "^[0-9]" /output/dir/links.csv  # Exclude header
grep -c "<li>" /output/dir/links.html
```

## Common Patterns and Regex Examples

### URL Patterns
```regex
# Numeric question IDs
/questions/[0-9]+

# Alphanumeric slugs
/posts/[a-zA-Z0-9-]+

# With query parameters
/questions/[0-9]+\?[^"]*

# GitHub issues
/issues/[0-9]+

# Full URLs with domain
https://example\.com/path/[0-9]+
```

### Extraction Variations
```bash
# Case-insensitive matching
grep -oiP 'pattern' file.txt

# Match multiple patterns
grep -oP 'pattern1|pattern2' file.txt

# Exclude certain patterns
grep -oP 'pattern' file.txt | grep -v 'exclude_pattern'

# Limit results
grep -oP 'pattern' file.txt | head -n 100
```

## Error Handling

### File Too Large
**Symptom:** "File exceeds maximum allowed size"
**Solution:** Use grep-based extraction instead of reading entire file

### No Matches Found
**Symptom:** `grep` returns empty results
**Troubleshooting:**
1. Test with broader pattern
2. Check for case sensitivity (add `-i` flag)
3. Verify file encoding (try `file` command)
4. Sample file content to inspect actual format

### Duplicate URLs
**Symptom:** Same URL appears multiple times
**Solution:** Already handled by `sort -u` command

### Path Format Issues (Windows/WSL)
**Symptom:** "File does not exist" with Windows paths
**Solution:** Convert Windows paths to WSL format:
- `C:\path\to\file` → `/mnt/c/path/to/file`

## Output Format Details

### Plain Text (links.txt)
```
https://example.com/questions/1
https://example.com/questions/2
https://example.com/questions/3
```
**Best for:** Scripts, automation, simple imports

### CSV (links.csv)
```csv
ID,URL
1,https://example.com/questions/1
2,https://example.com/questions/2
3,https://example.com/questions/3
```
**Best for:** Spreadsheets, databases, data analysis

### HTML (links.html)
- Interactive, browser-viewable
- Styled with CSS
- Hover effects
- Opens links in new tabs
**Best for:** Sharing, quick navigation, presentations

## Performance Considerations

### File Size
- Files < 256KB: Can read directly
- Files > 256KB: Use grep/sed pipeline
- Files > 10MB: Consider splitting or streaming

### Regex Complexity
- Simple patterns (e.g., `[0-9]+`) are fastest
- Lookaheads/lookbehinds add overhead
- Test pattern on sample before full file

### Output Generation
- Text file: Instant
- CSV file: Fast (linear time)
- HTML file: Moderate (requires formatting)

## Validation Checklist

- [ ] Source file exists and is readable
- [ ] Regex pattern tested on sample data
- [ ] Output directory exists or created
- [ ] All three output files generated
- [ ] URL counts match across all files
- [ ] HTML file opens in browser correctly
- [ ] Links are clickable and valid
- [ ] No placeholder/template IDs in final output (e.g., question #123)

## Example Complete Workflow

```bash
# 1. Set variables
SOURCE="/path/to/source.html"
PATTERN="/questions/[0-9]+"
DOMAIN="https://www.metaculus.com"
OUTDIR="/path/to/output"

# 2. Create output directory
mkdir -p "$OUTDIR"

# 3. Generate text file
grep -oP "$PATTERN" "$SOURCE" | sort -u | sed "s|^|$DOMAIN|" > "$OUTDIR/links.txt"

# 4. Count results
TOTAL=$(wc -l < "$OUTDIR/links.txt")
echo "Extracted $TOTAL unique URLs"

# 5. Generate CSV (programmatically or manually)
# 6. Generate HTML (programmatically or manually)

# 7. Verify
ls -lh "$OUTDIR"
```

## Extensions and Enhancements

### Fetch Additional Metadata
Use extracted URLs to fetch:
- Page titles
- Publication dates
- Author information
- Status flags

### Automation
Create script that:
- Accepts command-line arguments
- Validates inputs
- Generates all formats automatically
- Creates documentation

### Integration
- API integration to fetch live data
- Database storage for URL collections
- Periodic updates for dynamic content
- Deduplication across multiple sources

## Related Skills
- Web scraping
- HTML parsing
- Regex pattern matching
- Data format conversion
- Batch file processing

## References
- grep manual: `man grep`
- sed manual: `man sed`
- Regex testing: regex101.com
- HTML5 specification

## Version History
- v1.0 (2026-01-26): Initial skill documentation based on Metaculus URL extraction project
