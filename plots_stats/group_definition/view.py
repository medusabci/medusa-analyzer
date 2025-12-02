from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import loadUiType

ui_plots_groups = loadUiType('plots_stats/group_definition/view.ui')[0]

class GroupsWidget(QtWidgets.QWidget, ui_plots_groups):
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

        # Widget resizing policies
        self.setMinimumSize(0, 0) # Minimum size of the widget is set to 0x0 pixels, allowing it to shrink as needed.
        # Allows the widget to expand both horizontally and vertically within its parent layout.
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Initial table setup, 0 rows, 2 columns with names "Group Name" and "Color"
        self.groupstable.setRowCount(0)
        self.groupstable.setColumnCount(2)
        self.groupstable.setHorizontalHeaderLabels(["Group Name", "Color"])
        # Configures the column resize mode to be interactive and prevents the last column from stretching automatically.
        self.groupstable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.groupstable.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.groupstable.horizontalHeader().setStretchLastSection(False)

        # Override the table's resize event to call resizeColumns whenever the size changes, and call the function once
        # at the start to adjust the widths.
        self.groupstable.resizeEvent = lambda event: (self.resizeColumns(),
              QtWidgets.QTableWidget.resizeEvent(self.groupstable, event))
        self.resizeColumns()

    def resizeColumns(self):
        """
        Adjust the column widths of the groupstable based on the current width of the viewport, the first column
        takes 80% of the width and the second column takes 20%.
        """
        total_width = self.groupstable.viewport().width()
        self.groupstable.setColumnWidth(0, int(total_width * 0.8))
        self.groupstable.setColumnWidth(1, int(total_width * 0.2))
