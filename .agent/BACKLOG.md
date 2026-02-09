# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### If I close the probe watch window, there should be a button to open it again

### BUG: If a scalar is in watch window, clicking that symbol again does NOT create graphical probe
- It should create a new graphical probe for that symbol
- If a scalar is in graphical probe, alt+click does add it to watch window -- as expected


### BUG: Double click to edit axis max min does not work for constellation and other complex data probes
- Double click on axis max min does not work for constellation and other complex data probes
- works for waveform probes


### Drag graph with Alt key pressed to move to a different position
- When graph is click-dragged with Alt key pressed, the graph should move to a different position
  - If the graph is moved to a position where there is another graph, the other graph should be moved to the position of the graph that is being moved
  - If the graph is moved to a position where there is no other graph, the graph should be moved to the new position

### Delete Graph from Graphing Area
- User should be able to delete a graph by right clicking on the graph or by pressing x
- When a graph is deleted, the color of the probe should be released

### Manually Rearrange Graphs
- In right click menu, graph should be allowed to expand to full width & shrink back to half width

---

## P2 - Medium Priority

### Press P to Park
- When P is pressed, the active graph is parked.


### Custom probes per symbol type
- **Function calls**: Display return value
- **Module refs**: Display module name/path
- **Class refs**: Display class info

### Symbol type indicator in probe panel
- Show icon/badge indicating if symbol is DATA_VARIABLE, FUNCTION_CALL, etc.
- Help user understand why "Nothing to show" appears

---

## P3 - Future

### Expression probing
- Probe arbitrary expressions like `np.sin(x)` for return value
- Requires tracer enhancements

### Probe persistence
- Save/restore probe configurations across sessions
- Remember which variables user typically watches
