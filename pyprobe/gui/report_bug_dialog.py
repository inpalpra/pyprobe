"""
ReportBugDialog — collects user description, optional sections, and renders
a plaintext bug report ready for clipboard or file export.

M7: also supports a "Record Steps" flow via StepRecorder.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPlainTextEdit, QCheckBox, QPushButton,
    QFileDialog, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from pyprobe.report.session_snapshot import SessionStateCollector
from pyprobe.report.formatter import ReportFormatter
from pyprobe.report.report_model import BugReport, OpenFileEntry, SessionState, RecordedStep
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.gui.recording_indicator import RecordingIndicator


class ReportBugDialog(QDialog):
    """Bug report dialog.

    Accepts a SessionStateCollector at construction.  collector.collect()
    is called at generate time (not at construction time) so the snapshot
    always reflects the state at the moment the user clicks Generate.

    Optional signal_sources is a list of (signal, description) tuples.
    When recording starts, each signal is connected to the StepRecorder.
    """

    def __init__(
        self,
        collector: SessionStateCollector,
        parent: QWidget | None = None,
        signal_sources: list | None = None,
    ) -> None:
        super().__init__(parent)
        self._collector = collector
        self._report_text: str = ""
        self._formatter = ReportFormatter(max_file_bytes=50 * 1024)
        self._signal_sources: list = signal_sources or []

        # M7: recording state
        self._recorder = StepRecorder()
        self._indicator = RecordingIndicator()
        self._baseline: SessionState | None = None
        self._recorded_steps: tuple[RecordedStep, ...] = ()

        self._setup_ui()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Report Bug")
        self.resize(700, 600)

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
        self._logs_checkbox = QCheckBox("Include logs")
        self._sysinfo_checkbox = QCheckBox("Include system info")
        self._sysinfo_checkbox.setChecked(True)
        options_layout.addWidget(self._files_checkbox)
        options_layout.addWidget(self._logs_checkbox)
        options_layout.addWidget(self._sysinfo_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)

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

        # Clear previous session
        self._recorder.clear()

        # Capture baseline state at the moment recording starts
        self._baseline = self._collector.collect()

        # Connect application signals
        for signal, description in self._signal_sources:
            self._recorder.connect_signal(signal, description)

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

    # ── Core logic ────────────────────────────────────────────────────────────

    def _trigger_generate(self) -> None:
        """Build and render the BugReport from current dialog state."""
        state = self._collector.collect()

        # Open files — strip contents when include-files is off
        if state.open_files:
            if self._files_checkbox.isChecked():
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

        self._report_text = self._formatter.render(report)
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
        if self._recorder.is_recording:
            self._stop_recording()
        self._indicator.hide_indicator()
        super().closeEvent(event)

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
