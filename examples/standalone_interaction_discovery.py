import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow

class InteractionDiscoveryApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.main_window = QMainWindow()
        self.plot_widget = pg.PlotWidget(title="Interaction Discovery")
        self.main_window.setCentralWidget(self.plot_widget)
        self.main_window.resize(800, 600)
        
        # Add legend
        self.legend = self.plot_widget.addLegend()
        
        # Add some traces
        t = np.linspace(0, 10, 1000)
        
        self.plot1 = self.plot_widget.plot(t, np.sin(2 * np.pi * t), name="Sine Wave (Real)", pen='y')
        self.plot2 = self.plot_widget.plot(t, np.cos(2 * np.pi * t), name="Cosine Wave (Real)", pen='g')
        
        # Enable clicking on lines
        self.plot1.curve.setClickable(True)
        self.plot2.curve.setClickable(True)
        
        self.plot1.sigClicked.connect(lambda curve, ev: print(f"Line Clicked: {curve.name()}"))
        self.plot2.sigClicked.connect(lambda curve, ev: print(f"Line Clicked: {curve.name()}"))
        
        # Connect scene events
        scene = self.plot_widget.scene()
        scene.sigMouseClicked.connect(self.on_mouse_clicked)
        scene.sigMouseMoved.connect(self.on_mouse_moved)
        
        # Connect to axes
        self.plot_widget.getAxis('bottom').sigClicked = self.make_axis_click_handler('bottom')
        self.plot_widget.getAxis('left').sigClicked = self.make_axis_click_handler('left')
        
    def make_axis_click_handler(self, axis_name):
        def handler(axis, event):
            print(f"Axis Clicked: {axis_name}, Button: {event.button()}")
        return handler

    def on_mouse_clicked(self, event):
        pos = event.scenePos()
        items = self.plot_widget.scene().items(pos)
        
        clicked_components = []
        for item in items:
            if isinstance(item, pg.PlotDataItem):
                clicked_components.append("Line Plot")
            elif isinstance(item, pg.LegendItem):
                clicked_components.append("Legend Area")
            elif isinstance(item, pg.ViewBox):
                clicked_components.append("Graph Area (ViewBox)")
            elif isinstance(item, pg.AxisItem):
                clicked_components.append(f"Axis ({item.orientation})")
            elif "ItemSample" in type(item).__name__:
                clicked_components.append("Legend Sample (Color Box)")
            elif "LabelItem" in type(item).__name__:
                clicked_components.append("Legend Text Label")
        
        button_name = "Left" if event.button() == 1 else "Right" if event.button() == 2 else "Middle" if event.button() == 4 else str(event.button())
        modifiers = []
        if event.modifiers() & 0x02000000: modifiers.append("Alt") # Qt.KeyboardModifier.AltModifier
        if event.modifiers() & 0x04000000: modifiers.append("Ctrl") # Qt.KeyboardModifier.ControlModifier
        if event.modifiers() & 0x08000000: modifiers.append("Shift") # Qt.KeyboardModifier.ShiftModifier
        
        mod_str = "+".join(modifiers) + "+" if modifiers else ""
        
        print(f"Mouse Click: {mod_str}{button_name} Button at {pos.x(), pos.y()} -> Components: {clicked_components}")

    def on_mouse_moved(self, pos):
        # Could be noisy, let's just log drags if buttons are held
        # Unfortunately scene() doesn't easily emit drag events, but we can do it via mouse click/release if needed.
        pass

if __name__ == '__main__':
    app = InteractionDiscoveryApp(sys.argv)
    app.main_window.show()
    sys.exit(app.exec())
