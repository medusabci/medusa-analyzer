from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import Qt
import os

ui_plots_groups = loadUiType('plots_stats/data_assignment/view.ui')[0]

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
        self.deleteButton.clicked.connect(self.delete_selected)
        self.deleteallButton.clicked.connect(self.delete_all)

        # Search line
        self.searchEdit.setPlaceholderText("Find elements...")
        self.searchEdit.textChanged.connect(self.filter_items)
        self.searchEdit.setClearButtonEnabled(True)
        # Botón de lupa
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))


    def delete_selected(self):
        """Remove selected files from the list."""
        if self.filelistWidget.selectedItems():
            if self.confirm_deletion():
                for item in self.filelistWidget.selectedItems():
                    self.filelistWidget.takeItem(self.filelistWidget.row(item))
                self._update_preprocessing_widget()

    def delete_all(self):
        """Remove all files from the list."""
        if self.filelistWidget.count():
            if self.confirm_deletion():
                self.filelistWidget.clear()
                self._update_preprocessing_widget()

    def _update_preprocessing_widget(self):
        """Update the preprocessing widget with current file list."""
        updated_files = [self.filelistWidget.item(i).text()
                        for i in range(self.filelistWidget.count())]

        return updated_files

    def confirm_deletion(self):
        # Create the confirmation dialog
        confirmation_dialog = QtWidgets.QMessageBox(self)
        confirmation_dialog.setWindowTitle("Confirm Deletion")
        confirmation_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        confirmation_dialog.setText("Are you sure you want to delete these files?")
        confirmation_dialog.setInformativeText("This action cannot be undone.")

        # Add 'Yes' and 'No' buttons
        confirmation_dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        confirmation_dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)

        # Show the dialog and get the user's response
        response = confirmation_dialog.exec()

        return response == QtWidgets.QMessageBox.StandardButton.Yes

    def filter_items(self, text):
        """Filter the recordings in the list."""
        self.filelistWidget.clear()
        if not text:
            self.filelistWidget.addItems(self.all_items)
            return

        text = text.lower()
        filtered = [item for item in self.all_items if text in item.lower()]
        self.filelistWidget.addItems(filtered)