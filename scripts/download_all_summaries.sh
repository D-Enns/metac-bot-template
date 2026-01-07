#!/bin/bash
# Download and consolidate all forecast summaries from GitHub Actions artifacts
#
# This script downloads all forecast summary artifacts from GitHub Actions workflow runs
# and consolidates them into a single directory for analysis.
#
# Usage: ./scripts/download_all_summaries.sh [output_directory]
#
# Requirements:
#   - GitHub CLI (gh) must be installed and authenticated
#   - Run: gh auth login
#
# Example:
#   ./scripts/download_all_summaries.sh ./all_forecast_summaries

set -e  # Exit on error

# Configuration
OUTPUT_DIR="${1:-./all_forecast_summaries}"
REPO="D-Enns/metac-bot-template"  # Update with your GitHub username/repo
WORKFLOW_NAME="dre_run_bot_on_tournament.yaml"
TEMP_DIR="/tmp/forecast_artifacts_$$"

echo "📦 Downloading all forecast summaries from GitHub Actions..."
echo "Repository: $REPO"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

# Create output and temp directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMP_DIR"

echo "🔍 Finding all forecast-summaries artifacts..."

# Get all workflow runs and their artifacts
run_count=0
artifact_count=0
file_count=0

# Get recent workflow runs (last 100 runs)
gh run list \
    --repo "$REPO" \
    --workflow "$WORKFLOW_NAME" \
    --limit 100 \
    --json databaseId \
    --jq '.[].databaseId' | while read -r run_id; do

    run_count=$((run_count + 1))
    echo "[$run_count] Checking run $run_id..."

    # List artifacts for this run
    artifacts=$(gh run view "$run_id" \
        --repo "$REPO" \
        --json artifacts \
        --jq '.artifacts[] | select(.name | startswith("forecast-summaries")) | .name')

    if [ -n "$artifacts" ]; then
        echo "$artifacts" | while read -r artifact_name; do
            artifact_count=$((artifact_count + 1))
            echo "  📥 Downloading: $artifact_name..."

            # Download using gh CLI
            if gh run download "$run_id" \
                --repo "$REPO" \
                --name "$artifact_name" \
                --dir "$TEMP_DIR/$artifact_name" 2>/dev/null; then

                # Move all files from artifact to output directory
                if [ -d "$TEMP_DIR/$artifact_name" ]; then
                    # Count files before moving
                    new_files=$(find "$TEMP_DIR/$artifact_name" -type f 2>/dev/null | wc -l)

                    # Copy files (don't overwrite existing files)
                    if [ "$new_files" -gt 0 ]; then
                        cp -n "$TEMP_DIR/$artifact_name"/* "$OUTPUT_DIR/" 2>/dev/null || true
                        echo "    ✅ Extracted $new_files files"
                    fi
                fi
            else
                echo "    ⚠️  Failed to download (artifact may have expired)"
            fi
        done
    fi
done

# Cleanup temp directory
rm -rf "$TEMP_DIR"

# Count total files
total_files=$(find "$OUTPUT_DIR" -type f 2>/dev/null | wc -l)

echo ""
echo "✅ Download complete!"
echo "📊 Summary:"
echo "   - Total unique files: $total_files"
echo "   - Location: $OUTPUT_DIR"
echo ""
echo "📁 Files in output directory:"
ls -1 "$OUTPUT_DIR" 2>/dev/null | head -20
if [ "$(ls -1 "$OUTPUT_DIR" 2>/dev/null | wc -l)" -gt 20 ]; then
    echo "   ... and $(( $(ls -1 "$OUTPUT_DIR" 2>/dev/null | wc -l) - 20 )) more files"
fi
