# Specification: Investigate CI Failure and Create Issue

## Overview
Investigate the GitHub Actions failure for run `https://github.com/inpalpra/pyprobe/actions/runs/22540049369/` and create a comprehensive GitHub issue using the `gh` CLI. The issue should provide enough context and hypotheses for a future AI agent to resolve it.

## Functional Requirements
1. **Analyze CI Logs:** Retrieve and analyze the logs for the specified GitHub Actions run to identify the exact point of failure.
2. **Determine Root Causes:** Attempt to identify potential root causes based on the error traces and context within the logs, without performing local reproduction.
3. **Draft Issue Content:** Create an issue description that includes:
    - A summary of the failure.
    - Relevant error messages and stack traces.
    - Hypotheses on what "might" be causing the failures to aid future debugging.
4. **Create Issue via CLI:** Use the GitHub CLI (`gh issue create`) to create the issue in the repository.
5. **Apply Metadata:** 
    - Apply the `bug` and `ci` labels to the issue.
    - Assign the issue to the current user (the creator).

## Non-Functional Requirements
- The issue description must be optimized for readability and comprehension by subsequent AI agents.

## Out of Scope
- Local reproduction or debugging of the failure.
- Implementing a fix for the failure.

## Acceptance Criteria
- [ ] A new GitHub issue is created with the required metadata (labels and assignee).
- [ ] The issue body clearly details the failure, includes relevant logs, and suggests potential root causes.