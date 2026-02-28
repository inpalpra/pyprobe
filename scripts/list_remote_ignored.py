#!/usr/bin/env python3
"""List files tracked in origin/main that should be ignored.

Uses the GitHub API (via `gh` CLI) to fetch the remote tree, then checks
each path against .gitignore and ~/.gitignore_global using `git check-ignore`.
"""

import json
import subprocess
import sys


def gh_api(endpoint: str) -> dict:
    """Call the GitHub API via `gh api`."""
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def get_remote_files(owner: str, repo: str, branch: str = "main") -> list[str]:
    """Fetch every file path from the remote branch tree."""
    data = gh_api(f"repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    return [item["path"] for item in data["tree"] if item["type"] == "blob"]


def get_repo_identity() -> tuple[str, str]:
    """Detect owner/repo from the current git remote."""
    result = subprocess.run(
        ["gh", "api", "repos/{owner}/{repo}", "--jq", ".full_name"],
        capture_output=True, text=True, check=True,
    )
    owner, repo = result.stdout.strip().split("/")
    return owner, repo


def check_ignored(paths: list[str]) -> list[tuple[str, str]]:
    """Check which paths would be ignored by current gitignore rules.

    Returns list of (path, rule_source) for ignored paths.
    """
    ignored = []
    for path in paths:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-v", path],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            # Output: <source>:<line>:<pattern>\t<path>
            parts = result.stdout.strip().split("\t")[0]
            source_file, line_no, pattern = parts.split(":")
            ignored.append((path, f"{source_file}:{line_no}  ({pattern})"))
    return ignored


def main():
    owner, repo = get_repo_identity()
    print(f"  Fetching tree from GitHub: {owner}/{repo} @ main ...")

    remote_files = get_remote_files(owner, repo)
    print(f"  Remote has {len(remote_files)} tracked files. Checking ignore rules ...\n")

    violations = check_ignored(remote_files)

    if not violations:
        print("✅ No tracked files match gitignore rules. Clean!")
        return

    print(f"{'─' * 74}")
    print(f"  ⚠️  {len(violations)} file(s) tracked in origin/main that should be ignored")
    print(f"{'─' * 74}\n")

    for path, source in violations:
        print(f"  {path:<50} ← {source}")

    print(f"\n{'─' * 74}")
    print(f"  To remove from tracking (without deleting locally):")
    print(f"    git rm --cached <file>")
    print(f"    git commit -m 'stop tracking ignored files'")
    print(f"    git push")


if __name__ == "__main__":
    main()
