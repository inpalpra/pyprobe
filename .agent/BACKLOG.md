# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### Drag graph with Alt key pressed to move to a different position
- When graph is click-dragged with Alt key pressed, the graph should move to a different position
  - If the graph is moved to a position where there is another graph, the other graph should be moved to the position of the graph that is being moved
  - If the graph is moved to a position where there is no other graph, the graph should be moved to the new position

### Delete Graph from Graphing Area
- User should be able to delete a graph by right clicking on the graph or by pressing x
- When a graph is deleted, the color of the probe should be released

### Auto Layout
- Autolayout graphs such that no empty space is wasted
  - If there are odd number of graphs, the last row should occupy the full width

### Manually Rearrange Graphs
- User should be able to pick a layout for the graphs manually
- User should be able to click and drag graphs to rearrange them
- Layout should not be restricted to a grid
  - for example, when probing 3 variables, user should be able to arrange them in
    - three columns
    - three rows
    - two colums in one row and one column in the next row
    - etc.

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
