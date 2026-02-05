"""
Abstract base class for all plot widgets.
"""

from typing import Optional, Any
from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget


class BasePlot(QWidget, ABC):
    """
    Abstract base class for plot widgets.

    All plot types (waveform, constellation, scalar) inherit from this.
    """

    def __init__(self, var_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name

    @property
    def var_name(self) -> str:
        """The name of the variable being plotted."""
        return self._var_name

    @abstractmethod
    def update_data(
        self,
        value: Any,
        dtype: str,
        shape: Optional[tuple] = None,
        source_info: str = ""
    ) -> None:
        """
        Update the plot with new data.

        Args:
            value: The variable value (numpy array, scalar, etc.)
            dtype: Data type string from classifier
            shape: Shape of the data (if array)
            source_info: Source location string (e.g., "func:42")
        """
        pass
