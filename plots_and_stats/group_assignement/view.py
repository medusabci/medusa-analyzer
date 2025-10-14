from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtUiTools import loadUiType

ui_plots_groups = loadUiType('plots_and_stats/group_assignement/view.ui')[0]

class AssignementWidget(QtWidgets.QWidget, ui_plots_groups):
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

        # Initial table setup, 0 rows, 2 columns with names "Group Name" and "Color"
        self.tableAssignement.setRowCount(0)
        self.tableAssignement.setColumnCount(2)
        self.tableAssignement.setHorizontalHeaderLabels(["Subject", "Group"])
        # Configures the column resize mode to be interactive and prevents the last column from stretching automatically.
        self.tableAssignement.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.tableAssignement.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.tableAssignement.horizontalHeader().setStretchLastSection(False)

        # Override the table's resize event to call resizeColumns whenever the size changes, and call the function once
        # at the start to adjust the widths.
        self.tableAssignement.resizeEvent = lambda event: (self.resize_columns(),
              QtWidgets.QTableWidget.resizeEvent(self.tableAssignement, event))
        self.resize_columns()

        # Allow multiple row selection
        self.tableAssignement.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        self.tableAssignement.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.ExtendedSelection)
        # Overwrite mouse press event to clean the previous selection if Ctrl or Shift are not pressed
        self.tableAssignement.mousePressEvent = self.table_mouse_press

        # Search line
        self.searchEdit.setPlaceholderText("Find recordings...")
        self.searchEdit.textChanged.connect(self.filter_items)
        self.searchEdit.setClearButtonEnabled(True)
        # Botón de lupa
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))


    def table_mouse_press(self, event):
        """
        Custom mouse press event to allow multiple row selection with Ctrl and Shift keys, and clear previous selection
        if neither key is pressed.
        """
        if event.button() == QtCore.Qt.MouseButton.LeftButton:

            # Get the current keyboard modifiers (e.g., Ctrl, Shift)
            modifiers = QtWidgets.QApplication.keyboardModifiers()

            # If neither Ctrl nor Shift is pressed, clear the previous selection
            # This makes a normal click start a new selection instead of adding to the old one
            if not (modifiers & QtCore.Qt.KeyboardModifier.ControlModifier or
                    modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier):
                self.tableAssignement.clearSelection()

            # Call the original mousePressEvent to handle the actual row selection
            QtWidgets.QTableWidget.mousePressEvent(self.tableAssignement, event)


    def resize_columns(self):
        """
        Adjust the column widths of the tableAssignement based on the current width of the viewport, the first column
        takes 80% of the width and the second column takes 20%.
        """
        total_width = self.tableAssignement.viewport().width()
        self.tableAssignement.setColumnWidth(0, int(total_width * 0.8))
        self.tableAssignement.setColumnWidth(1, int(total_width * 0.2))

    def filter_items(self, text):
        """Filter the table rows by text in the 'Subject' column."""
        text = text.lower().strip()
        for row in range(self.tableAssignement.rowCount()):
            item = self.tableAssignement.item(row, 0)  # columna 'Subject'
            if item:
                # Show or hide the row based on whether the text is found
                self.tableAssignement.setRowHidden(row, text not in item.text().lower())