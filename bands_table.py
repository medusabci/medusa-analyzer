from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# This code enable the drag and drop of bands in the table
class BandTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)

        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return

        if self._drag_start_pos is None:
            return

        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < QtWidgets.QApplication.startDragDistance():
            return

        row = self.rowAt(self._drag_start_pos.y())
        if row == 0:
            return  # It is not possible to move the broadband

        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        mime_data.setData("application/x-qabstractitemmodeldatalist", b"")
        drag.setMimeData(mime_data)

        # Optional visual feedback
        drag.exec_(Qt.MoveAction)

    def dropEvent(self, event):
        source_row = self.currentRow()
        dest_index = self.indexAt(event.pos())
        dest_row = dest_index.row()

        if source_row == -1 or dest_row == -1:
            event.ignore()
            return

        if source_row == 0 or dest_row == 0:
            event.ignore()
            return

        if source_row == dest_row:
            event.ignore()
            return

        self._move_row(source_row, dest_row)
        event.accept()

    def _move_row(self, source_row, dest_row):
        if dest_row > source_row:
            dest_row += 1

        # Keep the data of the original row
        row_data = []
        for col in range(self.columnCount()):
            widget = self.cellWidget(source_row, col)
            if widget:
                row_data.append(("widget", widget))
            else:
                item = self.item(source_row, col)
                cloned_item = QtWidgets.QTableWidgetItem(item) if item else None
                row_data.append(("item", cloned_item))

        # Insert a new row in the destination
        self.insertRow(dest_row)

        for col, (kind, content) in enumerate(row_data):
            if kind == "widget":
                # Reemplazar con nuevo widget si es necesario
                if isinstance(content, QtWidgets.QCheckBox):
                    new_widget = QtWidgets.QCheckBox()
                    new_widget.setChecked(content.isChecked())
                    self.setCellWidget(dest_row, col, new_widget)
                elif isinstance(content, QtWidgets.QPushButton):
                    new_button = QtWidgets.QPushButton()
                    new_button.setIcon(content.icon())
                    new_button.setFixedSize(content.size())
                    self.setCellWidget(dest_row, col, new_button)
                else:
                    self.setCellWidget(dest_row, col, content)
            elif kind == "item":
                self.setItem(dest_row, col, QtWidgets.QTableWidgetItem(content))

        # Delete original row (take into account that the index may have changed "+1")
        if dest_row < source_row:
            self.removeRow(source_row + 1)
        else:
            self.removeRow(source_row)

class BandTable(QtWidgets.QDialog):
    def __init__(self, parameters_widget=None, preprocessing_widget=None, band_type=None, previous_bands=None,
                 min_broad=0.5, max_broad=69.0):
        super().__init__(parameters_widget or preprocessing_widget)
        self.parameters_widget = parameters_widget
        self.preprocessing_widget = preprocessing_widget
        self.band_type = band_type
        self.previous_bands = previous_bands or []
        self.default_min = min_broad
        self.default_max = max_broad
        uic.loadUi("bands_table.ui", self)

        original_table = self.findChild(QtWidgets.QTableWidget, "bandsTable")
        self.bandsTable = BandTableWidget(self)
        self.bandsTable.setObjectName("bandsTable")

        layout = original_table.parent().layout()
        if layout:
            index = layout.indexOf(original_table)
            layout.removeWidget(original_table)
            original_table.deleteLater()
            layout.insertWidget(index, self.bandsTable)

        self.addButton = self.findChild(QtWidgets.QPushButton, "addButton")
        self.resetButton = self.findChild(QtWidgets.QPushButton, "resetButton")
        self.acceptButton = self.findChild(QtWidgets.QPushButton, "acceptButton")
        self.selectallButton = self.findChild(QtWidgets.QPushButton, "selectallButton")

        self.min_broad = min_broad
        self.max_broad = max_broad
        self.default_bands = [
            {"name": "delta", "min": 1, "max": 4},
            {"name": "theta", "min": 4, "max": 8},
            {"name": "alpha", "min": 8, "max": 13},
            {"name": "beta", "min": 13, "max": 30},
            {"name": "gamma", "min": 30, "max": 70},
        ]

        self.accepted_bands = []
        self._setup_table()
        self.addButton.clicked.connect(self._add_band_row)
        self.resetButton.clicked.connect(self._reset_table)
        self.acceptButton.clicked.connect(self._accept_and_close)
        self.bandsTable.cellChanged.connect(self._handle_cell_change)
        self.selectallButton.clicked.connect(self._select_all_bands)

    def _setup_table(self, min_broad=None, max_broad=None, preserve_broadband=False):
        if min_broad is not None:
            self.min_broad = min_broad
        if max_broad is not None:
            self.max_broad = max_broad

        self.bandsTable.setColumnCount(5)
        self.bandsTable.setHorizontalHeaderLabels(["Enabled", "Name", "Min. Freq.", "Max. Freq.", "Remove"])

        # Header
        font = QFont()
        font.setBold(True)
        for i in range(5):
            item = self.bandsTable.horizontalHeaderItem(i)
            item.setFont(font)

        # Table configuration
        self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.bandsTable.setDragDropOverwriteMode(False)
        self.bandsTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.bandsTable.setDefaultDropAction(Qt.MoveAction)

        if preserve_broadband:
            while self.bandsTable.rowCount() > 1:
                self.bandsTable.removeRow(1)
        else:
            for row in range(self.bandsTable.rowCount()):
                for col in range(self.bandsTable.columnCount()):
                    widget = self.bandsTable.cellWidget(row, col)
                    if widget:
                        widget.deleteLater()
            self.bandsTable.clearContents()
            self.bandsTable.setRowCount(0)
            self._add_broadband_row()

        previous_dict = {band["name"]: band for band in self.previous_bands} if self.previous_bands else {}

        # Default bands
        for band in self.default_bands:
            name = band["name"]
            if name in previous_dict:
                prev_band = previous_dict[name]
                self._add_band_row(name, prev_band["min"], prev_band["max"])
                checkbox = self._get_checkbox_at_row(self.bandsTable.rowCount() - 1)
                if checkbox:
                    checkbox.setChecked(True)
                del previous_dict[name]
            else:
                self._add_band_row(name, band["min"], band["max"])

        # Personalized bands (different from default)
        for name, band in previous_dict.items():
            if name == 'broadband':
                continue
            self._add_band_row(name, band["min"], band["max"])
            checkbox = self._get_checkbox_at_row(self.bandsTable.rowCount() - 1)
            if checkbox:
                checkbox.setChecked(True)

    def _get_checkbox_at_row(self, row):
        container = self.bandsTable.cellWidget(row, 0)
        if container:
            return container.findChild(QtWidgets.QCheckBox)
        return None

    def _add_broadband_row(self):
        row = self.bandsTable.rowCount()
        self.bandsTable.insertRow(row)

        # Enabled
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(True)
        checkbox.setEnabled(True)
        def block_uncheck(state):
            if state == Qt.Unchecked:
                QtWidgets.QMessageBox.warning(self, "Not allowed", "Broadband cannot be disabled.")
                checkbox.setChecked(True)
        checkbox.stateChanged.connect(block_uncheck)

        self.bandsTable.setCellWidget(row, 0, self._center_widget(checkbox))

        # Name - not editable
        name_item = QtWidgets.QTableWidgetItem("broadband")
        name_item.setFlags(Qt.ItemIsEnabled)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{self.min_broad:.1f}")
        min_item.setTextAlignment(Qt.AlignCenter)
        min_item.setFlags(Qt.ItemIsEnabled)
        self.bandsTable.setItem(row, 2, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{self.max_broad:.1f}")
        max_item.setTextAlignment(Qt.AlignCenter)
        max_item.setFlags(Qt.ItemIsEnabled)
        self.bandsTable.setItem(row, 3, max_item)

        # Remove (empty)
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 4, item)

    def _add_band_row(self, name="custom", min_freq=None, max_freq=None):
        row = self.bandsTable.rowCount()
        self.bandsTable.insertRow(row)

        # Enabled
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(False)
        self.bandsTable.setCellWidget(row, 0, self._center_widget(checkbox))

        # Name
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{float(min_freq):.1f}" if min_freq is not None else "")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 2, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{float(max_freq):.1f}" if max_freq is not None else "")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 3, max_item)

        # Remove
        remove_button = QtWidgets.QPushButton()
        icon = QtGui.QIcon("media/delete_icon.png")
        remove_button.setIcon(icon)
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("margin-left:auto; margin-right:auto;")
        remove_button.clicked.connect(lambda _, r=row: self.bandsTable.removeRow(r))
        self.bandsTable.setCellWidget(row, 4, self._center_widget(remove_button))

    def _select_all_bands(self):
        row_count = self.bandsTable.rowCount()
        for row in range(row_count):
            checkbox = self._get_checkbox_at_row(row)
            if checkbox:
                checkbox.setChecked(True)

    def _reset_table(self):
        try:
            self.bandsTable.cellChanged.disconnect(self._handle_cell_change)
        except TypeError:
            pass
        self._setup_table(min_broad=self.default_min, max_broad=self.default_max, preserve_broadband=False)
        self.bandsTable.cellChanged.connect(self._handle_cell_change)

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

    def sync_broadband_range(self, min_val, max_val):
        # Solo actualizamos la primera fila, que es broadband
        self.bandsTable.blockSignals(True)
        self.bandsTable.item(0, 2).setText(f"{min_val:.2f}")
        self.bandsTable.item(0, 3).setText(f"{max_val:.2f}")
        self.bandsTable.blockSignals(False)

    def _handle_cell_change(self, row, column):
        if row == 0 and column in (2, 3):  # Si es broadband y cambiaron min o max
            try:
                min_val = float(self.bandsTable.item(0, 2).text())
                max_val = float(self.bandsTable.item(0, 3).text())
            except ValueError:
                return  # texto inválido

    def _center_widget(self, widget):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        return container

    def _get_broadband_value(self, col):
        item = self.bandsTable.item(0, col)
        if item:
            try:
                return float(item.text())
            except ValueError:
                return self.min_broad if col == 2 else self.max_broad
        return self.min_broad if col == 2 else self.max_broad