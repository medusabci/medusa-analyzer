from PySide6 import QtWidgets, QtCore, QtGui
import colorsys


class GroupsController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self

        # If there are already groups defined in the controller, load them
        if self.view.main_module.controller.groups:
            # Generar tabla con ese dict
            groups = self.view.main_module.controller.groups
            for i, group in enumerate(groups):
                # Group name
                self.view.groupstable.setItem(i, 0, QtWidgets.QTableWidgetItem(group))
                # Color button
                btn = QtWidgets.QPushButton()
                btn.setStyleSheet(f"background-color: {groups[group]}")
                btn.clicked.connect(lambda _, row=i: self.open_color_dialog(row))
                self.view.groupstable.setCellWidget(i, 1, btn)
                self.view.groupstable.setItem(i, 1, QtWidgets.QTableWidgetItem(groups[group]))

        # Button connect
        self.view.generateButton.clicked.connect(self.generate_table)
        self.view.groupstable.cellChanged.connect(self.on_cell_changed)

        self.view.main_module.nextButton.setEnabled(False)

        # Connect double click signal to clean cell content to avoid overwriting issues (old and new text)
        self.view.groupstable.itemDoubleClicked.connect(self.on_item_edit_start)

    def on_item_edit_start(self, item):
        """
        Clean cell content when editing starts.
        """
        # Only clean the first column (group names)
        if item.column() == 0:
            item.setText("")

    def generate_table(self):
        """
        Generate the groups table based on the number of groups specified.
        """
        # Number of groups
        n = self.view.numgroupBox.value()
        self.view.groupstable.setRowCount(n) # A row per group
        colors = self.generate_distinct_colors(n) # Generate distinct colors, one per group

        # To avoid calling on_cell_changed multiple times, disconnect the signal temporarily
        self.view.groupstable.cellChanged.disconnect(self.on_cell_changed)

        # For each group, create a row with a name and a color button
        for i in range(n):
            # Group name
            self.view.groupstable.setItem(i, 0, QtWidgets.QTableWidgetItem(f"Group {i+1}"))
            # Color button
            btn = QtWidgets.QPushButton()
            btn.setStyleSheet(f"background-color: {colors[i]}")
            btn.clicked.connect(lambda _, row=i: self.open_color_dialog(row))
            self.view.groupstable.setCellWidget(i, 1, btn)
            self.view.groupstable.setItem(i, 1, QtWidgets.QTableWidgetItem(colors[i]))

        self.view.groupstable.cellChanged.connect(self.on_cell_changed)
        self.on_cell_changed()

    def open_color_dialog(self, row):
        """
        Open a color dialog to select a color for the specified row.
        """
        current_color = self.view.groupstable.item(row, 1).text()
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current_color), self.view)
        if color.isValid():
            hex_code = color.name()
            self.view.groupstable.cellWidget(row, 1).setStyleSheet(f"background-color: {hex_code}")
            self.view.groupstable.item(row, 1).setText(hex_code)

    def generate_distinct_colors(self, n):
        """
        Generate n visually distinct colors.
        """
        colors = []
        for i in range(n):
            hue = i / n
            rgb = colorsys.hsv_to_rgb(hue, 0.6, 0.95)
            colors.append('#%02x%02x%02x' % tuple(int(c * 255) for c in rgb))
        return colors

    def on_cell_changed(self):
        """
        Update the main module's controller with the current groups and their colors.
        """
        self.view.main_module.controller.groups = {}
        for i in range(self.view.groupstable.rowCount()):
            name = self.view.groupstable.item(i, 0).text()
            color = self.view.groupstable.item(i, 1).text()
            self.view.main_module.controller.groups[name] = color

        # Enable next button if there is at least one group defined
        if self.view.groupstable.rowCount() > 0:
            self.view.main_module.nextButton.setEnabled(True)


