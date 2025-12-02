from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
import numpy as np
from os.path import basename, join, splitext
from os import makedirs
from copy import deepcopy
import re
import json
from pathlib import Path


# Worker class to run the pipeline in a separate thread
class PipelineWorker(QThread):
    # Emit when the processing is finished
    finished = Signal(bool)
    # For updating the progress bar in the GUI
    progress = Signal(int)
    # For updating text progress in the GUI
    text_progress = Signal(str)
    # For updating log messages in the GUI
    log = Signal(str,str)

    def __init__(self, settings_dic):
        super().__init__()
        self.settings_dic = settings_dic

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        try:
            # Call the main pipeline function
            error_found = self.run_pipeline(self.settings_dic)
        except Exception as e: # if error
            self.log.emit(f"Error in pipeline: {e}","error")
            error_found = True
        self.finished.emit(error_found)


    def run_pipeline(self, settings_dic):
        """
        Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
        computation for all selected files based on the provided configuration.
        """

        # Do something in an independent thread
        # Heavy task here
        print('Running pipeline in a separate thread')