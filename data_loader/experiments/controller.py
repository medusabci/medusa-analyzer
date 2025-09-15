from PySide6 import QtGui, QtCore, QtWidgets
import os


class ExperimentsController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Icons
        self._set_icon(self.view.eegIcon, "brain2.png", size=130)
        self._set_icon(self.view.ecgIcon, "heart.png", size=130)

        # Make all the QFrame clickable, selecting all the QFrame, discarding QFrame subclasses and those without
        # "QFrame" in their objectName
        frames = [f for f in self.view.findChildren(QtWidgets.QFrame)
                  if type(f) is QtWidgets.QFrame and "QFrame" in f.objectName()]
        # For each of the remaining frames, assign the click event to select the corresponding radio button
        for frame in frames:
            # Assign the click event
            frame.mousePressEvent = lambda event,frame=frame : self._on_frame_click(frame, event)

    def _on_frame_click(self, frame, event):
        # Simulate a click on its child radio button, if it exists
        radio = frame.findChild(QtWidgets.QRadioButton)
        if radio:
            radio.click()
        # Accept the event
        event.accept()

    def _set_icon(self, label, filename, size):
        """
        Helper to introduce icons in a QLabel
        """
        icon_path = os.path.join("media", filename)
        label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(icon_path)
        label.setPixmap(pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        label.setFixedSize(100, 100)

