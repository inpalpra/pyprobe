#!/Users/ppal/repos/pyprobe/.venv/bin/python
"""
Profile GUI tests and generate HTML performance report.

Uses pytest-json-report.
Outputs:
- gui_profile.json
- gui_profile.html
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse


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

JSON_FILE = PROJECT_ROOT / "gui_profile.json"
HTML_FILE = PROJECT_ROOT / "gui_profile.html"


# ────────────────────────────────────────────────────────────────
# Run pytest
# ────────────────────────────────────────────────────────────────

def run_pytest(target: str | None):
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-n", "0",  # sequential for accurate timing
        "--json-report",
        f"--json-report-file={JSON_FILE}",
        "-q",
        "-o", "console_output_style=classic",
    ]

    if target:
        cmd.insert(3, target)

    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Profiling target: {target or 'ALL TESTS'}\n")

    subprocess.run(cmd, cwd=PROJECT_ROOT)


# ────────────────────────────────────────────────────────────────
# Generate HTML
# ────────────────────────────────────────────────────────────────

def generate_html():
    with open(JSON_FILE) as f:
        data = json.load(f)

    rows = []

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

    rows.sort(key=lambda r: r["total"], reverse=True)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>GUI Test Performance Report</title>
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
table {{
    border-collapse: collapse;
    width: 100%;
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
<h1>GUI Test Performance Report</h1>
<p>Total tests: {len(rows)}</p>
<table>
<tr>
<th>Test</th>
<th>Setup (s)</th>
<th>Call (s)</th>
<th>Teardown (s)</th>
<th>Total (s)</th>
</tr>
"""

    max_total = max(r["total"] for r in rows) if rows else 1

    for r in rows:
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

    with open(HTML_FILE, "w") as f:
        f.write(html)

    print(f"\n✅ HTML report generated → {HTML_FILE}\n")


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        nargs="?",
        # default=str(PROJECT_ROOT / "tests" / "gui" / "test_probe_temporal_fast.py"),
        default=str(PROJECT_ROOT / "tests" / "gui" / "test_probe_temporal_correctness.py"),
        help="Test path (default: tests/gui)",
    )
    args = parser.parse_args()

    run_pytest(args.target)
    generate_html()


if __name__ == "__main__":
    main()