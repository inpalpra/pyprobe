from PyQt6.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg

app = QApplication([])
plot = pg.PlotWidget()
bax = plot.getAxis('bottom')
print("Default axis zValue:", bax.zValue())
bax.setZValue(10)
print("New axis zValue:", bax.zValue())
