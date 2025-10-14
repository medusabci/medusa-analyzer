
from PySide6 import QtWidgets, QtCore, QtGui

def validate_and_emit(self):
    groups = {}
    for i in range(self.widget.groupstable.rowCount()):
        name = self.widget.groupstable.item(i, 0).text()
        color = self.widget.groupstable.item(i, 1).text()
        groups[name] = color
    self.groups = groups
    print("Groups defined:", self.groups)

# self.widget.next_button.clicked.connect(self.validate_and_emit)