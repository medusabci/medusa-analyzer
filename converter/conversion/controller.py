from PySide6 import QtWidgets, QtGui, QtCore
import os, re
from medusa.bci.erp_spellers import *
from medusa.components import CustomExperimentData


class ConversionController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        self.view.namehelpButton.clicked.connect(self.on_name_help_button_clicked)

        self.view.namingTable.setColumnCount(2)
        self.view.namingTable.horizontalHeader().hide()
        self.view.namingTable.verticalHeader().hide()
        self.view.namingTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        # Override the table's resize event to call resizeColumns whenever the size changes, and call the function once
        # at the start to adjust the widths.
        self.view.namingTable.resizeEvent = lambda event: (self.resize_columns(),
              QtWidgets.QTableWidget.resizeEvent(self.view.namingTable, event))
        self.resize_columns()
        # Allow right-click context menu
        self.view.namingTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        # Right-click event calls the show_context_menu method
        self.view.namingTable.customContextMenuRequested.connect(self.show_context_menu)

    def on_name_help_button_clicked(self):
        QtWidgets.QMessageBox.information(
            self.view,
            "Jijij",
            "Aún no he configurado este botón jijijiji."
        )

    def populate_name_structure_table(self):
        # Clear existing table entries
        self.view.namingTable.clear()

        # Get the first file with the selected extension
        data_loader = self.view.main_window.stackedWidget.widget(0)
        base_file = data_loader.controller.selected_files[0].split('.')[0] # Remove extension
        # Separate the file path into components
        self.base_file_elements = [e for e in re.split(r"[\\/ _-]+", base_file) if e]

        # Add the elements to the table as rows
        self.view.namingTable.setRowCount(len(self.base_file_elements))
        for idx_elm, element in enumerate(self.base_file_elements):
            item = QtWidgets.QTableWidgetItem(element)
            # Non-editable items
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.view.namingTable.setItem(idx_elm, 0, item)

    def show_context_menu(self, pos):
        """
        Show a context menu to assign groups to selected recordings.
        """
        menu = QtWidgets.QMenu()

        # Add all the groups as actions in the menu
        for group in ['Subject','Session','Recording','Task']:
            action = menu.addAction(group)
            action.triggered.connect(lambda checked, g=group: self.assign_group_to_selected(g))

        # Add reset action
        action = menu.addAction('Reset Assignment')
        action.triggered.connect(lambda checked, g='Reset Assignment': self.assign_group_to_selected(g))

        # Run the context menu at the cursor position
        menu.exec_(self.view.namingTable.viewport().mapToGlobal(pos))

    def assign_group_to_selected(self, group_str):
        """
        Assign the selected group to all selected rows in the table.
        """
        # Get the selected rows
        selected_rows = set(idx.row() for idx in self.view.namingTable.selectionModel().selectedIndexes())
        # Assign the group to each selected row
        for row in selected_rows:
            if group_str == 'Reset Assignment':
                self.view.namingTable.setItem(row, 1, QtWidgets.QTableWidgetItem(''))
            else:
                self.view.namingTable.setItem(row, 1, QtWidgets.QTableWidgetItem(group_str))

        self.on_cell_changed()

    def resize_columns(self):
        """
        Adjust the column widths of the tableAssignment based on the current width of the viewport, the first column
        takes 80% of the width and the second column takes 20%.
        """
        total_width = self.view.namingTable.viewport().width()
        self.view.namingTable.setColumnWidth(0, int(total_width * 0.8))
        self.view.namingTable.setColumnWidth(1, int(total_width * 0.2))

    def on_cell_changed(self):

        names = {"Subject": [], "Session": [], "Recording": [], "Task": []}

        for row in range(self.view.namingTable.rowCount()):
            second_col_item = self.view.namingTable.item(row, 1)
            first_col_item = self.view.namingTable.item(row, 0)
            if second_col_item and first_col_item:
                key = second_col_item.text()
                if key in names:
                    names[key].append(first_col_item.text())

        # Concatenate the names
        subject_name = "".join(names["Subject"])
        session_name = "".join(names["Session"])
        recording_name = "".join(names["Recording"])
        task_name = "".join(names["Task"])


        # Update the labels
        if subject_name:
            self.view.subjectLabel.setText(f"sub-{subject_name}")
        else:
            self.view.subjectLabel.setText("")
        if session_name:
            self.view.sessionLabel.setText(f"ses-{session_name}")
        else:
            self.view.sessionLabel.setText("")
        if recording_name:
            self.view.recordingLabel.setText(f"rec-{recording_name}")
        else:
            self.view.recordingLabel.setText("rec-01")
        if task_name:
            self.view.taskLabel.setText(f"task-{task_name}")
        else:
            self.view.taskLabel.setText("")

        # Store the index of the elememnts
        index_map = {element: idx for idx, element in enumerate(self.base_file_elements)}
        self.names_idx = {
            key: [index_map[item]
                    for item in values
                        if item in index_map]
                for key, values in names.items()
        }
