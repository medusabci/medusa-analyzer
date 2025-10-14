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
        self.tableAssignement.resizeEvent = lambda event: (self.resizeColumns(),
              QtWidgets.QTableWidget.resizeEvent(self.tableAssignement, event))
        self.resizeColumns()

        # Allow multiple row selection
        self.tableAssignement.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        self.tableAssignement.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.MultiSelection)

        # Search line
        self.searchEdit.setPlaceholderText("Find recordings...")
        self.searchEdit.textChanged.connect(self.filter_items)
        # Botón de lupa
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))


    def resizeColumns(self):
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