# group_definition/flow.py
from .view import GroupDefinitionWidget
from .controller import GroupDefinitionController
from PyQt6 import QtWidgets

class GroupDefinitionFlow:
    def __init__(self, stack: QtWidgets.QStackedWidget):
        self.stack = stack
        self.widget = GroupDefinitionWidget()
        self.controller = GroupDefinitionController(self.widget)
        self.stack.addWidget(self.widget)
        self.stack.setCurrentWidget(self.widget)

    def get_groups(self):
        return self.controller.groups
