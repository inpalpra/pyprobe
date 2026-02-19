"""
Mixin providing shared pin-indicator layout logic.

Eliminates the duplicated _update_pin_layout() / get_mapped_rect()
pattern from constellation.py, scalar_history_chart.py, and waveform.py.

Requirements for the consuming class:
    - self._pin_indicator: PinIndicator instance (or None)
    - self._plot_widget: pyqtgraph PlotWidget instance
"""

from PyQt6.QtCore import QRectF, QTimer


class PinLayoutMixin:
    """Mixin that manages pin-indicator positioning for any plot widget.

    Add this to the class bases *before* QWidget so that showEvent/resizeEvent
    cooperate via super() in the MRO.
    """

    # ------------------------------------------------------------------
    # Coordinate mapping helper
    # ------------------------------------------------------------------
    @staticmethod
    def _get_mapped_rect(plot_widget, parent_widget, item) -> QRectF:
        """Map a pyqtgraph item's scene rect to parent_widget coordinates.

        Args:
            plot_widget: The pg.PlotWidget that owns the item.
            parent_widget: The QWidget to map coordinates into.
            item: A pyqtgraph graphics item (e.g., ViewBox).

        Returns:
            QRectF in parent_widget coordinates.
        """
        scene_rect = item.sceneBoundingRect()
        view_poly = plot_widget.mapFromScene(scene_rect)
        view_rect = view_poly.boundingRect()
        tl_mapped = plot_widget.mapTo(parent_widget, view_rect.topLeft())
        return QRectF(
            float(tl_mapped.x()), float(tl_mapped.y()),
            view_rect.width(), view_rect.height(),
        )

    # ------------------------------------------------------------------
    # Layout driver
    # ------------------------------------------------------------------
    def _update_pin_layout(self) -> None:
        """Size the pin-indicator overlay and position its buttons."""
        pin = getattr(self, '_pin_indicator', None)
        pw = getattr(self, '_plot_widget', None)
        if pin is None or pw is None:
            return

        # Resize indicator overlay to cover full widget
        pin.setGeometry(0, 0, self.width(), self.height())

        plot_item = pw.getPlotItem()
        view_rect = self._get_mapped_rect(pw, self, plot_item.getViewBox())

        pin.update_layout(view_rect)
        pin.raise_()

    # ------------------------------------------------------------------
    # Event helpers  (call super() so QWidget events still fire)
    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:          # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._update_pin_layout)

    def resizeEvent(self, event) -> None:        # noqa: N802
        super().resizeEvent(event)
        self._update_pin_layout()
