import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

app = QApplication([])
win = pg.GraphicsLayoutWidget()
plot = win.addPlot()

# Draw dense data
import numpy as np
t = np.linspace(0, 10, 50000)
data = np.sin(t * 1000) * 10 
plot.plot(t, data, pen=pg.mkPen('y', width=2))

# Use standard pg grid
plot.showGrid(x=True, y=True, alpha=1.0)

# Set axis Z value
plot.getAxis('bottom').setZValue(10)
plot.getAxis('left').setZValue(10)

img = pg.QtGui.QImage(800, 600, pg.QtGui.QImage.Format.Format_ARGB32)
img.fill(pg.QtGui.QColor("black"))
painter = pg.QtGui.QPainter(img)
win.resize(800, 600)
win.render(painter)
painter.end()

img.save('test_grid_z.png')
print("Saved test_grid_z.png")

# Now try with explicit GridItem
plot2 = win.addPlot()
plot2.plot(t, data, pen=pg.mkPen('y', width=2))
# Disable axis grid
plot2.showGrid(x=False, y=False)
# Add explicit GridItem
grid = pg.GridItem(pen=pg.mkPen('w', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
grid.setZValue(20)
plot2.addItem(grid)

img2 = pg.QtGui.QImage(800, 600, pg.QtGui.QImage.Format.Format_ARGB32)
img2.fill(pg.QtGui.QColor("black"))
painter2 = pg.QtGui.QPainter(img2)
win.resize(800, 600)
win.render(painter2)
painter2.end()

img2.save('test_grid_item.png')
print("Saved test_grid_item.png")
