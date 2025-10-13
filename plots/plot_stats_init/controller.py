# plots/initial_configuration/controller.py
import os
import json
from PySide6 import QtWidgets, QtCore
from .view import PlotStatsInitView
from . import flow


class PlotStatsInitController(QtCore.QObject):

    next_step_requested = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = PlotStatsInitView()
        self.config_path = os.path.join(os.path.dirname(__file__), "plot_stats_config.json")
        self.widget_config = flow.load_widget_config(self.config_path)
        self.experiment_info = None

        # Conectar señales UI
        self.view.browseButton.clicked.connect(self.browse_folder)
        self.view.pathEdit.textChanged.connect(self.validate_path)
        self.view.betweenRButton.toggled.connect(self.update_next_button_state)
        self.view.withinRButton.toggled.connect(self.update_next_button_state)
        self.view.preprocessedRButton.toggled.connect(self.update_next_button_state)
        self.view.parametersRButton.toggled.connect(self.update_next_button_state)
        self.view.nextButton.clicked.connect(self.emit_next_signal)

        self.update_next_button_state()

    def browse_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self.view, "Select Experiment Folder")
        if folder:
            self.view.pathEdit.setText(folder)

    def validate_path(self):
        path = self.view.pathEdit.text().strip()
        result = flow.validate_experiment_path(path)

        self.view.messageLabel.setText(result["message"])
        self.view.expinfoLabel.setText(result["expinfo"])
        self.experiment_info = result["experiment_info"]

        self.update_next_button_state()

    def update_next_button_state(self):
        valid = flow.is_next_enabled(
            self.experiment_info,
            between_checked=self.view.betweenRButton.isChecked(),
            within_checked=self.view.withinRButton.isChecked(),
            preproc_checked=self.view.preprocessedRButton.isChecked(),
            params_checked=self.view.parametersRButton.isChecked(),
        )
        self.view.nextButton.setEnabled(bool(valid))

    def emit_next_signal(self):
        config = flow.build_next_config(
            experiment_path=self.view.pathEdit.text().strip(),
            experiment_info=self.experiment_info,
            between_checked=self.view.betweenRButton.isChecked(),
            preproc_checked=self.view.preprocessedRButton.isChecked(),
            widget_config=self.widget_config,
        )
        self.next_step_requested.emit(config)
