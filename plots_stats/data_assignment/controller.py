from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

class DataAssignmentController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self
        self.first_show = False