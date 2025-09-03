from PySide6 import QtGui, QtCore
import os

class ExperimentsController:
    def __init__(self, ui, main_window):
        self.view = ui
        self.view.controller = self
        self.main_window = main_window

        # Icons
        self._set_icon(self.view.eegIcon, "brain2.png", size=130)
        self._set_icon(self.view.ecgIcon, "heart.png", size=130)

    def _set_icon(self, label, filename, size):
        """
        Helper to introduce icons in a QLabel
        """
        icon_path = os.path.join("media", filename)
        label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(icon_path)
        label.setPixmap(pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        label.setFixedSize(100, 100)
