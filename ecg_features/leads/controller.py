from PySide6 import QtWidgets, QtGui, QtCore

class LeadsController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self