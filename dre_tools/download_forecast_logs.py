#!/usr/bin/env python3
"""
Download GitHub Actions workflow logs and extract forecast metadata.

This script downloads full workflow run logs from GitHub Actions for the forecast bot,
extracts metadata about each question processed, and generates a TSV summary.

Usage:
    python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30
    python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --skip-existing
    python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --limit 10
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Set
from zoneinfo import ZoneInfo


# Regex patterns for log parsing
# Match URLs with optional slug: https://www.metaculus.com/questions/12345 or .../12345/slug-text
QUESTION_URL_PATTERN = re.compile(r'(https://www\.metaculus\.com/questions/\d+(?:/[^/\s]+)?)')
QUESTION_NUMBER_PATTERN = re.compile(r'/questions/(\d+)')
ERROR_PATTERN = re.compile(r'- ERROR -')
WARNING_PATTERN = re.compile(r'- WARNING -')
SUBMISSION_PATTERN = re.compile(r'(Forecasted URL|Posted forecast|Posted prediction|Posted comment|Saved full forecast to)')
TIMESTAMP_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)')

# Timezone configuration
MOUNTAIN_TZ = ZoneInfo("America/Denver")


@dataclass
class QuestionMetadata:
    """Metadata for a single question processed in a workflow run."""
    run_number: int
    timestamp_utc: str
    timestamp_mountain: str
    question_number: Optional[str]
    question_url: Optional[str]
    question_title: Optional[str]
    forecast_submitted: str
    error_count: int
    warning_count: int


@dataclass
class RunMetadata:
    """Metadata for a single workflow run."""
    run_id: int
    run_number: int
    created_at: str
    log_file: str
    downloaded_at: str
    questions_found: int
    conclusion: str


class LogDownloader:
    """Handles downloading and processing of GitHub Actions logs."""

    def __init__(self, repo: str, workflow: str, output_dir: Path, skip_existing: bool = False, fetch_titles: bool = False):
        self.repo = repo
        self.workflow = workflow
        self.output_dir = output_dir
        self.skip_existing = skip_existing
        self.fetch_titles = fetch_titles
        self.state_file = output_dir / "downloaded_logs_state.json"
        self.tsv_file = output_dir / "forecast_logs_metadata.tsv"
        self.report_file = output_dir / "download_logs_report.json"
        self.state = self._load_state()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict:
        """Load download state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
                return self._new_state()
        return self._new_state()

    def _new_state(self) -> Dict:
        """Create new empty state structure."""
        return {
            "downloaded_runs": {},
            "last_updated": None,
            "total_runs_downloaded": 0,
            "total_questions_processed": 0
        }

    def _save_state(self):
        """Save current state to JSON file."""
        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state file: {e}")

    def verify_gh_cli(self) -> bool:
        """Verify gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print("Error: gh CLI is not authenticated. Run 'gh auth login' first.")
                return False
            return True
        except FileNotFoundError:
            print("Error: gh CLI is not installed. Install from https://cli.github.com/")
            return False
        except Exception as e:
            print(f"Error checking gh CLI: {e}")
            return False

    def fetch_question_title(self, question_number: str) -> Optional[str]:
        """Fetch question title from Metaculus API."""
        if not self.fetch_titles or not question_number:
            return None

        try:
            url = f"https://www.metaculus.com/api2/questions/{question_number}/"

            # Add a small delay to avoid rate limiting
            time.sleep(0.3)

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; ForecastLogDownloader/1.0)')

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

                # Try to get the title from the response
                title = data.get('title')
                if title:
                    return title

                # Fallback: try to get the URL slug
                page_url = data.get('page_url', '')
                if page_url and '/questions/' in page_url:
                    # Extract slug from URL like /questions/41898/slug-here/
                    parts = page_url.rstrip('/').split('/')
                    if len(parts) >= 3:
                        slug = parts[-1]
                        if slug.isdigit():  # If last part is the number, no slug available
                            return None
                        return slug.replace('-', ' ').title()

                return None

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # Question not found
            elif e.code == 429:
                print(f"      Rate limited on question {question_number}, skipping title fetch")
                return None
            else:
                return None
        except Exception as e:
            # Silently skip on errors to avoid breaking the download process
            return None

    def get_workflow_runs(self, start_date: datetime, end_date: datetime, limit: Optional[int] = None) -> List[Dict]:
        """Query GitHub API for workflow runs in date range."""
        print(f"Querying workflow runs for {self.repo}/{self.workflow}...")

        try:
            # Get workflow runs using gh CLI
            cmd = [
                "gh", "api",
                f"repos/{self.repo}/actions/workflows/{self.workflow}/runs",
                "--paginate",
                "-q", ".workflow_runs[] | {id, run_number, created_at, conclusion, status}"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"Error querying workflow runs: {result.stderr}")
                return []

            # Parse JSON lines output
            runs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        run = json.loads(line)
                        runs.append(run)
                    except json.JSONDecodeError:
                        continue

            # Filter by date range
            filtered_runs = []
            for run in runs:
                created_at = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                if start_date <= created_at <= end_date:
                    filtered_runs.append(run)

            # Sort by run_number descending (newest first)
            filtered_runs.sort(key=lambda x: x['run_number'], reverse=True)

            # Apply limit if specified
            if limit:
                filtered_runs = filtered_runs[:limit]

            print(f"Found {len(filtered_runs)} runs in date range")
            return filtered_runs

        except Exception as e:
            print(f"Error querying workflow runs: {e}")
            return []

    def download_run_log(self, run_id: int, run_number: int, created_at: str, max_retries: int = 3) -> Optional[str]:
        """Download log for a single workflow run."""

        # Check if already downloaded
        if self.skip_existing and str(run_number) in self.state["downloaded_runs"]:
            existing_log = self.state["downloaded_runs"][str(run_number)]["log_file"]
            log_path = self.output_dir / existing_log
            if log_path.exists():
                print(f"  Skipping run {run_number} (already downloaded)")
                return str(log_path)

        # Generate log filename
        timestamp = created_at.replace(':', '-').replace('.', '-').split('+')[0].split('Z')[0]
        log_filename = f"run_{run_number}_{timestamp}.log"
        log_path = self.output_dir / log_filename

        print(f"  Downloading run {run_number}...")

        for attempt in range(max_retries):
            try:
                # Download log using gh CLI
                cmd = ["gh", "run", "view", str(run_id), "--repo", self.repo, "--log"]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode != 0:
                    if attempt < max_retries - 1:
                        print(f"    Retry {attempt + 1}/{max_retries - 1}...")
                        time.sleep(2)
                        continue
                    else:
                        print(f"    Error downloading log: {result.stderr}")
                        return None

                # Save log to file
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)

                print(f"    Saved to {log_filename}")
                return str(log_path)

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    Retry {attempt + 1}/{max_retries - 1}...")
                    time.sleep(2)
                    continue
                else:
                    print(f"    Error downloading log: {e}")
                    return None

        return None

    def extract_metadata_from_log(self, log_path: str, run_number: int, created_at: str) -> List[QuestionMetadata]:
        """Extract metadata from a log file."""

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except Exception as e:
            print(f"    Error reading log file: {e}")
            return []

        # Convert timestamps
        utc_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        mountain_time = utc_time.astimezone(MOUNTAIN_TZ)
        timestamp_utc = utc_time.strftime('%Y-%m-%d %H:%M:%S UTC')
        timestamp_mountain = mountain_time.strftime('%Y-%m-%d %H:%M:%S %Z')

        # Find all unique question URLs
        question_urls = list(set(QUESTION_URL_PATTERN.findall(log_content)))

        if not question_urls:
            # No questions found - create a single row with run info
            return [QuestionMetadata(
                run_number=run_number,
                timestamp_utc=timestamp_utc,
                timestamp_mountain=timestamp_mountain,
                question_number=None,
                question_url=None,
                question_title=None,
                forecast_submitted="No",
                error_count=len(ERROR_PATTERN.findall(log_content)),
                warning_count=len(WARNING_PATTERN.findall(log_content))
            )]

        # Extract metadata for each question
        metadata_list = []
        for url in question_urls:
            # Extract question number
            match = QUESTION_NUMBER_PATTERN.search(url)
            question_number = match.group(1) if match else None

            # Find the log section for this question
            # Look for lines containing the question URL, number, or related messages
            question_pattern = re.compile(
                rf'.*(?:{re.escape(url)}|(?:question|post|forecast_summaries/).*{question_number}|\b{question_number}\b).*',
                re.IGNORECASE
            )
            question_lines = [line for line in log_content.split('\n') if question_pattern.search(line)]
            question_section = '\n'.join(question_lines)

            # Count errors and warnings in this section
            error_count = len(ERROR_PATTERN.findall(question_section))
            warning_count = len(WARNING_PATTERN.findall(question_section))

            # Check for submission confirmation
            forecast_submitted = "Yes" if SUBMISSION_PATTERN.search(question_section) else "No"

            # Try to get question title - first from API if enabled, then from log patterns
            question_title = None
            if self.fetch_titles and question_number:
                question_title = self.fetch_question_title(question_number)

            # Fallback: try to extract from log patterns if API fetch failed or disabled
            if not question_title:
                title_patterns = [
                    re.compile(rf'question.*?{question_number}.*?["\']([^"\']+)["\']', re.IGNORECASE),
                    re.compile(rf'{question_number}.*?title.*?["\']([^"\']+)["\']', re.IGNORECASE),
                    re.compile(rf'Processing.*?["\']([^"\']+)["\']', re.IGNORECASE)
                ]
                for pattern in title_patterns:
                    match = pattern.search(question_section)
                    if match:
                        question_title = match.group(1)[:100]  # Limit to 100 chars
                        break

            metadata_list.append(QuestionMetadata(
                run_number=run_number,
                timestamp_utc=timestamp_utc,
                timestamp_mountain=timestamp_mountain,
                question_number=question_number,
                question_url=url,
                question_title=question_title,
                forecast_submitted=forecast_submitted,
                error_count=error_count,
                warning_count=warning_count
            ))

        return metadata_list

    def process_runs(self, runs: List[Dict]) -> List[QuestionMetadata]:
        """Download and process all workflow runs."""
        all_metadata = []

        for i, run in enumerate(runs, 1):
            run_id = run['id']
            run_number = run['run_number']
            created_at = run['created_at']
            conclusion = run.get('conclusion', 'unknown')

            print(f"\n[{i}/{len(runs)}] Processing run {run_number} (ID: {run_id})")

            # Download log
            log_path = self.download_run_log(run_id, run_number, created_at)

            if log_path:
                # Extract metadata
                metadata = self.extract_metadata_from_log(log_path, run_number, created_at)
                all_metadata.extend(metadata)

                # Update state
                self.state["downloaded_runs"][str(run_number)] = {
                    "run_id": run_id,
                    "created_at": created_at,
                    "log_file": Path(log_path).name,
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    "questions_found": len(metadata),
                    "conclusion": conclusion
                }
                self.state["total_runs_downloaded"] = len(self.state["downloaded_runs"])
                self.state["total_questions_processed"] += len(metadata)

                # Save state after each successful download
                self._save_state()

                print(f"    Extracted metadata for {len(metadata)} question(s)")
            else:
                print(f"    Failed to download log")

            # Rate limiting
            if i < len(runs):
                time.sleep(0.5)

        return all_metadata

    def generate_tsv(self, metadata_list: List[QuestionMetadata]):
        """Generate TSV file from metadata."""
        print(f"\nGenerating TSV file: {self.tsv_file}")

        try:
            with open(self.tsv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t')

                # Write header
                writer.writerow([
                    'run_number',
                    'timestamp_utc',
                    'timestamp_mountain',
                    'question_number',
                    'question_url',
                    'forecast_submitted',
                    'error_count',
                    'warning_count',
                    'question_title'
                ])

                # Sort by run_number descending
                metadata_list.sort(key=lambda x: x.run_number, reverse=True)

                # Write data rows
                for metadata in metadata_list:
                    writer.writerow([
                        metadata.run_number,
                        metadata.timestamp_utc,
                        metadata.timestamp_mountain,
                        metadata.question_number or 'None',
                        metadata.question_url or 'None',
                        metadata.forecast_submitted,
                        metadata.error_count,
                        metadata.warning_count,
                        metadata.question_title or 'None'
                    ])

            print(f"  Wrote {len(metadata_list)} rows to TSV")

        except Exception as e:
            print(f"Error generating TSV: {e}")

    def generate_report(self, metadata_list: List[QuestionMetadata]):
        """Generate summary report."""
        print(f"\nGenerating report: {self.report_file}")

        total_runs = len(self.state["downloaded_runs"])
        total_questions = len(metadata_list)
        questions_with_forecasts = sum(1 for m in metadata_list if m.forecast_submitted == "Yes")
        total_errors = sum(m.error_count for m in metadata_list)
        total_warnings = sum(m.warning_count for m in metadata_list)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_runs_downloaded": total_runs,
                "total_questions_processed": total_questions,
                "questions_with_forecasts": questions_with_forecasts,
                "total_errors": total_errors,
                "total_warnings": total_warnings
            },
            "output_files": {
                "tsv_file": str(self.tsv_file.name),
                "state_file": str(self.state_file.name),
                "log_directory": str(self.output_dir)
            }
        }

        try:
            with open(self.report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"  Report saved")
        except Exception as e:
            print(f"Error generating report: {e}")

        # Print summary to console
        print("\n" + "="*60)
        print("DOWNLOAD SUMMARY")
        print("="*60)
        print(f"Total runs downloaded:      {total_runs}")
        print(f"Total questions processed:  {total_questions}")
        print(f"Forecasts submitted:        {questions_with_forecasts}")
        print(f"Total errors:               {total_errors}")
        print(f"Total warnings:             {total_warnings}")
        print(f"\nOutput files:")
        print(f"  TSV:    {self.tsv_file}")
        print(f"  State:  {self.state_file}")
        print(f"  Report: {self.report_file}")
        print(f"  Logs:   {self.output_dir}")
        print("="*60)


def parse_args():
    """Parse command-line arguments."""
    # Default output directory: ../logs relative to this script
    default_output_dir = Path(__file__).parent.parent / "logs"

    parser = argparse.ArgumentParser(
        description="Download GitHub Actions workflow logs and extract forecast metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30
  python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --skip-existing
  python download_forecast_logs.py --start-date 2026-01-20 --end-date 2026-01-30 --limit 10
        """
    )

    parser.add_argument(
        '--start-date',
        required=True,
        help='Start of date range (YYYY-MM-DD, inclusive)'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End of date range (YYYY-MM-DD, inclusive)'
    )
    parser.add_argument(
        '--repo',
        default='D-Enns/metac-bot-template',
        help='GitHub repository (default: D-Enns/metac-bot-template)'
    )
    parser.add_argument(
        '--workflow',
        default='dre_run_bot_on_tournament.yaml',
        help='Workflow filename (default: dre_run_bot_on_tournament.yaml)'
    )
    parser.add_argument(
        '--output-dir',
        default=str(default_output_dir),
        help=f'Output directory for logs (default: {default_output_dir})'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip already downloaded runs'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of runs to process (for testing)'
    )
    parser.add_argument(
        '--fetch-titles',
        action='store_true',
        help='Fetch question titles from Metaculus API (slower but gets accurate titles)'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        print("Date format should be YYYY-MM-DD")
        sys.exit(1)

    if start_date > end_date:
        print("Error: start-date must be before or equal to end-date")
        sys.exit(1)

    # Initialize downloader
    output_dir = Path(args.output_dir)
    downloader = LogDownloader(
        repo=args.repo,
        workflow=args.workflow,
        output_dir=output_dir,
        skip_existing=args.skip_existing,
        fetch_titles=args.fetch_titles
    )

    # Verify gh CLI
    if not downloader.verify_gh_cli():
        sys.exit(1)

    print("\n" + "="*60)
    print("GITHUB ACTIONS LOG DOWNLOADER")
    print("="*60)
    print(f"Repository:    {args.repo}")
    print(f"Workflow:      {args.workflow}")
    print(f"Date range:    {args.start_date} to {args.end_date}")
    print(f"Output dir:    {output_dir}")
    print(f"Skip existing: {args.skip_existing}")
    print(f"Fetch titles:  {args.fetch_titles}")
    if args.limit:
        print(f"Limit:         {args.limit} runs")
    print("="*60 + "\n")

    # Get workflow runs
    runs = downloader.get_workflow_runs(start_date, end_date, args.limit)

    if not runs:
        print("\nNo workflow runs found in date range")
        sys.exit(0)

    # Process runs
    metadata_list = downloader.process_runs(runs)

    # Generate outputs
    if metadata_list:
        downloader.generate_tsv(metadata_list)
        downloader.generate_report(metadata_list)
    else:
        print("\nNo metadata extracted")

    print("\nDone!")


if __name__ == "__main__":
    main()
