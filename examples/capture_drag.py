import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QEvent
import pyqtgraph as pg
import numpy as np

class LoggingPlotWidget(pg.PlotWidget):
    def wheelEvent(self, ev):
        print(f"WHEEL EVENT | delta: {ev.angleDelta().y()} | phase: {ev.phase()} | pos: {ev.position()}", flush=True)
        super().wheelEvent(ev)
        
    def mousePressEvent(self, ev):
        print(f"MOUSE PRESS | button: {ev.button()} | pos: {ev.position()}", flush=True)
        super().mousePressEvent(ev)
        
    def mouseMoveEvent(self, ev):
        print(f"MOUSE MOVE | buttons: {ev.buttons().value} | pos: {ev.position()}", flush=True)
        super().mouseMoveEvent(ev)
        
    def mouseReleaseEvent(self, ev):
        print(f"MOUSE RELEASE | button: {ev.button()} | pos: {ev.position()}", flush=True)
        super().mouseReleaseEvent(ev)

    def event(self, ev):
        if ev.type() == QEvent.Type.NativeGesture:
            print(f"NATIVE GESTURE | type: {ev.gestureType()} | val: {ev.value()}", flush=True)
        elif ev.type() == QEvent.Type.Gesture:
            print(f"GESTURE EVENT", flush=True)
        return super().event(ev)

def main():
    app = QApplication(sys.argv)
    win = QMainWindow()
    
    plot = LoggingPlotWidget()
    t = np.linspace(0, 10, 1000)
    plot.plot(t, np.sin(2 * np.pi * t), name="Sine")
    
    win.setCentralWidget(plot)
    win.resize(800, 600)
    win.show()
    
    print("==========================================", flush=True)
    print("Please try two-finger drag and three-finger drag on the graph or axes.", flush=True)
    print("==========================================", flush=True)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
