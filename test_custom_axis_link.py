import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
app = QApplication([])
plot = pg.PlotWidget()
new_axis = pg.AxisItem('bottom')
plot.getPlotItem().setAxisItems({'bottom': new_axis})

print("Linked view of new axis:", plot.getPlotItem().getAxis('bottom').linkedView())
print("Expected view:", plot.getPlotItem().vb)
