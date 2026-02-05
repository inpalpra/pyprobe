"""
Smart data type detection for automatic plot selection.
"""

from typing import Any, Tuple, Optional
import numpy as np

# Data type constants
DTYPE_SCALAR = 'scalar'
DTYPE_ARRAY_1D = 'array_1d'
DTYPE_ARRAY_COMPLEX = 'array_complex'
DTYPE_ARRAY_2D = 'array_2d'
DTYPE_UNKNOWN = 'unknown'


def classify_data(value: Any) -> Tuple[str, Optional[tuple]]:
    """
    Classify data type for automatic plot widget selection.

    Returns:
        Tuple of (dtype_string, shape_or_none)

    Classification rules:
    1. Scalar (int, float, complex single value) -> 'scalar'
    2. 1D numpy array of complex -> 'array_complex' (constellation)
    3. 1D numpy array of real -> 'array_1d' (waveform)
    4. 2D numpy array -> 'array_2d' (heatmap/image)
    5. List/tuple -> converted to numpy and re-classified
    6. Everything else -> 'unknown'
    """
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            # 0-dimensional array is a scalar
            return DTYPE_SCALAR, ()
        elif value.ndim == 1:
            if np.issubdtype(value.dtype, np.complexfloating):
                return DTYPE_ARRAY_COMPLEX, value.shape
            else:
                return DTYPE_ARRAY_1D, value.shape
        elif value.ndim == 2:
            if np.issubdtype(value.dtype, np.complexfloating):
                # 2D complex - treat as constellation (flatten)
                return DTYPE_ARRAY_COMPLEX, value.shape
            else:
                return DTYPE_ARRAY_2D, value.shape
        else:
            return DTYPE_UNKNOWN, value.shape

    # Handle scalars
    if isinstance(value, (int, float, np.integer, np.floating)):
        return DTYPE_SCALAR, None

    if isinstance(value, (complex, np.complexfloating)):
        return DTYPE_SCALAR, None  # Single complex displayed as scalar

    # Handle lists/tuples - try to convert to numpy
    if isinstance(value, (list, tuple)):
        try:
            arr = np.asarray(value)
            return classify_data(arr)
        except (ValueError, TypeError):
            return DTYPE_UNKNOWN, None

    return DTYPE_UNKNOWN, None


def is_large_array(value: Any, threshold: int = 10000) -> bool:
    """Check if value is a large array that should use shared memory."""
    if isinstance(value, np.ndarray):
        return value.size > threshold
    return False


def get_array_memory_size(value: np.ndarray) -> int:
    """Get memory size in bytes for a numpy array."""
    return value.nbytes
