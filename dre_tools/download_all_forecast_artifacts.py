#!/usr/bin/env python3
"""
Download All Forecast Artifacts from GitHub Actions (v3.0)

This script downloads forecast summary artifacts from GitHub Actions workflow runs,
keeping only the FIRST OCCURRENCE of each question to minimize disk space and
maintain a clean, navigable archive.

Key Features:
- Downloads only first occurrence of each question
- Adds missing file types in subsequent runs (e.g., condensed.md added later)
- TSV manifest tracks all questions with first run info
- Tool run logs capture all console output
- Space-efficient: ~90% reduction vs keeping all versions

Requirements:
- GitHub CLI (gh) installed and authenticated: gh auth login
- Python 3.7+

Usage:
    python download_all_forecast_artifacts.py
    python download_all_forecast_artifacts.py --limit 500
    python download_all_forecast_artifacts.py --output-dir my_forecasts

Version History:
- v3.0 (Feb 2026): First occurrence only, TSV manifest, tool logging
- v2.0 (Feb 2026): Keep all versions with run numbers [DEPRECATED - too much space]
- v1.0 (Jan 2026): Basic download with run_*/ subdirectories
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class ToolLogger:
    """Dual output logger: console + timestamped log file"""

    def __init__(self, output_dir: Path):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        self.log_file = output_dir / f"tool_run_{timestamp}.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Write header
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Tool Run Log - {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

    def log(self, message: str):
        """Write to both console and log file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(message)  # Console output without timestamp for readability

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')


class ArtifactDownloader:
    def __init__(self, repo: str, workflow: str, output_dir: str = "forecast_summaries"):
        self.repo = repo
        self.workflow = workflow
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logger
        self.logger = ToolLogger(self.output_dir)

        # TSV manifest
        self.tsv_data = {}  # {question_id: {first_run, first_run_date, tournament, files, notes}}
        self.latest_tsv_file = self._get_latest_tsv_path()  # Most recent existing TSV
        self.next_tsv_file = None  # Set after save

        # Track run dates for TSV updates
        self.run_dates = {}  # {run_number: date}

        # Verify gh CLI
        self._verify_gh_cli()

        # Load existing TSV manifest
        self.load_tsv_manifest()

    def _verify_gh_cli(self):
        """Verify GitHub CLI is installed and authenticated"""
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            self.logger.log("✓ GitHub CLI (gh) is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.log("ERROR: GitHub CLI (gh) is not installed or not in PATH")
            self.logger.log("Please install it: https://cli.github.com/")
            self.logger.log("Then authenticate: gh auth login")
            sys.exit(1)

        try:
            subprocess.run(["gh", "auth", "status"], capture_output=True, check=True, text=True)
            self.logger.log("✓ GitHub CLI is authenticated")
        except subprocess.CalledProcessError:
            self.logger.log("ERROR: GitHub CLI is not authenticated")
            self.logger.log("Please run: gh auth login")
            sys.exit(1)

    # ========================================================================
    # TSV Manifest Methods
    # ========================================================================

    def _get_latest_tsv_path(self) -> Optional[Path]:
        """Find the most recent Question_Run_and_Date TSV file"""
        tsv_files = sorted(self.output_dir.glob("Question_Run_and_Date_*.txt"))
        return tsv_files[-1] if tsv_files else None

    def _get_next_tsv_path(self) -> Path:
        """Generate next versioned TSV filename for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        n = 1
        while True:
            path = self.output_dir / f"Question_Run_and_Date_{today}_v{n}.txt"
            if not path.exists():
                return path
            n += 1

    def load_tsv_manifest(self):
        """Load existing TSV manifest if it exists"""
        if not self.latest_tsv_file:
            self.logger.log("No existing TSV manifest found (starting fresh)")
            return

        try:
            with open(self.latest_tsv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    question_id = row['question_id']
                    self.tsv_data[question_id] = {
                        'first_run': int(row['first_run']),
                        'first_run_date': row['first_run_date'],
                        'tournament': row['tournament'],
                        'file_count': int(row['file_count']),
                        'notes': row.get('notes', '')
                    }

            self.logger.log(f"✓ Loaded TSV manifest: {len(self.tsv_data)} questions tracked ({self.latest_tsv_file.name})")
        except Exception as e:
            self.logger.log(f"Warning: Failed to load TSV manifest: {e}")
            self.logger.log("Will rebuild from files if needed")

    def save_tsv_manifest(self):
        """Save TSV manifest (rebuild from actual files on disk)"""
        self.logger.log("\nUpdating TSV manifest...")

        # Rebuild from files on disk
        manifest = {}

        for file in sorted(self.output_dir.glob("*_r*.*")):
            if file.suffix not in ['.md', '.json']:
                continue

            question_id = self.extract_question_id(file.name)
            if not question_id:
                continue

            run_number = self.extract_run_number(file.name)
            tournament = self.extract_tournament(file.name)

            if question_id not in manifest:
                manifest[question_id] = {
                    'first_run': run_number,
                    'tournament': tournament,
                    'files': set(),
                    'notes': self.tsv_data.get(question_id, {}).get('notes', '')
                }
            else:
                # Update first_run if this file is from earlier run
                if run_number < manifest[question_id]['first_run']:
                    manifest[question_id]['first_run'] = run_number

            manifest[question_id]['files'].add(file.name)

        # Extract Forecast Date from each question's full summary file
        for question_id in manifest:
            manifest[question_id]['first_run_date'] = self.extract_forecast_date(question_id)

        # Write to next versioned TSV file
        self.next_tsv_file = self._get_next_tsv_path()

        with open(self.next_tsv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(['question_id', 'first_run', 'first_run_date', 'tournament', 'file_count', 'notes'])

            for question_id in sorted(manifest.keys(), key=int):
                data = manifest[question_id]
                writer.writerow([
                    question_id,
                    data['first_run'],
                    data['first_run_date'],
                    data['tournament'],
                    len(data['files']),
                    data['notes']
                ])

        self.logger.log(f"✓ TSV manifest saved: {len(manifest)} questions")
        self.logger.log(f"  Location: {self.next_tsv_file.name}")

    # ========================================================================
    # Filename Parsing Helpers
    # ========================================================================

    def extract_question_id(self, filename: str) -> Optional[str]:
        """Extract question ID from filename (e.g., '41871' from '41871_spring_aib_2026_full_r909.md')"""
        match = re.match(r'^(\d+)_', filename)
        return match.group(1) if match else None

    def extract_run_number(self, filename: str) -> int:
        """Extract run number from filename (e.g., 909 from '41871_spring_aib_2026_full_r909.md')"""
        match = re.search(r'_r(\d+)\.', filename)
        return int(match.group(1)) if match else 0

    def extract_tournament(self, filename: str) -> str:
        """Extract tournament from filename (e.g., 'spring_aib_2026' from filename)"""
        # Pattern: questionID_tournament_type_rRUN.ext
        # Example: 41871_spring_aib_2026_full_r909.md
        parts = filename.split('_')

        # Find where tournament ends (before 'full', 'condensed', 'scenarios')
        file_types = ['full', 'condensed', 'scenarios']
        tournament_parts = []

        for i, part in enumerate(parts[1:], 1):  # Skip question ID
            if part in file_types or part.startswith('r'):
                break
            tournament_parts.append(part)

        return '_'.join(tournament_parts) if tournament_parts else 'unknown'

    def extract_file_type(self, filename: str) -> Optional[str]:
        """Extract file type from filename (full, condensed, or scenarios)"""
        if '_full_r' in filename:
            return 'full'
        elif '_condensed_r' in filename:
            return 'condensed'
        elif '_scenarios_r' in filename:
            return 'scenarios'
        return None

    def extract_forecast_date(self, question_id: str) -> str:
        """Extract Forecast Date from the full summary file for a question"""
        for file in self.output_dir.glob(f"{question_id}_*_full_r*.md"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    for line in f:
                        match = re.match(r'\*\*Forecast Date\*\*:\s*(.+)', line)
                        if match:
                            return match.group(1).strip()
            except Exception:
                continue
        return 'unknown'

    # ========================================================================
    # Question Tracking Methods
    # ========================================================================

    def get_existing_files(self, question_id: str) -> Dict[str, Optional[int]]:
        """
        Check what file types we already have for a question.
        Returns: {'full': run_number or None, 'condensed': run_number or None, 'scenarios': run_number or None}
        """
        existing = {'full': None, 'condensed': None, 'scenarios': None}

        # Check TSV first
        if question_id in self.tsv_data:
            # Question is tracked, check files on disk
            for file in self.output_dir.glob(f"{question_id}_*"):
                file_type = self.extract_file_type(file.name)
                if file_type:
                    run_num = self.extract_run_number(file.name)
                    existing[file_type] = run_num
        else:
            # Fall back to file scan
            for file in self.output_dir.glob(f"{question_id}_*"):
                file_type = self.extract_file_type(file.name)
                if file_type:
                    run_num = self.extract_run_number(file.name)
                    existing[file_type] = run_num

        return existing

    def should_download_file(self, question_id: str, file_type: str) -> bool:
        """Determine if we should download this file type for this question"""
        existing = self.get_existing_files(question_id)
        return existing[file_type] is None

    # ========================================================================
    # GitHub API Methods
    # ========================================================================

    def get_workflow_runs(self, limit: int = 1000) -> List[Dict]:
        """Get list of all workflow runs"""
        self.logger.log(f"\nFetching workflow runs for: {self.workflow}")
        self.logger.log(f"Repository: {self.repo}")
        self.logger.log(f"Limit: {limit} runs")

        cmd = [
            "gh", "api",
            f"repos/{self.repo}/actions/workflows/{self.workflow}/runs",
            "--paginate",
            "--jq", ".workflow_runs[] | {run_number: .run_number, id: .id, created_at: .created_at, conclusion: .conclusion}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)

            # Parse NDJSON output
            runs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    runs.append(json.loads(line))

            # Sort by run number (newest first)
            runs.sort(key=lambda x: x['run_number'], reverse=True)

            # Apply limit
            runs = runs[:limit]

            # Store run dates for TSV
            for run in runs:
                self.run_dates[run['run_number']] = run['created_at']

            self.logger.log(f"✓ Found {len(runs)} workflow runs")
            return runs

        except subprocess.CalledProcessError as e:
            self.logger.log(f"ERROR: Failed to get workflow runs: {e.stderr}")
            return []

    def get_run_artifacts(self, run_id: int) -> List[Dict]:
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

    # ========================================================================
    # Download Methods
    # ========================================================================

    def download_artifact(self, run_id: int, run_number: int, artifact_name: str) -> Dict:
        """Download artifact and process files (only download missing file types)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                "gh", "run", "download", str(run_id),
                "--repo", self.repo,
                "--name", artifact_name,
                "--dir", temp_dir
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True, text=True)

                downloaded_files = []
                questions_processed = set()
                skipped_files = []

                for file in Path(temp_dir).rglob("*"):
                    if not file.is_file() or file.name.startswith('.'):
                        continue

                    # Parse filename
                    question_id = self.extract_question_id(file.name)
                    if not question_id:
                        continue

                    file_type = self.extract_file_type(file.name)
                    if not file_type:
                        continue

                    questions_processed.add(question_id)

                    # Check if we should download this file
                    if not self.should_download_file(question_id, file_type):
                        skipped_files.append(file.name)
                        continue

                    # Generate target filename with run number
                    stem = file.stem
                    suffix = file.suffix

                    # Check if file already has a run number
                    existing_run_match = re.search(r'_r(\d+)$', stem)

                    if existing_run_match:
                        # File already has run number - use as is
                        new_name = file.name
                    else:
                        # Remove trailing counter if present (e.g., _1)
                        if stem[-2:].startswith('_') and stem[-1].isdigit():
                            stem = stem[:-2]

                        # Add run number
                        new_name = f"{stem}_r{run_number}{suffix}"

                    target_path = self.output_dir / new_name

                    # Copy file
                    if not target_path.exists():
                        shutil.copy2(file, target_path)
                        downloaded_files.append(new_name)
                        self.logger.log(f"      ✓ {new_name}")
                    else:
                        self.logger.log(f"      ⊙ {new_name} (already exists)")

                # Summary
                if downloaded_files:
                    self.logger.log(f"    ✓ Downloaded {len(downloaded_files)} file(s)")
                if skipped_files:
                    self.logger.log(f"    ⊙ Skipped {len(skipped_files)} file(s) (already have)")

                return {
                    'downloaded': len(downloaded_files),
                    'skipped': len(skipped_files),
                    'questions': list(questions_processed)
                }

            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode() if e.stderr else 'Unknown error'
                self.logger.log(f"    ✗ Failed: {error_msg}")
                return {'downloaded': 0, 'skipped': 0, 'questions': [], 'error': error_msg}

    # ========================================================================
    # Main Download Method
    # ========================================================================

    def download_all_artifacts(self, limit: int = 1000):
        """Main method to download all artifacts (first occurrence only)"""
        self.logger.log("=" * 80)
        self.logger.log("FORECAST ARTIFACT DOWNLOADER v3.0 - First Occurrence Only")
        self.logger.log("=" * 80)

        # Get all workflow runs
        runs = self.get_workflow_runs(limit)
        if not runs:
            self.logger.log("No workflow runs found!")
            return

        self.logger.log(f"\nProcessing {len(runs)} workflow runs...")
        self.logger.log(f"Output directory: {self.output_dir.absolute()}")
        self.logger.log("-" * 80)

        stats = {
            'total_runs': len(runs),
            'runs_with_artifacts': 0,
            'total_artifacts': 0,
            'files_downloaded': 0,
            'files_skipped': 0,
            'failed': 0,
            'expired': 0
        }

        # Process each run
        for i, run in enumerate(runs, 1):
            run_id = run['id']
            run_number = run['run_number']
            created_at = run['created_at']
            conclusion = run['conclusion']

            self.logger.log(f"\n[{i}/{len(runs)}] Run #{run_number} (ID: {run_id})")
            self.logger.log(f"  Date: {created_at}")
            self.logger.log(f"  Status: {conclusion}")

            # Skip failed runs
            if conclusion not in ["success", "completed", None]:
                self.logger.log(f"  ⊙ Skipping (not successful)")
                continue

            # Get artifacts for this run
            artifacts = self.get_run_artifacts(run_id)

            if not artifacts:
                self.logger.log(f"  ⊙ No forecast artifacts found")
                continue

            stats['runs_with_artifacts'] += 1
            stats['total_artifacts'] += len(artifacts)

            # Download each artifact
            for artifact in artifacts:
                artifact_name = artifact['name']
                size_mb = artifact['size_in_bytes'] / (1024 * 1024)
                expired = artifact['expired']

                self.logger.log(f"  - {artifact_name} ({size_mb:.2f} MB)")

                if expired:
                    self.logger.log(f"    ✗ Expired (cannot download)")
                    stats['expired'] += 1
                    continue

                # Download
                result = self.download_artifact(run_id, run_number, artifact_name)

                if 'error' in result:
                    stats['failed'] += 1
                else:
                    stats['files_downloaded'] += result['downloaded']
                    stats['files_skipped'] += result['skipped']

        # Generate summary
        self._generate_summary(stats)

        # Save TSV manifest
        self.save_tsv_manifest()

    def _generate_summary(self, stats: Dict):
        """Generate summary report"""
        self.logger.log("\n" + "=" * 80)
        self.logger.log("DOWNLOAD SUMMARY")
        self.logger.log("=" * 80)

        self.logger.log(f"\n📊 Statistics:")
        self.logger.log(f"  Total workflow runs processed: {stats['total_runs']}")
        self.logger.log(f"  Runs with forecast artifacts: {stats['runs_with_artifacts']}")
        self.logger.log(f"  Total artifacts found: {stats['total_artifacts']}")
        self.logger.log(f"  ✓ Files downloaded: {stats['files_downloaded']}")
        self.logger.log(f"  ⊙ Files skipped (already have): {stats['files_skipped']}")
        self.logger.log(f"  ✗ Failed: {stats['failed']}")
        self.logger.log(f"  ⊗ Expired: {stats['expired']}")

        # Count unique questions
        question_ids = set()
        for file in self.output_dir.glob("*_r*.md"):
            qid = self.extract_question_id(file.name)
            if qid:
                question_ids.add(qid)

        self.logger.log(f"\n📝 Unique questions with forecast data: {len(question_ids)}")
        if question_ids and len(question_ids) <= 50:
            self.logger.log(f"  Question IDs: {', '.join(sorted(question_ids, key=int))}")

        self.logger.log(f"\n📁 Files organized in: {self.output_dir.absolute()}/")
        self.logger.log(f"📄 TSV manifest: (saved after summary)")
        self.logger.log(f"📋 Tool run log: {self.logger.log_file}")
        self.logger.log("\n✅ Download complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Download forecast artifacts from GitHub Actions (first occurrence only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all artifacts (last 1000 runs)
  python download_all_forecast_artifacts.py

  # Download from specific workflow
  python download_all_forecast_artifacts.py --workflow dre_run_bot_on_tournament.yaml

  # Download last 500 runs only
  python download_all_forecast_artifacts.py --limit 500

  # Use custom output directory
  python download_all_forecast_artifacts.py --output-dir my_forecasts

Version: 3.0 (First Occurrence Only)
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

    args = parser.parse_args()

    # Create downloader
    downloader = ArtifactDownloader(
        repo=args.repo,
        workflow=args.workflow,
        output_dir=args.output_dir
    )

    # Download all artifacts
    downloader.download_all_artifacts(limit=args.limit)

    print("\n" + "=" * 80)
    print("All done! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    main()
