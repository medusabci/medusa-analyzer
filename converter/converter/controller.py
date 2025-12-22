from PySide6 import QtWidgets, QtGui, QtCore
import os

class ConverterController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
