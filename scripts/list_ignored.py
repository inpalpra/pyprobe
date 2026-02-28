#!/usr/bin/env python3
"""List all files and directories ignored by .gitignore and ~/.gitignore_global."""

import subprocess
import sys
from pathlib import Path


def get_ignored_items():
    """Use `git status --ignored` to find all ignored files/dirs."""
    result = subprocess.run(
        ["git", "status", "--ignored", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    # Lines starting with "!! " are ignored items
    return [line[3:] for line in result.stdout.splitlines() if line.startswith("!! ")]


def get_ignore_source(path: str) -> str:
    """Use `git check-ignore -v` to find which rule ignores a path."""
    result = subprocess.run(
        ["git", "check-ignore", "-v", path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return "unknown"
    # Output format: <source>:<line>:<pattern>\t<path>
    parts = result.stdout.strip().split("\t")[0]
    source_file, line_no, pattern = parts.split(":")
    return f"{source_file}:{line_no}  ({pattern})"


def main():
    items = get_ignored_items()
    if not items:
        print("No ignored files found.")
        return

    # Separate files and directories
    dirs = sorted(p for p in items if p.endswith("/"))
    files = sorted(p for p in items if not p.endswith("/"))

    print(f"{'─' * 70}")
    print(f"  Ignored directories: {len(dirs)}    Ignored files: {len(files)}")
    print(f"{'─' * 70}\n")

    if dirs:
        print("📁 DIRECTORIES")
        for d in dirs:
            source = get_ignore_source(d.rstrip("/"))
            print(f"  {d:<45} ← {source}")

    if files:
        print("\n📄 FILES")
        for f in files:
            source = get_ignore_source(f)
            print(f"  {f:<45} ← {source}")

    print(f"\n{'─' * 70}")
    print(f"  Total: {len(dirs)} directories, {len(files)} files")


if __name__ == "__main__":
    main()
