from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Load UI class
ui_bands_table = loadUiType("eeg_features/bands_table.ui")[0]

# THIS CODE ENABLE THE DRAG AND DROP OF BANDS IN THE TABLE
class BandTableWidget(QtWidgets.QDialog, ui_bands_table):
    def __init__(self, parameters_widget=None, preprocessing_widget=None, band_type=None, previous_bands=None,
                 min_broad=0.5, max_broad=69.0):
        super().__init__((parameters_widget or preprocessing_widget).view)
        self.setupUi(self)
        self.setFixedSize(440, 380)

        # Initialize general parameters
        self.parameters_widget = parameters_widget
        self.preprocessing_widget = preprocessing_widget
        self.band_type = band_type
        self.previous_bands = previous_bands or []
        self.default_min = min_broad
        self.default_max = max_broad
        self.accepted_bands = []

        ## ADD THE DRAG AND DROP FUNCTIONALITY TO THE TABLE
        # Store the original table
        original_table = self.bandsTable
        parent_widget = original_table.parent()

        # Create a new table
        self.bandsTable = QtWidgets.QTableWidget(self)
        self.bandsTable.setObjectName("bandsTable")

        # Replace the original table with the new one
        layout = parent_widget.layout()
        if layout:
            index = layout.indexOf(original_table)
            layout.removeWidget(original_table)
            original_table.deleteLater()
            layout.insertWidget(index, self.bandsTable)

        # Add the drag and drop functionality
        self.drag_start_pos = None
        self.bandsTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.bandsTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.bandsTable.setDragDropOverwriteMode(False)
        self.bandsTable.setDefaultDropAction(Qt.MoveAction)
        self.bandsTable.setDropIndicatorShown(True)
        self.bandsTable.installEventFilter(self)

        ### ELEMENT CONFIGURATION ###

        # Configure the bands
        self.min_broad = min_broad
        self.max_broad = max_broad
        self.default_bands = [
            {"name": "delta", "min": 1, "max": 4},
            {"name": "theta", "min": 4, "max": 8},
            {"name": "alpha", "min": 8, "max": 13},
            {"name": "beta", "min": 13, "max": 30},
            {"name": "gamma", "min": 30, "max": 70},
        ]

        self.addButton.clicked.connect(self.add_band)
        self.resetButton.clicked.connect(self.on_reset_click)
        self.acceptButton.clicked.connect(self.accept_and_close)

        # Set initial state
        self.setup_table()


    # Drag and drop logic via eventFilter
    def eventFilter(self, source, event):
        """
        Event filter function to handle drag and drop in the table.
        """
        if source is self.bandsTable:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == Qt.LeftButton: # If left button pressed
                self.drag_start_pos = event.pos()
            elif event.type() == QtCore.QEvent.MouseMove and (event.buttons() & Qt.LeftButton): # If mouse is moving with left button pressed
                if self.drag_start_pos is None: # If for some reason the start position is None, we cannot continue
                    return False
                distance = (event.pos() - self.drag_start_pos).manhattanLength() # Distance moved
                if distance < QtWidgets.QApplication.startDragDistance(): # If the distance is too small, we cannot continue
                    return False
                # Create a drag object and start the drag operation
                drag = QtGui.QDrag(self.bandsTable)
                mime_data = QtCore.QMimeData()
                mime_data.setData("application/x-qabstractitemmodeldatalist", b"")
                drag.setMimeData(mime_data)
                drag.exec_(Qt.MoveAction)
                return True
            elif event.type() == QtCore.QEvent.Drop: # If a drop event occurs
                source_row = self.bandsTable.currentRow()
                dest_index = self.bandsTable.indexAt(event.pos())
                dest_row = dest_index.row()
                if source_row == -1 or dest_row == -1 or source_row == dest_row: # -1 means no valid row
                    event.ignore() # Required as we want to reject the drop
                    return True
                # Move the row
                self._move_row(source_row, dest_row)
                event.accept() # Accept the handling of the event
                return True
        return super().eventFilter(source, event) # Required by bureaucracy of Qt
    # Helper function to move rows
    def _move_row(self, source_row, dest_row):

        # Keep the data of the original row
        row_data = []
        for col in range(self.bandsTable.columnCount()):
            widget = self.bandsTable.cellWidget(source_row, col)
            if widget: # For the trash buttons
                row_data.append(("widget", widget))
            else: # For the texts
                item = self.bandsTable.item(source_row, col)
                cloned_item = QtWidgets.QTableWidgetItem(item) if item else None
                row_data.append(("item", cloned_item))

        # Delete the old row and insert a new row in the destination
        self.bandsTable.removeRow(source_row)
        self.bandsTable.insertRow(dest_row)

        for col, (kind, content) in enumerate(row_data):

            if kind == "widget": # Add the elements to the new row, for the trash buttons...
                new_button = QtWidgets.QPushButton()
                new_button.setIcon(content.icon())
                new_button.setFixedSize(content.size())
                self.bandsTable.setCellWidget(dest_row, col, new_button)
            elif kind == "item": # And for the texts
                self.bandsTable.setItem(dest_row, col, QtWidgets.QTableWidgetItem(content))


    def setup_table(self, min_broad=None, max_broad=None):
        """
        Set (or reset) the table to its initial state
        """
        # Store the min and max broadband values if provided
        if min_broad is not None:
            self.min_broad = min_broad
        if max_broad is not None:
            self.max_broad = max_broad

        # Set the number of columns and their names
        self.bandsTable.setColumnCount(4)
        self.bandsTable.setHorizontalHeaderLabels(["Name", "Min. Freq.", "Max. Freq.", "Remove"])

        # Set the header format
        font = QFont()
        font.setBold(True)
        for i in range(4):
            item = self.bandsTable.horizontalHeaderItem(i)
            item.setFont(font)

        # Drag and drop functionality
        self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.bandsTable.setDragDropOverwriteMode(False)
        self.bandsTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.bandsTable.setDefaultDropAction(Qt.MoveAction)

        # Clear all the table contents
        self.bandsTable.clearContents()
        self.bandsTable.setRowCount(0)

        # For each default band...
        for band in self.default_bands:
            self.add_band(band["name"], band["min"], band["max"])

        # # Get the previous band values (if they are passed from another iteration of the bands table widget)
        # previous_dict = {band["name"]: band for band in self.previous_bands} if self.previous_bands else {}
        # # For each default band...
        # for band in self.default_bands:
        #     name = band["name"]
        #     if name in previous_dict: # If it was in the previous bands, use those values
        #         prev_band = previous_dict[name]
        #         self.add_band(name, prev_band["min"], prev_band["max"])
        #         del previous_dict[name] # Remove it from the dict to avoid adding it again later
        #     else: # Else, use the default values
        #         self.add_band(name, band["min"], band["max"])
        #
        # # Personalized bands (different from default, that have been already added and removed from previous_dict)
        # for name, band in previous_dict.items():
        #     if name == 'broadband':
        #         continue
        #     self.add_band(name, band["min"], band["max"])


    def add_band(self, name="custom", min_freq=None, max_freq=None):
        """
        Add a new band row to the table with default or provided values.
        """
        # Insert a new row at the end of the table
        row = self.bandsTable.rowCount()
        self.bandsTable.insertRow(row)

        # Name
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 0, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{float(min_freq):.1f}" if min_freq is not None else "")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{float(max_freq):.1f}" if max_freq is not None else "")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 2, max_item)

        # Trash button
        remove_button = QtWidgets.QPushButton()
        icon = QtGui.QIcon("media/delete_icon.png")
        remove_button.setIcon(icon)
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("margin-left:auto; margin-right:auto;")
        remove_button.clicked.connect(lambda _, r=row: self.bandsTable.removeRow(r))
        self.bandsTable.setCellWidget(row, 3, self._center_widget(remove_button))
    # Helper function to center widgets in table cells
    def _center_widget(self, widget):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        return container


    def on_reset_click(self):
        """
        Reset the table to its default state.
        """
        try: # Try to disconnect the cell change signal
            self.bandsTable.cellChanged.disconnect(self.on_cell_change)
        except TypeError:
            pass
        # Set table to default state
        self.setup_table(min_broad=self.default_min, max_broad=self.default_max, preserve_broadband=False)
        # Connect again the cell change signal
        self.bandsTable.cellChanged.connect(self.on_cell_change)


    # Helper function that returns the broadband values
    def _get_broadband_range(self):

        return float(self.minbroadbandLabel.text()), float(self.maxbroadbandLabel.text())


    # Helper function to update the broadband values
    def _set_broadband_range(self, min_broad, max_broad):

        self.minbroadbandLabel.setText(f"{min_broad:.1f}")
        self.maxbroadbandLabel.setText(f"{max_broad:.1f}")











































    def _accept_and_close(self):
        self.accepted_bands = []
        empty_name_rows = []
        zero_max_rows = []
        zero_min_rows = []
        invalid_value_rows = []
        negative_value_rows = []
        invalid_interval_rows = []
        out_of_range_rows = []

        for row in range(self.bandsTable.rowCount()):
            checkbox_container = self.bandsTable.cellWidget(row, 0)
            if not checkbox_container:
                continue
            checkbox = checkbox_container.findChild(QtWidgets.QCheckBox)
            if not checkbox or not checkbox.isChecked():
                continue

            name_item = self.bandsTable.item(row, 1)
            min_item = self.bandsTable.item(row, 2)
            max_item = self.bandsTable.item(row, 3)

            name = name_item.text().strip() if name_item else ""
            min_text = min_item.text().strip() if min_item else ""
            max_text = max_item.text().strip() if max_item else ""

            if not name or not min_text or not max_text:
                empty_name_rows.append(row + 1)
                continue

            try:
                min_val = float(min_text)
                max_val = float(max_text)
            except ValueError:
                invalid_value_rows.append(row + 1)
                continue

            if min_val < 0 or max_val < 0: # negative frequencies
                negative_value_rows.append(row + 1)

            if max_val >= 0 and max_val < 0.2: # max_values below its low limit
                zero_max_rows.append(row + 1)

            if min_val >= 0 and min_val < 0.1: # min_values below its low limit
                zero_min_rows.append(row + 1)

            if min_val >= max_val: # max_value is lower than min_value
                invalid_interval_rows.append(row + 1)

            if min_val < self.min_broad or max_val > self.max_broad:
                out_of_range_rows.append(row + 1)

            if (row + 1 not in empty_name_rows and
                    row + 1 not in zero_max_rows and
                    row + 1 not in zero_min_rows and
                    row + 1 not in invalid_value_rows and
                    row + 1 not in negative_value_rows and
                    row + 1 not in invalid_interval_rows and
                    row + 1 not in out_of_range_rows):

                self.accepted_bands.append({
                    "name": name,
                    "min": min_val,
                    "max": max_val
                })

        if (empty_name_rows or zero_max_rows or zero_min_rows or invalid_value_rows or
                negative_value_rows or invalid_interval_rows or out_of_range_rows):

            message = "Some entries in the table contain invalid data. Please review the following rows before continuing:\n\n"

            if empty_name_rows:
                message += f"• Row(s) {', '.join(map(str, empty_name_rows))}: missing name, minimum, or maximum frequency.\n"
            if zero_max_rows:
                message += f"• Row(s) {', '.join(map(str, zero_max_rows))}: maximum frequency must be greater than 0.2.\n"
            if zero_min_rows:
                message += f"• Row(s) {', '.join(map(str, zero_min_rows))}: minimum frequency must be greater than 0.1.\n"
            if invalid_value_rows:
                message += f"• Row(s) {', '.join(map(str, invalid_value_rows))}: frequency values must be numeric.\n"
            if negative_value_rows:
                message += f"• Row(s) {', '.join(map(str, negative_value_rows))}: negative frequency values are not allowed.\n"
            if invalid_interval_rows:
                message += f"• Row(s) {', '.join(map(str, invalid_interval_rows))}: minimum frequency must be less than the maximum frequency.\n"
            if out_of_range_rows:
                message += f"• Row(s) {', '.join(map(str, out_of_range_rows))}: frequency range must be within the broadband range ({self.min_broad:.1f}–{self.max_broad:.1f} Hz).\n"

            message += "\nCorrect the above issues and try again."
            QtWidgets.QMessageBox.warning(self, "Invalid Table Entries", message)
            return

        if self.band_type:
            if self.parameters_widget:
                self.parameters_widget.update_band_label(self.band_type, self.accepted_bands)
            elif self.preprocessing_widget:
                self.preprocessing_widget.update_band_label(self.band_type, self.accepted_bands)
        self.close()


