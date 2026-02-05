"""Animation utilities for probe lifecycle."""
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve


class ProbeAnimations:
    """Factory for probe lifecycle animations."""

    @staticmethod
    def fade_out(widget: QWidget, duration_ms: int = 300, on_finished=None) -> QPropertyAnimation:
        """Create fade-out animation for probe removal."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        if on_finished:
            anim.finished.connect(on_finished)

        return anim

    @staticmethod
    def fade_in(widget: QWidget, duration_ms: int = 200, on_finished=None) -> QPropertyAnimation:
        """Create fade-in animation for probe creation."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)

        if on_finished:
            anim.finished.connect(on_finished)

        return anim

    @staticmethod
    def pulse(widget: QWidget, duration_ms: int = 500) -> QPropertyAnimation:
        """Create pulse animation for emphasis."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setKeyValueAt(0.5, 0.5)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        return anim
