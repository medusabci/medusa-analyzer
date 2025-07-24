from PyQt5 import QtWidgets, uic

class FilesListDialog(QtWidgets.QDialog):
    def __init__(self, files, preprocessing_widget):
        super().__init__()
        uic.loadUi("files_list.ui", self)

        self.preprocessing_widget = preprocessing_widget
        self.filelistWidget = self.findChild(QtWidgets.QListWidget, "filelistWidget")
        self.deletefilesButton = self.findChild(QtWidgets.QPushButton, "deletefilesButton")
        self.acceptfilesButton = self.findChild(QtWidgets.QPushButton, "acceptfilesButton")

        self.filelistWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.filelistWidget.addItems(files)

        self.deletefilesButton.clicked.connect(self.delete_selected)
        self.acceptfilesButton.clicked.connect(self.accept)

    def delete_selected(self):
        """Eliminar archivos seleccionados de la lista."""
        for item in self.filelistWidget.selectedItems():
            self.filelistWidget.takeItem(self.filelistWidget.row(item))

        # Actualizar estado en PreprocessingWidget
        updated_files = self.get_updated_files()
        if not updated_files:
            self.preprocessing_widget.selected_files = []
            self.preprocessing_widget.reset_all_controls()
            self.preprocessing_widget.update_select_label()

    def get_updated_files(self):
        """Devolver la lista actual de archivos."""
        return [self.filelistWidget.item(i).text() for i in range(self.filelistWidget.count())]