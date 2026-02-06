"""
Smart data type detection for automatic plot selection.
"""

from typing import Any, Tuple, Optional, Dict, List
import numpy as np

# Data type constants
DTYPE_SCALAR = 'scalar'
DTYPE_ARRAY_1D = 'array_1d'
DTYPE_ARRAY_COMPLEX = 'array_complex'
DTYPE_ARRAY_2D = 'array_2d'
DTYPE_WAVEFORM_REAL = 'waveform_real'
DTYPE_UNKNOWN = 'unknown'


def _is_scalar_real(value: Any) -> bool:
    """Check if value is a scalar real number."""
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return not np.issubdtype(value.dtype, np.complexfloating)
    return False


def _is_1d_real_array(value: Any) -> bool:
    """Check if value is a 1D array of real numbers."""
    if isinstance(value, np.ndarray):
        return value.ndim == 1 and not np.issubdtype(value.dtype, np.complexfloating)
    # Also accept lists/tuples that can convert to 1D real array
    if isinstance(value, (list, tuple)):
        try:
            arr = np.asarray(value)
            return arr.ndim == 1 and not np.issubdtype(arr.dtype, np.complexfloating)
        except (ValueError, TypeError):
            return False
    return False


def _get_public_attrs(obj: Any) -> Dict[str, Any]:
    """Get public (non-underscore) attributes of an object."""
    attrs = {}
    for name in dir(obj):
        if name.startswith('_'):
            continue
        try:
            val = getattr(obj, name)
            # Skip methods/callables
            if callable(val) and not isinstance(val, np.ndarray):
                continue
            attrs[name] = val
        except (AttributeError, Exception):
            continue
    return attrs


def _classify_as_waveform(value: Any) -> Optional[Dict[str, Any]]:
    """
    Check if object is a waveform-like structure.
    
    A waveform object has:
    - At least 2 scalar real numbers (e.g., t0, dt)
    - Exactly 1 1D real array (samples)
    
    We check public attributes and identify the first matching set.
    Properties returning arrays (like computed time vectors) are allowed
    but only one "primary" samples array is expected.
    
    Returns:
        Dict with {'samples_attr': str, 'scalar_attrs': [str, str]} if waveform,
        None otherwise.
    """
    # Skip primitive types and numpy arrays
    if isinstance(value, (int, float, complex, str, bytes, bool, type(None))):
        return None
    if isinstance(value, np.ndarray):
        return None
    if isinstance(value, (list, tuple, dict, set)):
        return None
    
    attrs = _get_public_attrs(value)
    
    # Need at least 3 attributes
    if len(attrs) < 3:
        return None
    
    scalar_attrs: List[str] = []
    array_attrs: List[str] = []
    
    for name, val in attrs.items():
        if _is_scalar_real(val):
            scalar_attrs.append(name)
        elif _is_1d_real_array(val):
            array_attrs.append(name)
        # Ignore other attribute types (methods, computed properties returning other types)
    
    # Need at least 2 scalars and exactly 1 array for waveform classification
    # If there are multiple arrays (e.g., x and computed t), prefer the one
    # that looks like samples (not 't' or 'time' which are typically computed)
    if len(scalar_attrs) >= 2 and len(array_attrs) >= 1:
        # Prefer array attr that's NOT named 't', 'time', 'times' (computed time vector)
        samples_attr = None
        time_like_names = {'t', 'time', 'times', 'time_vector'}
        
        for arr_name in array_attrs:
            if arr_name.lower() not in time_like_names:
                samples_attr = arr_name
                break
        
        # If all arrays are time-like, just pick the first one
        if samples_attr is None:
            samples_attr = array_attrs[0]
        
        return {
            'samples_attr': samples_attr,
            'scalar_attrs': scalar_attrs[:2],  # Take first 2 scalars
        }
    
    return None


def classify_data(value: Any) -> Tuple[str, Optional[tuple]]:
    """
    Classify data type for automatic plot widget selection.

    Returns:
        Tuple of (dtype_string, shape_or_none)

    Classification rules:
    1. Serialized waveform dict from IPC -> 'waveform_real'
    2. Waveform-like objects (2 scalars + 1 array) -> 'waveform_real'
    3. Scalar (int, float, complex single value) -> 'scalar'
    4. 1D numpy array of complex -> 'array_complex' (constellation)
    5. 1D numpy array of real -> 'array_1d' (waveform)
    6. 2D numpy array -> 'array_2d' (heatmap/image)
    7. List/tuple -> converted to numpy and re-classified
    8. Everything else -> 'unknown'
    """
    # Serialized waveform from IPC
    if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_REAL:
        samples = value.get('samples')
        if samples is not None:
            return DTYPE_WAVEFORM_REAL, samples.shape
        return DTYPE_WAVEFORM_REAL, None

    # Check for waveform-like objects (2 scalars + 1 array)
    waveform_info = _classify_as_waveform(value)
    if waveform_info is not None:
        samples = getattr(value, waveform_info['samples_attr'])
        arr = np.asarray(samples)
        return DTYPE_WAVEFORM_REAL, arr.shape

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


# Export for use in tracer
def get_waveform_info(value: Any) -> Optional[Dict[str, Any]]:
    """Get waveform structure info if value is a waveform object."""
    return _classify_as_waveform(value)

