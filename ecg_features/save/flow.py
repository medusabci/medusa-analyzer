from ecg_features.utils import PipelineWorker
from PySide6.QtCore import QThread, Qt
from PySide6 import QtWidgets

def handle_exceptions(func):
    """
    Decorator that manages exceptions raised inside UI actions. Logs the error if possible, otherwise prints it.
    """

    def wrapper(self, *args, **kwargs):
        # Try to run the function
        try:
            return func(self, *args, **kwargs)
        # If Exception
        except Exception as e:
            # Log the error with the custom format, if possible
            if hasattr(self, 'log_message'):
                self.view._log_message(f"[ERROR] {func.__name__}: {str(e)}", style='error')
            # Otherwise, print it
            else:
                print(f"[ERROR] {func.__name__}: {str(e)}")

            # To avoid closing the app
            return False

    return wrapper


@handle_exceptions # Decorator to handle exceptions and log them
def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It runs the pipeline and shows a message box upon completion.
    """
    # If the pipeline has not already been completed, run it
    if not view.controller.pipeline_completed:

        # If no folder is selected, show a warning and return
        if not view.selected_folder:
            QtWidgets.QMessageBox.warning(view, "Error", "Please, select one folder to save the data.")
            return False

        # Visibility of progress bars
        view.progressLabel.show()
        view.progressBar.show()
        view.progressBar.setValue(0)
        view.error_occurred = False
        view._log_message("Starting...")

        # Get the total number of tasks to perform
        total_tasks = sum([
            view.settingsCBox.isChecked(),
            view.prepsignalsCBox.isChecked(),
            view.paramsignalsCBox.isChecked()
        ])
        total_tasks = max(total_tasks, 1)  # To avoid division by 0

        # Get configuration data, with error handling
        try:
            files = view.main_window.controller.files_config
            leads = view.main_window.controller.leads_config
            preprocessing = view.main_window.controller.preproc_config
            parameters = view.main_window.controller.parameters_config
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(view, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return

        # Create a settings dictionary grouping all configurations
        view.controller.settings_dic = {
            "files": files,
            "leads": leads,
            "preprocessing": preprocessing,
            "parameters": parameters
        }
        # Save the settings dict
        if view.settingsCBox.isChecked():
            view.controller.save_settings_to_json(view.controller.settings_dic)

        # Disable the button while the pipeline is running
        view.main_window.nextButton.setEnabled(False)
        # Create the thread and worker
        view.thread = QThread()
        worker = PipelineWorker(view.controller, view.controller.settings_dic)
        # Move the worker to the thread
        worker.moveToThread(view.thread)

        # Connect the signals to the functions
        worker.progress.connect(view.progressBar.setValue, type=Qt.QueuedConnection)
        worker.text_progress.connect(view.progressLabel.setText, type=Qt.QueuedConnection)
        worker.log.connect(view._log_message, type=Qt.QueuedConnection)

        # Clean up when done
        worker.finished.connect(view.thread.quit)
        worker.finished.connect(worker.deleteLater)
        view.thread.finished.connect(view.thread.deleteLater)

        # When the worker is finished, enable the button and change its text
        def on_finished(error_found):
            view.main_window.nextButton.setEnabled(True)
            # If not error found, change button text to "Close"
            if not error_found:
                view.main_window.nextButton.setText('Close')
                view.controller.pipeline_completed = True
        # Connect the on_finished function
        worker.finished.connect(on_finished)

        # Assign the callbacks, the worker will call these to update the UI, and we assign them to the signals
        view.controller.on_log = lambda msg, style="": worker.log.emit(msg,style)
        view.controller.on_progress_text = worker.text_progress.emit
        view.controller.on_progress_value = worker.progress.emit

        # Run the thread
        view.thread.started.connect(worker.run)
        view.thread.start()

        return False # Prevent closing the app immediately

    # Otherwise, if the pipeline was already completed, return True to close the app
    else:
        return True