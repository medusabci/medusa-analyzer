from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

class GroupAssignmentController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self
        self.first_show = True
        self.group_assignment = {}

        # If there are already groups defined in the controller, load them
        if self.view.main_module.controller.config_config['analysis_mode'] == 'within':
            self.all_items = self.view.main_module.controller.recordings
        else:
            self.all_items = self.view.main_module.controller.subjects

        self.view.tableAssignment.setRowCount(len(self.all_items))
        for idx_rec, recording in enumerate(self.all_items):
            # Recording name
            # name = Path(recording).stem
            self.view.tableAssignment.setItem(idx_rec, 0, QtWidgets.QTableWidgetItem(str(recording)))

        # Button connect
        self.view.main_module.nextButton.setEnabled(False)

        # Allow right-click context menu
        self.view.tableAssignment.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        # Right-click event calls the show_context_menu method
        self.view.tableAssignment.customContextMenuRequested.connect(self.show_context_menu)

        # First usage
        self.view.shown.connect(self.on_show_event)

        # Connects
        self.view.searchEdit.textChanged.connect(self.filter_items)

        # Override the table's resize event to call resizeColumns whenever the size changes, and call the function once
        # at the start to adjust the widths.
        self.view.tableAssignment.resizeEvent = lambda event: (self.resize_columns(),
              QtWidgets.QTableWidget.resizeEvent(self.view.tableAssignment, event))
        self.resize_columns()


    def show_context_menu(self, pos):
        """
        Show a context menu to assign groups to selected recordings.
        """
        menu = QtWidgets.QMenu()

        # Add all the groups as actions in the menu
        for group in self.view.main_module.controller.groups.keys():
            action = menu.addAction(group)
            action.triggered.connect(lambda checked, g=group: self.assign_group_to_selected(g))

        # Add reset group action
        action = menu.addAction('Reset Group')
        action.triggered.connect(lambda checked, g='Reset Group': self.assign_group_to_selected(g))

        # Run the context menu at the cursor position
        menu.exec_(self.view.tableAssignment.viewport().mapToGlobal(pos))

    def assign_group_to_selected(self, group_str):
        """
        Assign the selected group to all selected rows in the table.
        """

        # Get the selected rows
        selected_rows = set(idx.row() for idx in self.view.tableAssignment.selectionModel().selectedIndexes())
        # Assign the group to each selected row
        for row in selected_rows:
            if group_str == 'Reset Group':
                self.view.tableAssignment.setItem(row, 1, QtWidgets.QTableWidgetItem(''))
            else:
                self.view.tableAssignment.setItem(row, 1, QtWidgets.QTableWidgetItem(group_str))

            # Change the background color of the row to the group's color
            if group_str == 'Reset Group':
                color = QtGui.QColor(255, 255, 255)  # White color for reset
            else:
                color = self.view.main_module.controller.groups[group_str]
            for col in range(self.view.tableAssignment.columnCount()):
                item = self.view.tableAssignment.item(row, col)
                qt_color = QtGui.QColor(color)
                qt_color.setAlpha(100) # Set transparency
                item.setBackground(qt_color)

        self.on_cell_changed()


    def on_show_event(self):
        if self.first_show:
            # Add the group summary text

            # Start with a horizontal line
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            # AAdd the horizontal line to the layout
            self.view.groupLayout.addWidget(line)

            for name in self.view.main_module.controller.groups:
                # Create the label
                label = QtWidgets.QLabel(name + ": 0 subjects")
                label.setStyleSheet("font-weight: bold;")
                label.setObjectName(name.replace(' ', ''))
                # Add the label to the layout
                self.view.groupLayout.addWidget(label)

            # Finish with a horizontal line
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            # AAdd the horizontal line to the layout
            self.view.groupLayout.addWidget(line)

            self.first_show = False

    def on_cell_changed(self):

        ## Count the number of subjects in each group
        # Create an empty count dictionary
        group_counts = {k: 0 for k in self.view.main_module.controller.groups}
        # Groups are in column 1
        for r in range(self.view.tableAssignment.rowCount()):
            item = self.view.tableAssignment.item(r, 1)
            if item:
                group = item.text()
                if group:
                    group_counts[group] = group_counts.get(group, 0) + 1

        # Update the labels
        for group in group_counts:
            label = self.view.findChild(QtWidgets.QLabel, group.replace(' ', ''))
            if label:
                label.setText(f"{group}: {group_counts[group]} subject(s)")

        ## Store the group assignment in the controller of the main_module
        # Create an empty count dictionary
        self.group_assignment = {k: [] for k in self.view.main_module.controller.groups}
        # Groups are in column 1
        for r in range(self.view.tableAssignment.rowCount()):
            item = self.view.tableAssignment.item(r, 1)
            if item:
                group = item.text()
                subject = self.view.tableAssignment.item(r, 0).text()
                if group:
                    self.group_assignment[group].append(subject)


    def filter_items(self, text):
        """Filter the table rows by text in the 'Subject' column."""
        text = text.lower().strip()
        for row in range(self.view.tableAssignment.rowCount()):
            item = self.view.tableAssignment.item(row, 0)  # columna 'Subject'
            if item:
                # Show or hide the row based on whether the text is found
                self.view.tableAssignment.setRowHidden(row, text not in item.text().lower())


    def resize_columns(self):
        """
        Adjust the column widths of the tableAssignment based on the current width of the viewport, the first column
        takes 80% of the width and the second column takes 20%.
        """
        total_width = self.view.tableAssignment.viewport().width()
        self.view.tableAssignment.setColumnWidth(0, int(total_width * 0.8))
        self.view.tableAssignment.setColumnWidth(1, int(total_width * 0.2))