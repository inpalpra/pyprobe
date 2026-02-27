============================================================
MOUSE + TRACKPAD + MODIFIER INTERACTION TAXONOMY
(Platform-aware, PyQt-relevant, macOS included)
============================================================

------------------------------------------------------------
1. BASIC MOUSE BUTTON EVENTS
------------------------------------------------------------

L_PRESS
L_RELEASE
L_CLICK
L_DOUBLE_CLICK
L_TRIPLE_CLICK

R_PRESS
R_RELEASE
R_CLICK

M_PRESS
M_RELEASE
M_CLICK

MOVE_NO_BUTTON
MOVE_WITH_L_BUTTON
MOVE_WITH_R_BUTTON
MOVE_WITH_M_BUTTON


------------------------------------------------------------
2. DRAG INTERACTIONS
------------------------------------------------------------

L_DRAG
R_DRAG
M_DRAG

DRAG_START
DRAG_UPDATE
DRAG_END

CLICK_DRAG_SELECT_BOX
CLICK_DRAG_PAN
CLICK_DRAG_AXIS_SCALE_X
CLICK_DRAG_AXIS_SCALE_Y


------------------------------------------------------------
3. WHEEL / SCROLL EVENTS
------------------------------------------------------------

WHEEL_SCROLL_VERTICAL
WHEEL_SCROLL_HORIZONTAL
WHEEL_SCROLL_HIGH_RESOLUTION   (trackpad smooth scroll)
WHEEL_SCROLL_MOMENTUM
WHEEL_SCROLL_BEGIN
WHEEL_SCROLL_UPDATE
WHEEL_SCROLL_END

SHIFT + WHEEL_SCROLL_VERTICAL     (often horizontal scroll)
CTRL + WHEEL_SCROLL               (often zoom)
ALT + WHEEL_SCROLL
META + WHEEL_SCROLL


------------------------------------------------------------
4. TRACKPAD GESTURES (macOS specific where noted)
------------------------------------------------------------

TWO_FINGER_SCROLL_VERTICAL
TWO_FINGER_SCROLL_HORIZONTAL
TWO_FINGER_TAP              (maps to right click on macOS)
TWO_FINGER_DRAG

THREE_FINGER_DRAG           (macOS accessibility feature)
THREE_FINGER_SWIPE_LEFT
THREE_FINGER_SWIPE_RIGHT
THREE_FINGER_SWIPE_UP
THREE_FINGER_SWIPE_DOWN

FOUR_FINGER_SWIPE_LEFT      (Mission Control / OS-level)
FOUR_FINGER_SWIPE_RIGHT
FOUR_FINGER_SWIPE_UP
FOUR_FINGER_SWIPE_DOWN

PINCH_ZOOM_IN
PINCH_ZOOM_OUT

ROTATE_GESTURE              (two-finger rotate)

SMART_ZOOM_DOUBLE_TAP       (macOS two-finger double tap)


------------------------------------------------------------
5. NATIVE GESTURE EVENTS (Qt abstraction layer)
------------------------------------------------------------

NATIVE_GESTURE_BEGIN
NATIVE_GESTURE_UPDATE
NATIVE_GESTURE_END

NATIVE_ZOOM
NATIVE_ROTATE
NATIVE_PAN
NATIVE_SWIPE


------------------------------------------------------------
6. MODIFIER KEYS (Keyboard Layer)
------------------------------------------------------------

SHIFT
CTRL
ALT
META            (Command on macOS, Windows key on Windows)

CAPS_LOCK
FN              (macOS only, hardware dependent)


------------------------------------------------------------
7. MOUSE + MODIFIER COMBINATIONS
------------------------------------------------------------

SHIFT + L_CLICK
CTRL  + L_CLICK
ALT   + L_CLICK
META  + L_CLICK

SHIFT + L_DOUBLE_CLICK
CTRL  + L_DOUBLE_CLICK

SHIFT + L_DRAG
CTRL  + L_DRAG
ALT   + L_DRAG
META  + L_DRAG

SHIFT + R_CLICK
CTRL  + R_CLICK
ALT   + R_CLICK
META  + R_CLICK

SHIFT + WHEEL_SCROLL
CTRL  + WHEEL_SCROLL
ALT   + WHEEL_SCROLL
META  + WHEEL_SCROLL

SHIFT + PINCH_ZOOM
CTRL  + PINCH_ZOOM
ALT   + PINCH_ZOOM
META  + PINCH_ZOOM

SHIFT + TWO_FINGER_SCROLL
CTRL  + TWO_FINGER_SCROLL
ALT   + TWO_FINGER_SCROLL
META  + TWO_FINGER_SCROLL


------------------------------------------------------------
8. ADVANCED / CHORD INTERACTIONS
------------------------------------------------------------

SHIFT + CTRL + L_CLICK
SHIFT + ALT + L_CLICK
CTRL  + ALT + L_CLICK
SHIFT + CTRL + L_DRAG

CTRL  + PINCH_ZOOM
ALT   + PINCH_ZOOM
META  + PINCH_ZOOM

CTRL  + TWO_FINGER_TAP
SHIFT + TWO_FINGER_TAP

CTRL  + THREE_FINGER_DRAG
ALT   + THREE_FINGER_DRAG


------------------------------------------------------------
9. PRESS-HOLD VARIANTS
------------------------------------------------------------

LONG_PRESS_L_BUTTON
LONG_PRESS_R_BUTTON
SHIFT + LONG_PRESS
CTRL  + LONG_PRESS

PRESS_AND_HOLD_THEN_DRAG
PRESS_AND_HOLD_THEN_CONTEXT_MENU


------------------------------------------------------------
10. PLATFORM-SPECIFIC NOTES
------------------------------------------------------------

macOS:
- META == Command key
- Two-finger tap == Right click
- NativeGestureType events available
- Three-finger drag requires accessibility setting
- Pinch and Rotate emit high-resolution native gestures

Windows:
- Precision touchpad emits high-resolution wheel events
- Some gestures converted to wheel events
- META == Windows key (often not delivered to app)

Linux:
- Gesture support depends on compositor
- Many trackpads emit wheel-only events


============================================================
IMPORTANT IMPLEMENTATION NOTE
============================================================

If modifier combinations like Option+Click are not detected,
you must explicitly track:

- keyPressEvent()
- keyReleaseEvent()
- event.modifiers()

in combination with:

- mousePressEvent()
- wheelEvent()
- nativeGestureEvent()

Qt will not implicitly combine them for you.

You must build your own interaction state model.
============================================================
