from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtUiTools import loadUiType

ui_plots_groups = loadUiType('plots_stats/group_assignment/view.ui')[0]

class GroupAssignmentWidget(QtWidgets.QWidget, ui_plots_groups):
    shown = QtCore.Signal()
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

        # Initial table setup, 0 rows, 2 columns with names "Group Name" and "Color"
        self.tableAssignment.setRowCount(0)
        self.tableAssignment.setColumnCount(2)
        self.tableAssignment.setHorizontalHeaderLabels(["Subject", "Group"])
        # Configures the column resize mode to be interactive and prevents the last column from stretching automatically.
        self.tableAssignment.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.tableAssignment.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.tableAssignment.horizontalHeader().setStretchLastSection(False)

        # Allow multiple row selection
        self.tableAssignment.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        self.tableAssignment.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.ExtendedSelection)
        # Overwrite mouse press event to clean the previous selection if Ctrl or Shift are not pressed
        self.tableAssignment.mousePressEvent = self.table_mouse_press
        # Do not allow editing the table cells
        self.tableAssignment.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)

        # Search line
        self.searchEdit.setPlaceholderText("Find recordings...")
        self.searchEdit.setClearButtonEnabled(True)
        # Botón de lupa
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def showEvent(self, event):
        super().showEvent(event)
        self.shown.emit()


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
                self.tableAssignment.clearSelection()

            # Call the original mousePressEvent to handle the actual row selection
            QtWidgets.QTableWidget.mousePressEvent(self.tableAssignment, event)





