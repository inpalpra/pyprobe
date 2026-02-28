#!./.venv/bin/python
"""
Profile GUI tests and generate HTML performance report.

Uses pytest-json-report.
Outputs in tmp/:
- gui_profile.json
- gui_profile_<run_id>[_headless].html
- gui_profile_aggregated_<run_id>[_headless].html

Usage Examples:
    # Run all tests in 'tests' directory
    ./scripts/profile.py
    
    # Run tests in a specific file
    ./scripts/profile.py tests/gui/test_probe_temporal_fast.py
    
    # Run tests in headless mode
    ./scripts/profile.py tests/gui/test_folder_browsing_fast.py --headless
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse
import os
from collections import defaultdict
from datetime import datetime


# ────────────────────────────────────────────────────────────────
# Root Detection
# ────────────────────────────────────────────────────────────────

def find_project_root(start: Path) -> Path:
    current = start.resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find pyproject.toml.")

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = find_project_root(SCRIPT_PATH.parent)

TMP_DIR = PROJECT_ROOT / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# Random Phrase Generator (base36 suffix)
# ────────────────────────────────────────────────────────────────

import secrets
import string

ADJECTIVES = [
    "silent", "frozen", "rapid", "golden", "crimson",
    "electric", "ancient", "hidden", "cosmic", "neon",
    "velvet", "shaded", "silver", "wild", "burning",
]

COLORS = [
    "blue", "red", "amber", "violet", "indigo",
    "emerald", "scarlet", "teal", "obsidian", "ivory",
]

ANIMALS = [
    "falcon", "tiger", "panther", "wolf", "eagle",
    "otter", "lynx", "raven", "orca", "cobra",
]

BASE36_ALPHABET = string.digits + string.ascii_lowercase  # 0-9a-z


def random_base36(n=4):
    return ''.join(secrets.choice(BASE36_ALPHABET) for _ in range(n))


def random_phrase():
    return (
        f"{secrets.choice(ADJECTIVES)}_"
        f"{secrets.choice(COLORS)}_"
        f"{secrets.choice(ANIMALS)}_"
        f"{random_base36(4)}"
    )


PHRASE = random_phrase()

JSON_FILE = TMP_DIR /  f"gui_profile.json"


# ────────────────────────────────────────────────────────────────
# Run pytest
# ────────────────────────────────────────────────────────────────

def run_pytest(target: str | None, headless: bool):
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-n", "0",
        "--json-report",
        f"--json-report-file={JSON_FILE}",
        "-q",
        "-o", "console_output_style=classic",
    ]

    if target:
        cmd.append(target)

    env = os.environ.copy()

    # Headless mode = force Qt offscreen
    if headless and "QT_QPA_PLATFORM" not in env:
        env["QT_QPA_PLATFORM"] = "offscreen"

    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Output directory: {TMP_DIR}")
    print(f"Profiling target: {target or 'ALL TESTS'}")
    print(f"Headless mode: {'ON' if headless else 'OFF'}\n")
    print(f"Run ID: {PHRASE}\n")

    subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)


# ────────────────────────────────────────────────────────────────
# Generate HTML
# ────────────────────────────────────────────────────────────────

def generate_html(headless: bool):
    with open(JSON_FILE) as f:
        data = json.load(f)

    rows = []
    file_aggregates = defaultdict(lambda: {"setup": 0.0, "call": 0.0, "teardown": 0.0, "total": 0.0})

    for test in data.get("tests", []):
        nodeid = test["nodeid"]
        setup = test.get("setup", {}).get("duration", 0.0)
        call = test.get("call", {}).get("duration", 0.0)
        teardown = test.get("teardown", {}).get("duration", 0.0)
        total = setup + call + teardown

        rows.append({
            "name": nodeid,
            "setup": setup,
            "call": call,
            "teardown": teardown,
            "total": total,
        })
        
        file_path = nodeid.split("::")[0]
        file_aggregates[file_path]["setup"] += setup
        file_aggregates[file_path]["call"] += call
        file_aggregates[file_path]["teardown"] += teardown
        file_aggregates[file_path]["total"] += total

    rows.sort(key=lambda r: r["total"], reverse=True)
    
    agg_rows = []
    for fpath, stats in file_aggregates.items():
        agg_rows.append({
            "name": fpath,
            "setup": stats["setup"],
            "call": stats["call"],
            "teardown": stats["teardown"],
            "total": stats["total"]
        })
    agg_rows.sort(key=lambda r: r["total"], reverse=True)

    headless_suffix = "_headless" if headless else ""
    headless_text = "Yes" if headless else "No"
    run_time = datetime.now().strftime("Date: %Y-%m-%d Time: %H-%M-%S")

    html_file = TMP_DIR / f"gui_profile_{PHRASE}{headless_suffix}.html"
    agg_html_file = TMP_DIR / f"gui_profile_aggregated_{PHRASE}{headless_suffix}.html"

    def render_html(title, report_rows, out_file):
        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title} — {PHRASE}</title>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    background: #111;
    color: #eee;
    padding: 40px;
}}
h1 {{
    margin-bottom: 20px;
}}
.subtitle {{
    margin-bottom: 5px;
    color: #ccc;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 20px;
}}
th, td {{
    padding: 8px 12px;
    border-bottom: 1px solid #333;
    text-align: right;
}}
th {{
    background: #222;
}}
td.name {{
    text-align: left;
    font-family: monospace;
}}
tr.slow {{
    background-color: #2a1a1a;
}}
.bar {{
    height: 6px;
    background: linear-gradient(90deg, #ff4d4d, #ffa500);
}}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="subtitle">Run ID: {PHRASE}</div>
<div class="subtitle">Headless: {headless_text}</div>
<div class="subtitle">{run_time}</div>
<p>Total entries: {len(report_rows)}</p>
<table>
<tr>
<th>Name</th>
<th>Setup (s)</th>
<th>Call (s)</th>
<th>Teardown (s)</th>
<th>Total (s)</th>
</tr>
"""

        max_total = max(r["total"] for r in report_rows) if report_rows else 1

        for r in report_rows:
            slow_class = "slow" if r["total"] > 0.5 else ""
            bar_width = (r["total"] / max_total) * 100

            html += f"""
<tr class="{slow_class}">
<td class="name">
{r["name"]}
<div class="bar" style="width:{bar_width}%;"></div>
</td>
<td>{r["setup"]:.4f}</td>
<td>{r["call"]:.4f}</td>
<td>{r["teardown"]:.4f}</td>
<td><strong>{r["total"]:.4f}</strong></td>
</tr>
"""

        html += """
</table>
</body>
</html>
"""

        with open(out_file, "w") as f:
            f.write(html)

    render_html("GUI Test Performance Report", rows, html_file)
    render_html("GUI Test Performance Report (Aggregated)", agg_rows, agg_html_file)

    print(f"\n✅ HTML report generated → {html_file}")
    print(f"✅ Aggregated HTML report generated → {agg_html_file}\n")
    
    import webbrowser
    webbrowser.open(html_file.as_uri())
    webbrowser.open(agg_html_file.as_uri())


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "target",
        nargs="?",
        default=str(PROJECT_ROOT / "tests"),
        help="Test path",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Force Qt to run offscreen (no GUI windows)",
    )

    args = parser.parse_args()

    run_pytest(args.target, args.headless)
    generate_html(args.headless)


if __name__ == "__main__":
    main()