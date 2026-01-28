#!/usr/bin/env python3
"""
Download All Forecast Artifacts from GitHub Actions

This script systematically downloads all forecast summary artifacts from GitHub Actions
workflow runs, ensuring complete data recovery for all tournaments.

Requirements:
- GitHub CLI (gh) installed and authenticated: gh auth login
- Python 3.7+

Usage:
    python download_all_forecast_artifacts.py
    python download_all_forecast_artifacts.py --workflow dre_run_bot_on_tournament.yaml
    python download_all_forecast_artifacts.py --limit 500
    python download_all_forecast_artifacts.py --output-dir my_forecasts
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import time


class ArtifactDownloader:
    def __init__(self, repo: str, workflow: str, output_dir: str = "forecast_summaries"):
        self.repo = repo
        self.workflow = workflow
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track what we've downloaded
        self.download_log_file = Path("downloaded_artifacts_log.json")
        self.downloaded_artifacts = self._load_download_log()

        # Verify gh CLI is available
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            print("✓ GitHub CLI (gh) is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: GitHub CLI (gh) is not installed or not in PATH")
            print("Please install it: https://cli.github.com/")
            print("Then authenticate: gh auth login")
            sys.exit(1)

        # Verify authentication
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                check=True,
                text=True
            )
            print("✓ GitHub CLI is authenticated")
        except subprocess.CalledProcessError:
            print("ERROR: GitHub CLI is not authenticated")
            print("Please run: gh auth login")
            sys.exit(1)

    def _load_download_log(self) -> Dict:
        """Load log of previously downloaded artifacts"""
        if self.download_log_file.exists():
            with open(self.download_log_file, 'r') as f:
                return json.load(f)
        return {
            "downloaded_artifacts": {},
            "last_updated": None
        }

    def _save_download_log(self):
        """Save log of downloaded artifacts"""
        self.downloaded_artifacts["last_updated"] = datetime.now().isoformat()
        with open(self.download_log_file, 'w') as f:
            json.dump(self.downloaded_artifacts, f, indent=2)

    def get_workflow_runs(self, limit: int = 1000) -> List[Dict]:
        """Get list of all workflow runs"""
        print(f"\nFetching workflow runs for: {self.workflow}")
        print(f"Repository: {self.repo}")
        print(f"Limit: {limit} runs")

        cmd = [
            "gh", "api",
            f"repos/{self.repo}/actions/workflows/{self.workflow}/runs",
            "--paginate",
            "--jq", ".workflow_runs[] | {run_number: .run_number, id: .id, created_at: .created_at, conclusion: .conclusion}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)

            # Parse NDJSON output (one JSON object per line)
            runs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    runs.append(json.loads(line))

            # Sort by run number (newest first)
            runs.sort(key=lambda x: x['run_number'], reverse=True)

            # Apply limit
            runs = runs[:limit]

            print(f"✓ Found {len(runs)} workflow runs")
            return runs

        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to get workflow runs: {e.stderr}")
            return []

    def get_run_artifacts(self, run_id: int, run_number: int) -> List[Dict]:
        """Get artifacts for a specific run"""
        cmd = [
            "gh", "api",
            f"repos/{self.repo}/actions/runs/{run_id}/artifacts",
            "--jq", ".artifacts[] | {name: .name, id: .id, size_in_bytes: .size_in_bytes, expired: .expired}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)

            if not result.stdout.strip():
                return []

            artifacts = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    artifact = json.loads(line)
                    # Only include forecast-related artifacts
                    if 'forecast' in artifact['name'].lower():
                        artifacts.append(artifact)

            return artifacts

        except subprocess.CalledProcessError:
            return []

    def download_artifact(self, run_id: int, run_number: int, artifact_name: str) -> Optional[Path]:
        """Download a specific artifact"""
        # Check if already downloaded
        artifact_key = f"{run_number}:{artifact_name}"
        if artifact_key in self.downloaded_artifacts.get("downloaded_artifacts", {}):
            existing_path = self.downloaded_artifacts["downloaded_artifacts"][artifact_key].get("path")
            if existing_path and Path(existing_path).exists():
                print(f"    ⊙ Already downloaded (skipping)")
                return Path(existing_path)

        # Create subdirectory for this run
        run_dir = self.output_dir / f"run_{run_number}"
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "gh", "run", "download", str(run_id),
            "--repo", self.repo,
            "--name", artifact_name,
            "--dir", str(run_dir)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)

            # Record download
            if "downloaded_artifacts" not in self.downloaded_artifacts:
                self.downloaded_artifacts["downloaded_artifacts"] = {}

            self.downloaded_artifacts["downloaded_artifacts"][artifact_key] = {
                "run_number": run_number,
                "run_id": run_id,
                "artifact_name": artifact_name,
                "path": str(run_dir),
                "downloaded_at": datetime.now().isoformat()
            }

            print(f"    ✓ Downloaded to {run_dir}/")
            return run_dir

        except subprocess.CalledProcessError as e:
            print(f"    ✗ Failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
            return None

    def download_all_artifacts(self, limit: int = 1000, skip_existing: bool = True):
        """Main method to download all artifacts"""
        print("=" * 80)
        print("FORECAST ARTIFACT DOWNLOADER")
        print("=" * 80)

        # Get all workflow runs
        runs = self.get_workflow_runs(limit)
        if not runs:
            print("No workflow runs found!")
            return

        print(f"\nProcessing {len(runs)} workflow runs...")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("-" * 80)

        stats = {
            "total_runs": len(runs),
            "runs_with_artifacts": 0,
            "total_artifacts": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "expired": 0
        }

        # Process each run
        for i, run in enumerate(runs, 1):
            run_id = run['id']
            run_number = run['run_number']
            created_at = run['created_at']
            conclusion = run['conclusion']

            print(f"\n[{i}/{len(runs)}] Run #{run_number} (ID: {run_id})")
            print(f"  Date: {created_at}")
            print(f"  Status: {conclusion}")

            # Skip failed runs
            if conclusion not in ["success", "completed", None]:
                print(f"  ⊙ Skipping (not successful)")
                continue

            # Get artifacts for this run
            artifacts = self.get_run_artifacts(run_id, run_number)

            if not artifacts:
                print(f"  ⊙ No forecast artifacts found")
                continue

            stats["runs_with_artifacts"] += 1
            stats["total_artifacts"] += len(artifacts)

            # Download each artifact
            for artifact in artifacts:
                artifact_name = artifact['name']
                artifact_id = artifact['id']
                size_mb = artifact['size_in_bytes'] / (1024 * 1024)
                expired = artifact['expired']

                print(f"  - {artifact_name} ({size_mb:.2f} MB)")

                if expired:
                    print(f"    ✗ Expired (cannot download)")
                    stats["expired"] += 1
                    continue

                # Download
                result = self.download_artifact(run_id, run_number, artifact_name)

                if result:
                    if "Already downloaded" in str(result):
                        stats["skipped"] += 1
                    else:
                        stats["downloaded"] += 1
                else:
                    stats["failed"] += 1

            # Save progress after each run
            self._save_download_log()

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        # Generate summary report
        self._generate_summary_report(stats, runs)

    def _generate_summary_report(self, stats: Dict, runs: List[Dict]):
        """Generate a summary report of the download operation"""
        print("\n" + "=" * 80)
        print("DOWNLOAD SUMMARY")
        print("=" * 80)

        print(f"\n📊 Statistics:")
        print(f"  Total workflow runs processed: {stats['total_runs']}")
        print(f"  Runs with forecast artifacts: {stats['runs_with_artifacts']}")
        print(f"  Total artifacts found: {stats['total_artifacts']}")
        print(f"  ✓ Downloaded: {stats['downloaded']}")
        print(f"  ⊙ Skipped (already downloaded): {stats['skipped']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  ⊗ Expired: {stats['expired']}")

        # List all downloaded files
        print(f"\n📁 Files organized in: {self.output_dir.absolute()}/")

        # Count unique questions
        question_ids = set()
        for run_dir in self.output_dir.glob("run_*/"):
            for file in run_dir.glob("*.md"):
                # Extract question ID from filename (e.g., 41871_spring_aib_2026_full_1.md)
                parts = file.name.split('_')
                if parts[0].isdigit():
                    question_ids.add(parts[0])

        print(f"\n📝 Unique questions with forecast data: {len(question_ids)}")
        if question_ids:
            print(f"  Question IDs: {', '.join(sorted(question_ids, key=int))}")

        # Save detailed report
        report_file = self.output_dir / "download_report.json"
        report = {
            "timestamp": datetime.now().isoformat(),
            "repository": self.repo,
            "workflow": self.workflow,
            "statistics": stats,
            "unique_questions": sorted(list(question_ids), key=int),
            "runs_processed": [
                {
                    "run_number": run['run_number'],
                    "run_id": run['id'],
                    "date": run['created_at']
                }
                for run in runs[:20]  # Save first 20 for reference
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")
        print(f"📋 Download log saved to: {self.download_log_file}")
        print("\n✅ Download complete!")

    def consolidate_files(self):
        """
        Consolidate all downloaded files into the main forecast_summaries directory,
        avoiding duplicates.
        """
        print("\n" + "=" * 80)
        print("CONSOLIDATING FILES")
        print("=" * 80)

        consolidated_count = 0
        duplicate_count = 0

        # Process each run directory
        for run_dir in sorted(self.output_dir.glob("run_*/")):
            run_number = run_dir.name.replace("run_", "")
            print(f"\nProcessing {run_dir.name}...")

            for file in run_dir.glob("*"):
                if file.is_file() and not file.name.startswith('.'):
                    target = self.output_dir / file.name

                    # Check if file already exists
                    if target.exists():
                        # Compare file sizes to determine if they're the same
                        if target.stat().st_size == file.stat().st_size:
                            print(f"  ⊙ {file.name} (duplicate, skipping)")
                            duplicate_count += 1
                        else:
                            # Different content - rename with run number
                            new_name = file.stem + f"_run{run_number}" + file.suffix
                            target = self.output_dir / new_name
                            file.rename(target)
                            print(f"  ✓ {file.name} → {new_name} (different version)")
                            consolidated_count += 1
                    else:
                        # Move file to main directory
                        file.rename(target)
                        print(f"  ✓ {file.name}")
                        consolidated_count += 1

        print(f"\n📊 Consolidation complete:")
        print(f"  Files moved: {consolidated_count}")
        print(f"  Duplicates skipped: {duplicate_count}")
        print(f"\n📁 All files now in: {self.output_dir.absolute()}/")


def main():
    parser = argparse.ArgumentParser(
        description="Download all forecast artifacts from GitHub Actions workflow runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all artifacts from default workflow
  python download_all_forecast_artifacts.py

  # Download from specific workflow
  python download_all_forecast_artifacts.py --workflow dre_run_bot_on_tournament.yaml

  # Download last 500 runs only
  python download_all_forecast_artifacts.py --limit 500

  # Use custom output directory
  python download_all_forecast_artifacts.py --output-dir my_forecasts

  # Skip consolidation step
  python download_all_forecast_artifacts.py --no-consolidate
        """
    )

    parser.add_argument(
        "--repo",
        default="D-Enns/metac-bot-template",
        help="GitHub repository (owner/repo format)"
    )
    parser.add_argument(
        "--workflow",
        default="dre_run_bot_on_tournament.yaml",
        help="Workflow filename to download artifacts from"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of workflow runs to process (default: 1000)"
    )
    parser.add_argument(
        "--output-dir",
        default="forecast_summaries",
        help="Output directory for downloaded artifacts (default: forecast_summaries)"
    )
    parser.add_argument(
        "--no-consolidate",
        action="store_true",
        help="Skip consolidation step (keep files in run_* subdirectories)"
    )

    args = parser.parse_args()

    # Create downloader
    downloader = ArtifactDownloader(
        repo=args.repo,
        workflow=args.workflow,
        output_dir=args.output_dir
    )

    # Download all artifacts
    downloader.download_all_artifacts(limit=args.limit)

    # Consolidate files (optional)
    if not args.no_consolidate:
        response = input("\n\nConsolidate files into main directory? (y/n): ")
        if response.lower() == 'y':
            downloader.consolidate_files()

    print("\n" + "=" * 80)
    print("All done! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    main()
