#!/usr/bin/env python
"""
run_tests.py — Auto-discover and run all pyprobe test suites.

Scans the tests/ directory for test files, groups them by suite
(core / gui / ipc / top-level), then runs each group with pytest.

Usage:
    python run_tests.py                   # run all suites
    python run_tests.py --suite gui       # run one suite by name
    python run_tests.py --failfast        # stop on first failure
    python run_tests.py --no-header       # skip the pretty header
    python run_tests.py -v                # pass -v through to pytest
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.resolve()
TESTS_DIR = REPO_ROOT / "tests"

# Subdirectories (relative to TESTS_DIR) that form named suites.
# Order controls execution order.
SUITE_DIRS = ["core", "ipc", "gui", "report"]

# Files in TESTS_DIR itself that are not conftest / helpers.
# Any file matching test_*.py at the top level forms the "top-level" suite.

# Files to exclude from discovery (helpers, not proper test modules).
EXCLUDE_FILES = {"check_scroll_click.py", "conftest.py"}


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover_suites(tests_dir: Path) -> dict[str, list[Path]]:
    """Return an ordered dict of {suite_name: [test_file, ...]}."""
    suites: dict[str, list[Path]] = {}

    # Named sub-directory suites first (in declared order).
    for sub in SUITE_DIRS:
        sub_path = tests_dir / sub
        if not sub_path.is_dir():
            continue
        files = sorted(
            p for p in sub_path.glob("test_*.py")
            if p.name not in EXCLUDE_FILES
        )
        if files:
            suites[sub] = files

    # Top-level test files last.
    top = sorted(
        p for p in tests_dir.glob("test_*.py")
        if p.name not in EXCLUDE_FILES
    )
    if top:
        suites["top-level"] = top

    return suites


# ── Runner ────────────────────────────────────────────────────────────────────

def run_suite(
    name: str,
    files: list[Path],
    extra_args: list[str],
    failfast: bool,
) -> tuple[int, float]:
    """
    Run pytest on a list of files.

    Returns (returncode, elapsed_seconds).
    """
    cmd = [sys.executable, "-m", "pytest"]
    cmd += [str(f) for f in files]
    cmd += extra_args
    if failfast:
        cmd.append("-x")

    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.perf_counter() - t0

    return result.returncode, elapsed


# ── Formatting ────────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def banner(text: str) -> None:
    width = 72
    print(f"\n{BOLD}{'═' * width}")
    print(f"  {text}")
    print(f"{'═' * width}{RESET}\n")


def status_line(name: str, rc: int, elapsed: float) -> None:
    label = f"{GREEN}PASSED{RESET}" if rc == 0 else f"{RED}FAILED{RESET}"
    print(f"  {BOLD}{name:<14}{RESET}  {label}   ({elapsed:.1f}s)")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and run all pyprobe test suites."
    )
    parser.add_argument(
        "--suite",
        metavar="NAME",
        help="Run only the named suite (core | ipc | gui | report | top-level).",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Stop after the first test failure.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Skip the discovery summary header.",
    )
    # Collect any extra flags (e.g. -v, --tb=short) and forward to pytest.
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments forwarded verbatim to pytest.",
    )
    args = parser.parse_args()

    suites = discover_suites(TESTS_DIR)
    if not suites:
        print(f"{RED}No test suites found under {TESTS_DIR}{RESET}")
        return 1

    # Filter by --suite if requested.
    if args.suite:
        if args.suite not in suites:
            available = ", ".join(suites)
            print(f"{RED}Unknown suite '{args.suite}'. Available: {available}{RESET}")
            return 1
        suites = {args.suite: suites[args.suite]}

    if not args.no_header:
        total_files = sum(len(v) for v in suites.values())
        banner(f"pyprobe test runner — {len(suites)} suite(s), {total_files} file(s)")
        for suite_name, files in suites.items():
            print(f"  {YELLOW}{suite_name}{RESET}  ({len(files)} file(s))")
            for f in files:
                print(f"    {f.relative_to(REPO_ROOT)}")
        print()

    results: list[tuple[str, int, float]] = []
    overall_rc = 0

    for suite_name, files in suites.items():
        banner(f"Suite: {suite_name}")
        rc, elapsed = run_suite(suite_name, files, args.pytest_args, args.failfast)
        results.append((suite_name, rc, elapsed))
        if rc != 0:
            overall_rc = rc
            if args.failfast:
                break

    # Summary.
    banner("Results")
    total_elapsed = sum(e for _, _, e in results)
    for name, rc, elapsed in results:
        status_line(name, rc, elapsed)
    print(f"\n  Total time: {total_elapsed:.1f}s")

    if overall_rc == 0:
        print(f"\n  {BOLD}{GREEN}All suites passed.{RESET}")
    else:
        failing = [n for n, rc, _ in results if rc != 0]
        print(f"\n  {BOLD}{RED}Failed suites: {', '.join(failing)}{RESET}")

    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
