"""
PyProbe entry point.

Usage:
    python -m pyprobe [script.py]
    python -m pyprobe --loglevel DEBUG examples/dsp_demo.py
    python -m pyprobe --trace-states examples/dsp_demo.py
"""

import sys
import argparse


def main():
    """Main entry point for PyProbe."""
    parser = argparse.ArgumentParser(
        description="PyProbe - Variable probing based debugger for Python DSP debugging"
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Python script to probe (optional, can be loaded from GUI)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="append",
        default=["received_symbols", "signal_i", "signal_q", "snr_db", "power_db","peak_to_avg"],
        help="Variable names to watch (can be specified multiple times)"
    )
    parser.add_argument(
        "-l", "--loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
        help="Set logging level (default: WARNING). DEBUG writes to /tmp/pyprobe_debug.log"
    )
    parser.add_argument(
        "--logfile",
        default="/tmp/pyprobe_debug.log",
        help="Log file path (default: /tmp/pyprobe_debug.log)"
    )
    parser.add_argument(
        "--log-console",
        action="store_true",
        help="Also log to console (stderr)"
    )
    parser.add_argument(
        "--trace-states",
        action="store_true",
        help="Enable detailed state tracing. Logs all user actions and reactions to /tmp/pyprobe_state_trace.log"
    )

    args = parser.parse_args()

    # Initialize state tracer FIRST if requested
    if args.trace_states:
        from .state_tracer import init_tracer
        init_tracer(enabled=True)
        print("State tracing enabled. Log: /tmp/pyprobe_state_trace.log")

    # Setup logging before importing anything else
    from .logging import setup_logging
    setup_logging(
        level=args.loglevel,
        log_file=args.logfile,
        console=args.log_console
    )

    # Import here to avoid slow startup for --help
    from .gui.app import run_app

    # Run the application
    sys.exit(run_app(script_path=args.script, watch_variables=args.watch))


if __name__ == "__main__":
    main()

