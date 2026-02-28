"""Tests for highlight lifecycle across panels, overlays, and watch sidebar.

Fast Tests Implementation:
This file uses the 'megascript' strategy to execute all GUI scenarios sequentially
in a single `MainWindow` instance at the module level. Individual test functions
then assert against the captured state dictionary to achieve massive speedups
by avoiding repeated QApplication/MainWindow tearups.

Invariant: A symbol should be highlighted in the code viewer if and only if
it is being used somewhere — as a standalone panel, as an overlay on another
panel, or in the watch sidebar. The gutter eye icon follows the same rule
at the line level.
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QPushButton

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.trace_reference_manager import TraceReferenceManager
from pyprobe.gui.main_window import MainWindow


# ---------------------------------------------------------------------------
# Global State Store
# ---------------------------------------------------------------------------
_STATE = {}


def _capture_state(main_window, key, anchors: list[ProbeAnchor], lines: list[int] = None):
    """Record highlighting states for given anchors and lines."""
    lines = lines or []
    _STATE[key] = {
        "highlights": {a.symbol: (a in main_window._code_viewer._active_probes) for a in anchors},
        "gutters": {l: (l in main_window._code_gutter._probed_lines) for l in lines}
    }


def _close_panel(panel):
    """Click the close button on a panel and wait for async cleanup."""
    for child in panel.findChildren(QPushButton):
        if child.text() == "\u00d7":
            QTest.mouseClick(child, Qt.MouseButton.LeftButton)
            QTest.qWait(10)
            return
    raise RuntimeError("Close button not found on panel")


def _find_panel_for_anchor(main_window, anchor):
    """Find the panel associated with an anchor."""
    for p in main_window._probe_container.get_all_panels():
        if p._anchor == anchor:
            return p
    return None


def _flush_stale_panels(main_window):
    """Clean stale (deleted/closing) panels from the controller."""
    from pyprobe.gui.probe_controller import is_obj_deleted
    panels = main_window._probe_controller._probe_panels
    for a in list(panels.keys()):
        panels[a] = [
            p for p in panels[a]
            if not is_obj_deleted(p) and not getattr(p, 'is_closing', False)
        ]
        if not panels[a]:
            del panels[a]


@pytest.fixture(scope="module", autouse=True)
def _run_all_scenarios(qapp):
    """Run all scenarios on a single MainWindow to populate _STATE."""
    TraceReferenceManager._instance = None
    mw = MainWindow()
    mw.show()
    QTest.qWait(10)  # Let it render

    # --- TestPanelAndWatch scenarios ---
    # scenario: test_close_panel_while_in_watch_keeps_highlight
    a_cp = ProbeAnchor(file="test.py", line=10, col=0, symbol="x_cp")
    mw._on_probe_requested(a_cp)
    _capture_state(mw, "cp_after_panel", [a_cp])
    mw._on_watch_probe_requested(a_cp)
    panel = _find_panel_for_anchor(mw, a_cp)
    _close_panel(panel)
    _capture_state(mw, "cp_after_close", [a_cp], [10])

    # scenario: test_remove_watch_while_panel_open_keeps_highlight
    a_rw = ProbeAnchor(file="test.py", line=11, col=0, symbol="x_rw")
    mw._on_probe_requested(a_rw)
    mw._on_watch_probe_requested(a_rw)
    mw._scalar_watch_sidebar.remove_scalar(a_rw)
    _capture_state(mw, "rw_after_remove", [a_rw])

    # scenario: test_close_panel_then_remove_watch_removes_highlight
    a_cp_rw = ProbeAnchor(file="test.py", line=12, col=0, symbol="x_cprw")
    mw._on_probe_requested(a_cp_rw)
    mw._on_watch_probe_requested(a_cp_rw)
    panel2 = _find_panel_for_anchor(mw, a_cp_rw)
    _close_panel(panel2)
    _capture_state(mw, "cprw_after_close", [a_cp_rw])
    mw._scalar_watch_sidebar.remove_scalar(a_cp_rw)
    _capture_state(mw, "cprw_after_remove", [a_cp_rw])

    # scenario: test_remove_watch_then_close_panel_removes_highlight
    a_rw_cp = ProbeAnchor(file="test.py", line=13, col=0, symbol="x_rwcp")
    mw._on_probe_requested(a_rw_cp)
    mw._on_watch_probe_requested(a_rw_cp)
    mw._scalar_watch_sidebar.remove_scalar(a_rw_cp)
    _capture_state(mw, "rwcp_after_remove", [a_rw_cp])
    panel3 = _find_panel_for_anchor(mw, a_rw_cp)
    _close_panel(panel3)
    _capture_state(mw, "rwcp_after_close", [a_rw_cp])

    # --- TestOverlayHighlight scenarios ---
    # scenario: test_overlay_existing_anchor_keeps_highlight_after_panel_close
    a_host1 = ProbeAnchor(file="test.py", line=20, col=0, symbol="host_20")
    a_over1 = ProbeAnchor(file="test.py", line=21, col=0, symbol="over_21")
    mw._on_probe_requested(a_host1)
    mw._on_probe_requested(a_over1)
    panel_host1 = _find_panel_for_anchor(mw, a_host1)
    mw._probe_controller.handle_overlay_requested(panel_host1, a_over1)
    panel_over1 = _find_panel_for_anchor(mw, a_over1)
    _close_panel(panel_over1)
    _capture_state(mw, "over1_after_close", [a_over1])

    # scenario: test_overlay_only_anchor_highlighted
    a_host2 = ProbeAnchor(file="test.py", line=22, col=0, symbol="host_22")
    a_over2 = ProbeAnchor(file="test.py", line=23, col=0, symbol="over_23")
    mw._on_probe_requested(a_host2)
    panel_host2 = _find_panel_for_anchor(mw, a_host2)
    mw._probe_controller.handle_overlay_requested(panel_host2, a_over2)
    _capture_state(mw, "over2_highlight", [a_over2])

    # scenario: test_removing_overlay_removes_highlight_when_not_used_elsewhere
    a_host3 = ProbeAnchor(file="test.py", line=24, col=0, symbol="host_24")
    a_over3 = ProbeAnchor(file="test.py", line=25, col=0, symbol="over_25")
    mw._on_probe_requested(a_host3)
    panel_host3 = _find_panel_for_anchor(mw, a_host3)
    mw._probe_controller.handle_overlay_requested(panel_host3, a_over3)
    _capture_state(mw, "over3_before_remove", [a_over3])
    mw._probe_controller.remove_overlay(panel_host3, a_over3)
    _capture_state(mw, "over3_after_remove", [a_over3])

    # scenario: test_overlay_in_watch_keeps_highlight_after_overlay_removed
    a_host4 = ProbeAnchor(file="test.py", line=26, col=0, symbol="host_26")
    a_over4 = ProbeAnchor(file="test.py", line=27, col=0, symbol="over_27")
    mw._on_probe_requested(a_host4)
    panel_host4 = _find_panel_for_anchor(mw, a_host4)
    mw._probe_controller.handle_overlay_requested(panel_host4, a_over4)
    mw._on_watch_probe_requested(a_over4)
    mw._probe_controller.remove_overlay(panel_host4, a_over4)
    _capture_state(mw, "over4_after_remove", [a_over4])

    # scenario: test_close_panel_then_remove_overlay_clears_highlight
    a_host5 = ProbeAnchor(file="test.py", line=28, col=0, symbol="host_28")
    a_over5 = ProbeAnchor(file="test.py", line=29, col=0, symbol="over_29")
    mw._on_probe_requested(a_host5)
    mw._on_probe_requested(a_over5)
    panel_host5 = _find_panel_for_anchor(mw, a_host5)
    mw._probe_controller.handle_overlay_requested(panel_host5, a_over5)
    panel_over5 = _find_panel_for_anchor(mw, a_over5)
    _close_panel(panel_over5)
    _capture_state(mw, "over5_after_close", [a_over5])
    _flush_stale_panels(mw)
    mw._probe_controller.remove_overlay(panel_host5, a_over5)
    _capture_state(mw, "over5_after_remove", [a_over5])

    # scenario: test_close_panel_then_remove_overlay_without_stale_flush
    a_host6 = ProbeAnchor(file="test.py", line=30, col=0, symbol="host_30")
    a_over6 = ProbeAnchor(file="test.py", line=31, col=0, symbol="over_31")
    mw._on_probe_requested(a_host6)
    mw._on_probe_requested(a_over6)
    panel_host6 = _find_panel_for_anchor(mw, a_host6)
    mw._probe_controller.handle_overlay_requested(panel_host6, a_over6)
    panel_over6 = _find_panel_for_anchor(mw, a_over6)
    _close_panel(panel_over6)
    _capture_state(mw, "over6_after_close", [a_over6])
    mw._probe_controller.remove_overlay(panel_host6, a_over6)
    _capture_state(mw, "over6_after_remove", [a_over6])

    # --- TestWatchOnlyHighlight scenarios ---
    # scenario: test_watch_only_variable_highlighted
    a_w1 = ProbeAnchor(file="test.py", line=40, col=0, symbol="w1")
    mw._on_watch_probe_requested(a_w1)
    _capture_state(mw, "w1_highlight", [a_w1])

    # scenario: test_removing_watch_only_removes_highlight
    a_w2 = ProbeAnchor(file="test.py", line=41, col=0, symbol="w2")
    mw._on_watch_probe_requested(a_w2)
    _capture_state(mw, "w2_before_remove", [a_w2])
    mw._scalar_watch_sidebar.remove_scalar(a_w2)
    _capture_state(mw, "w2_after_remove", [a_w2])

    # --- TestAllThreeUsageTypes scenarios ---
    # scenario: test_triple_usage_survives_incremental_removal
    a_t_host = ProbeAnchor(file="test.py", line=50, col=0, symbol="t_host")
    a_t_var = ProbeAnchor(file="test.py", line=51, col=0, symbol="t_var")
    mw._on_probe_requested(a_t_var)
    mw._on_probe_requested(a_t_host)
    _capture_state(mw, "triple_initial", [a_t_var])
    panel_host7 = _find_panel_for_anchor(mw, a_t_host)
    mw._probe_controller.handle_overlay_requested(panel_host7, a_t_var)
    mw._on_watch_probe_requested(a_t_var)
    
    panel_t_var = _find_panel_for_anchor(mw, a_t_var)
    _close_panel(panel_t_var)
    _capture_state(mw, "triple_after_panel", [a_t_var])
    
    mw._probe_controller.remove_overlay(panel_host7, a_t_var)
    _capture_state(mw, "triple_after_overlay", [a_t_var])
    
    mw._scalar_watch_sidebar.remove_scalar(a_t_var)
    _capture_state(mw, "triple_after_watch", [a_t_var])

    # --- TestOverlayRemovalAfterPanelClose regression scenarios ---
    # We can effectively just run them here as well.
    def _run_regression(sym_i, sym_q, prefix, flush_stale):
        a_reg_i = ProbeAnchor(file="dsp.py", line=100, col=4, symbol=sym_i)
        a_reg_q = ProbeAnchor(file="dsp.py", line=101, col=4, symbol=sym_q)
        mw._on_probe_requested(a_reg_i)
        mw._on_probe_requested(a_reg_q)
        _capture_state(mw, f"{prefix}_init", [a_reg_i, a_reg_q])
        
        p_i = _find_panel_for_anchor(mw, a_reg_i)
        mw._probe_controller.handle_overlay_requested(p_i, a_reg_q)
        
        p_q = _find_panel_for_anchor(mw, a_reg_q)
        _close_panel(p_q)
        _capture_state(mw, f"{prefix}_after_q_close", [a_reg_q])
        
        if flush_stale:
            _flush_stale_panels(mw)
            
        mw._probe_controller.remove_overlay(p_i, a_reg_q)
        _capture_state(mw, f"{prefix}_end", [a_reg_i, a_reg_q])
        
    _run_regression("reg_i1", "reg_q1", "reg_flushed", True)
    _run_regression("reg_i2", "reg_q2", "reg_not_flushed", False)

    mw.close()


# ---------------------------------------------------------------------------
# Test Functions asserting against _STATE
# ---------------------------------------------------------------------------

class TestPanelAndWatch:
    def test_close_panel_while_in_watch_keeps_highlight(self):
        assert _STATE["cp_after_panel"]["highlights"]["x_cp"] is True
        assert _STATE["cp_after_close"]["highlights"]["x_cp"] is True
        
    def test_gutter_eye_survives_panel_close_when_in_watch(self):
        assert _STATE["cp_after_close"]["gutters"][10] is True

    def test_remove_watch_while_panel_open_keeps_highlight(self):
        assert _STATE["rw_after_remove"]["highlights"]["x_rw"] is True

    def test_close_panel_then_remove_watch_removes_highlight(self):
        assert _STATE["cprw_after_close"]["highlights"]["x_cprw"] is True
        assert _STATE["cprw_after_remove"]["highlights"]["x_cprw"] is False

    def test_remove_watch_then_close_panel_removes_highlight(self):
        assert _STATE["rwcp_after_remove"]["highlights"]["x_rwcp"] is True
        assert _STATE["rwcp_after_close"]["highlights"]["x_rwcp"] is False


class TestOverlayHighlight:
    def test_overlay_existing_anchor_keeps_highlight_after_panel_close(self):
        assert _STATE["over1_after_close"]["highlights"]["over_21"] is True

    def test_overlay_only_anchor_highlighted(self):
        assert _STATE["over2_highlight"]["highlights"]["over_23"] is True

    def test_removing_overlay_removes_highlight_when_not_used_elsewhere(self):
        assert _STATE["over3_before_remove"]["highlights"]["over_25"] is True
        assert _STATE["over3_after_remove"]["highlights"]["over_25"] is False

    def test_overlay_in_watch_keeps_highlight_after_overlay_removed(self):
        assert _STATE["over4_after_remove"]["highlights"]["over_27"] is True

    def test_close_panel_then_remove_overlay_clears_highlight(self):
        assert _STATE["over5_after_close"]["highlights"]["over_29"] is True
        assert _STATE["over5_after_remove"]["highlights"]["over_29"] is False

    def test_close_panel_then_remove_overlay_without_stale_flush(self):
        assert _STATE["over6_after_close"]["highlights"]["over_31"] is True
        assert _STATE["over6_after_remove"]["highlights"]["over_31"] is False


class TestWatchOnlyHighlight:
    def test_watch_only_variable_highlighted(self):
        assert _STATE["w1_highlight"]["highlights"]["w1"] is True

    def test_removing_watch_only_removes_highlight(self):
        assert _STATE["w2_before_remove"]["highlights"]["w2"] is True
        assert _STATE["w2_after_remove"]["highlights"]["w2"] is False


class TestAllThreeUsageTypes:
    def test_triple_usage_survives_incremental_removal(self):
        assert _STATE["triple_initial"]["highlights"]["t_var"] is True
        assert _STATE["triple_after_panel"]["highlights"]["t_var"] is True
        assert _STATE["triple_after_overlay"]["highlights"]["t_var"] is True
        assert _STATE["triple_after_watch"]["highlights"]["t_var"] is False


class TestOverlayRemovalAfterPanelClose:
    def test_stale_panels_already_flushed(self):
        assert _STATE["reg_flushed_init"]["highlights"]["reg_i1"] is True
        assert _STATE["reg_flushed_init"]["highlights"]["reg_q1"] is True
        assert _STATE["reg_flushed_after_q_close"]["highlights"]["reg_q1"] is True
        assert _STATE["reg_flushed_end"]["highlights"]["reg_q1"] is False
        assert _STATE["reg_flushed_end"]["highlights"]["reg_i1"] is True

    def test_stale_panels_not_yet_flushed(self):
        assert _STATE["reg_not_flushed_init"]["highlights"]["reg_i2"] is True
        assert _STATE["reg_not_flushed_init"]["highlights"]["reg_q2"] is True
        assert _STATE["reg_not_flushed_after_q_close"]["highlights"]["reg_q2"] is True
        assert _STATE["reg_not_flushed_end"]["highlights"]["reg_q2"] is False
        assert _STATE["reg_not_flushed_end"]["highlights"]["reg_i2"] is True
