"""
PyProbe entry point.

Usage:
    python -m pyprobe [script.py]
    python -m pyprobe --loglevel DEBUG examples/dsp_demo.py
    python -m pyprobe --trace-states examples/dsp_demo.py
"""

import sys
import os
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
        "--auto-run",
        action="store_true",
        help="Automatically run the script after loading"
    )
    parser.add_argument(
        "--auto-quit",
        action="store_true",
        help="Automatically quit the application when the script finishes"
    )
    parser.add_argument(
        "--auto-quit-timeout",
        type=float,
        default=None,
        help="Force quit after specified seconds, even if errors prevent normal auto-quit (default: infinite)"
    )
    parser.add_argument(
        "-p", "--probe",
        action="append",
        help="Add graphical probe. Format: line:symbol:instance (e.g., 4:x:1)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="append",
        help="Add scalar watch. Format: line:symbol:instance (e.g., 4:x:1)"
    )
    parser.add_argument(
        "--overlay",
        action="append",
        help="Overlay a signal on an existing probe. Format: target_symbol:line:symbol:instance "
             "(e.g., signal_i:75:received_symbols:1 overlays received_symbols onto signal_i)"
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

    # Auto-detect file vs. folder
    script_path = args.script
    folder_path = None
    if script_path and os.path.isdir(script_path):
        folder_path = os.path.abspath(script_path)
        script_path = None

    # Run the application
    sys.exit(run_app(
        script_path=script_path,
        folder_path=folder_path,
        probes=args.probe,
        watches=args.watch,
        overlays=args.overlay,
        auto_run=args.auto_run,
        auto_quit=args.auto_quit,
        auto_quit_timeout=args.auto_quit_timeout
    ))


if __name__ == "__main__":
    main()

