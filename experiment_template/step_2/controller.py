import numpy as np
from PySide6 import QtWidgets
import json

class Step2Controller:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Connects
        self.view.button1.toggled.connect(self.on_button1_toggle)
        self.view.button2.toggled.connect(self.on_button2_toggle)

        # Set initial state
        self.view.shown.connect(self.on_show_event)


    def on_button1_toggle(self, checked):
        # Do something when button1 is toggled
        print('Button 1 toggled')
        for widget in [self.view.label1, self.view.text1]:
            widget.setVisible(checked)


    def on_button2_toggle(self, checked):
        # Do something when button1 is toggled
        print('Button 2 toggled')
        for widget in [self.view.label2, self.view.text2]:
            widget.setVisible(checked)

    def on_show_event(self):
        # Do something when the widget is shown
        if not self.first_show:
            self.first_show = True
            print('Step 1 widget shown for the first time')