import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
import numpy as np

# Create app first!
app = QApplication(sys.argv)

from pyprobe.plugins.builtins.complex_plots import ComplexFftMagWidget
from pyprobe.plugins.builtins.waveform import WaveformFftMagWidget

def test():
    w_comp = ComplexFftMagWidget("Complex", QColor("red"))
    comp_data = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 500))
    w_comp.set_data(comp_data, "[500]")
    
    data = w_comp.get_plot_data()
    print("Complex plot curves:", len(data))
    if data and data[0]['x']:
        print("Complex plot data X:", data[0]['x'][:5])
        print("Complex plot data Y:", data[0]['y'][:5])
    else:
        print("Complex plot data is empty!")

    w_wave = WaveformFftMagWidget("Waveform", QColor("blue"))
    w_wave.update_data(comp_data.real, "waveform_real", (500,), "test")
    
    data2 = w_wave.get_plot_data()
    print("Waveform plot curves:", len(data2))
    if data2 and data2[0]['x']:
        print("Waveform plot data X:", data2[0]['x'][:5])
        print("Waveform plot data Y:", data2[0]['y'][:5])
    else:
        print("Waveform plot data is empty!")

test()
