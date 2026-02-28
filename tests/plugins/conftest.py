import pytest
from pyprobe.plots.marker_model import MarkerStore


@pytest.fixture(autouse=True)
def _reset_marker_global_ids():
    """Reset the global ID set and store list between tests so each test starts fresh."""
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
    yield
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
