import time, json, importlib

from PySide6 import QtGui, QtCore, QtWidgets
from experiments import flow as main_flow
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
        self._set_icon(self.view.plotprepIcon, "plot_preprocessed.png", size=[165, 157])
        self._set_icon(self.view.ploterpIcon, "plot_erps.png", size=[165, 157])
        self._set_icon(self.view.convIcon, "converter.png", size=[165, 157])


        # self._hide_all_radiobuttons()

        # Make all the QFrame clickable, selecting all the QFrame, discarding QFrame subclasses and those without
        # "QFrame" in their objectName
        frames = [f for f in self.view.findChildren(QtWidgets.QFrame)
                  if type(f) is QtWidgets.QFrame and "QFrame" in f.objectName()]
        # For each of the remaining frames, assign the click event to select the corresponding radio button
        for frame in frames:
            # Assign the click event
            frame.mousePressEvent = lambda event,frame=frame : self._on_frame_click(frame, event)

        self.view.featureseegFrame.mousePressEvent = lambda event: self._open_module("eeg_features")
        self.view.featuresecgFrame.mousePressEvent = lambda event: self._open_module("ecg_features")
        self.view.plotparamstatsFrame.mousePressEvent = lambda event: self._open_module("params")
        self.view.plotprepstatsFrame.mousePressEvent = lambda event: self._open_module("preprocess")
        self.view.ploterpstatsFrame.mousePressEvent = lambda event: self._open_module("erps")
        self.view.convFrame.mousePressEvent = lambda event: self._open_module("conv")



    def _on_frame_click(self, frame, event):
        # Simulate a click on its child radio button, if it exists
        radio = frame.findChild(QtWidgets.QRadioButton)
        if radio:
            radio.click()
        # Accept the event
        event.accept()

    # def on_radiobutton_toggle(self, checked):
    #     """
    #     Executes when the radiobutton toggle is clicked. Called de on_next_clicked function from flow.py
    #     """
    #     if checked:
    #         main_flow.on_next_click(self.view.main_window.controller)  # simulate a click
    #
    # def _hide_all_radiobuttons(self):
    #     """
    #     Hide all radiobuttons but maintaining the functionality.
    #     """
    #     radios = self.view.findChildren(QtWidgets.QRadioButton)
    #     for radio in radios:
    #         radio.setVisible(False)
    #         radio.clicked.connect(self.on_radiobutton_toggle)

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

    def _open_module(self, module_type: str):
        """
        Open main window of 'Plot & Stats' module depending on 'module_type'.
        """

        if module_type in ("eeg_features", "ecg_features"):

            # Loading screen
            self.view.main_window.loading.show()
            self.view.main_window.loading.set_progress(0, self.view.main_window)

            from experiments.controller import MainExperimentController
            from experiments.view import MainExperiment

            self.holis_window = MainExperiment()
            self.holis_controller = MainExperimentController(self.holis_window)

            # Read the corresponding config file
            with open('experiments/' + module_type + "/config.json", "r") as f:
                experiment_data = json.load(f)
                self.holis_controller.experiment = experiment_data

            self.view.main_window.total_steps = len(self.holis_controller.experiment['pipeline'])
            self.holis_window.total_steps = self.view.main_window.total_steps

            # Loading
            self.view.main_window.loading.set_progress((1 / self.view.main_window.total_steps) * 100, self.view.main_window)

            # Load the widgets, instantiate their controllers and add them to the stackedWidget
            for idx, widget_info in enumerate(self.holis_controller.experiment['pipeline']):
                # Take the path
                print(f"→ Loading widget {idx}: {widget_info}")
                widget_path = widget_info['path'].replace('/', '.')  # use dots instead of slashes

                # Import the view
                ui_module = importlib.import_module(f"{widget_path}.view")
                # Import the controller
                ctrl_module = importlib.import_module(f"{widget_path}.controller")

                # Get the classes from the modules
                widget_class = getattr(ui_module, widget_info['widget'])
                widget_controller_class = getattr(ctrl_module, widget_info['controller'])

                # Instantiate the widget
                widget = widget_class(self.holis_window)
                # Instantiate the controller, passing the widget and the main window
                widget_controller_class(widget)

                # Optionally, add the widget to a stackedWidget
                self.holis_window.stackedWidget.insertWidget(idx + 1, widget)

                # Update loading progress
                self.view.main_window.loading.set_progress(((idx + 2) / self.view.main_window.total_steps) * 100,
                                                      self.view.main_window)

            # Finish loading
            self.view.main_window.loading.finish()

            # Store the experiment id
            self.holis_window.selected_experiment = module_type
            # Update total steps and progress bar in the main window
            self.holis_window.nextButton.setDisabled(True)
            self.holis_window.controller.set_progressbar()
            # main_flow.on_next_click(view.main_window.controller) # simulate a click

            # Create and show the converter dialog, that is where the converter window will be inserted
            self.dialog = QtWidgets.QDialog(self.view.window())
            self.dialog.setModal(True)
            self.dialog.setWindowTitle("Converter")
            self.dialog.setMinimumWidth(1200)
            self.dialog.setMinimumHeight(1000)
            self.dialog.setWindowFlags(QtCore.Qt.Window)

            # Store the reference of the main QDialog to close it at the end
            self.holis_controller.dialog = self.dialog

            # Insert the converter window into the dialog and run it
            layout = QtWidgets.QVBoxLayout(self.dialog)
            layout.addWidget(self.holis_window)
            self.dialog.exec()

            return True

        # Loading screen
        self.view.main_window.loading.show()
        self.view.main_window.loading.set_progress(50, self.view.main_window)

        if module_type == "conv":
            # Import converter
            from converter.controller import MainConverterController
            from converter.view import MainConverter

            # Create converter window and controller
            self.converter_window = MainConverter()
            self.converter_controller = MainConverterController(self.converter_window)

            # Finish loading before opening the converter
            self.view.main_window.loading.set_progress(100, self.view.main_window)
            time.sleep(0.5)
            self.view.main_window.loading.finish()

            # Create and show the converter dialog, that is where the converter window will be inserted
            self.dialog = QtWidgets.QDialog(self.view.window())
            self.dialog.setModal(True)
            self.dialog.setWindowTitle("Converter")
            self.dialog.setMinimumWidth(1200)
            self.dialog.setMinimumHeight(1000)
            self.dialog.setWindowFlags(QtCore.Qt.Window)

            # Store the reference of the main QDialog to close it at the end
            self.converter_controller.dialog = self.dialog

            # Insert the converter window into the dialog and run it
            layout = QtWidgets.QVBoxLayout(self.dialog)
            layout.addWidget(self.converter_window)
            self.dialog.exec()

            return  # Avoid running the rest of the function

        # Move inside the loop when preprocessing is done
        from plots_stats.main_module.view import MainModuleWindow
        from plots_stats.main_module.controller import MainModuleWindowController
        from plots_stats.features.config.view import ConfigWidget
        from plots_stats.features.config.controller import ConfigController
        from plots_stats.timeplot.loading.view import PreprocessingWidget
        from plots_stats.timeplot.loading.controller import PreprocessingController

        # Main Module
        self.plot_stats_window = MainModuleWindow()
        self.plot_stats_controller = MainModuleWindowController(self.plot_stats_window)

        # Setting Main Module tittle depending on module type
        if module_type == "params":
            window_title = "Plot & Stats - Experiment Setup"
        elif module_type == "preprocess":
            window_title = "Preprocessing - Experiment Setup"
        elif module_type == "erps":
            window_title = "ERP Analysis - Experiment Setup"

        # Loading screen
        self.view.main_window.loading.set_progress(100, self.view.main_window)
        time.sleep(0.5) # Just to see the loading bar complete

        # Insert initial widget into the stackedWidget dependindo on module type
        if module_type == "params":
            widget = ConfigWidget(self.plot_stats_window)
            ConfigController(widget)
        elif module_type == "preprocess":
            widget = PreprocessingWidget(self.plot_stats_window)
            PreprocessingController(widget)
        elif module_type == "erps":
            widget = ConfigWidget(self.plot_stats_window, is_erp=True)
            ConfigController(widget)

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