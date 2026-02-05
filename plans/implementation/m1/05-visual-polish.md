# Plan 5: Visual Polish & UX

**Focus:** Probe panel UX - liveness, colors, animations, identity.

**Branch:** `m1/visual-polish`

**Dependencies:** Plan 0 (ProbeAnchor, ProbeState)

**Complexity:** Large (L)

**UX Requirements Addressed:**
- #1 Silent failures → pulse animation feedback
- #2 Live/frozen ambiguity → liveness indicators
- #3 First-hit latency → armed state with pulsing ring
- #5 Color overload → limited palette (5 colors)
- #6 Removal lacks finality → fade-out animation
- #8 Identity not nameable → `symbol @ file:line` labels
- #9 Performance cost opaque → throttle indicator

---

## Files to Create

### `pyprobe/gui/probe_state_indicator.py`

Visual indicator widget showing probe state:
- **ARMED:** Pulsing yellow ring (waiting for data)
- **LIVE:** Solid green dot (receiving data)
- **STALE:** Dim gray dot (no recent updates)
- **INVALID:** Red X (anchor invalid)

Key features:
- `QPropertyAnimation` for pulsing effect
- `show_invalid_feedback()` for brief error flash
- Custom `paintEvent` for state visualization

See main plan file for full code (~120 lines).

### `pyprobe/gui/animations.py`

```python
"""Animation utilities for probe lifecycle."""
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

class ProbeAnimations:
    """Factory for probe lifecycle animations."""

    @staticmethod
    def fade_out(widget: QWidget, duration_ms: int = 300, on_finished=None) -> QPropertyAnimation:
        """Create fade-out animation for probe removal."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        if on_finished:
            anim.finished.connect(on_finished)

        return anim
```

---

## Files to Modify (Replace Stubs)

### `pyprobe/gui/color_manager.py`

Full implementation with:
- **Limited palette:** 5 colors (cyan, magenta, green, yellow, orange)
- **LRU tracking:** OrderedDict for usage order
- **De-emphasis:** Older probes fade toward 0.6 alpha
- **Recycling:** When all colors used, recycle oldest

Key methods:
- `get_color(anchor)` - Get/assign color
- `release_color(anchor)` - Free color on removal
- `get_emphasis_level(anchor)` - 0.0-1.0 based on recency

See main plan file for full code (~90 lines).

### `pyprobe/gui/probe_registry.py`

Full implementation with:
- **Lifecycle tracking:** ARMED → LIVE → STALE → INVALID
- **Stale detection:** Timer checks every 500ms, marks stale after 2s
- **Signal emission:** For UI updates on state changes
- **Color management:** Integration with ColorManager

Key methods:
- `add_probe(anchor)` - Returns color
- `remove_probe(anchor)` - With signal emission
- `update_data_received(anchor)` - Updates liveness
- `invalidate_anchors(anchors)` - Batch invalidation

See main plan file for full code (~110 lines).

### `pyprobe/gui/probe_panel.py`

Add M1 enhancements:
- **State indicator:** ProbeStateIndicator widget in header
- **Identity label:** `symbol @ file:line` in probe color
- **Throttle indicator:** Lightning bolt icon when throttling
- **Removal animation:** `animate_removal()` method with fade

```python
# === M1 ADDITIONS ===

class ProbePanel(QFrame):
    def __init__(self, anchor: ProbeAnchor, color: QColor, parent=None):
        # M1: Now takes anchor instead of var_name
        self._anchor = anchor
        self._color = color
        self._state_indicator = ProbeStateIndicator()
        self._identity_label = QLabel(anchor.identity_label())
        self._throttle_label = QLabel("⚡")  # Hidden by default

    def set_state(self, state: ProbeState) -> None:
        self._state_indicator.set_state(state)

    def animate_removal(self, on_complete=None) -> None:
        anim = ProbeAnimations.fade_out(self, on_finished=on_complete)
        anim.start()

# === M1 ADDITIONS END ===
```

---

## Key Implementation Notes

### State Indicator Visual Design

```
ARMED:   ○  (pulsing yellow ring)
LIVE:    ●  (solid green dot)
STALE:   ●  (dim gray dot)
INVALID: ✗  (red X)
```

### Color Palette

```python
PALETTE = [
    QColor('#00ffff'),  # Cyan (primary)
    QColor('#ff00ff'),  # Magenta
    QColor('#00ff00'),  # Green
    QColor('#ffff00'),  # Yellow
    QColor('#ff8800'),  # Orange
]
```

### Emphasis Calculation

```python
def get_emphasis_level(anchor):
    position = keys.index(anchor)  # 0 = oldest
    total = len(keys)
    normalized = position / (total - 1)
    return 0.6 + (normalized * 0.4)  # Range: 0.6 to 1.0
```

---

## Verification

```bash
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)

from pyprobe.gui.probe_state_indicator import ProbeStateIndicator
from pyprobe.gui.probe_state import ProbeState

indicator = ProbeStateIndicator()
indicator.set_state(ProbeState.ARMED)
indicator.show()
app.exec()
"
```

Expected: Yellow pulsing ring animation.

---

## Merge Conflict Risk

**Medium** - Modifies `probe_panel.py` and replaces stub implementations:
- `color_manager.py` - Replaces stub with full implementation
- `probe_registry.py` - Replaces stub with full implementation
- `probe_panel.py` - Adds new parameters and methods

Mitigation: Stub files define the interface, so implementation is compatible.
