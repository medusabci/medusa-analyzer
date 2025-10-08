from PySide6 import QtWidgets
from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import Qt
import os

# Load UI class
ui_files_list_dialog = loadUiType("data_loader/files/file_list.ui")[0]

class FilesListDialog(QtWidgets.QDialog, ui_files_list_dialog):
    def __init__(self, files, preprocessing_widget):
        super().__init__()

        # Setup UI
        self.setupUi(self)

        # Remove the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Change the title
        self.setWindowTitle("List of Files")

        # Store reference to preprocessing widget
        self.preprocessing_widget = preprocessing_widget

        # --- ELEMENT SETUP ---
        self.filelistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.filelistWidget.addItems(files)
        self.deleteButton.clicked.connect(self.delete_selected)
        self.deleteallButton.clicked.connect(self.delete_all)
        self.acceptButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)


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