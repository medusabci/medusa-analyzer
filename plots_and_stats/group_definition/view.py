# group_definition/view.py
from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import loadUiType

# ui_plots_groups = loadUiType('plots_and_stats/group_definition/view.ui')[0]
ui_plots_groups = loadUiType('view.ui')[0]

class GroupsWidget(QtWidgets.QWidget, ui_plots_groups):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # self.main_module = main_module

        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.groupstable.setRowCount(0)
        self.groupstable.setColumnCount(2)
        self.groupstable.setHorizontalHeaderLabels(["Group Name", "Color"])

        self.groupstable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.groupstable.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.groupstable.horizontalHeader().setStretchLastSection(False)

        def resizeColumns():
            total_width = self.groupstable.viewport().width()
            self.groupstable.setColumnWidth(0, int(total_width * 0.8))
            self.groupstable.setColumnWidth(1, int(total_width * 0.2))

        self.groupstable.resizeEvent = lambda event: (
        resizeColumns(), QtWidgets.QTableWidget.resizeEvent(self.groupstable, event))
        resizeColumns()
