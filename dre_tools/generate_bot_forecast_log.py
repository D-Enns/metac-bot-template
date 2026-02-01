#!/usr/bin/env python3
"""
Bot Forecast Log Generator

Generates a TSV (Tab-Separated Values) file containing one row per forecast,
extracting data from condensed forecast summary markdown files.

The output TSV contains:
- run (empty, to be populated externally)
- forecast_number
- date
- time
- question_type
- tournament_name
- question_url
- comments (empty, to be populated externally)
- forecast (JSON formatted, varies by question type)
- community_forecast (empty, to be populated externally)
- score (empty, to be populated externally)
- community_score (empty, to be populated externally)
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class ForecastLogGenerator:
    """Generates TSV log from condensed forecast summaries"""

    def __init__(self, source_dir: str, output_file: str, verbose: bool = False):
        self.source_dir = Path(source_dir)
        self.output_file = Path(output_file)
        self.verbose = verbose

        # Statistics tracking
        self.stats = {
            'total_files_found': 0,
            'successfully_parsed': 0,
            'skipped_non_condensed': 0,
            'read_errors': 0,
            'parse_errors': 0,
            'missing_metadata': 0,
            'validation_errors': 0,
            'question_types': {
                'Binary': 0,
                'Multiple Choice': 0,
                'Numeric': 0,
                'Other': 0
            }
        }

        # Parsed forecast data
        self.forecasts = []

    def find_condensed_summaries(self) -> List[Path]:
        """Find all condensed summary files in source directory"""
        if not self.source_dir.exists():
            raise ValueError(f"Source directory not found: {self.source_dir}")

        # Find files matching pattern *_condensed_*.md
        files = sorted(self.source_dir.glob("*_condensed_*.md"))
        return files

    def extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract metadata from FORECAST METADATA section"""
        metadata = {}

        # Find the FORECAST METADATA section
        metadata_section = re.search(
            r'# FORECAST METADATA\s*\n(.*?)\n---',
            content,
            re.DOTALL
        )

        if not metadata_section:
            return metadata

        section_text = metadata_section.group(1)

        # Extract all **Field**: value pairs
        pattern = r'\*\*(.+?)\*\*:\s*(.+?)(?:\n|$)'
        matches = re.findall(pattern, section_text)

        for field, value in matches:
            field = field.strip()
            value = value.strip()

            # Extract URL from markdown links [text](url)
            if field == 'Question URL':
                url_match = re.search(r'\[([^\]]*)\]\(([^\)]+)\)', value)
                if url_match:
                    value = url_match.group(2)

            # Remove 'q' prefix from Forecast ID
            if field == 'Forecast ID' and value.startswith('q'):
                value = value[1:]

            metadata[field] = value

        return metadata

    def extract_forecast_number_from_filename(self, filename: str) -> Optional[str]:
        """Extract forecast number from filename (e.g., '41871_spring_aib_2026_condensed_1.md' -> '41871')"""
        match = re.match(r'^(\d+)_', filename)
        if match:
            return match.group(1)
        return None

    def extract_binary_forecast(self, content: str) -> str:
        """Extract forecast value for Binary questions"""
        # Pattern: *Final Prediction*: XX.XX%
        pattern = r'\*Final Prediction\*:\s*(\d+\.?\d*)%?'
        match = re.search(pattern, content)

        if match:
            return match.group(1)

        raise ValueError("Could not extract binary forecast value")

    def extract_multiple_choice_forecast(self, content: str) -> str:
        """Extract forecast values for Multiple Choice questions"""
        # Find the Final Prediction section
        prediction_section = re.search(
            r'\*Final Prediction\*:\s*\n((?:- .+?:\s*\d+\.?\d*%?\s*\n?)+)',
            content,
            re.MULTILINE
        )

        if not prediction_section:
            raise ValueError("Could not find Final Prediction section for Multiple Choice")

        section_text = prediction_section.group(1)

        # Extract option-percentage pairs
        # Pattern: - option: percentage%
        pattern = r'-\s*(.+?):\s*(\d+\.?\d*)%?'
        matches = re.findall(pattern, section_text)

        if not matches:
            raise ValueError("Could not extract Multiple Choice options")

        # Build dictionary with underscores replacing spaces
        forecast_dict = {}
        for option, percentage in matches:
            option = option.strip()
            # Replace spaces with underscores in option names
            option = option.replace(' ', '_')
            forecast_dict[option] = float(percentage)

        return json.dumps(forecast_dict)

    def extract_numeric_forecast(self, content: str) -> str:
        """Extract forecast values for Numeric questions"""
        # Pattern: XX.XX% chance of value below YY.YY
        pattern = r'(\d+\.?\d*)%\s+chance of value below\s+([\d.]+)'
        matches = re.findall(pattern, content)

        if not matches:
            raise ValueError("Could not extract Numeric percentile values")

        # Map percentages to percentile keys
        percentile_map = {
            '1': 'p1', '1.0': 'p1', '1.00': 'p1',
            '5': 'p5', '5.0': 'p5', '5.00': 'p5',
            '25': 'p25', '25.0': 'p25', '25.00': 'p25',
            '50': 'p50', '50.0': 'p50', '50.00': 'p50',
            '75': 'p75', '75.0': 'p75', '75.00': 'p75',
            '95': 'p95', '95.0': 'p95', '95.00': 'p95',
            '99': 'p99', '99.0': 'p99', '99.00': 'p99'
        }

        # Build percentile dictionary
        forecast_dict = {}
        for percentile_str, value_str in matches:
            # Normalize percentile string (remove trailing zeros)
            percentile_normalized = percentile_str.rstrip('0').rstrip('.')

            if percentile_normalized in percentile_map:
                key = percentile_map[percentile_normalized]
                forecast_dict[key] = float(value_str)

        if not forecast_dict:
            raise ValueError("Could not map percentiles to standard format")

        return json.dumps(forecast_dict)

    def extract_forecast_values(self, content: str, question_type: str) -> str:
        """Extract forecast values based on question type"""
        try:
            if question_type == 'Binary':
                return self.extract_binary_forecast(content)
            elif question_type == 'Multiple Choice':
                return self.extract_multiple_choice_forecast(content)
            elif question_type == 'Numeric':
                return self.extract_numeric_forecast(content)
            else:
                return f"ERROR: Unknown question type '{question_type}'"
        except Exception as e:
            if self.verbose:
                print(f"    Error extracting forecast values: {e}")
            raise

    def parse_condensed_summary(self, file_path: Path) -> Optional[Dict]:
        """Parse a single condensed summary file and extract all data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"  ❌ Failed to read {file_path.name}: {e}")
            self.stats['read_errors'] += 1
            return None

        # Extract forecast number from filename
        forecast_number = self.extract_forecast_number_from_filename(file_path.name)
        if not forecast_number:
            if self.verbose:
                print(f"  ⚠️  Could not extract forecast number from {file_path.name}")
            self.stats['parse_errors'] += 1
            return None

        # Extract metadata
        metadata = self.extract_metadata(content)

        # Validate required metadata fields
        required_fields = ['Forecast Date', 'Question Type', 'Question URL']
        missing_fields = [f for f in required_fields if f not in metadata]

        if missing_fields:
            if self.verbose:
                print(f"  ⚠️  Missing metadata in {file_path.name}: {', '.join(missing_fields)}")
            self.stats['missing_metadata'] += 1
            return None

        # Parse forecast date into date and time
        try:
            forecast_datetime = metadata['Forecast Date']
            # Parse formats like "2026-01-26 19:33:47 UTC"
            dt_match = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', forecast_datetime)
            if dt_match:
                date = dt_match.group(1)
                time = dt_match.group(2)
            else:
                # Try parsing with datetime
                dt = datetime.fromisoformat(forecast_datetime.replace(' UTC', ''))
                date = dt.strftime('%Y-%m-%d')
                time = dt.strftime('%H:%M:%S')
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not parse date in {file_path.name}: {e}")
            self.stats['parse_errors'] += 1
            return None

        question_type = metadata['Question Type']
        question_url = metadata['Question URL']
        tournament_name = metadata.get('Tournament', '')  # Get tournament name, default to empty

        # Extract forecast values
        try:
            forecast_values = self.extract_forecast_values(content, question_type)
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not parse forecast values in {file_path.name}: {e}")
            self.stats['parse_errors'] += 1
            forecast_values = f"ERROR: {str(e)}"

        # Build row dictionary
        row = {
            'run': '',  # Empty, to be populated externally
            'forecast_number': forecast_number,
            'date': date,
            'time': time,
            'question_type': question_type,
            'tournament_name': tournament_name,
            'question_url': question_url,
            'comments': '',  # Empty, to be populated externally
            'forecast': forecast_values,
            'community_forecast': '',  # Empty, to be populated externally
            'score': '',  # Empty, to be populated externally
            'community_score': ''  # Empty, to be populated externally
        }

        return row

    def validate_row(self, row: Dict) -> Tuple[bool, Optional[str]]:
        """Validate row data before writing"""
        required_fields = ['forecast_number', 'date', 'time', 'question_type', 'question_url']

        for field in required_fields:
            if not row.get(field):
                return False, f"Missing {field}"

        # Validate date format
        try:
            datetime.strptime(row['date'], '%Y-%m-%d')
        except ValueError:
            return False, "Invalid date format"

        # Validate time format
        try:
            datetime.strptime(row['time'], '%H:%M:%S')
        except ValueError:
            return False, "Invalid time format"

        return True, None

    def generate_tsv(self, dry_run: bool = False) -> None:
        """Main method: process all files and generate TSV"""
        print("=" * 80)
        print("BOT FORECAST LOG GENERATOR")
        print("=" * 80)
        print(f"\nSource directory: {self.source_dir.absolute()}")
        print(f"Output file: {self.output_file.absolute()}")

        if dry_run:
            print("\n⚠️  DRY RUN MODE - No file will be written")

        print("\nProcessing condensed forecast summaries...")
        print("-" * 80)

        # Find all condensed summary files
        files = self.find_condensed_summaries()
        self.stats['total_files_found'] = len(files)

        if not files:
            print("\n❌ No condensed summary files found!")
            return

        print(f"\nFound {len(files)} condensed summary files\n")

        if self.verbose:
            print("Processing files:")

        # Process each file
        for file_path in files:
            row = self.parse_condensed_summary(file_path)

            if row:
                # Validate row
                valid, error_msg = self.validate_row(row)

                if valid:
                    self.forecasts.append(row)
                    self.stats['successfully_parsed'] += 1

                    # Track question type
                    q_type = row['question_type']
                    if q_type in self.stats['question_types']:
                        self.stats['question_types'][q_type] += 1
                    else:
                        self.stats['question_types']['Other'] += 1

                    if self.verbose:
                        print(f"  ✓ {file_path.name} ({q_type})")
                else:
                    self.stats['validation_errors'] += 1
                    if self.verbose:
                        print(f"  ❌ Validation failed for {file_path.name}: {error_msg}")

        # Write TSV file
        if not dry_run and self.forecasts:
            self.write_tsv()

        # Print summary
        self.print_summary()

    def write_tsv(self) -> None:
        """Write forecasts to TSV file"""
        # Define column order
        columns = ['run', 'forecast_number', 'date', 'time', 'question_type',
                   'tournament_name', 'question_url', 'comments', 'forecast',
                   'community_forecast', 'score', 'community_score']

        # Sort forecasts by date and time (oldest to newest)
        sorted_forecasts = sorted(self.forecasts, key=lambda x: (x['date'], x['time']))

        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write('\t'.join(columns) + '\n')

            # Write data rows
            for row in sorted_forecasts:
                values = [str(row.get(col, '')) for col in columns]
                # Escape any tabs in the data
                values = [v.replace('\t', ' ') for v in values]
                f.write('\t'.join(values) + '\n')

    def print_summary(self) -> None:
        """Print generation summary"""
        print("\n" + "=" * 80)
        print("GENERATION SUMMARY")
        print("=" * 80)

        print(f"\nStatistics:")
        print(f"  Total files found: {self.stats['total_files_found']}")
        print(f"  ✓ Successfully parsed: {self.stats['successfully_parsed']}")
        print(f"  ⊙ Skipped (non-condensed): {self.stats['skipped_non_condensed']}")
        print(f"  ⚠️  Parse errors: {self.stats['parse_errors']}")
        print(f"  ⚠️  Missing metadata: {self.stats['missing_metadata']}")
        print(f"  ⚠️  Validation errors: {self.stats['validation_errors']}")
        print(f"  ❌ Read errors: {self.stats['read_errors']}")

        # Question type breakdown
        print(f"\nForecast Types:")
        for q_type, count in self.stats['question_types'].items():
            if count > 0:
                print(f"  {q_type}: {count}")

        if self.forecasts:
            print(f"\nOutput saved to: {self.output_file.absolute()}")
            print(f"Total rows written: {len(self.forecasts)}")

            # Show sample rows
            print(f"\nSample rows:")
            for i, row in enumerate(sorted(self.forecasts, key=lambda x: int(x['forecast_number']))[:3]):
                print(f"  {row['forecast_number']} | {row['date']} {row['time']} | {row['question_type']}")

            print(f"\n✅ Log generation complete!")
        else:
            print(f"\n❌ No valid forecasts found - no file written")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate Bot Forecast Log TSV from condensed forecast summaries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate TSV from all condensed summaries (default)
  python generate_bot_forecast_log.py

  # Specify custom source directory
  python generate_bot_forecast_log.py --source-dir custom_forecasts/

  # Specify custom output file
  python generate_bot_forecast_log.py --output custom_log.tsv

  # Dry run (validate without writing)
  python generate_bot_forecast_log.py --dry-run

  # Verbose mode for debugging
  python generate_bot_forecast_log.py --verbose
        """
    )

    parser.add_argument(
        '--source-dir',
        default='all_forecast_summaries',
        help='Directory containing condensed forecast summaries (default: all_forecast_summaries)'
    )

    parser.add_argument(
        '--output',
        default='all_forecast_summaries/bot_forecast_log.tsv',
        help='Output TSV file path (default: all_forecast_summaries/bot_forecast_log.tsv)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate files without writing output'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed parsing information'
    )

    args = parser.parse_args()

    # Create generator and run
    generator = ForecastLogGenerator(
        source_dir=args.source_dir,
        output_file=args.output,
        verbose=args.verbose
    )

    generator.generate_tsv(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
