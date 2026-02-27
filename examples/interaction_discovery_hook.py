import sys
import os
from PyQt6.QtCore import QObject, QEvent, Qt

class InteractionLogger(QObject):
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseMove, QEvent.Type.Wheel):
            try:
                # To avoid flood, only log Press, Release, and Wheel. Ignore Move unless a button is pressed
                if event.type() == QEvent.Type.MouseMove and int(event.buttons()) == 0:
                    return False
                    
                obj_name = obj.__class__.__name__
                
                # Get event details
                type_name = str(event.type()).split('.')[-1]
                
                button = "None"
                if hasattr(event, "button") and event.button() != Qt.MouseButton.NoButton:
                    button = str(event.button()).split('.')[-1]
                elif hasattr(event, "buttons") and int(event.buttons()) != 0:
                    button = "Buttons:" + str(int(event.buttons()))
                    
                modifiers = "None"
                if hasattr(event, "modifiers") and int(event.modifiers()) != 0:
                    modifiers = str(int(event.modifiers()))
                
                pos = "Unknown"
                if hasattr(event, "position"):
                    pos = f"({event.position().x()}, {event.position().y()})"
                elif hasattr(event, "pos"):
                    pos = f"({event.pos().x()}, {event.pos().y()})"
                
                print(f"INTERACTION | {type_name} on {obj_name} | Pos: {pos} | Btn: {button} | Mod: {modifiers}", flush=True)
            except Exception as e:
                pass
        return False # Do not swallow the event

def inject_logger():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        logger = InteractionLogger(app)
        app.installEventFilter(logger)
        # Keep a reference
        app._interaction_logger = logger
