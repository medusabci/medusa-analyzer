from PySide6 import QtWidgets, QtGui, QtCore
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

        # Search line
        self.searchEdit.setPlaceholderText("Find recordings...")
        self.searchEdit.textChanged.connect(self.filter_items)
        self.searchEdit.setClearButtonEnabled(True)
        # Lens icon
        self.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

        self.all_items = files


    def delete_selected(self):
        """Remove selected files from the list."""
        if self.filelistWidget.selectedItems():
            if self.confirm_deletion():
                for item in self.filelistWidget.selectedItems():
                    self.filelistWidget.takeItem(self.filelistWidget.row(item))
                    self.all_items.remove(item.text())
                self._update_preprocessing_widget()

    def delete_all(self):
        """Remove all files from the list."""
        if self.filelistWidget.count():
            if self.confirm_deletion():
                self.filelistWidget.clear()
                self._update_preprocessing_widget()
                self.all_items = []

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