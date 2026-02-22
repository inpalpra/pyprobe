import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPixmap
import numpy as np

app = QApplication(sys.argv)

from pyprobe.plugins.builtins.complex_plots import ComplexFftMagWidget

def generate_qam_signal(num_symbols: int, snr_db: float) -> tuple:
    QAM16_CONSTELLATION = np.array([
        -3-3j, -3-1j, -3+1j, -3+3j,
        -1-3j, -1-1j, -1+1j, -1+3j,
        +1-3j, +1-1j, +1+1j, +1+3j,
        +3-3j, +3-1j, +3+1j, +3+3j
    ]) / np.sqrt(10)
    symbol_indices = np.random.randint(0, 16, num_symbols)
    symbols = QAM16_CONSTELLATION[symbol_indices]
    noise_power = 10 ** (-snr_db / 10)
    noise = np.sqrt(noise_power / 2) * (np.random.randn(num_symbols) + 1j * np.random.randn(num_symbols))
    return symbols + noise

data = generate_qam_signal(500, 20)

w = ComplexFftMagWidget("Complex", QColor("red"))
w.resize(800, 600)
w.show()

# Feed data
w.set_data(data, "[500]")

# Force process events to render
app.processEvents()

# Save screenshot
pixmap = w.grab()
pixmap.save("screenshot.png")
print("Saved screenshot.png")
