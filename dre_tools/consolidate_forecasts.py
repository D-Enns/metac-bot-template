#!/usr/bin/env python3
"""
Consolidate Forecast Files - Remove Duplicates

Consolidates all forecast files from run_* subdirectories into a single
"consolidated" folder, removing duplicates based on filename and content hash.
"""

import hashlib
import shutil
from pathlib import Path
from collections import defaultdict


def get_file_hash(filepath):
    """Calculate MD5 hash of file content"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def consolidate_forecasts(source_dir="forecast_summaries", target_subdir="consolidated"):
    """Consolidate all forecast files into single directory"""

    source_path = Path(source_dir)
    target_path = source_path / target_subdir

    # Create target directory
    target_path.mkdir(exist_ok=True)

    print("=" * 80)
    print("FORECAST FILE CONSOLIDATION")
    print("=" * 80)
    print(f"\nSource: {source_path.absolute()}")
    print(f"Target: {target_path.absolute()}")
    print(f"\nProcessing run_* subdirectories...")
    print("-" * 80)

    # Track files and their hashes
    file_registry = {}  # filename -> (path, hash, size)
    stats = {
        "total_files_found": 0,
        "unique_files": 0,
        "duplicates_skipped": 0,
        "errors": 0
    }

    # Process each run directory
    run_dirs = sorted(source_path.glob("run_*"))

    if not run_dirs:
        print("❌ No run_* directories found!")
        return

    print(f"Found {len(run_dirs)} run directories to process\n")

    for i, run_dir in enumerate(run_dirs, 1):
        if (i - 1) % 50 == 0:
            print(f"Processing {i}/{len(run_dirs)}...")

        # Process all files in this run directory
        for file_path in run_dir.iterdir():
            if not file_path.is_file():
                continue

            # Skip hidden files and non-forecast files
            if file_path.name.startswith('.'):
                continue

            stats["total_files_found"] += 1
            filename = file_path.name

            # Check if we've seen this filename before
            if filename in file_registry:
                # Compare file hashes to detect true duplicates
                existing_path, existing_hash, existing_size = file_registry[filename]
                current_hash = get_file_hash(file_path)

                if current_hash == existing_hash:
                    # True duplicate - skip
                    stats["duplicates_skipped"] += 1
                    continue
                else:
                    # Same filename, different content - this shouldn't happen often
                    # Use run number to disambiguate
                    run_num = run_dir.name.replace("run_", "")
                    new_filename = f"{file_path.stem}_run{run_num}{file_path.suffix}"
                    target_file = target_path / new_filename
                    print(f"  ⚠️  Different content for {filename}, saving as {new_filename}")
            else:
                # New file
                target_file = target_path / filename

            # Copy file to consolidated directory
            try:
                if not target_file.exists():
                    shutil.copy2(file_path, target_file)

                    # Register this file
                    file_hash = get_file_hash(target_file)
                    file_size = target_file.stat().st_size
                    file_registry[filename] = (target_file, file_hash, file_size)

                    stats["unique_files"] += 1
                else:
                    stats["duplicates_skipped"] += 1

            except Exception as e:
                print(f"  ❌ Error copying {file_path.name}: {e}")
                stats["errors"] += 1

    # Generate summary
    print("\n" + "=" * 80)
    print("CONSOLIDATION SUMMARY")
    print("=" * 80)
    print(f"\n📊 Statistics:")
    print(f"  Total files found: {stats['total_files_found']}")
    print(f"  ✓ Unique files copied: {stats['unique_files']}")
    print(f"  ⊙ Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"  ❌ Errors: {stats['errors']}")

    # Break down by file type
    print(f"\n📁 Files in consolidated directory:")
    full_summaries = list(target_path.glob("*_full_*.md"))
    condensed_summaries = list(target_path.glob("*_condensed_*.md"))
    scenario_files = list(target_path.glob("*_scenarios_*.json"))
    other_files = [f for f in target_path.iterdir()
                   if f.is_file() and f not in full_summaries + condensed_summaries + scenario_files]

    print(f"  Full summaries: {len(full_summaries)}")
    print(f"  Condensed summaries: {len(condensed_summaries)}")
    print(f"  Scenario JSONs: {len(scenario_files)}")
    if other_files:
        print(f"  Other files: {len(other_files)}")

    # Extract unique question IDs
    question_ids = set()
    for file in target_path.glob("*.md"):
        # Extract question ID from filename (first numeric part)
        parts = file.stem.split('_')
        if parts[0].isdigit():
            question_ids.add(parts[0])

    print(f"\n📝 Unique questions: {len(question_ids)}")
    print(f"  Question IDs: {', '.join(sorted(question_ids, key=int)[:20])}...")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in target_path.iterdir() if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"\n💾 Total size: {size_mb:.1f} MB")
    print(f"\n✅ Consolidation complete!")
    print(f"   Files are in: {target_path.absolute()}")


if __name__ == "__main__":
    consolidate_forecasts()
