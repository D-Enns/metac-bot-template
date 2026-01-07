# Forecast Summary Utilities

This directory contains utility scripts for managing forecast summaries from GitHub Actions.

## Download All Summaries

Two scripts are provided to download and consolidate all forecast summaries from GitHub Actions artifacts into a single directory:

### Python Script (Recommended)

**Requirements:**
- Python 3.6+
- GitHub CLI (`gh`) installed and authenticated

**Usage:**
```bash
# From repository root
python scripts/download_all_summaries.py

# With custom output directory
python scripts/download_all_summaries.py --output-dir ~/my_forecasts

# Download from different repository
python scripts/download_all_summaries.py --repo username/repo-name

# Check more workflow runs (default: 100)
python scripts/download_all_summaries.py --limit 200
```

**Help:**
```bash
python scripts/download_all_summaries.py --help
```

### Bash Script (Unix/Linux/WSL)

**Requirements:**
- Bash shell
- GitHub CLI (`gh`) installed and authenticated

**Usage:**
```bash
# From repository root
./scripts/download_all_summaries.sh

# With custom output directory
./scripts/download_all_summaries.sh ~/my_forecasts
```

**Make executable (first time only):**
```bash
chmod +x scripts/download_all_summaries.sh
```

## Setup Instructions

### 1. Install GitHub CLI

**Windows:**
```powershell
winget install --id GitHub.cli
```

**macOS:**
```bash
brew install gh
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install gh

# Or download from: https://cli.github.com/
```

### 2. Authenticate with GitHub

```bash
gh auth login
```

Follow the prompts to authenticate using your GitHub account.

### 3. Run the Download Script

```bash
python scripts/download_all_summaries.py
```

This will:
1. Find all workflow runs for `dre_run_bot_on_tournament.yaml`
2. Download all `forecast-summaries-*` artifacts
3. Consolidate them into `./all_forecast_summaries/` directory
4. Skip duplicate files automatically

## Output Structure

After running the script, you'll have a directory with all forecast summaries:

```
all_forecast_summaries/
├── 41384_unknown_full_1.md
├── 41384_unknown_condensed_1.md
├── 41384_unknown_scenarios_1.json
├── 41392_unknown_full_1.md
├── 41392_unknown_condensed_1.md
├── 41392_unknown_scenarios_1.json
├── 41421_unknown_full_1.md
├── 41421_unknown_condensed_1.md
├── 41421_unknown_scenarios_1.json
└── ... (hundreds more)
```

## File Naming Convention

Files follow this pattern:
- `{question_id}_{tournament}_full_{counter}.md` - Full forecast analysis
- `{question_id}_{tournament}_condensed_{counter}.md` - Condensed summary
- `{question_id}_{tournament}_scenarios_{counter}.json` - Individual scenario data

Where:
- `question_id`: Metaculus question ID (e.g., `41384`)
- `tournament`: Tournament slug (e.g., `unknown`, `ai_forecasting_benchmark_2026`)
- `counter`: Forecast version number (e.g., `1`, `2`, `3`)

## Troubleshooting

### "gh: command not found"

Install the GitHub CLI as shown in Setup Instructions above.

### "Error: Not authenticated with GitHub CLI"

Run:
```bash
gh auth login
```

### "Artifact has expired"

GitHub Actions artifacts have a 90-day retention period. Expired artifacts cannot be downloaded.

### Script runs but downloads 0 files

- Check that you're using the correct repository name
- Verify workflow runs exist: Visit GitHub Actions tab in your repository
- Ensure artifacts were successfully uploaded in the workflow runs

### Permission denied (bash script)

Make the script executable:
```bash
chmod +x scripts/download_all_summaries.sh
```

## Advanced Usage

### Download from specific workflow

```bash
python scripts/download_all_summaries.py --workflow dre_test_bot.yaml
```

### Check last 200 runs instead of 100

```bash
python scripts/download_all_summaries.py --limit 200
```

### Update repository in Python script

Edit `scripts/download_all_summaries.py` line:
```python
default="D-Enns/metac-bot-template",  # Change this
```

### Update repository in Bash script

Edit `scripts/download_all_summaries.sh` line:
```bash
REPO="D-Enns/metac-bot-template"  # Change this
```

## Notes

- Both scripts skip duplicate files (won't overwrite existing files)
- Downloads are stored in a temporary directory during processing
- The output directory is created automatically if it doesn't exist
- The `all_forecast_summaries/` directory is ignored by git (see `.gitignore`)
