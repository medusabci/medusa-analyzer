from PySide6.QtWidgets import QFrame
from converter.flow import on_next_click

class MainConverterController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        self.view.nextButton.clicked.connect(lambda: on_next_click(self))