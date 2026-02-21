"""Collapsible pane that wraps a content widget with an EdgeStrip toggle."""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, QSize

from .edge_strip import EdgeStrip


class CollapsiblePane(QWidget):
    """Wraps *content* and an :class:`EdgeStrip` in a horizontal layout.

    **Collapsed** — content hidden, 20 px edge strip visible with expand
    chevron.  Click the strip to expand.

    **Expanded** — strip hidden, full content visible.  The content widget
    is expected to provide its own collapse affordance (e.g. a header
    button) that emits a ``collapse_requested`` signal.  If that signal
    exists on *content*, CollapsiblePane auto-connects it.
    """

    toggled = pyqtSignal(bool)  # True = expanded

    def __init__(
        self,
        content: QWidget,
        side: str = "left",
        expand_tooltip: str = "Expand",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._content = content
        self._expanded = False

        self._strip = EdgeStrip(side=side, tooltip=expand_tooltip)
        self._strip.clicked.connect(self.expand)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if side == "left":
            layout.addWidget(self._strip)
            layout.addWidget(self._content)
        else:
            layout.addWidget(self._content)
            layout.addWidget(self._strip)

        # Start collapsed
        self._content.hide()
        self._strip.show()

        # Auto-connect content's collapse affordance if it provides one
        sig = getattr(content, "collapse_requested", None)
        if sig is not None:
            sig.connect(self.collapse)

    # -- Public API ----------------------------------------------------------

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def expand(self) -> None:
        if self._expanded:
            return
        self._expanded = True
        self._content.show()
        self._strip.hide()
        self.toggled.emit(True)

    def collapse(self) -> None:
        if not self._expanded:
            return
        self._expanded = False
        self._content.hide()
        self._strip.show()
        self.toggled.emit(False)

    def toggle(self) -> None:
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    # -- Qt overrides --------------------------------------------------------

    def sizeHint(self) -> QSize:
        if self._expanded:
            return self._content.sizeHint()
        return QSize(20, 100)
