from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Load UI class
ui_bands_table = loadUiType("eeg_features/bands_table.ui")[0]

# THIS CODE ENABLE THE DRAG AND DROP OF BANDS IN THE TABLE
class BandTableWidget(QtWidgets.QDialog, ui_bands_table):
    def __init__(self, parameters_widget=None, preprocessing_widget=None, band_type=None, previous_bands=None):
        super().__init__((parameters_widget or preprocessing_widget).view)
        self.setupUi(self)
        self.setFixedSize(440, 380)

        # Initialize general parameters
        self.parameters_widget = parameters_widget
        self.preprocessing_widget = preprocessing_widget
        self.band_type = band_type
        self.previous_bands = previous_bands or []
        self.min_broad = preprocessing_widget.view.minbroadBox.value()
        self.max_broad = preprocessing_widget.view.maxbroadBox.value()
        self.correct_bands = []
        self._showing_forbidden = False

        # Set the broadband label values
        self.minbroadbandLabel.setText(f"{self.min_broad:.1f}")
        self.maxbroadbandLabel.setText(f"{self.max_broad:.1f}")

        # Add the drag and drop functionality
        self.drag_start_pos = None
        self.bandsTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.bandsTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.bandsTable.setDragDropOverwriteMode(False)
        self.bandsTable.setDefaultDropAction(Qt.MoveAction)
        self.bandsTable.setDropIndicatorShown(True)
        self.bandsTable.installEventFilter(self)  # already set; used now to block overwrite drops


        ### ELEMENT CONFIGURATION ###

        # Configure the bands
        self.default_bands = [
            {"name": "delta", "min": 1, "max": 4},
            {"name": "theta", "min": 4, "max": 8},
            {"name": "alpha", "min": 8, "max": 13},
            {"name": "beta", "min": 13, "max": 30},
            {"name": "gamma", "min": 30, "max": 70},
        ]

        self.addButton.clicked.connect(lambda: self.add_band()) # Add a new band with default values
        self.resetButton.clicked.connect(self.on_reset_click)
        self.acceptButton.clicked.connect(self.on_accept_click)

        self.bandsTable.setAlternatingRowColors(True)
        self.bandsTable.setStyleSheet("""
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: #f9f9f9;
                alternate-background-color: #ecf0f1;
                selection-background-color: #2980b9;
                selection-color: white;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)

        header = self.bandsTable.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px;
            }
        """)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        self.bandsTable.verticalHeader().setVisible(False)
        self.bandsTable.verticalHeader().setDefaultSectionSize(36)

        # Set initial state
        self.setup_table()


    def setup_table(self):
        """
        Set (or reset) the table to its initial state
        """

        # Set the number of columns and their names
        self.bandsTable.setColumnCount(4)
        self.bandsTable.setHorizontalHeaderLabels(["Name", "Min. Freq.", "Max. Freq.", "Remove"])

        # Set the header format
        font = QFont()
        font.setBold(True)
        for i in range(4):
            item = self.bandsTable.horizontalHeaderItem(i)
            item.setFont(font)

        # # Drag and drop functionality
        # self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # self.bandsTable.setDragDropOverwriteMode(False)
        # self.bandsTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        # self.bandsTable.setDefaultDropAction(Qt.MoveAction)

        # Clear all the table contents
        self.bandsTable.clearContents()
        self.bandsTable.setRowCount(0)

        # For each default band...
        for band in self.default_bands:
            self.add_band(band["name"], band["min"], band["max"])


    def add_band(self, name="custom_band", min_freq=None, max_freq=None):
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

        # Remove ability to drop ON these items (only between rows)
        for col in (0, 1, 2):
            itm = self.bandsTable.item(row, col)
            if itm:
                itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

        # Trash button
        remove_button = QtWidgets.QPushButton()
        icon = QtGui.QIcon("media/delete_icon.png")
        remove_button.setIcon(icon)
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("margin-left:auto; margin-right:auto;")
        remove_button.clicked.connect(self._delete_row)
        self.bandsTable.setCellWidget(row, 3, self._center_widget(remove_button))
    # Helper function to center widgets in table cells
    def _center_widget(self, widget):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        return container
    # Helper function to delete a row when the trash button is clicked
    def _delete_row(self):
        # Get the button that was clicked
        button = self.sender()
        # Find the row of that button and remove it
        for row in range(self.bandsTable.rowCount()):
            if self.bandsTable.cellWidget(row, 3).findChild(QtWidgets.QPushButton) == button:
                self.bandsTable.removeRow(row)
                break


    def on_reset_click(self):
        """
        Reset the table to its default state.
        """
        # Create the confirmation dialog
        confirmation_dialog = QtWidgets.QMessageBox(self)
        confirmation_dialog.setWindowTitle("Confirm Reset")
        confirmation_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        confirmation_dialog.setText("Are you sure you want to reset the bands?")
        confirmation_dialog.setInformativeText("This action cannot be undone.")

        # Add 'Yes' and 'No' buttons
        confirmation_dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        confirmation_dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)

        response = confirmation_dialog.exec()

        if response == QtWidgets.QMessageBox.StandardButton.Yes:
            # Set table to default state
            self.setup_table()


    # Helper function that returns the broadband values
    def _get_broadband_range(self):

        return float(self.minbroadbandLabel.text()), float(self.maxbroadbandLabel.text())


    # Helper function to update the broadband values
    def _set_broadband_range(self, min_broad, max_broad):

        self.minbroadbandLabel.setText(f"{min_broad:.1f}")
        self.maxbroadbandLabel.setText(f"{max_broad:.1f}")

    def closeEvent(self, event):
        """
        Handle the close event to discard all the non-accepted changes.
        """
        if event.spontaneous():
            if self.correct_bands:
                self.bandsTable.clearContents()
                self.bandsTable.setRowCount(0)
                for band in self.correct_bands:
                    self.add_band(band["name"], band["min"], band["max"])
            else:
                self.setup_table()
            event.accept()


    def on_accept_click(self):
        """
        Validate the table entries and accept the changes if all entries are valid.
        """
        # Create variables to track errors
        self.correct_bands = []
        empty_name_rows = []
        invalid_value_rows = []
        negative_zero_value_rows = []
        invalid_interval_rows = []
        out_of_range_rows = []

        # For each row in the table...
        for row in range(self.bandsTable.rowCount()):

            # Get name, and range
            name_item = self.bandsTable.item(row, 0)
            min_item = self.bandsTable.item(row, 1)
            max_item = self.bandsTable.item(row, 2)

            # Remove spaces and convert to text
            name = name_item.text().strip() if name_item else ""
            min_freq_text = min_item.text().strip() if min_item else ""
            max_freq_text = max_item.text().strip() if max_item else ""

            # If any of the fields is empty, mark the row as erroneous
            if not name or not min_freq_text or not max_freq_text:
                empty_name_rows.append(row)
                continue

            # Try to convert the frequency values to float, if not possible, mark the row as erroneous
            try:
                min_val = float(min_freq_text)
                max_val = float(max_freq_text)
            except ValueError:
                invalid_value_rows.append(row)
                continue

            # If negative values in the frequency range, mark the row as erroneous
            if min_val < 0 or max_val <= 0:
                negative_zero_value_rows.append(row)
            # If min_freq > max_freq, mark the row as erroneous
            if min_val >= max_val: # max_value is lower than min_value
                invalid_interval_rows.append(row)
            # If the frequency range is not within the broadband, mark the row as erroneous
            if min_val < self.min_broad or max_val > self.max_broad:
                out_of_range_rows.append(row + 1)

            # If the row is correct, add it to the correct_bands list
            if (row + 1 not in empty_name_rows and
                    row + 1 not in invalid_value_rows and
                    row + 1 not in negative_zero_value_rows and
                    row + 1 not in invalid_interval_rows and
                    row + 1 not in out_of_range_rows):
                self.correct_bands.append({
                    "name": name,
                    "min": min_val,
                    "max": max_val
                })

        # If there are any errors, show a message (one for each error) box and do not accept the changes
        if (empty_name_rows or invalid_value_rows or negative_zero_value_rows or
                invalid_interval_rows or out_of_range_rows):

            message = "Some entries in the table contain invalid data. Please review the following rows before continuing:\n\n"

            if empty_name_rows:
                message += f"• Row(s) {', '.join(map(str, empty_name_rows))}: missing name, minimum, or maximum frequency.\n"
            if invalid_value_rows:
                message += f"• Row(s) {', '.join(map(str, invalid_value_rows))}: frequency values must be numeric.\n"
            if negative_zero_value_rows:
                message += f"• Row(s) {', '.join(map(str, negative_zero_value_rows))}: negative or zero frequency values are not allowed.\n"
            if invalid_interval_rows:
                message += f"• Row(s) {', '.join(map(str, invalid_interval_rows))}: minimum frequency must be less than the maximum frequency.\n"
            if out_of_range_rows:
                message += f"• Row(s) {', '.join(map(str, out_of_range_rows))}: frequency range must be within the broadband range ({self.min_broad:.1f}–{self.max_broad:.1f} Hz).\n"

            message += "\nCorrect the above issues and try again."
            QtWidgets.QMessageBox.warning(self, "Invalid Table Entries", message)
            return

        if self.band_type == 'segmentation':
            self.preprocessing_widget.update_band_label(self.band_type, self.correct_bands)
        elif self.band_type == 'rp':
            self.parameters_widget.update_band_label(self.band_type, self.correct_bands)
        self.close()

    def eventFilter(self, source, event):
        if source is self.bandsTable:
            et = event.type()
            if et in (QtCore.QEvent.DragMove, QtCore.QEvent.Drop):
                if self.bandsTable.dropIndicatorPosition() == QtWidgets.QAbstractItemView.OnItem:
                    # Block overwrite
                    event.ignore()
                    if not self._showing_forbidden and et == QtCore.QEvent.DragMove:
                        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.ForbiddenCursor)
                        self._showing_forbidden = True
                    if et == QtCore.QEvent.Drop:
                        if self._showing_forbidden:
                            QtWidgets.QApplication.restoreOverrideCursor()
                            self._showing_forbidden = False
                    return True
                else:
                    if self._showing_forbidden:
                        QtWidgets.QApplication.restoreOverrideCursor()
                        self._showing_forbidden = False
            # elif et in (QtCore.QEvent.DragLeave, QtCore.QEvent.DragEnd):
            #     if self._showing_forbidden:
            #         QtWidgets.QApplication.restoreOverrideCursor()
            #         self._showing_forbidden = False
        return super().eventFilter(source, event)
