from PyQt6.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg
import numpy as np

app = QApplication([])
win = QMainWindow()
plot = pg.PlotWidget()
win.setCentralWidget(plot)

# Dense block of data to hide background (like a solid sine wave)
t = np.linspace(0, 10, 50000)
data = np.sin(t * 1000) * 10 # very high frequency

# Curve takes Z=0 natively
plot.plot(t, data, pen='r')

plot.showGrid(x=True, y=True, alpha=0.8)

# Now, push the axes (which draw the grid) to Z > 0
plot.getAxis('bottom').setZValue(10)
plot.getAxis('left').setZValue(10)

# Export an image or wait directly to see if it worked
img = pg.QtGui.QImage(800, 600, pg.QtGui.QImage.Format.Format_ARGB32)
img.fill(pg.QtGui.QColor("transparent"))
# Just save a screenshot
import time
def export():
    plot.grab().save('test.png')
    app.quit()

pg.QtCore.QTimer.singleShot(1000, export)
win.show()
app.exec()
