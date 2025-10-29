from PySide6 import QtWidgets

from ecg_features.leads.view import LeadsWidget


def on_next_click(controller):
    """
    Controls the next (and finish) button behaviour
    """
    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget

    # Call the specific on_next_clicked function of the previous widget
    current_widget = controller.view.stackedWidget.widget(idx)
    widget_module = current_widget.__module__.rsplit('.', 1)[0]
    flow_module = __import__(widget_module + '.flow', fromlist=['on_next_click'])
    next_validation = flow_module.on_next_click(current_widget)
    if next_validation is False:
        return False

    idx += 1 # Now is the index of the next widget

    # Update the buttons, the progressbar, and the stacked widget
    controller.update_progressbar(idx)
    controller.view.stackedWidget.setCurrentIndex(idx)
    controller.view.backButton.setVisible(idx > 0)
    controller.view.nextButton.setVisible(idx > 0)
    # Go the next widget, set text to "Next"
    if idx < controller.view.total_steps:
        controller.view.nextButton.setText("Next")
    # If going to the last widget
    elif idx == controller.view.total_steps:
        controller.view.nextButton.setText("Run pipeline")
    # If in the last widget, close the app
    elif idx == controller.view.total_steps + 1:
        controller.view.close()


def on_back_click(controller):
    """
    Controls the back button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget
    idx -= 1 # Now is the index of the future widget

    # If going back to the LeadsWidget, set from_back to True to avoid reloading, sorry for this but I cannot find a better way :(
    if isinstance(controller.view.stackedWidget.widget(idx), LeadsWidget):
        controller.view.stackedWidget.widget(idx).controller.from_back = True

    if idx == 0:
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle("Warning")
        msg.setText("If you continue, all unsaved changes will be lost. Do you want to proceed?")
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)
        reply = msg.exec()
        if reply == QtWidgets.QMessageBox.No:
            return

        # If going back to the first widget, remove all the progress bar frames, get the layout
        layout = controller.view.widget.layout()
        # Loop through all the frames in the layout and remove them
        for frame in controller.view.widget.findChildren(QtWidgets.QFrame):
            if frame.objectName().startswith("frame_"):  # Only consider the frames we created (that were named "frame_{n_step}")
                layout.removeWidget(frame)  # Remove the frame from the layout
                frame.deleteLater() # Delete the frame safely

    # Update the buttons, the progressbar, and the stacked widget
    controller.update_progressbar(idx)
    controller.view.stackedWidget.setCurrentIndex(idx)
    controller.view.backButton.setVisible(idx > 0)
    controller.view.nextButton.setDisabled(False)
    controller.view.nextButton.setText("Run pipeline" if idx == controller.view.total_steps else "Next")
    controller.view.nextButton.setVisible(idx > 0)
