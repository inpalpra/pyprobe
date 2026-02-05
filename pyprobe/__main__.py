"""
PyProbe entry point.

Usage:
    python -m pyprobe [script.py]
"""

import sys
import argparse


def main():
    """Main entry point for PyProbe."""
    parser = argparse.ArgumentParser(
        description="PyProbe - LabVIEW-style variable probe for Python DSP debugging"
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Python script to probe (optional, can be loaded from GUI)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="append",
        default=["received_symbols", "signal_i", "signal_q", "snr_db"],
        help="Variable names to watch (can be specified multiple times)"
    )

    args = parser.parse_args()

    # Import here to avoid slow startup for --help
    from .gui.app import run_app

    # Run the application
    sys.exit(run_app(script_path=args.script, watch_variables=args.watch))


if __name__ == "__main__":
    main()
