from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg

app = QApplication([])
plot = pg.PlotWidget()

# Replace axis
new_axis = pg.AxisItem('bottom')
plot.getPlotItem().setAxisItems({'bottom': new_axis})

# Now call showGrid
plot.showGrid(x=True, y=True, alpha=0.5)

# Check if the new axis actually got the grid enabled
print('xGridCheck:', plot.getPlotItem().ctrl.xGridCheck.isChecked())
# For pyqtgraph AxisItem, the grid is controlled by a grid property
print('New axis grid (alpha 0-255):', new_axis.grid)
