from PySide6 import QtGui, QtCore, QtWidgets
from main_window import flow as main_flow
from data_loader.experiments.flow import on_next_click
import os

class ExperimentsController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Icons
        self._set_icon(self.view.eegIcon, "eeg_features.png", size=[150, 150])
        self._set_icon(self.view.ecgIcon, "ecg_features.png", size=[165, 157])
        self._set_icon(self.view.plotparamIcon, "plot_parameters.png", size=[165, 157])
        self._set_icon(self.view.plotprepIcon, "plot_preprocessed.jpeg", size=[165, 157])

        self._hide_all_radiobuttons()

        # Make all the QFrame clickable, selecting all the QFrame, discarding QFrame subclasses and those without
        # "QFrame" in their objectName
        frames = [f for f in self.view.findChildren(QtWidgets.QFrame)
                  if type(f) is QtWidgets.QFrame and "QFrame" in f.objectName()]
        # For each of the remaining frames, assign the click event to select the corresponding radio button
        for frame in frames:
            # Assign the click event
            frame.mousePressEvent = lambda event,frame=frame : self._on_frame_click(frame, event)

        self.view.plotparamstatsFrame.mousePressEvent = lambda event: self._open_plot_stats_module("params")
        self.view.plotprepstatsFrame.mousePressEvent = lambda event: self._open_plot_stats_module("preprocess")


    def _on_frame_click(self, frame, event):
        # Simulate a click on its child radio button, if it exists
        radio = frame.findChild(QtWidgets.QRadioButton)
        if radio:
            radio.click()
        # Accept the event
        event.accept()

    def on_radiobutton_toggle(self, checked):
        """
        Executes when the radiobutton toggle is clicked. Called de on_next_clicked function from flow.py
        """
        if checked:
            main_flow.on_next_click(self.view.main_window.controller)  # simulate a click

    def _hide_all_radiobuttons(self):
        """
        Hide all radiobuttons but maintaining the functionality.
        """
        radios = self.view.findChildren(QtWidgets.QRadioButton)
        for radio in radios:
            radio.setVisible(False)
            radio.clicked.connect(self.on_radiobutton_toggle)

    def _set_icon(self, label, filename, size=None, scale_factor=0.12):
        """
        Helper to introduce icons in a QLabel
        """
        icon_path = os.path.join("media", filename)
        label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(icon_path)

        if size is not None:
            # For the small icons, set a fixed size
            pixmap = pixmap.scaled(size[0], size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            label.setFixedSize(size[0], size[1])
        else:
            # Set a scale factor for larger images
            width = int(pixmap.width() * scale_factor)
            pixmap = pixmap.scaledToWidth(width, QtCore.Qt.SmoothTransformation)

            # Let the label expand to fit the window, maintaining aspect ratio
            label.setFixedHeight(pixmap.height())
            label.setPixmap(pixmap)
            label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        label.setPixmap(pixmap)

    def _open_plot_stats_module(self, module_type: str):
        """
        Open main window of 'Plot & Stats' module depending on 'module_type'.
        """
        # Loading screen
        self.view.main_window.loading.show()
        self.view.main_window.loading.set_progress(50, self.view.main_window)

        # Move inside the loop when preprocessing is done
        from plots_stats.main_module.view import MainModuleWindow
        from plots_stats.main_module.controller import MainModuleWindowController
        from plots_stats.config.view import ConfigWidget
        from plots_stats.config.controller import ConfigController
        from plots_stats.preprocessing.loading.view import PreprocessingWidget
        from plots_stats.preprocessing.loading.controller import PreprocessingController

        # Main Module
        self.plot_stats_window = MainModuleWindow()
        self.plot_stats_controller = MainModuleWindowController(self.plot_stats_window)

        # Setting Main Module tittle depending on module type
        if module_type == "params":
            window_title = "Plot & Stats - Experiment Setup"
        elif module_type == "preprocess":
            window_title = "Preprocessing - Experiment Setup"

        # Insert initial widget into the stackedWidget dependindo on module type
        if module_type == "params":
            widget = ConfigWidget(self.plot_stats_window)
            ConfigController(widget)
        elif module_type == "preprocess":
            widget = PreprocessingWidget(self.plot_stats_window)
            PreprocessingController(widget)

        # Replace the default widget in index 0
        self.plot_stats_window.stackedWidget.insertWidget(0, widget)
        self.plot_stats_window.stackedWidget.setCurrentIndex(0)

        # Show the dialog
        self.dialog = QtWidgets.QDialog(self.view.window())
        self.dialog.setModal(True)
        self.dialog.setWindowTitle(window_title)
        self.dialog.setMinimumWidth(1200)
        self.dialog.setMinimumHeight(700)
        self.dialog.setWindowFlags(QtCore.Qt.Window)

        # Store the reference of the main QDialog to close it at the end
        self.plot_stats_controller.dialog = self.dialog

        # Finish loading
        self.view.main_window.loading.finish()

        # Run the new window
        layout = QtWidgets.QVBoxLayout(self.dialog)
        layout.addWidget(self.plot_stats_window)
        self.dialog.exec()