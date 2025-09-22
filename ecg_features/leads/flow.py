from PySide6 import QtWidgets

def on_next_click(view):
    # Get the layout containing the leads
    layout = view.LeadsSelection

    selected_leads = dict()
    # Find all the checkboxes in LeadsSelection
    for checkbox in layout.findChildren(QtWidgets.QCheckBox):
        # if the checkbox is checked, get the corresponding channel label
        if checkbox.isChecked():
            # The label with the channel name is the second widget in the same row
            row_widget = checkbox.parentWidget().layout() # Get the parent
            channel_label = row_widget.itemAt(1).widget().text().replace("Channel ", "")  # Get the label
            channel_lead = row_widget.itemAt(3).widget().currentText()  # Get the text of the combo box
            selected_leads[channel_label] = channel_lead
    view.controller.selected_leads = selected_leads

    if not selected_leads:
        QtWidgets.QMessageBox.warning(view, "Invalid channel selection",
                                      f"You have to select at least one channel to proceed.")
        return False

    return True