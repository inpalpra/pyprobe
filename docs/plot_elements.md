============================================================
CANONICAL UI ELEMENT MAP — FULLY EXPANDED
(Granular, testable, event-routable IDs)
============================================================

Naming Convention:
LAYER_PREFIX__COMPONENT__SUBCOMPONENT__INSTANCE

Layers:
W0__        = Window Layer
PLOT__      = Plot Structural Layer
DATA__      = Rendered Data Layer
LEGEND__    = Legend System
OVERLAY__   = Tool / HUD / Interaction Overlay
STATUS__    = Status Bar
MENU__      = Dropdown / Menu System


============================================================
1. WINDOW LAYER
============================================================

W0__ROOT
W0__FRAME_BORDER
W0__TITLE_BAR
W0__TITLE_TEXT
W0__WINDOW_ICON
W0__WINDOW_CLOSE_BTN
W0__WINDOW_PIN_BTN
W0__WINDOW_DRAG_REGION
W0__CONTENT_REGION
W0__RESIZE_HANDLE_BOTTOM_RIGHT
W0__RESIZE_HANDLE_EDGES


============================================================
2. PLOT STRUCTURAL LAYER
============================================================

PLOT__CONTAINER
PLOT__CANVAS
PLOT__BACKGROUND
PLOT__GRID_MAJOR
PLOT__GRID_MINOR
PLOT__GRID_ORIGIN_CROSSHAIR

PLOT__X_AXIS_LINE
PLOT__Y_AXIS_LINE

PLOT__X_AXIS_LABEL
PLOT__Y_AXIS_LABEL

PLOT__X_TICK_CONTAINER
PLOT__Y_TICK_CONTAINER

PLOT__X_TICK_MARK__N
PLOT__Y_TICK_MARK__N

PLOT__X_TICK_LABEL__N
PLOT__Y_TICK_LABEL__N

PLOT__VIEWPORT_CLIP_REGION
PLOT__DATA_RENDER_LAYER
PLOT__SELECTION_OVERLAY_LAYER
PLOT__ANNOTATION_LAYER


============================================================
3. DATA RENDERING LAYER
============================================================

DATA__TRACE_CONTAINER
DATA__TRACE__TR1
DATA__TRACE__TR3

DATA__TRACE__TR1__POINT__N
DATA__TRACE__TR3__POINT__N

DATA__TRACE__TR1__CLUSTER__N
DATA__TRACE__TR3__CLUSTER__N

DATA__POINT_HITBOX
DATA__TRACE_HIT_REGION

DATA__SELECTED_POINT_MARKER
DATA__HOVERED_POINT_MARKER
DATA__MULTI_SELECTED_REGION

DATA__CONSTELLATION_CENTROID
DATA__CONSTELLATION_BOUNDING_BOX

DATA__DENSITY_HEATMAP_LAYER (future-proof if added)


============================================================
4. LEGEND SYSTEM  (Expanded)
============================================================

LEGEND__CONTAINER
LEGEND__BACKGROUND
LEGEND__BORDER
LEGEND__TITLE

LEGEND__ITEM_CONTAINER

LEGEND__ITEM__TR1
LEGEND__ITEM__TR3

LEGEND__ITEM__TR1__SWATCH_CONTAINER
LEGEND__ITEM__TR3__SWATCH_CONTAINER

LEGEND__ITEM__TR1__SWATCH_SYMBOL
LEGEND__ITEM__TR3__SWATCH_SYMBOL

LEGEND__ITEM__TR1__SWATCH_LINE
LEGEND__ITEM__TR3__SWATCH_LINE

LEGEND__ITEM__TR1__LABEL
LEGEND__ITEM__TR3__LABEL

LEGEND__ITEM__TR1__VISIBILITY_TOGGLE
LEGEND__ITEM__TR3__VISIBILITY_TOGGLE

LEGEND__ITEM__TR1__LOCK_ICON
LEGEND__ITEM__TR3__LOCK_ICON

LEGEND__SCROLL_REGION (if legend becomes scrollable)

LEGEND__RESIZE_HANDLE
LEGEND__DRAG_REGION


============================================================
5. TOOL / MODE OVERLAY SYSTEM
============================================================

OVERLAY__MODE_SELECTOR_BUTTON
OVERLAY__MODE_SELECTOR_ICON
OVERLAY__MODE_SELECTOR_LABEL

OVERLAY__MODE_MENU_CONTAINER
OVERLAY__MODE_MENU_BACKGROUND
OVERLAY__MODE_MENU_ITEM__CONSTELLATION
OVERLAY__MODE_MENU_ITEM__FFT_MAG_ANGLE
OVERLAY__MODE_MENU_ITEM__REAL_IMAG
OVERLAY__MODE_MENU_ITEM__MAG_PHASE
OVERLAY__MODE_MENU_ITEM__LOG_MAG
OVERLAY__MODE_MENU_ITEM__LINEAR_MAG
OVERLAY__MODE_MENU_ITEM__PHASE_RAD
OVERLAY__MODE_MENU_ITEM__PHASE_DEG

OVERLAY__MODE_MENU_SCROLL_REGION

OVERLAY__ACTIVE_TOOL_BADGE
OVERLAY__ACTIVE_TOOL_LABEL

OVERLAY__ZOOM_BOX_RECT
OVERLAY__PAN_CURSOR_INDICATOR
OVERLAY__CROSSHAIR_CURSOR
OVERLAY__DRAG_SELECTION_RECT

OVERLAY__TOOLTIP_CONTAINER
OVERLAY__TOOLTIP_TEXT


============================================================
6. STATUS BAR SYSTEM
============================================================

STATUS__CONTAINER
STATUS__BACKGROUND

STATUS__SHAPE_LABEL
STATUS__SHAPE_VALUE

STATUS__POWER_LABEL
STATUS__POWER_VALUE

STATUS__SYMBOL_COUNT_LABEL
STATUS__SYMBOL_COUNT_VALUE

STATUS__SEPARATOR__N

STATUS__LIVE_CURSOR_COORD_LABEL
STATUS__LIVE_CURSOR_COORD_VALUE

STATUS__ERROR_INDICATOR
STATUS__WARNING_INDICATOR


============================================================
7. INTERACTION / HIT TEST ZONES
============================================================

HIT__CANVAS_DRAG_ZONE
HIT__AXIS_DRAG_ZONE_X
HIT__AXIS_DRAG_ZONE_Y
HIT__CORNER_ZOOM_ZONE
HIT__DATA_POINT_RADIUS
HIT__LEGEND_ITEM_REGION
HIT__MODE_MENU_ITEM_REGION
HIT__TITLE_BAR_DRAG_REGION


============================================================
8. TRANSIENT / STATEFUL ELEMENTS
============================================================

STATE__HOVERED_TRACE
STATE__ACTIVE_TRACE
STATE__HOVERED_POINT
STATE__SELECTED_POINTS_SET
STATE__ACTIVE_MODE
STATE__ACTIVE_TOOL
STATE__FOCUSED_ELEMENT
STATE__DRAG_IN_PROGRESS
STATE__SELECTION_IN_PROGRESS
STATE__PAN_IN_PROGRESS
STATE__ZOOM_IN_PROGRESS


============================================================
WHY THIS MATTERS
============================================================

With this granularity, you can:

• Route events precisely
• Write deterministic GUI tests
• Separate view vs interaction logic
• Implement modifier-specific behavior
• Support accessibility hooks
• Implement multi-select / hover / tool switching cleanly
• Extend safely (e.g., heatmap mode later)

If you'd like next:
- We can split these into MVC boundaries
- Or define which elements are “interactive” vs “render-only”
- Or define event priority / bubbling order
- Or define a clean internal event naming grammar
