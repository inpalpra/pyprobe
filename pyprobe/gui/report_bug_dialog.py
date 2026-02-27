"""
ReportBugDialog — collects user description, optional sections, and renders
a plaintext bug report ready for clipboard or file export.

M7: also supports a "Record Steps" flow via StepRecorder.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPlainTextEdit, QCheckBox, QPushButton,
    QFileDialog, QWidget, QRadioButton,
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import QApplication

from pyprobe.report.session_snapshot import SessionStateCollector
from pyprobe.report.formatter import ReportFormatter
from pyprobe.report.report_model import BugReport, OpenFileEntry, SessionState, RecordedStep
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.gui.recording_indicator import RecordingIndicator


class ReportBugDialog(QDialog):
    """Bug report dialog.

    Accepts a SessionStateCollector and an externally-owned StepRecorder.
    MainWindow handles all signal wiring; the dialog controls start/stop
    and reads steps but does not own or wire the recorder.
    """

    def __init__(
        self,
        collector: SessionStateCollector,
        recorder: StepRecorder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._collector = collector
        self._report_text: str = ""
        self._formatter = ReportFormatter(max_file_bytes=50 * 1024)

        # M7: recording state — recorder is injected by MainWindow
        self._recorder = recorder
        self._indicator = RecordingIndicator()
        self._baseline: SessionState | None = None
        self._recorded_steps: tuple[RecordedStep, ...] = ()

        self._setup_ui()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Report Bug")
        self.resize(700, 600)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        # Description
        layout.addWidget(QLabel("Describe the problem:"))
        self._description_edit = QTextEdit()
        self._description_edit.setPlaceholderText(
            "What happened? What did you expect to happen?"
        )
        self._description_edit.setFixedHeight(100)
        layout.addWidget(self._description_edit)

        # Recording controls
        recording_layout = QHBoxLayout()
        self._start_recording_btn = QPushButton("Start Recording")
        self._start_recording_btn.clicked.connect(self._start_recording)
        self._stop_recording_btn = QPushButton("Stop Recording")
        self._stop_recording_btn.setEnabled(False)
        self._stop_recording_btn.clicked.connect(self._stop_recording)
        recording_layout.addWidget(self._start_recording_btn)
        recording_layout.addWidget(self._stop_recording_btn)
        recording_layout.addStretch()
        layout.addLayout(recording_layout)

        # Options
        options_layout = QHBoxLayout()
        self._files_checkbox = QCheckBox("Include file contents")
        self._files_checkbox.setChecked(True)
        self._logs_checkbox = QCheckBox("Include logs")
        self._sysinfo_checkbox = QCheckBox("Include system info")
        self._sysinfo_checkbox.setChecked(True)
        self._llm_mode_checkbox = QCheckBox("Optimize report for LLM consumption")
        self._llm_mode_checkbox.setChecked(True)
        options_layout.addWidget(self._files_checkbox)
        options_layout.addWidget(self._logs_checkbox)
        options_layout.addWidget(self._sysinfo_checkbox)
        options_layout.addWidget(self._llm_mode_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # File contents mode (sub-option of "Include file contents")
        file_mode_layout = QHBoxLayout()
        file_mode_layout.addSpacing(20)
        self._snippets_radio = QRadioButton("Relevant snippets")
        self._full_files_radio = QRadioButton("Full files")
        self._snippets_radio.setChecked(True)
        self._snippets_radio.setEnabled(True)
        self._full_files_radio.setEnabled(True)
        file_mode_layout.addWidget(self._snippets_radio)
        file_mode_layout.addWidget(self._full_files_radio)
        file_mode_layout.addStretch()
        layout.addLayout(file_mode_layout)

        self._files_checkbox.toggled.connect(self._on_files_toggled)

        # Generate button
        self._generate_btn = QPushButton("Generate Report")
        self._generate_btn.clicked.connect(self._trigger_generate)
        layout.addWidget(self._generate_btn)

        # Preview
        layout.addWidget(QLabel("Report preview:"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        layout.addWidget(self._preview)

        # Output actions
        output_layout = QHBoxLayout()
        self._copy_btn = QPushButton("Copy to Clipboard")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._trigger_copy)
        self._save_btn = QPushButton("Save to File…")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._trigger_save)
        self._github_btn = QPushButton("Open GitHub Issue")
        self._github_btn.setEnabled(False)
        self._github_btn.clicked.connect(self._trigger_open_github)
        output_layout.addStretch()
        output_layout.addWidget(self._copy_btn)
        output_layout.addWidget(self._save_btn)
        output_layout.addWidget(self._github_btn)
        layout.addLayout(output_layout)

    # ── Recording ─────────────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        """Begin a recording session."""
        if self._recorder.is_recording:
            return  # idempotent

        self._recorder.clear()
        self._baseline = self._collector.collect()
        self._recorder.start()
        self._indicator.show_indicator()

        # Toggle controls
        self._start_recording_btn.setEnabled(False)
        self._stop_recording_btn.setEnabled(True)

    def _stop_recording(self) -> None:
        """End the current recording session."""
        self._recorded_steps = self._recorder.stop()
        self._indicator.hide_indicator()

        # Toggle controls
        self._start_recording_btn.setEnabled(True)
        self._stop_recording_btn.setEnabled(False)

    # ── UI callbacks ─────────────────────────────────────────────────────────

    def _on_files_toggled(self, checked: bool) -> None:
        self._snippets_radio.setEnabled(checked)
        self._full_files_radio.setEnabled(checked)

    # ── Core logic ────────────────────────────────────────────────────────────

    def _trigger_generate(self) -> None:
        """Build and render the BugReport from current dialog state."""
        state = self._collector.collect()
        llm_mode = self._llm_mode_checkbox.isChecked()
        include_files = self._files_checkbox.isChecked()
        include_full_file = include_files and self._full_files_radio.isChecked()

        # Open files — keep contents when files are included, or when snippets
        # might be needed (LLM mode extracts windows from contents)
        if state.open_files:
            if include_files or llm_mode:
                open_files: tuple[OpenFileEntry, ...] = state.open_files
            else:
                open_files = tuple(
                    OpenFileEntry(
                        path=e.path,
                        is_probed=e.is_probed,
                        is_executed=e.is_executed,
                        has_unsaved=e.has_unsaved,
                        contents=None,
                    )
                    for e in state.open_files
                )
        else:
            open_files = None  # type: ignore[assignment]

        # Environment
        environment = None
        if self._sysinfo_checkbox.isChecked():
            from pyprobe.report.environment import EnvironmentCollector
            environment = EnvironmentCollector.collect()

        # Logs
        logs_text: str | None = None
        if self._logs_checkbox.isChecked():
            from pyprobe.report.log_capture import LogCapture
            snapshot = LogCapture.capture()
            logs_text = snapshot.raw_lines if snapshot else "(no log data available)"

        description = self._description_edit.toPlainText().strip()

        report = BugReport(
            description=description,
            steps=self._recorded_steps if self._recorded_steps else None,
            baseline_state=self._baseline if self._baseline is not None else None,
            open_files=open_files if open_files else None,
            environment=environment,
            logs=logs_text,
        )

        self._report_text = self._formatter.render(
            report, llm_mode=llm_mode, include_full_file=include_full_file
        )
        self._preview.setPlainText(self._report_text)
        self._copy_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._github_btn.setEnabled(True)

    def _trigger_copy(self) -> None:
        QApplication.clipboard().setText(self._report_text)

    def _trigger_open_github(self) -> None:
        import urllib.parse
        import webbrowser
        import pyprobe

        title = self._description_edit.toPlainText().strip()[:100]
        body = self._report_text
        params = urllib.parse.urlencode({"title": title, "body": body})
        url = f"{pyprobe.GITHUB_REPO_URL}/issues/new?{params}"
        webbrowser.open(url)

    def _trigger_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Bug Report", "bug_report.txt", "Text Files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._report_text)

    # ── Qt event overrides ────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        # Recording continues even if the dialog is closed — MainWindow owns
        # the recorder. Only hide the visual indicator and reset button state.
        self._indicator.hide_indicator()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:
        """Handle window activation/deactivation to toggle opacity."""
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.setWindowOpacity(1.0)
            else:
                self.setWindowOpacity(0.5)
        super().changeEvent(event)

    # ── Test helper API ───────────────────────────────────────────────────────

    def _get_preview_text(self) -> str:
        return self._preview.toPlainText()

    def _set_description(self, text: str) -> None:
        self._description_edit.setPlainText(text)

    def _copy_action_enabled(self) -> bool:
        return self._copy_btn.isEnabled()

    def _save_action_enabled(self) -> bool:
        return self._save_btn.isEnabled()

    def _github_action_enabled(self) -> bool:
        return self._github_btn.isEnabled()

    def _set_sysinfo_enabled(self, flag: bool) -> None:
        self._sysinfo_checkbox.setChecked(flag)

    def _set_logs_enabled(self, flag: bool) -> None:
        self._logs_checkbox.setChecked(flag)

    def _set_files_enabled(self, flag: bool) -> None:
        self._files_checkbox.setChecked(flag)

    # M7 test helpers

    def _trigger_start_recording(self) -> None:
        self._start_recording()

    def _trigger_stop_recording(self) -> None:
        self._stop_recording()

    def _start_recording_action_enabled(self) -> bool:
        return self._start_recording_btn.isEnabled()

    def _stop_recording_action_enabled(self) -> bool:
        return self._stop_recording_btn.isEnabled()

    def _recording_indicator_visible(self) -> bool:
        return self._indicator.is_shown

    def _inject_step(self, description: str) -> None:
        """Directly records a step into the recorder (test helper)."""
        self._recorder.record(description)

    def _recorder_is_active(self) -> bool:
        return self._recorder.is_recording

    def _simulate_probe_added(self, symbol: str, line: int) -> None:
        """Injects a fake probe_added step into the recorder (test helper)."""
        self._recorder.record(f"Added probe: {symbol} at line {line}")

    def _set_llm_mode_enabled(self, flag: bool) -> None:
        self._llm_mode_checkbox.setChecked(flag)

    def _set_full_files_mode(self, full: bool) -> None:
        if full:
            self._full_files_radio.setChecked(True)
        else:
            self._snippets_radio.setChecked(True)
