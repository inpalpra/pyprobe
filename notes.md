features

Graph interactions:
1. pin x scale, pin y scale -- have visual indicator of pinned state
2. set max x, min x, max y, min y -- have visual indicator of set state
3. double click to maximize, double click again to restore
4. a way to minimize graphs to the bottom bar, and restore them back to the graph area
5. a way to group graphs together, to make their x scales sync, or y scales sync, or both
6. within each graph area, translucent tiny buttons:
    - hand: pan
    - zoom: zoom arbitrary rectangle
    - zoom x: zoom x axis only
    - zoom y: zoom y axis only
    - reset: reset zoom
    - mousepointer: normal, default (disable all zoom, pan etc.) 



import sys
import os
import time
from pyprobe.core.tracer import VariableTracer, WatchConfig, CapturedVariable
from pyprobe.core.anchor import ProbeAnchor

# Path to regression script
script_path = os.path.abspath("regression/loop.py")
print(f"Target script: {script_path}")

# Callback to print captured values
def on_data(captured):
    print(f"CAPTURED: {captured.name} = {captured.value} @ line {captured.line_number}")

def on_anchor_data(anchor, captured):
    print(f"ANCHOR CAPTURE: {anchor.symbol} = {captured.value} @ line {anchor.line}")

# Initialize Tracer
tracer = VariableTracer(
    data_callback=on_data,
    anchor_data_callback=on_anchor_data,
    target_files={script_path}
)

# Create Anchor for 'x' at line 4 (x = x - 1)
# 'x' is on LHS.
anchor = ProbeAnchor(
    file=script_path,
    line=4,
    col=8, 
    symbol="x",
    func="main",
    is_assignment=True 
)

tracer.add_anchor_watch(anchor)

print("Starting tracer...")
tracer.start()

# Manually trigger trace init if needed? No, start() sets sys.settrace

# Execute the script
try:
    with open(script_path) as f:
        code = compile(f.read(), script_path, 'exec')
        # Use a fresh globals dict
        globs = {
            '__name__': '__main__',
            '__file__': script_path,
        }
        exec(code, globs)
except Exception as e:
    print(f"Script exception: {e}")
    import traceback
    traceback.print_exc()

print("Script finished.")
tracer.stop()


--- 

LIVE reload upon edit saved
save and load?
python decoration for probing?