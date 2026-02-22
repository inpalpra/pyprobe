from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg

app = QApplication([])
plot = pg.PlotWidget()
plot.showGrid(x=True, y=True, alpha=0.5)

types = [type(i).__name__ for i in plot.getPlotItem().items]
print("Items in plot:", types)
plot.getAxis('bottom').setZValue(10)

types2 = [type(i).__name__ for i in plot.getPlotItem().items]
print("After setting Z=10, does something change?:", types2)
print("Grid is child of axis?", plot.getAxis('bottom').childItems())
