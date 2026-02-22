import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

app = QApplication([])
plot = pg.PlotWidget()

# Replace axis
new_axis = pg.AxisItem('bottom')
plot.getPlotItem().setAxisItems({'bottom': new_axis})

plot.showGrid(x=True, y=True, alpha=0.5)
import numpy as np
plot.plot(np.random.normal(size=100))

# Try rendering to an image to test without event loop
img = pg.QtGui.QImage(800, 600, pg.QtGui.QImage.Format.Format_ARGB32)
plot.grab().save('test.png')
print("Image saved")
