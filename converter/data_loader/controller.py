from PySide6 import QtWidgets, QtGui, QtCore
from converter.CONVERTERS import CONVERTERS
import os

class DataLoaderController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.selected_files = []

        # --- ELEMENT SETUP ---
        self.view.filelistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.view.loadButton.clicked.connect(self.on_converter_click)
        self.view.deleteButton.clicked.connect(self.delete_selected)
        self.view.deleteallButton.clicked.connect(self.delete_all)
        self.view.converterBox.currentIndexChanged.connect(lambda _: self._refresh_list())

        # Search line
        self.view.searchEdit.setPlaceholderText("Find recordings...")
        self.view.searchEdit.textChanged.connect(self.filter_items)
        # Lens icon
        self.view.iconLabel.setPixmap(QtGui.QPixmap("media/search.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

        self.show_only_names = False  # Checkbox disabled

        self.view.showNamesCheck.toggled.connect(self.toggle_display_mode)

    def on_converter_click(self):
        """
        Opens a dialog that allows the user to select a directory containing data files
        to be converted, displays a tree-view dialog to select specific files, and runs `conversor_to_rec` on the
        chosen files.
        """

        # Select the root input directory
        input_dir = str(QtWidgets.QFileDialog.getExistingDirectory(self.view,"Select Root Directory Containing Data to Convert"))
        if not input_dir:
            return

        # Gather valid files recursively
        valid_exts = tuple(CONVERTERS.keys())
        valid_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.endswith(valid_exts)]

        if not valid_files:
            QtWidgets.QMessageBox.warning(
                self.view,
                "No Valid Files Found",
                f"No supported files were detected in:\n{input_dir}\n\n"
                f"Supported extensions: {', '.join(valid_exts)}"
            )
            return

        # Get the selected file extensions, and the associated available converters
        valid_files_exts = ['.' + file.split('.')[-1] for file in valid_files]
        available_converters = list(set(valid_exts) & set(valid_files_exts))
        available_converters_names = [
            CONVERTERS[ext]["name"]
            for ext in available_converters
            if ext in CONVERTERS
        ]
        # Add the available converters to the combo box
        self.view.converterBox.setDisabled(False)
        self.view.converterBox.clear()
        self.view.converterBox.addItems(available_converters_names)

        # Show files in the list
        self.selected_files = valid_files
        self._refresh_list(self.selected_files)

    def delete_selected(self):
        """Remove selected files from the list."""
        if self.view.filelistWidget.selectedItems():
            if self.confirm_deletion():
                for item in self.view.filelistWidget.selectedItems():
                    self.view.filelistWidget.takeItem(self.view.filelistWidget.row(item))
                    self.selected_files = [x for x in self.selected_files if item.text() not in x]
        self._refresh_list()

    def delete_all(self):
        """Remove all files from the list."""
        if self.view.filelistWidget.count():
            if self.confirm_deletion():
                self.view.filelistWidget.clear()
                self.selected_files = []
        self._refresh_list()
        self.view.converterBox.clear()
        self.view.converterBox.setDisabled(True)

    def confirm_deletion(self):
        # Create the confirmation dialog
        confirmation_dialog = QtWidgets.QMessageBox(self.view)
        confirmation_dialog.setWindowTitle("Confirm Deletion")
        confirmation_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        confirmation_dialog.setText("Are you sure you want to delete these files?")

        # Add 'Yes' and 'No' buttons
        confirmation_dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        confirmation_dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)

        # Show the dialog and get the user's response
        response = confirmation_dialog.exec()

        return response == QtWidgets.QMessageBox.StandardButton.Yes

    def filter_items(self, text):
        """Filter the recordings in the list."""
        filtered = self.selected_files
        if text:
            text = text.lower()
            filtered = [item for item in self.selected_files if text in os.path.basename(item).lower() or text in item.lower()]
        self._refresh_list(filtered)

    def _refresh_list(self, items=None):
        """Refresh the list according to the visualization mode (paths or names)."""
        # If no items provided, use all items
        if items is None or items == 0:
            items = self.selected_files

        # Show only the files that match the selected converter
        for ext, data in CONVERTERS.items():
            if data["name"] == self.view.converterBox.currentText():
                break
        items = [item for item in items if item.endswith(ext)]

        # Clear current list
        self.view.filelistWidget.clear()

        if self.show_only_names: # If showing only names
            display_items = [os.path.basename(item) for item in items]
        else: # Else, show full paths
            display_items = items

        # Add items to the list widget
        self.view.filelistWidget.addItems(display_items)

        # Update the files count label
        self.view.filesLabel.setText(f"{len(display_items)}")
        # Activate or deactivate buttons based on list content
        self.view.main_window.nextButton.setDisabled(not len(display_items) > 0)

    def toggle_display_mode(self, checked):
        """Changes between showing complete paths or only the names."""
        self.show_only_names = checked
        self._refresh_list()