from PySide6 import QtWidgets
from PySide6.QtCore import QStringListModel
from eeg_features.segmentation import marks_utils
import time

class LeadsController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Show event
        self.first_show = False
        self.view.shown.connect(self.on_show_event)



    def load_marks_from_file(self, file):
        """
        Loads and displays the available conditions and events from a single data file.
        Behavior:
            - Extracts conditions, events, and condition-event associations using an external function.
            - Introduces the condition and event list with unique values in the corresponding boxes.
            - Connects selection change signals to update the descriptive labels accordingly.
            - Handles and reports any errors encountered during file processing.
        """
        try:
            self.conditions, _, _ = marks_utils.extract_condition_events([file])

            # Set unique sorted conditions and events in models
            self.view.conditionList.setModel(QStringListModel(sorted(set(self.conditions))))

            # Connect selection changes to label updates
            self.view.conditionList.selectionModel().selectionChanged.connect(self.update_labels)

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self.view, "Error", f"An error occurred while loading conditions and events from the data:\n{e}")


    def update_labels(self):
        """
        Updates the UI labels displaying the selected conditions and events.
        Behavior:
            - Retrieves the user-selected items from both lists.
            - Displays a summary of selected items in the UI labels.
            - Enables the "Next" button.
        """
        # Get selected conditions and events
        selected_conditions = {index.data() for index in self.view.conditionList.selectionModel().selectedIndexes()}

        # Format and update labels
        cond_text = ", ".join(f"{cnd}" for cnd in selected_conditions) or "None"

        # Show in the labels
        self.view.conditionLabel.setText(f"Conditions: {cond_text}")

    def on_show_event(self):
        if not self.first_show:
            self.first_show = True

            # Loading screen
            self.view.main_window.loading.show()
            self.view.main_window.loading.set_progress(25, self.view.main_window)
            time.sleep(0.3)  # Simulate loading time for better UX

            files_widget_controller = self.view.main_window.stackedWidget.widget(1).controller # widget(1) is the file selection widget
            selected_files = files_widget_controller.selected_files
            # Update loading progress
            self.view.main_window.loading.set_progress(75, self.view.main_window)

            self.load_marks_from_file(selected_files[0])
            # Update loading progress
            self.view.main_window.loading.set_progress(100, self.view.main_window)
            time.sleep(0.5)  # Simulate loading time for better UX

            # Finish loading
            self.view.main_window.loading.finish()
