
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollArea, QLabel
from PyQt6.QtCore import Qt
import sys

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        content = QLabel("Content inside scroll area\n" * 10)
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)
        
    def mousePressEvent(self, event):
        print("Window mousePressEvent triggered")
        super().mousePressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TestWindow()
    w.show()
    # We can't easily assert print output in this environment without blocking.
    # But I can check if QScrollArea generally consumes events.
    print("Test script capable of printing")
