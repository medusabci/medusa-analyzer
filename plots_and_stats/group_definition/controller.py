# group_definition/controller.py
from PyQt6 import QtWidgets, QtGui
import colorsys

class GroupDefinitionController:
    def __init__(self, widget: "GroupDefinitionWidget"):
        self.widget = widget
        self.groups = {}
        self.connect_signals()

    def connect_signals(self):
        self.widget.generate_btn.clicked.connect(self.generate_table)
        self.widget.next_button.clicked.connect(self.validate_and_emit)

    def generate_table(self):
        n = self.widget.num_groups_spin.value()
        self.widget.table.setRowCount(n)
        colors = self.generate_distinct_colors(n)
        for i in range(n):
            self.widget.table.setItem(i, 0, QtWidgets.QTableWidgetItem(f"Group {i+1}"))
            btn = QtWidgets.QPushButton()
            btn.setStyleSheet(f"background-color: {colors[i]}")
            btn.clicked.connect(lambda _, row=i: self.open_color_dialog(row))
            self.widget.table.setCellWidget(i, 1, btn)
            self.widget.table.setItem(i, 1, QtWidgets.QTableWidgetItem(colors[i]))

    def open_color_dialog(self, row):
        current_color = self.widget.table.item(row, 1).text()
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current_color), self.widget)
        if color.isValid():
            hex_code = color.name()
            self.widget.table.cellWidget(row, 1).setStyleSheet(f"background-color: {hex_code}")
            self.widget.table.item(row, 1).setText(hex_code)

    def validate_and_emit(self):
        groups = {}
        for i in range(self.widget.table.rowCount()):
            name = self.widget.table.item(i, 0).text()
            color = self.widget.table.item(i, 1).text()
            groups[name] = color
        self.groups = groups
        # Aquí se podría emitir señal a flow
        print("Groups defined:", self.groups)

    def generate_distinct_colors(self, n):
        colors = []
        for i in range(n):
            hue = i / n
            rgb = colorsys.hsv_to_rgb(hue, 0.6, 0.95)
            colors.append('#%02x%02x%02x' % tuple(int(c*255) for c in rgb))
        return colors
