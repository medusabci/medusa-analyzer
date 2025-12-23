from PySide6.QtWidgets import QFrame
from converter.flow import on_next_click, on_back_click

class MainConverterController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        self.view.nextButton.clicked.connect(lambda: on_next_click(self))
        self.view.nextButton.setDisabled(True)
        self.view.backButton.clicked.connect(lambda: on_back_click(self))
        self.view.backButton.setDisabled(True)