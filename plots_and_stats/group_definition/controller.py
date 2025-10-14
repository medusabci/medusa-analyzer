# group_definition/controller.py
from PySide6 import QtWidgets, QtCore, QtGui
import colorsys
import sys
from plots_and_stats.group_definition.view import GroupsWidget

class GroupsController:
    def __init__(self, widget: GroupsWidget):
        self.view = widget
        self.groups = {}

        self.view.generateButton.clicked.connect(self.generate_table)

    def generate_table(self):
        n = self.view.numgroupBox.value()
        self.view.groupstable.setRowCount(n)
        colors = self.generate_distinct_colors(n)

        for i in range(n):
            # Group name
            self.view.groupstable.setItem(i, 0, QtWidgets.QTableWidgetItem(f"Group {i+1}"))

            # Color button
            btn = QtWidgets.QPushButton()
            btn.setStyleSheet(f"background-color: {colors[i]}")
            btn.clicked.connect(lambda _, row=i: self.open_color_dialog(row))
            self.view.groupstable.setCellWidget(i, 1, btn)
            self.view.groupstable.setItem(i, 1, QtWidgets.QTableWidgetItem(colors[i]))

    def open_color_dialog(self, row):
        current_color = self.view.groupstable.item(row, 1).text()
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current_color), self.view)
        if color.isValid():
            hex_code = color.name()
            self.view.groupstable.cellWidget(row, 1).setStyleSheet(f"background-color: {hex_code}")
            self.view.groupstable.item(row, 1).setText(hex_code)

    def generate_distinct_colors(self, n):
        colors = []
        for i in range(n):
            hue = i / n
            rgb = colorsys.hsv_to_rgb(hue, 0.6, 0.95)
            colors.append('#%02x%02x%02x' % tuple(int(c * 255) for c in rgb))
        return colors

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    stack = QtWidgets.QStackedWidget()
    widget = GroupsWidget()
    controller = GroupsController(widget)

    stack.addWidget(widget)
    stack.setCurrentWidget(widget)

    stack.setWindowTitle("Group Definition Test")
    stack.resize(500, 400)
    stack.show()

    sys.exit(app.exec())