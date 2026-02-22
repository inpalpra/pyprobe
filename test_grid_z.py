from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg
import numpy as np

app = QApplication([])
plot = pg.PlotWidget()

# Dense block of data to hide background (like a solid sine wave)
t = np.linspace(0, 10, 5000)
data = np.sin(t * 100)
plot.plot(t, data, fillLevel=0, brush=(255,0,0,255), pen='r')

plot.showGrid(x=True, y=True, alpha=1.0)
print('Axis Z:', plot.getAxis('bottom').zValue())

import sys
# Just print info, no need to execute event loop
sys.exit(0)
