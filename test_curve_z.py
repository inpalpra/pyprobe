from PIL import Image
from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg

app = QApplication([])
win = pg.GraphicsLayoutWidget()
plot = win.addPlot()

import numpy as np
t = np.linspace(0, 10, 50000)
data = np.sin(t * 1000) * 10 

# PUSH THE CURVE BACK
curve = plot.plot(t, data, pen=pg.mkPen('y', width=2))
curve.setZValue(-10)

plot.showGrid(x=True, y=True, alpha=1.0)
plot.getAxis('bottom').setGrid(255)
plot.getAxis('left').setGrid(255)

img = pg.QtGui.QImage(400, 300, pg.QtGui.QImage.Format.Format_ARGB32)
img.fill(pg.QtGui.QColor("black"))
painter = pg.QtGui.QPainter(img)
win.resize(400, 300)
win.render(painter)
painter.end()

img.save('test_grid_z3.png')

# Count grey pixels (the grid lines from the axis)
img = Image.open('test_grid_z3.png')
width, height = img.size
pixels = img.load()
grey_count = 0
for x in range(width):
    for y in range(height):
        r, g, b, a = pixels[x, y]
        # Grid lines are typically drawn with axis pen.
        if abs(r - g) < 5 and abs(r - b) < 5 and r > 100 and r < 200:
            grey_count += 1
print(f"Grey pixels (grid lines overlapping yellow data):{grey_count}")
