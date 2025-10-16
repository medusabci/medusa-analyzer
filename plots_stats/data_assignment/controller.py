from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

class DataAssignmentController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Connects
        self.view.searchEdit.textChanged.connect(self.filter_items)


    def filter_items(self, text):
        """Filter the recordings in the list."""
        self.view.filelistWidget.clear()
        if not text:
            self.view.filelistWidget.addItems(self.view.all_items)
            return

        text = text.lower()
        filtered = [item for item in self.view.all_items if text in item.lower()]
        self.view.filelistWidget.addItems(filtered)


    def delete_selected(self):
        """Remove selected files from the list."""
        if self.view.filelistWidget.selectedItems():
            if self.confirm_deletion():
                for item in self.view.filelistWidget.selectedItems():
                    self.view.filelistWidget.takeItem(self.view.filelistWidget.row(item))
                self._update_preprocessing_widget()


    def delete_all(self):
        """Remove all files from the list."""
        if self.view.filelistWidget.count():
            if self.confirm_deletion():
                self.view.filelistWidget.clear()
                self._update_preprocessing_widget()


    def _update_preprocessing_widget(self):
        """Update the preprocessing widget with current file list."""
        updated_files = [self.view.filelistWidget.item(i).text()
                        for i in range(self.view.filelistWidget.count())]

        return updated_files


    def confirm_deletion(self):
        # Create the confirmation dialog
        confirmation_dialog = QtWidgets.QMessageBox(self.view)
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
