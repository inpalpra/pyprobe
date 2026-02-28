import gc

import pytest
from PyQt6.QtWidgets import QApplication

from pyprobe.plots.marker_model import MarkerStore


@pytest.fixture(autouse=True)
def _reset_marker_global_ids():
    """Reset the global ID set and store list between tests so each test starts fresh."""
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
    yield
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()


@pytest.fixture(autouse=True)
def _flush_qt_events(request):
    """Flush deferred Qt events between tests to prevent segfaults.

    Widgets use QTimer.singleShot(0, ...) and deleteLater() which schedule
    work for the next event-loop iteration.  If these fire during a *later*
    test's teardown the C++ object may already be freed -> SIGSEGV.

    Two processEvents passes: the first drains the queue; the second catches
    anything the first pass enqueued (e.g. deleteLater queues a destroy event).

    We temporarily disable pytest-qt's exception capture during the flush so
    that known pyqtgraph-internal AttributeErrors (e.g. LabelItem._sizeHint)
    don't get promoted to test ERRORs.
    """
    yield
    app = QApplication.instance()
    if app is None:
        return

    # Temporarily disable pytest-qt exception capture during flush
    qt_plugin = request.config.pluginmanager.get_plugin("qt")
    if qt_plugin and hasattr(qt_plugin, "_exception_capture_manager"):
        mgr = qt_plugin._exception_capture_manager
        was_capturing = mgr._is_started if hasattr(mgr, "_is_started") else False
        if was_capturing:
            try:
                mgr.finish()
            except Exception:
                pass
        app.processEvents()
        gc.collect()  # release Python refs so Qt C++ destructs run now
        app.processEvents()
        if was_capturing:
            try:
                mgr.start()
            except Exception:
                pass
    else:
        app.processEvents()
        gc.collect()
        app.processEvents()
