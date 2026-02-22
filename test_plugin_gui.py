import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
import numpy as np
from pyprobe.plugins.builtins.complex_plots import ComplexFftMagPlugin, ComplexFftMagWidget

app = QApplication(sys.argv)

w_comp = ComplexFftMagWidget("Complex", QColor("red"))
w_comp.resize(800, 600)
w_comp.show()

comp_data = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 500))

plugin = ComplexFftMagPlugin()

# Mimic ProbePanel logic
from PyQt6.QtCore import QTimer
def update_call():
    plugin.update(w_comp, comp_data, "array.complex", (500,))
QTimer.singleShot(0, update_call)

app.processEvents()
import time
time.sleep(0.5)
app.processEvents()

pixmap = w_comp.grab()
pixmap.save("screenshot2.png")
print("Saved screenshot2.png")
