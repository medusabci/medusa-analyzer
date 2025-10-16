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
        self.view.selectallButton.clicked.connect(self.view.filelistWidget.selectAll)
        self.view.clearselectionButton.clicked.connect(self.view.filelistWidget.clearSelection)
        self.view.filelistWidget.itemSelectionChanged.connect(self.on_selection_changed)

    def filter_items(self, text):
        """Filter the recordings in the list."""
        self.view.filelistWidget.clear()
        if not text:
            self.view.filelistWidget.addItems(self.view.all_items)
            return

        text = text.lower()
        filtered = [item for item in self.view.all_items if text in item.lower()]
        self.view.filelistWidget.addItems(filtered)

    def on_selection_changed(self):
        """Enable the next button if at least one item is selected, and update the selected items label."""
        selected_items = self.view.filelistWidget.selectedItems()
        self.view.selectedLabel.setText(f"{len(selected_items)} parameter(s) selected")
        self.view.main_module.nextButton.setEnabled(len(selected_items) > 0)

        # Store the selected items in the main controller
        self.view.main_module.controller.param_selection = selected_items


