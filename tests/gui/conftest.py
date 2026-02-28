import gc

import pytest
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication

from pyprobe.plots.marker_model import MarkerStore


@pytest.fixture(autouse=True)
def _enforce_widget_cleanup():
    """Error if a test leaks pyprobe.* widgets without cleanup.

    Defined first in conftest.py so it tears down last (LIFO), after
    _flush_qt_events has already processed deferred events and GC'd.
    Only flags top-level widgets (parent=None) from pyprobe.* modules,
    ignoring transient Qt/pyqtgraph internals (QMenu, QToolTip, etc.).
    """
    app = QApplication.instance()
    if app is None:
        yield
        return

    before = set(id(w) for w in app.allWidgets())
    yield

    # Finalize any deleteLater()/close() calls from fixture teardowns.
    # gc.collect() releases Python refs so Qt C++ destructors can run,
    # then processEvents() processes the deferred delete events.
    gc.collect()
    app.processEvents()
    app.processEvents()

    # Only flag widgets that:
    # - Were created during this test (not in before set)
    # - Have no parent (top-level)
    # - Are not yet deleted (C++ side alive)
    # - Come from pyprobe.* modules (ignore Qt/pyqtgraph internals)
    # - Are still visible (close() was never called = real leak)
    #   Widgets that were close()d + deleteLater()d but whose Python ref
    #   hasn't been GC'd yet will be isVisible()=False — that's fine.
    leaked = [
        w for w in app.allWidgets()
        if id(w) not in before
        and w.parent() is None
        and not sip.isdeleted(w)
        and type(w).__module__.startswith("pyprobe.")
        and w.isVisible()
    ]
    if leaked:
        names = [type(w).__name__ for w in leaked]
        for w in leaked:
            try:
                w.close()
                w.deleteLater()
            except RuntimeError:
                pass
        app.processEvents()
        pytest.fail(
            f"Leaked {len(leaked)} widget(s) without cleanup: {names}. "
            "Add qtbot.addWidget(w) and close/deleteLater/processEvents "
            "in fixture teardown.",
            pytrace=False,
        )


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
