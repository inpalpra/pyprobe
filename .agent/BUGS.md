# PyProbe Bug Backlog

## B1 2026-02-06 constellation-graph-no-data (INTERMITTENT)
**Status:** Backlog - Hard to reproduce

**Symptoms:**
- Click wrong symbol first (e.g., `np`)
- Click target symbol (`received_symbols`)
- Press RUN
- Panel exists but constellation graph shows nothing

**Works when:**
- Fresh open → click `received_symbols` directly → RUN → graph appears

**Suspected area:**
- Data flow timing between panel creation and runner IPC
- Registry `active_anchors` sync with `_probe_panels`
- Possible race with animation callbacks

**Debug logging added:**
- `probe_panel.py`: create_panel, remove_panel with _panels/_panels_by_name state

**Next steps when reproducible:**
1. Capture full debug log with probe_panel.py logging
2. Check if panel is in `active_anchors` when runner starts
3. Verify IPC messages include correct anchor

---

## B2 2026-02-06 highlight-rect-misplaced
**Status:** Backlog

**Symptoms:**
- Probe-able symbols show highlight rectangles in wrong locations
- Example: `received_symbols` @ line 72 and `power_db` @ line 77 show highlights far from actual variable text
- Most prominent when PyProbe window is not full screen / resized

**Suspected area:**
- `code_viewer.py:_get_rect_for_variable()` - character width or offset calculation
- `blockBoundingGeometry()` + `contentOffset()` may not account for scroll/resize
- Font metrics (`QFontMetricsF.horizontalAdvance`) vs actual rendered width

**Files:**
- `pyprobe/gui/code_viewer.py` lines 362-391

**Next steps:**
1. Add debug logging in `_get_rect_for_variable()` to print calculated vs expected positions
2. Test with different window sizes and scroll positions
3. Check if `contentOffset()` is being applied correctly
