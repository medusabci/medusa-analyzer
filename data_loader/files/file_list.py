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

        self.all_items = files.copy()
        self.show_only_names = False  # Checkbox disabled

        self.showNamesCheck.toggled.connect(self.toggle_display_mode)


    def toggle_display_mode(self, checked):
        """Changes between showing complete paths or only the names."""
        self.show_only_names = checked
        self._refresh_list()


    def delete_selected(self):
        """Remove selected files from the list."""
        if self.filelistWidget.selectedItems():
            if self.confirm_deletion():
                for item in self.filelistWidget.selectedItems():
                    self.filelistWidget.takeItem(self.filelistWidget.row(item))
                    self.all_items = [x for x in self.all_items if item.text() not in x]
                self._update_preprocessing_widget()

    def delete_all(self):
        """Remove all files from the list."""
        if self.filelistWidget.count():
            if self.confirm_deletion():
                self.filelistWidget.clear()
                self._update_preprocessing_widget()
                self.all_items = []

    def _update_preprocessing_widget(self):
        """Update the list with the current file list."""
        # Get the currently visible names in the list widget
        visible_items = [self.filelistWidget.item(i).text()
                         for i in range(self.filelistWidget.count())]

        # If only names are being displayed, reconstruct the full paths
        if self.show_only_names:
            # Keep only the paths that correspond to the visible names
            updated_files = [path for path in self.all_items
                             if os.path.basename(path) in visible_items]
        else:
            # If full paths are already displayed, use them directly
            updated_files = visible_items

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
        filtered = self.all_items
        if text:
            text = text.lower()
            filtered = [item for item in self.all_items if text in os.path.basename(item).lower() or text in item.lower()]
        self._refresh_list(filtered)

    def _refresh_list(self, items=None):
        """Refresh the list according to the visualization mode (paths or names)."""
        # If no items provided, use all items
        if items is None:
            items = self.all_items

        # Clear current list
        self.filelistWidget.clear()

        if self.show_only_names: # If showing only names
            display_items = [os.path.basename(item) for item in items]
        else: # Else, show full paths
            display_items = items

        # Add items to the list widget
        self.filelistWidget.addItems(display_items)