from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg

app = QApplication([])
plot = pg.PlotWidget()
new_axis = pg.AxisItem('bottom')
plot.getPlotItem().setAxisItems({'bottom': new_axis})
plot.showGrid(x=True, y=True, alpha=0.5)

print("Grid on old axis?", plot.getPlotItem().axes['top']['item'].grid)
print("Grid on new axis?", plot.getPlotItem().axes['bottom']['item'].grid)

# Manual grid enable
plot.getPlotItem().getAxis('bottom').setGrid(127)
print("Grid on new axis after manual set?", plot.getPlotItem().axes['bottom']['item'].grid)
