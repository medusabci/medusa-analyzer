from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
import os

class FilesListDialog(QtWidgets.QDialog):
    def __init__(self, files, preprocessing_widget):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "files_list.ui")
        uic.loadUi(ui_path, self)

        # Remove the "?" button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Change the title
        self.setWindowTitle("List of Files")

        # Define variables
        self.preprocessing_widget = preprocessing_widget

        # --- GET ELEMENTS FROM UI MODULE ---
        self.filelistWidget = self.findChild(QtWidgets.QListWidget, "filelistWidget")
        self.deletefilesButton = self.findChild(QtWidgets.QPushButton, "deletefilesButton")
        self.acceptfilesButton = self.findChild(QtWidgets.QPushButton, "acceptfilesButton")

        # --- ELEMENT SETUP ---
        self.filelistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.filelistWidget.addItems(files)
        self.deletefilesButton.clicked.connect(self.delete_selected)
        self.acceptfilesButton.clicked.connect(self.accept)

    def delete_selected(self):
        """
            Remove the selected files.
        """
        for item in self.filelistWidget.selectedItems():
            self.filelistWidget.takeItem(self.filelistWidget.row(item))

        # Actualizar estado en PreprocessingWidget
        updated_files = self.get_updated_files()
        if not updated_files:
            self.preprocessing_widget.selected_files = []
            self.preprocessing_widget.reset_all_controls()
            self.preprocessing_widget.update_select_label()

    def get_updated_files(self):
        """
            Return the current file list.
        """
        return [self.filelistWidget.item(i).text() for i in range(self.filelistWidget.count())]