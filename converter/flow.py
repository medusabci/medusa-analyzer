from PySide6 import QtWidgets

def on_next_click(controller):
    """
    Controls the next (and finish) button behaviour
    """
    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget
    controller.view.stackedWidget.setCurrentIndex(idx+1)
