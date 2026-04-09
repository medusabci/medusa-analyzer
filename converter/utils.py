import numpy as np
from PySide6.QtCore import QThread, Signal, Qt
from converter.converters import CONVERTERS
from PySide6 import QtWidgets
from pathlib import Path
import re

from medusa.components import Recording, CustomExperimentData
import shutil

def do_conversion(controller, files, converter, names_idx):

    idx_conversion_widget = 1
    conversion = controller.view.stackedWidget.widget(idx_conversion_widget)
    conversion.convertProgressBar.setVisible(True)
    conversion.convertLogTextBrowser.setVisible(True)

    # Create the thread
    output_path = _select_output_directory(controller)
    if output_path is None:
        return
    controller.view.worker = ConverterWorker(files, converter, output_path, names_idx)

    # Connect the signals to the functions
    controller.view.worker.progress.connect(conversion.convertProgressBar.setValue, type=Qt.QueuedConnection)
    controller.view.worker.log.connect(conversion._log_message, type=Qt.QueuedConnection)

    # Clean up when done
    controller.view.worker.finished.connect(controller.view.worker.deleteLater)

    # When the worker is finished, enable the button and change its text
    def on_finished(converted_files, error_found, already_correct):
        # Set the buttons in the last state
        controller.view.backButton.setVisible(False)
        controller.view.nextButton.setDisabled(False)
        controller.view.nextButton.setText("Close")
        if error_found:
            QtWidgets.QMessageBox.critical(
                conversion,
                "Conversion Error",
                f"❌ An unexpected error occurred during conversion:\n\n"
            )
        else:
            QtWidgets.QMessageBox.information(
                conversion,
                "Conversion Complete",
                f"✅ Successfully converted {len(converted_files)} file(s).\n 🛠️ Already correct {already_correct} file(s)."
            )

    # Connect the on_finished function
    controller.view.worker.finished.connect(on_finished)

    # Disable the buttons
    controller.view.nextButton.setDisabled(True)
    controller.view.backButton.setDisabled(True)

    # Run the thread
    controller.view.worker.start()

def _select_output_directory(controller):
    """Ask the user for output directory and prepare folders."""
    msg = QtWidgets.QMessageBox()
    msg.setWindowTitle("Select output path")
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText(
        f"Select a folder to save files in BIDS format.\n\n"
        "Original files will not be modified."
    )
    msg.exec()

    idx_conversion_widget = 1
    conversion = controller.view.stackedWidget.widget(idx_conversion_widget)
    output_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Select destination folder for converted files (BIDS root)"
    )
    if not output_path:
        conversion._log_message("🚫 Conversion cancelled (no output folder selected).")
        return None

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    conversion._log_message(f"📁 Output path selected: {output_dir}")
    return output_dir


def _log_conversion_summary(counters, worker):
    """Print final summary."""
    summary = (
        "<hr><b>Summary:</b><br>"
        f"🟢 Converted: {counters['converted']} file(s)<br>"
        f"🔵 Already correct: {counters['already_correct']} file(s)<br>"
    )
    if counters["skipped"]:
        summary += f"⚠️ Skipped: {counters['skipped']} file(s)"
    worker.log.emit(summary)


# Worker class to run the converter in a separate thread
class ConverterWorker(QThread):
    # Emit when the processing is finished
    finished = Signal(list, bool, int)
    # For updating the progress bar in the GUI
    progress = Signal(int)
    # For updating log messages in the GUI
    log = Signal(str)

    def __init__(self, files, converter, output_dir, names_idx):
        super().__init__()
        self.files = files
        self.converter = converter
        self.output_dir = output_dir
        self.names_idx = names_idx

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        error_found = False
        already_correct = 0
        try:
            # Call the main pipeline function
            converted_files, counters = self.converter_main(self.files, self.converter, self.output_dir, self.names_idx)
            already_correct = counters.get('already_correct', 0)
        except Exception as e: # if error
            self.log.emit(f"Error in conversion: {e}")
            converted_files = []
            error_found = True
        self.finished.emit(converted_files, error_found, already_correct)

    def converter_main(self, files, converter, output_dir, names_idx):
        """
        Convert different file types to .rec.bson format and arrange them in BIDS structure.
        - If a file is .rec.bson and already contains data.marks -> skip.
        - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
        - For other supported extensions -> run their converters.
        """

        counters = {"converted": 0, "already_correct": 0, "skipped": 0}
        total_steps = len(files)

        converter_func = self.get_converter_function_by_name(converter)

        converted_files = []

        for i, file in enumerate(files):
            bids_path = self.generate_bids_name(file, names_idx)

            file, result = self.process_file(file, output_dir / bids_path, converter_func, self)
            counters[result] += 1
            if result == "converted":
                converted_files.append(str(file))

            self.progress.emit(int((i + 1) / total_steps * 100))

        self.progress.emit(100)
        _log_conversion_summary(counters, self)
        return converted_files, counters


    def get_converter_function_by_name(self, name):
        for converters in CONVERTERS.values():
            for conv in converters:
                if conv["name"] == name:
                    return conv["function"]
        return None


    def process_file(self, file, bids_full_path, converter_func, worker):

        file = Path(file)

        worker.log.emit(f"⚙️ {file} → Converting...")
        try:
            # Run the converter
            result = converter_func(file, bids_full_path, worker)
            if not result:
                raise ValueError("Conversion function returned None or failed.")

            if result == 'already_correct':
                worker.log.emit(f"ℹ️ {file} → Already contains 'marks'. The file will not be converted, but will be restructured into BIDS format.")
                return file, 'already_correct'
            else:
                worker.log.emit(f"✅ {file} → Converting successful.")
                return file, 'converted'
        except Exception as e:
            worker.log.emit(f"❌ {file} → Error during conversion: {e}")
            return [], 'skipped'


    def generate_bids_name(self, file, names_idx, signal_name='eeg'):
        """
        Generate BIDS-compliant filenames based on user-defined elements and indices.
        """
        elements = [e for e in re.split(r"[\\/ _-]+", file.split('.')[0]) if e]

        # Extract the name elements
        subject_name = ''.join([elements[idx] for idx in names_idx["Subject"]])
        if names_idx["Session"]:
            session_name = ''.join([elements[idx] for idx in names_idx["Session"]])
        if names_idx["Recording"]:
            recording_name = ''.join([elements[idx] for idx in names_idx["Recording"]])
        else:
            recording_name = '01'  # Default recording name
        if names_idx["Task"]:
            task_name = ''.join([elements[idx] for idx in names_idx["Task"]])

        # Set the folder structure
        bids_name = ['sub-' + subject_name + '/']
        if names_idx["Session"]:
            bids_name.append('ses-' + session_name + '/')
        bids_name.append(signal_name + '/')
        # Set the name structure
        bids_name.append('sub-' + subject_name)
        if names_idx["Session"]:
            bids_name.append('_ses-' + session_name)
        if names_idx["Task"]:
            bids_name.append('_task-' + task_name)
        bids_name.append('_rec-' + recording_name)
        bids_name = ''.join(bids_name) + '.rec.bson'

        return bids_name