from PySide6 import QtWidgets
import os

class FilteringPlotController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
