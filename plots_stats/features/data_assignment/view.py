from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_plots_groups = loadUiType('plots_stats/features/data_assignment/view.ui')[0]

class DataAssignmentWidget(QtWidgets.QWidget, ui_plots_groups):
    shown = QtCore.Signal()
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

        # Define the elements based on the configuration
        if self.main_module.controller.config_config['analysis_mode'] == 'within':
            self.all_items = self.main_module.controller.subjects
        else:
            self.all_items = self.main_module.controller.recordings

        # --- ELEMENT SETUP ---
        self.filelistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.filelistWidget.addItems(self.all_items)

        # Search line
        self.searchEdit.setPlaceholderText("Find elements...")
        self.searchEdit.setClearButtonEnabled(True)
        # Lens icon
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))



