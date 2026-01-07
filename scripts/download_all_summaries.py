#!/usr/bin/env python3
"""
Download and consolidate all forecast summaries from GitHub Actions artifacts.

This script downloads all forecast summary artifacts from GitHub Actions workflow runs
and consolidates them into a single directory for analysis.

Usage:
    python scripts/download_all_summaries.py [--output-dir DIR] [--repo OWNER/REPO]

Requirements:
    - GitHub CLI (gh) must be installed and authenticated
    - Run: gh auth login

Example:
    python scripts/download_all_summaries.py --output-dir ./all_forecast_summaries

Environment:
    Uses GitHub CLI authentication (gh auth login)
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict

def run_gh_command(args: List[str]) -> str:
    """Run a GitHub CLI command and return output."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running gh command: {e.stderr}")
        raise
    except FileNotFoundError:
        print("❌ Error: GitHub CLI (gh) is not installed.")
        print("Install it from: https://cli.github.com/")
        sys.exit(1)

def check_gh_auth() -> bool:
    """Check if GitHub CLI is authenticated."""
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_workflow_runs(repo: str, workflow: str, limit: int = 100) -> List[str]:
    """Get list of workflow run IDs."""
    print(f"🔍 Finding workflow runs for {workflow}...")

    output = run_gh_command([
        "run", "list",
        "--repo", repo,
        "--workflow", workflow,
        "--limit", str(limit),
        "--json", "databaseId",
        "--jq", ".[].databaseId"
    ])

    run_ids = [line.strip() for line in output.split('\n') if line.strip()]
    print(f"   Found {len(run_ids)} workflow runs")
    return run_ids

def get_run_artifacts(repo: str, run_id: str) -> List[Dict[str, str]]:
    """Get artifacts for a specific run."""
    try:
        output = run_gh_command([
            "run", "view", run_id,
            "--repo", repo,
            "--json", "artifacts"
        ])

        data = json.loads(output)
        artifacts = data.get("artifacts", [])

        # Filter for forecast-summaries artifacts
        forecast_artifacts = [
            {"name": a["name"], "expired": a.get("expired", False)}
            for a in artifacts
            if a["name"].startswith("forecast-summaries")
        ]

        return forecast_artifacts
    except Exception as e:
        print(f"   ⚠️  Error getting artifacts for run {run_id}: {e}")
        return []

def download_artifact(repo: str, run_id: str, artifact_name: str, temp_dir: Path) -> Path:
    """Download an artifact and return the extraction directory."""
    artifact_dir = temp_dir / artifact_name
    artifact_dir.mkdir(exist_ok=True)

    try:
        run_gh_command([
            "run", "download", run_id,
            "--repo", repo,
            "--name", artifact_name,
            "--dir", str(artifact_dir)
        ])
        return artifact_dir
    except Exception as e:
        print(f"      ⚠️  Failed to download: {e}")
        return None

def consolidate_files(source_dir: Path, output_dir: Path) -> int:
    """Copy files from source to output, skipping duplicates. Returns number of new files."""
    if not source_dir.exists():
        return 0

    new_files = 0
    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            dest_path = output_dir / file_path.name

            # Only copy if destination doesn't exist (avoid overwriting)
            if not dest_path.exists():
                shutil.copy2(file_path, dest_path)
                new_files += 1

    return new_files

def main():
    parser = argparse.ArgumentParser(
        description="Download all forecast summaries from GitHub Actions artifacts"
    )
    parser.add_argument(
        "--output-dir",
        default="./all_forecast_summaries",
        help="Output directory for consolidated summaries (default: ./all_forecast_summaries)"
    )
    parser.add_argument(
        "--repo",
        default="D-Enns/metac-bot-template",
        help="GitHub repository (OWNER/REPO format)"
    )
    parser.add_argument(
        "--workflow",
        default="dre_run_bot_on_tournament.yaml",
        help="Workflow filename"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of runs to check (default: 100)"
    )

    args = parser.parse_args()

    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("📦 Downloading all forecast summaries from GitHub Actions...")
    print(f"Repository: {args.repo}")
    print(f"Workflow: {args.workflow}")
    print(f"Output directory: {output_dir}")
    print()

    # Check authentication
    if not check_gh_auth():
        print("❌ Error: Not authenticated with GitHub CLI.")
        print("Run: gh auth login")
        sys.exit(1)

    # Get workflow runs
    run_ids = get_workflow_runs(args.repo, args.workflow, args.limit)

    if not run_ids:
        print("❌ No workflow runs found")
        sys.exit(1)

    # Download artifacts
    total_artifacts = 0
    total_files = 0
    files_in_output_before = len(list(output_dir.glob('*')))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for i, run_id in enumerate(run_ids, 1):
            print(f"[{i}/{len(run_ids)}] Checking run {run_id}...")

            artifacts = get_run_artifacts(args.repo, run_id)

            if not artifacts:
                continue

            for artifact in artifacts:
                if artifact.get("expired"):
                    print(f"   ⏰ Artifact '{artifact['name']}' has expired, skipping...")
                    continue

                print(f"   📥 Downloading: {artifact['name']}...")
                total_artifacts += 1

                artifact_dir = download_artifact(
                    args.repo,
                    run_id,
                    artifact['name'],
                    temp_path
                )

                if artifact_dir:
                    new_files = consolidate_files(artifact_dir, output_dir)
                    total_files += new_files
                    if new_files > 0:
                        print(f"      ✅ Extracted {new_files} new files")
                    else:
                        print(f"      ℹ️  No new files (duplicates skipped)")

    files_in_output_after = len(list(output_dir.glob('*')))

    print()
    print("✅ Download complete!")
    print("📊 Summary:")
    print(f"   - Processed runs: {len(run_ids)}")
    print(f"   - Downloaded artifacts: {total_artifacts}")
    print(f"   - New files added: {total_files}")
    print(f"   - Total unique files: {files_in_output_after}")
    print(f"   - Location: {output_dir.absolute()}")
    print()

    # List files
    files = sorted(output_dir.glob('*'))
    if files:
        print("📁 Files in output directory:")
        for file in files[:20]:
            print(f"   {file.name}")

        if len(files) > 20:
            print(f"   ... and {len(files) - 20} more files")
    else:
        print("⚠️  No files in output directory")

if __name__ == "__main__":
    main()
