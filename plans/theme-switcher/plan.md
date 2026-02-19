# Theme Switcher Plan

## Goal

Allow users to select from multiple bundled themes at runtime, with their choice persisted across sessions, including a high-end RF instrument-panel dark theme.

---

## Current State

- One theme: `cyberpunk.py` in `pyprobe/gui/theme/`, applied once at startup via `apply_cyberpunk_theme(widget)`.
- The `COLORS` dict in `cyberpunk.py` is **not** referenced by most widgets. Nearly all color usage is raw hex strings scattered throughout widget files (`file_tree.py`, `probe_panel.py`, `dock_bar.py`, `code_highlighter.py`, plots, etc.).
- No settings/preferences persistence for UI state — only per-script sidecar `.pyprobe` JSON files exist.
- No settings dialog, no `QSettings` usage.

---

## Architecture

### Theme Protocol

Each theme is a dataclass conforming to:

```python
@dataclass
class Theme:
    name: str                     # display name, e.g. "Cyberpunk"
    id: str                       # stable key for persistence, e.g. "cyberpunk"
    colors: dict[str, str]        # semantic color tokens (same keys as today's COLORS)
    stylesheet: str               # QSS applied to the app
    syntax_colors: dict[str, str] # tokens used by CodeHighlighter
    plot_colors: dict[str, str]   # tokens used by PyQtGraph widgets
    row_colors: list[str]         # ordered palette for multi-signal plots
```

The `colors` dict must define the full set of semantic tokens (bg_darkest, bg_dark, ... text_muted, neon_cyan, etc.) so widgets can look up tokens by name without needing to hardcode hex.

### ThemeManager Singleton

`pyprobe/gui/theme/theme_manager.py`

```python
class ThemeManager(QObject):
    theme_changed = pyqtSignal(Theme)   # emitted after theme swap

    @classmethod
    def instance(cls) -> "ThemeManager": ...

    def set_theme(self, theme_id: str) -> None:
        # applies stylesheet to QApplication, emits theme_changed
    
    @property
    def current(self) -> Theme: ...
    
    def available(self) -> list[Theme]: ...
```

- Holds the global `QApplication` reference for `setStyleSheet()`.
- Emits `theme_changed` so any connected widget can re-apply its local colors.
- Applied at app init, and again whenever the user picks a new theme.

### Theme Registry

`pyprobe/gui/theme/__init__.py`

```python
from .cyberpunk import CYBERPUNK_THEME
from .monokai   import MONOKAI_THEME
from .ocean     import OCEAN_THEME
from .instrument_panel import INSTRUMENT_PANEL_THEME

THEMES: dict[str, Theme] = {
    t.id: t for t in [CYBERPUNK_THEME, MONOKAI_THEME, OCEAN_THEME, INSTRUMENT_PANEL_THEME]
}
DEFAULT_THEME_ID = "cyberpunk"
```

---

## Widget Side: Token Consumption

Today most widgets call `self.setStyleSheet("background: #0d0d0d; color: #ffffff; ...")`.

After this change they will:

1. Connect to `ThemeManager.instance().theme_changed`.
2. Implement `_apply_theme(theme: Theme)` that rebuilds the stylesheet from `theme.colors`.
3. Call `_apply_theme(ThemeManager.instance().current)` in `__init__` for initial setup.

For QSS strings the pattern is:

```python
def _apply_theme(self, theme: Theme):
    c = theme.colors
    self.setStyleSheet(f"""
        QWidget {{ background: {c['bg_dark']}; color: {c['text_primary']}; }}
        ...
    """)
```

For PyQtGraph widgets: call `self.plot_widget.setBackground(theme.plot_colors['bg'])` and update `pg.mkPen` colors.

**Files to update** (from audit):
- `gui/file_tree.py`
- `gui/probe_panel.py`
- `gui/dock_bar.py`
- `gui/code_gutter.py`
- `gui/control_bar.py`
- `gui/code_highlighter.py` — syntax colors come from `theme.syntax_colors`
- `plots/scalar_history_chart.py`
- `plots/scalar_display.py`
- `plots/constellation.py`
- `plots/pin_indicator.py`
- `plugins/builtins/waveform.py` — `ROW_COLORS` replaced by `theme.row_colors`
- `plugins/builtins/scalar_display.py`
- `plugins/builtins/constellation.py`
- `plugins/builtins/scalar_history.py`

---

## Bundled Themes

Ship four themes to start:

| ID | Name | Style |
|----|------|-------|
| `cyberpunk` | Cyberpunk | Current default — black bg, neon cyan/magenta/green |
| `monokai` | Monokai Dark | Dark gray bg, warm orange/yellow/green accents |
| `ocean` | Ocean Dark | Deep navy bg, blue/teal/white accents |
| `instrument-panel` | Instrument Panel Dark | Charcoal panel surfaces, muted grays, amber markers, green pass-state accents, cyan trace highlights |

### New Theme Notes: Instrument Panel Dark

- Visual target: premium RF test-and-measurement front panel with high readability in dense data views.
- Base tones: near-black/charcoal backgrounds with subtle panel separation.
- Accent hierarchy:
    - Primary signal accent: cyan/blue for active traces and selections.
    - Status accent: green for healthy/locked/pass states.
    - Marker accent: amber for cursors, deltas, warnings, and reference readouts.
- Text hierarchy: bright neutral for primary text, cooler muted neutral for secondary labels.
- Plot behavior: keep grids low-contrast, traces high-contrast, and marker/readout colors consistent with non-plot widgets.

### Detailed Requirements: Instrument Panel Dark

#### 1) Visual System Requirements

- Overall feel: professional lab instrument UI, low-glare, high information density, zero decorative neon effects.
- Surfaces must be layered with clear depth cues:
    - App chrome (`bg_darkest`) for global frame and dock background.
    - Panel (`bg_dark`) for control groups and side panes.
    - Elevated panel (`bg_medium`) for active cards, selected rows, and input fields.
    - Delimiters (`border_default`, `border_strong`) for section boundaries and axis framing.
- Avoid pure black and pure white; use near-black and off-white to reduce eye fatigue during long sessions.

#### 2) Color Token Requirements

All required semantic tokens must be populated in `colors` for this theme; no widget should introduce ad-hoc hex values.

- Background tokens:
    - `bg_darkest`: outer shell and main application canvas.
    - `bg_dark`: standard panel background.
    - `bg_medium`: active controls and selected list rows.
    - `bg_light`: hover surfaces and editable cell emphasis.
- Border tokens:
    - `border_default`: standard separators and card outlines.
    - `border_strong`: plot frame, focus ring fallback, selected table row outline.
- Text tokens:
    - `text_primary`: primary labels, values, and code text.
    - `text_secondary`: secondary labels and unit captions.
    - `text_muted`: disabled or tertiary metadata.
- Accent/status tokens:
    - `accent_primary`: active trace, selected control, active tab underline.
    - `accent_secondary`: secondary series/alternate active indicator.
    - `accent_marker`: marker/cursor labels, delta readouts, threshold references.
    - `success`: pass/lock/valid states.
    - `warning`: caution states and soft alerts.
    - `error`: clipping/invalid/error states.

#### 3) Typography Requirements (High-End Instrument Style)

Typography should feel precise and technical while remaining readable at smaller sizes.

- UI Sans stack (controls, menus, panel labels):
    - Preferred: `Inter`, `IBM Plex Sans`.
    - System fallback: `SF Pro Text` (macOS), `Segoe UI` (Windows), `Noto Sans`.
    - Final fallback: generic `sans-serif`.
- Data/Code Mono stack (numerical readouts, code viewer, axis value labels where practical):
    - Preferred: `JetBrains Mono`, `IBM Plex Mono`.
    - System fallback: `SF Mono` (macOS), `Consolas` (Windows), `Menlo`.
    - Final fallback: generic `monospace`.
- Size/weight rhythm:
    - Major value readout: 15–17 px, weight 600.
    - Section headings: 13–14 px, weight 600.
    - Standard controls/labels: 12–13 px, weight 500.
    - Dense metadata/table cells: 11–12 px, weight 450–500.
    - Never drop below 11 px for critical values.
- Numeric readability rules:
    - Use tabular figures where supported for stable number alignment.
    - Keep decimal points vertically aligned in table-style readouts.
    - Preserve strong contrast between value and unit text.

#### 4) Plot & Signal Visualization Requirements

- Plot background must be darker than surrounding control panels, but not pure black.
- Grid strategy:
    - Major grid visible but subdued.
    - Minor grid faint enough to avoid Moiré-like clutter.
- Trace strategy:
    - Primary trace uses `accent_primary` with highest prominence.
    - Secondary traces use ordered `row_colors` tuned for dark backgrounds.
    - Marker/cursor overlays must always outrank trace visibility using `accent_marker`.
- Readout consistency:
    - Marker text, delta labels, and threshold annotations use the same token family across waveform, scalar history, and constellation views.

#### 5) Interaction State Requirements

- Hover: subtle luminance increase on panel/control background; no hue jump.
- Active/selected: border or underline emphasis using `accent_primary`.
- Keyboard focus: clearly visible ring using `border_strong` or `accent_primary`, minimum 2 px equivalent visual weight.
- Disabled: lower contrast and saturation, while remaining legible.
- Status pills/badges:
    - Pass/locked uses `success` with restrained fill.
    - Warning uses `warning` with readable foreground contrast.
    - Error uses `error` with strongest urgency contrast.

#### 6) Code/Syntax Requirements

- `syntax_colors` for Instrument Panel Dark should be less saturated than cyberpunk defaults.
- Recommended mapping intent:
    - Keywords: cool cyan/blue family.
    - Strings: subdued green family.
    - Numbers/constants: amber family aligned with marker color language.
    - Comments: muted neutral with clear readability.
- Gutter line numbers and highlights must harmonize with panel tones and avoid drawing more attention than active code selection.

#### 7) Accessibility & Contrast Requirements

- Target minimum contrast:
    - Normal text: 4.5:1 against its background.
    - Large text/major readouts: 3:1 minimum.
    - Critical data (marker labels, alarms, active trace labels): 7:1 preferred where feasible.
- Do not encode meaning by color alone; status cues should include iconography/text labels where already available.

#### 8) Acceptance Criteria for This Theme

- Theme switches live without restart and updates all registered widgets/plots.
- No hardcoded hex values remain in migrated instrumented widgets.
- Data-dense views remain readable for long sessions at default scaling.
- Typography stack gracefully falls back across macOS/Windows/Linux without layout breakage.
- Plot marker/readout visibility remains clear with 4+ simultaneous traces.
- Theme menu, persistence, and restore-on-startup work identically to other bundled themes.

A light theme is a stretch goal — it requires flipping every background assumption and is a larger effort.

---

## Persistence

Store the selected theme ID in `~/.config/pyprobe/settings.json`:

```json
{ "theme": "monokai" }
```

`pyprobe/core/settings.py` (new file) — thin wrapper:

```python
def load_settings() -> dict: ...
def save_settings(data: dict) -> None: ...
def get_setting(key: str, default) -> Any: ...
def set_setting(key: str, value) -> None: ...
```

Loaded at app startup in `app.py`, written whenever the user changes theme.

---

## UI: Theme Selector

A `View → Theme` submenu on the menu bar (or a `⚙ Settings` dialog if one exists later):

```
View
  └── Theme
        ○ Cyberpunk      ← checked if active
        ○ Monokai Dark
        ○ Ocean Dark
                ○ Instrument Panel Dark
```

Each action calls `ThemeManager.instance().set_theme(theme_id)` and `set_setting("theme", theme_id)`.

The menu is built dynamically from `ThemeManager.instance().available()` so adding new themes in the future requires no menu code changes.

---

## Milestones

### M1 — Theme Protocol + ThemeManager (foundation)
- Define `Theme` dataclass in `pyprobe/gui/theme/base.py`.
- Create `ThemeManager` singleton in `pyprobe/gui/theme/theme_manager.py`.
- Convert `cyberpunk.py` to produce a `Theme` instance; keep `apply_cyberpunk_theme()` as a shim to not break things.
- Wire `ThemeManager` into `app.py` startup.

### M2 — Token Centralization (biggest chunk)
- Audit all hardcoded hex strings (see file list above).
- Replace each with a theme token lookup in a `_apply_theme(theme)` method.
- Connect each widget to `theme_changed`.
- Code highlighter pulls syntax colors from `theme.syntax_colors`.
- PyQtGraph widgets update backgrounds + pen colors via `_apply_theme`.

### M3 — Additional Themes
- Implement `monokai.py`, `ocean.py`, and `instrument_panel.py` as `Theme` instances.
- Register them in `__init__.py`.
- Verify all widgets look correct under each theme.
- Verify dense RF plot readability (trace/marker/grid contrast) specifically in `instrument-panel`.

### M4 — Persistence
- Implement `pyprobe/core/settings.py`.
- Load theme id from settings at startup in `app.py`.
- Fallback to `cyberpunk` if setting is missing or unknown.

### M5 — Theme Switcher UI
- Add `View` menu (or extend existing menu bar) to `MainWindow`.
- Build Theme submenu dynamically from `ThemeManager.available()`.
- Switching theme live: `ThemeManager.set_theme()` propagates via signal with no restart required.
- Persist new choice immediately on selection.

---

## Open Questions

- **Live switch vs restart**: M3 signal-based approach allows live switching. If wiring all widgets is too much work, an alternative is to write the setting and required a restart — but live is better UX and not that much harder once M2 tokens are centralized.
- **Plugin-provided widgets**: Third-party plugins that hardcode colors won't inherit theme changes. A `ThemeManager.instance().current` getter and the `theme_changed` signal should be documented in the plugin API so plugin authors can opt in.
- **ColorManager probe palette**: The golden-angle HSL color assignment already works on any dark background. For a light theme (stretch goal), saturation/lightness parameters would need to be theme-dependent.
- **Contrast tuning in instrument theme**: If cyan/amber markers compete in busy plots, define explicit marker-vs-trace priority and minimum luminance contrast thresholds in `plot_colors`.
