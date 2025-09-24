from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Load UI class
ui_bands_table = loadUiType("eeg_features/bands_table.ui")[0]

# THIS CODE ENABLE THE DRAG AND DROP OF BANDS IN THE TABLE
class BandTableWidget(QtWidgets.QDialog, ui_bands_table):
    def __init__(self, parameters_widget=None, previous_bands=None):
        super().__init__(parameters_widget.view)
        self.setupUi(self)
        self.setFixedSize(440, 320)

        # Initialize general parameters
        self.parameters_widget = parameters_widget
        self.previous_bands = previous_bands or []

        ### ELEMENT CONFIGURATION ###

        # Configure the bands
        self.default_bands = [
            {'name': 'Broadband', 'min': 0.0033, 'max': 0.4},
            {"name": "Very Low", "min": 0.0033, "max": 0.04},
            {"name": "Low", "min": 0.04, "max": 0.15},
            {"name": "High", "min": 0.15, "max": 0.4}
        ]

        # Button connections
        self.resetButton.clicked.connect(self.on_reset_click)
        self.acceptButton.clicked.connect(self.on_accept_click)

        self.bandsTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Set the table style, with alteranting row colors (light gray - white - light gray - white...)
        self.bandsTable.setAlternatingRowColors(True)
        self.bandsTable.setStyleSheet("""
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: #f9f9f9;
                alternate-background-color: #ecf0f1;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 6px;
                selection-background-color: transparent;
            }
        """)
        # Set a different style for the header
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
        # Disable the vertical header (as we don't have)
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

        # Set the default bands as selected bands
        self.selected_bands = self.default_bands.copy()

        # Set the header format
        font = QFont()
        font.setBold(True)
        for i in range(4):
            item = self.bandsTable.horizontalHeaderItem(i)
            item.setFont(font)

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
        min_item = QtWidgets.QTableWidgetItem(f"{float(min_freq):.3f}" if min_freq is not None else "")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{float(max_freq):.3f}" if max_freq is not None else "")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 2, max_item)

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
                name_item = self.bandsTable.item(row, 0)
                self.selected_bands = [b for b in self.selected_bands if b.get("name") != name_item.text()]
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

    def closeEvent(self, event):
        """
        Handle the close event to discard all the non-accepted changes.
        """
        if event.spontaneous():
            if self.selected_bands:
                self.bandsTable.clearContents()
                self.bandsTable.setRowCount(0)
                for band in self.selected_bands:
                    self.add_band(band["name"], band["min"], band["max"])
            else:
                self.setup_table()
            event.accept()


    def on_accept_click(self):
        """
        Validate the table entries and accept the changes if all entries are valid.
        """
        self.parameters_widget.update_band_label(self.selected_bands)
        self.close()

