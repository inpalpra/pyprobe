import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

app = QApplication([])
plot = pg.PlotWidget()

import numpy as np
t = np.linspace(0, 10, 50000)
data = np.sin(t * 1000) * 10 

plot.showGrid(x=True, y=True, alpha=1.0)
plot.getAxis('bottom').setZValue(10)

img = pg.QtGui.QImage(400, 300, pg.QtGui.QImage.Format.Format_ARGB32)
img.fill(pg.QtGui.QColor("black"))
painter = pg.QtGui.QPainter(img)
plot.resize(400, 300)
plot.render(painter)
painter.end()

def count_grey(filename):
    from PIL import Image
    i = Image.open(filename)
    pc = 0
    for p in i.getdata():
        if abs(p[0]-p[1]) < 5 and p[0] > 100 and p[0] < 200:
            pc += 1
    return pc

img.save('test_empty.png')
grey_empty = count_grey('test_empty.png')

curve = plot.plot(t, data, pen=pg.mkPen('y', width=2))
img.fill(pg.QtGui.QColor("black"))
painter = pg.QtGui.QPainter(img)
plot.render(painter)
painter.end()
img.save('test_defaultz.png')
grey_default = count_grey('test_defaultz.png')

curve.setZValue(-10)
img.fill(pg.QtGui.QColor("black"))
painter = pg.QtGui.QPainter(img)
plot.render(painter)
painter.end()
img.save('test_curve_z.png')
grey_curve_z = count_grey('test_curve_z.png')

print(f"Empty: {grey_empty}")
print(f"Default Z (axis 10): {grey_default}")
print(f"Curve -10 (axis 10): {grey_curve_z}")
