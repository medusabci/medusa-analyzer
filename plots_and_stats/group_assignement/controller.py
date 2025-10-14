from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

class AssignementController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self

        # If there are already groups defined in the controller, load them
        if self.view.main_module.controller.config_config['selection']['analysis_mode'] == 'within':
            self.all_items = self.view.main_module.controller.recordings
        else:
            self.all_items = self.view.main_module.controller.subjects

        self.view.tableAssignement.setRowCount(len(self.all_items))
        for idx_rec, recording in enumerate(self.all_items):
            # Recording name
            # name = Path(recording).stem
            self.view.tableAssignement.setItem(idx_rec, 0, QtWidgets.QTableWidgetItem(str(recording)))

        # Button connect
        self.view.main_module.nextButton.setEnabled(False)

        # Allow right-click context menu
        self.view.tableAssignement.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        # Right-click event calls the show_context_menu method
        self.view.tableAssignement.customContextMenuRequested.connect(self.show_context_menu)


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


    def show_context_menu(self, pos):
        """
        Show a context menu to assign groups to selected recordings.
        """
        menu = QtWidgets.QMenu()

        # Add all the groups as actions in the menu
        for group in self.view.main_module.controller.groups.keys():
            action = menu.addAction(group)
            action.triggered.connect(lambda checked, g=group: self.assign_group_to_selected(g))

        # Run the context menu at the cursor position
        menu.exec_(self.view.tableAssignement.viewport().mapToGlobal(pos))

    def assign_group_to_selected(self, group_str):
        """
        Assign the selected group to all selected rows in the table.
        """
        # Get the selected rows
        selected_rows = set(idx.row() for idx in self.view.tableAssignement.selectionModel().selectedIndexes())
        # Assign the group to each selected row
        for row in selected_rows:
            self.view.tableAssignement.setItem(row, 1, QtWidgets.QTableWidgetItem(group_str))