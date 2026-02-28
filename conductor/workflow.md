# Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation
3. **Test-Driven Development:** Write unit tests before implementing functionality
4. **High Code Coverage:** Aim for >80% code coverage for all modules
5. **User Experience First:** Every decision should prioritize user experience
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order

2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`

3. **Write Failing Tests (Red Phase):**
   - Create a new test file for the feature or bug fix.
   - Write one or more unit tests that clearly define the expected behavior and acceptance criteria for the task.
   - **CRITICAL:** Run the tests and confirm that they fail as expected. This is the "Red" phase of TDD. Do not proceed until you have failing tests.

4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum amount of application code necessary to make the failing tests pass.
   - Run the test suite again and confirm that all tests now pass. This is the "Green" phase.

5. **Refactor (Optional but Recommended):**
   - With the safety of passing tests, refactor the implementation code and the test code to improve clarity, remove duplication, and enhance performance without changing the external behavior.
   - Rerun tests to ensure they still pass after refactoring.

6. **Verify Coverage:** Run coverage reports:
   ```bash
   uv run pytest --cov=pyprobe --cov-report=html
   ```
   Target: >80% coverage for new code.

7. **Document Deviations:** If implementation differs from tech stack:
   - **STOP** implementation
   - Update `tech-stack.md` with new design
   - Add dated note explaining the change
   - Resume implementation

8. **Commit Code Changes:**
   - Stage all code changes related to the task.
   - Propose a clear, concise commit message e.g, `feat(ui): Create basic HTML structure for calculator`.
   - Perform the commit.

9. **Attach Task Summary with Git Notes:**
   - **Step 9.1: Get Commit Hash:** Obtain the hash of the *just-completed commit* (`git log -1 --format="%H"`).
   - **Step 9.2: Draft Note Content:** Create a detailed summary for the completed task. This should include the task name, a summary of changes, a list of all created/modified files, and the core "why" for the change.
   - **Step 9.3: Attach Note:** Use the `git notes` command to attach the summary to the commit.
     ```bash
     # The note content from the previous step is passed via the -m flag.
     git notes add -m "<note content>" <commit_hash>
     ```

10. **Get and Record Task Commit SHA:**
    - **Step 10.1: Update Plan:** Read `plan.md`, find the line for the completed task, update its status from `[~]` to `[x]`, and append the first 7 characters of the *just-completed commit's* commit hash.
    - **Step 10.2: Write Plan:** Write the updated content back to `plan.md`.

11. **Commit Plan Update:**
    - **Action:** Stage the modified `plan.md` file.
    - **Action:** Commit this change with a descriptive message (e.g., `conductor(plan): Mark task 'Create user model' as complete`).

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in this phase, you must first find the starting point. Read `plan.md` to find the Git commit SHA of the *previous* phase's checkpoint. If no previous checkpoint exists, the scope is all changes since the first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` to get a precise list of all files modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files (e.g., `.json`, `.md`, `.yaml`).
        -   For each remaining code file, verify a corresponding test file exists.
        -   If a test file is missing, you **must** create one. Before writing the test, **first, analyze other test files in the repository to determine the correct naming convention and testing style.** The new tests **must** validate the functionality described in this phase's tasks (`plan.md`).

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Before execution, you **must** announce the exact shell command you will use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to verify the phase. **Command:** `./.venv/bin/python -m pytest`"
    -   Execute the announced command.
    -   If tests fail, you **must** inform the user and begin debugging. You may attempt to propose a fix a **maximum of two times**. If the tests still fail after your second proposed fix, you **must stop**, report the persistent failure, and ask the user for guidance.

4.  **Propose a Detailed, Actionable Manual Verification Plan:**
    -   **CRITICAL:** To generate the plan, first analyze `product.md`, `product-guidelines.md`, and `plan.md` to determine the user-facing goals of the completed phase.
    -   You **must** generate a step-by-step plan that walks the user through the verification process, including any necessary commands and specific, expected outcomes.
    -   The plan you present to the user **must** follow this format:

        **Example for a GUI Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Launch PyProbe:** `uv run pyprobe`
        2.  **Open a test script:** Load one of the regression scripts from `regression/`
        3.  **Confirm that you see:** The expected plot rendering, marker behavior, or UI change.
        ```

        **Example for a Core/IPC Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Run a regression script:** `uv run python regression/<script>.py`
        2.  **Confirm that:** PyProbe launches, receives data, and displays plots correctly.
        ```

5.  **Await Explicit User Feedback:**
    -   After presenting the detailed plan, ask the user for confirmation: "**Does this meet your expectations? Please confirm with yes or provide feedback on what needs to be changed.**"
    -   **PAUSE** and await the user's response. Do not proceed without an explicit yes or confirmation.

6.  **Create Checkpoint Commit:**
    -   Stage all changes. If no changes occurred in this step, proceed with an empty commit.
    -   Perform the commit with a clear and concise message (e.g., `conductor(checkpoint): Checkpoint end of Phase X`).

7.  **Attach Auditable Verification Report using Git Notes:**
    -   **Step 7.1: Draft Note Content:** Create a detailed verification report including the automated test command, the manual verification steps, and the user's confirmation.
    -   **Step 7.2: Attach Note:** Use the `git notes` command and the full commit hash from the previous step to attach the full report to the checkpoint commit.

8.  **Get and Record Phase Checkpoint SHA:**
    -   **Step 8.1: Get Commit Hash:** Obtain the hash of the *just-created checkpoint commit* (`git log -1 --format="%H"`).
    -   **Step 8.2: Update Plan:** Read `plan.md`, find the heading for the completed phase, and append the first 7 characters of the commit hash in the format `[checkpoint: <sha>]`.
    -   **Step 8.3: Write Plan:** Write the updated content back to `plan.md`.

9. **Commit Plan Update:**
    - **Action:** Stage the modified `plan.md` file.
    - **Action:** Commit this change with a descriptive message following the format `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10.  **Announce Completion:** Inform the user that the phase is complete and the checkpoint has been created, with the detailed verification report attached as a git note.

### Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows project's code style guidelines (as defined in `code_styleguides/`)
- [ ] All public functions/methods are documented (e.g., docstrings, JSDoc, GoDoc)
- [ ] Type safety is enforced (e.g., type hints, TypeScript types, Go types)
- [ ] No linting or static analysis errors (using the project's configured tools)
- [ ] Works correctly in the desktop GUI
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced

## Development Commands

### Setup
```bash
# Install dependencies using uv
uv sync --all-groups
```

### Daily Development
```bash
# Run all tests
./.venv/bin/python -m pytest

# Run tests with coverage
./.venv/bin/python -m pytest --cov=pyprobe

# Run specific GUI test file (headless)
QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest tests/gui/test_waveform_plot_gui.py
```

### Before Committing
```bash
# Run full test suite and linting
./.venv/bin/python -m pytest && ruff check .
```

## Testing Requirements

### Unit Testing
- Every module must have corresponding tests.
- Use appropriate test setup/teardown mechanisms (e.g., fixtures, beforeEach/afterEach).
- Mock external dependencies.
- Test both success and failure cases.

### Integration Testing
- Test complete user flows (probe lifecycle, lens switching, overlay)
- Verify IPC message roundtrips between runner and GUI
- Test plugin registry and widget creation
- Check marker persistence across lens switches

### GUI Testing
- Use `pytest-qt` with `qtbot` for widget testing
- Test with `--forked` flag if tests interfere with each other
- Verify plot rendering with pyqtgraph ViewBox assertions
- Check theme application across all widgets
- > **RULE: If a test creates a `QWidget`, it MUST call `qtbot.addWidget(w)`. Always. No exceptions.**
- **MANDATORY: Every test that creates a Qt/pyqtgraph widget MUST:**
  1. **Register it** with `qtbot.addWidget(w)` — this gives pytest-qt ownership of the C++ object's lifetime for deterministic cleanup.
  2. **Explicitly destroy it** before the test returns. The cleanup is three lines — no exceptions, no shortcuts:
  ```python
  qtbot.addWidget(w)   # register for lifecycle management
  # ... test body ...
  w.close()
  w.deleteLater()
  qapp.processEvents()
  ```
  This is not optional for "complex" widgets only. Any widget can grow secondary axes, legends, or axis label rebuilds in a future commit, turning a safe test into a teardown bomb. Always clean up.

  **Past failure:** `TestComplexMAWidgetColor` tests passed assertions but crashed in teardown with `AttributeError: 'LabelItem' object has no attribute '_sizeHint'`. Root cause: `set_series_color()` calls `setLabel()`, which recreates pyqtgraph's internal `LabelItem` objects post-construction. Without explicit cleanup, GC destroyed them in random order while Qt still held references. Tests in other files using the same widget (`test_draw_mode_e2e.py`, `test_draw_mode.py`) were unaffected because they already had `deleteLater()` calls.
- **DO NOT remove the `_flush_qt_events` autouse fixture** in `tests/gui/conftest.py`. It is the project-wide safety net that processes pending Qt events after every test, preventing deferred callbacks from accumulating across tests and crashing on freed C++ objects.
- **The `_enforce_widget_cleanup` autouse fixture** will `pytest.fail()` any test that creates a `pyprobe.*` widget without calling `close()`. If you see "Leaked N widget(s) without cleanup", add `qtbot.addWidget(w)` + the cleanup pattern above.

## Code Review Process

### Self-Review Checklist
Before requesting review:

1. **Functionality**
   - Feature works as specified
   - Edge cases handled
   - Error messages are user-friendly

2. **Code Quality**
   - Follows style guide
   - DRY principle applied
   - Clear variable/function names
   - Appropriate comments

3. **Testing**
   - Unit tests comprehensive
   - Integration tests pass
   - Coverage adequate (>80%)

4. **Security**
   - No hardcoded secrets or file paths
   - Input validation on IPC messages
   - Safe deserialization of probe data

5. **Performance**
   - Plot update throttling for high-frequency data
   - No unnecessary widget rebuilds
   - Memory-efficient buffer management

6. **Desktop UX**
   - Keyboard shortcuts documented and working
   - Theme consistency across all widgets
   - Proper Qt cleanup (no leaked signals/slots)
   - Every GUI test registers widgets with `qtbot.addWidget()` and destroys them (`close()` → `deleteLater()` → `processEvents()`)

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat(auth): Add remember me functionality"
git commit -m "fix(posts): Correct excerpt generation for short posts"
git commit -m "test(comments): Add tests for emoji reaction limits"
git commit -m "style(mobile): Improve button touch targets"
```

## Definition of Done

A task is complete when:

1. All code implemented to specification
2. Unit tests written and passing
3. Code coverage meets project requirements
4. Documentation complete (if applicable)
5. Code passes all configured linting and static analysis checks
6. Works correctly in the desktop GUI
7. Implementation notes added to `plan.md`
8. Changes committed with proper message
9. Git note with task summary attached to the commit

## Emergency Procedures

### Critical Bug in Release
1. Create hotfix branch from main
2. Write failing test for bug
3. Implement minimal fix
4. Run full test suite (`./.venv/bin/python -m pytest`)
5. Push and let CI verify
6. Document in plan.md

### Segfault or Crash
1. Clear stale bytecache: `find . -name __pycache__ -not -path '*/.venv/*' -exec rm -rf {} +`
2. Check for native library conflicts (scipy vs PyQt6 import order)
3. Run with `--forked` to isolate: `./.venv/bin/python -m pytest --forked`
4. Check stderr (stdout is captured by IPC transport)
5. Document root cause in CLAUDE.md

## Release Workflow

### Pre-Release Checklist
- [ ] All tests passing (`./.venv/bin/python -m pytest`)
- [ ] Coverage >80%
- [ ] No linting errors (`ruff check .`)
- [ ] Pre-push hook passes
- [ ] No gitignored files tracked (`scripts/list_remote_ignored.py`)
- [ ] Version bumped in `pyproject.toml`

### Release Steps
1. Merge feature branch to main
2. Tag release with version (`git tag vX.Y.Z`)
3. Push tags (`git push --tags`)
4. CI builds and publishes wheel (`.github/workflows/release.yml`)
5. Verify package installs cleanly: `pip install pyprobe==X.Y.Z`

### Post-Release
1. Run regression scripts against installed package
2. Check GitHub Actions logs for warnings
3. Plan next iteration

## Continuous Improvement

- Review workflow weekly
- Update based on pain points
- Document lessons learned
- Optimize for user happiness
- Keep things simple and maintainable

## AI Agent Problem Solving Strategies
When confronting complex bugs, especially those involving opaque third-party GUI frameworks or event bubbling, you **MUST** apply the following workflow. Do not rely on assumptions or brute-force coordinate arithmetic when events aren't firing.

1. **Isolation via Minimal Reproduction:** Never debug subtle event flow issues inside the massive main application. You MUST write a standalone script (e.g., `<20` lines) that isolates the component. This strips away state noise and proves whether your baseline assumption about the framework is true.
2. **Runtime Introspection of Third-Party Code:** If an action isn't triggering your handlers, do not guess the internal logic. Use direct Python reflection to read the source. Run `python -c "import inspect; import module; print(inspect.getsource(module.ProblemClass.method))"` directly in your shell. You must read the vendor code to understand the native mechanics.
3. **Respect GUI Event Bubbling (The Swallow Effect):** In Qt (and web DOM), events bubble up from child to parent. If a parent container isn't receiving a click event, assume a child component is intercepting it, handling it natively, and calling `.accept()`. Always look for child sub-components that might have their own event handlers.
4. **Follow the Path of Least Resistance (Native Hooks):** If the framework provides a native implementation of an action (e.g., a native `sigClicked` or `sigSampleClicked` emitted when the component natively handles its own state), **DO NOT fight the framework.** Wire into the existing signal instead of trying to override the internal event handler.
5. **Strict Typing in Mocks for C++ Frameworks:** When mocking objects passed to C++ extensions (like PyQt or PySide), generic `MagicMock` instances will frequently fail with `TypeError: arguments did not match any overloaded call`. You **MUST** instantiate the actual required C++ wrapper objects (e.g., `QPointF`, `QRectF`) for geometry, positions, or specific event metadata.
