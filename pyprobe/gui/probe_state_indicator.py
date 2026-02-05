"""Visual indicator widget for probe lifecycle state."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

from pyprobe.gui.probe_state import ProbeState


class ProbeStateIndicator(QWidget):
    """
    Visual indicator showing probe state with animations.

    States:
    - ARMED: Pulsing yellow ring (waiting for first data)
    - LIVE: Solid green dot (receiving data)
    - STALE: Dim gray dot (no recent updates)
    - INVALID: Red X (anchor no longer valid)
    """

    # Color mapping for each state
    STATE_COLORS = {
        ProbeState.ARMED: QColor('#ffff00'),    # Yellow
        ProbeState.LIVE: QColor('#00ff00'),     # Green
        ProbeState.STALE: QColor('#666666'),    # Gray
        ProbeState.INVALID: QColor('#ff0000'),  # Red
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = ProbeState.ARMED
        self._pulse_opacity = 1.0
        self._feedback_active = False

        # Fixed size 16x16
        self.setFixedSize(16, 16)

        # Pulsing animation for ARMED state
        self._pulse_animation = QPropertyAnimation(self, b"pulse_opacity")
        self._pulse_animation.setDuration(1000)
        self._pulse_animation.setStartValue(0.3)
        self._pulse_animation.setEndValue(1.0)
        self._pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_animation.setLoopCount(-1)  # Infinite loop

        # Feedback timer for invalid click flash
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self._end_feedback)

        # Start pulsing if ARMED
        self._update_animation()

    def _get_pulse_opacity(self) -> float:
        return self._pulse_opacity

    def _set_pulse_opacity(self, value: float):
        self._pulse_opacity = value
        self.update()

    pulse_opacity = pyqtProperty(float, _get_pulse_opacity, _set_pulse_opacity)

    def set_state(self, state: ProbeState):
        """Update the displayed state."""
        if self._state != state:
            self._state = state
            self._update_animation()
            self.update()

    def _update_animation(self):
        """Start or stop pulsing based on state."""
        if self._state == ProbeState.ARMED:
            self._pulse_animation.start()
        else:
            self._pulse_animation.stop()
            self._pulse_opacity = 1.0

    def show_invalid_feedback(self):
        """Flash red briefly to indicate invalid click."""
        self._feedback_active = True
        self.update()
        self._feedback_timer.start(300)  # 300ms flash

    def _end_feedback(self):
        """End the feedback flash."""
        self._feedback_active = False
        self.update()

    def paintEvent(self, event):
        """Draw the state indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center point and radius
        cx, cy = 8, 8
        radius = 6

        # Handle feedback flash
        if self._feedback_active:
            color = QColor('#ff0000')
            color.setAlphaF(0.8)
            painter.setPen(QPen(color, 2))
            painter.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            painter.drawLine(cx - 4, cy + 4, cx + 4, cy - 4)
            return

        if self._state == ProbeState.ARMED:
            # Pulsing yellow ring
            color = QColor(self.STATE_COLORS[ProbeState.ARMED])
            color.setAlphaF(self._pulse_opacity)
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        elif self._state == ProbeState.LIVE:
            # Solid green dot
            color = self.STATE_COLORS[ProbeState.LIVE]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        elif self._state == ProbeState.STALE:
            # Dim gray dot
            color = self.STATE_COLORS[ProbeState.STALE]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        elif self._state == ProbeState.INVALID:
            # Red X
            color = self.STATE_COLORS[ProbeState.INVALID]
            painter.setPen(QPen(color, 2))
            painter.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            painter.drawLine(cx - 4, cy + 4, cx + 4, cy - 4)
