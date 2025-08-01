from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Código para poder arrastras filas
class APBandTableWidget(QtWidgets.QTableWidget):
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

        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        mime_data.setData("application/x-qabstractitemmodeldatalist", b"")
        drag.setMimeData(mime_data)

        # Visual feedback opcional
        drag.exec_(Qt.MoveAction)

    def dropEvent(self, event):
        source_row = self.currentRow()
        dest_index = self.indexAt(event.pos())
        dest_row = dest_index.row()

        if source_row == -1 or dest_row == -1:
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

        # Guardar datos de la fila origen
        row_data = []
        for col in range(self.columnCount()):
            widget = self.cellWidget(source_row, col)
            if widget:
                row_data.append(("widget", widget))
            else:
                item = self.item(source_row, col)
                cloned_item = QtWidgets.QTableWidgetItem(item) if item else None
                row_data.append(("item", cloned_item))

        # Insertar una nueva fila en el destino
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

        # Eliminar fila original (tener en cuenta que se desplazó si está antes)
        if dest_row < source_row:
            self.removeRow(source_row + 1)
        else:
            self.removeRow(source_row)
#-------

class APBandTable(QtWidgets.QDialog):
    def __init__(self, parameters_widget=None):
        super().__init__(parameters_widget)  # <- No le pongas parent Qt real

        self.parameters_widget = parameters_widget  # <- Comunicación lógica
        uic.loadUi("bands_table.ui", self)

        # Reemplazamos el QTableWidget original con el customizado
        original_table = self.findChild(QtWidgets.QTableWidget, "bandsTable")
        self.apbandsTable = APBandTableWidget(self)
        self.apbandsTable.setObjectName("bandsTable")

        # Reemplazar en el layout
        layout = original_table.parent().layout()
        if layout:
            index = layout.indexOf(original_table)
            layout.removeWidget(original_table)
            original_table.deleteLater()
            layout.insertWidget(index, self.apbandsTable)

        self.addButton = self.findChild(QtWidgets.QPushButton, "addButton")
        self.resetButton = self.findChild(QtWidgets.QPushButton, "resetButton")
        self.acceptButton = self.findChild(QtWidgets.QPushButton, "acceptButton")

        self.default_bands = [
            {"name": "Delta", "min": 1, "max": 4},
            {"name": "Theta", "min": 4, "max": 8},
            {"name": "Alpha", "min": 8, "max": 13},
            {"name": "Beta", "min": 13, "max": 30},
            {"name": "Gamma", "min": 30, "max": 70},
        ]

        self.accepted_ap_bands = []
        self._setup_table()
        self.addButton.clicked.connect(self._add_band_row)
        self.resetButton.clicked.connect(self._reset_table)
        self.acceptButton.clicked.connect(self._accept_and_close)

    def _setup_table(self):

        self.apbandsTable.setRowCount(0)
        self.apbandsTable.setColumnCount(5)
        self.apbandsTable.setHorizontalHeaderLabels(["Enabled", "Name", "Min. Freq.", "Max. Freq.", "Remove"])

        # Cabecera en negrita
        font = QFont()
        font.setBold(True)
        for i in range(5):
            item = self.apbandsTable.horizontalHeaderItem(i)
            item.setFont(font)

        # Permitir reordenar filas
        self.apbandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.apbandsTable.setDragDropOverwriteMode(False)
        self.apbandsTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.apbandsTable.setDefaultDropAction(Qt.MoveAction)

        # # Eliminar widgets embebidos de la tabla
        for row in range(self.apbandsTable.rowCount()):
            for col in range(self.apbandsTable.columnCount()):
                widget = self.apbandsTable.cellWidget(row, col)
                if widget:
                    widget.deleteLater()
        self.apbandsTable.clearContents()
        self.apbandsTable.setRowCount(0)

        for band in self.default_bands:
            self._add_band_row(band["name"], band["min"], band["max"])

    def _add_band_row(self, name="custom", min_freq=0.0, max_freq=0.0):
        row = self.apbandsTable.rowCount()
        self.apbandsTable.insertRow(row)

        # Enabled
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(False)
        self.apbandsTable.setCellWidget(row, 0, self._center_widget(checkbox))

        # Name
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.apbandsTable.setItem(row, 1, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{float(min_freq):.1f}")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.apbandsTable.setItem(row, 2, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{float(max_freq):.1f}")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.apbandsTable.setItem(row, 3, max_item)

        # Remove
        remove_button = QtWidgets.QPushButton()
        icon = QtGui.QIcon("../media/delete_icon.png")  # o usa tu propia imagen
        remove_button.setIcon(icon)
        remove_button.setFixedSize(20, 20)
        remove_button.clicked.connect(lambda _, r=row: self.apbandsTable.removeRow(r))
        self.apbandsTable.setCellWidget(row, 4, self._center_widget(remove_button))

    def _reset_table(self):
        # try:
        #     self.apbandsTable.cellChanged.disconnect()
        # except TypeError:
        #     pass
        self._setup_table()
        # self.apbandsTable.cellChanged.connect()

    def _accept_and_close(self):
        self.accepted_ap_bands = []
        empty_name_rows = []
        zero_max_rows = []
        zero_min_rows = []
        invalid_value_rows = []
        negative_value_rows = []
        invalid_interval_rows = []
        out_of_range_rows = []

        for row in range(self.apbandsTable.rowCount()):
            checkbox_container = self.apbandsTable.cellWidget(row, 0)
            if not checkbox_container:
                continue
            checkbox = checkbox_container.findChild(QtWidgets.QCheckBox)
            if not checkbox or not checkbox.isChecked():
                continue

            name_item = self.apbandsTable.item(row, 1)
            min_item = self.apbandsTable.item(row, 2)
            max_item = self.apbandsTable.item(row, 3)

            name = name_item.text().strip() if name_item else ""
            min_text = min_item.text().strip() if min_item else ""
            max_text = max_item.text().strip() if max_item else ""

            row_num = row + 1

            if not name or not min_text or not max_text:
                empty_name_rows.append(row_num)
            try:
                min_val = float(min_text)
                max_val = float(max_text)
            except ValueError:
                invalid_value_rows.append(row_num)
                continue

            if min_val < 0 or max_val < 0: # negative frequencies
                negative_value_rows.append(row_num)

            if max_val >= 0 and max_val < 0.2: # max_values below its low limit
                zero_max_rows.append(row_num)

            if min_val >= 0 and min_val < 0.1: # min_values below its low limit
                zero_min_rows.append(row_num)

            if min_val >= max_val: # max_value is lower than min_value
                invalid_interval_rows.append(row_num)

            current_min = self.parameters_widget.minbroadBox.value()
            current_max = self.parameters_widget.maxbroadBox.value()
            if min_val < current_min or max_val > current_max: #exceding broadband range
                out_of_range_rows.append(row_num)

            if (row_num not in empty_name_rows and
                    row_num not in zero_max_rows and
                    row_num not in zero_min_rows and
                    row_num not in invalid_value_rows and
                    row_num not in negative_value_rows and
                    row_num not in invalid_interval_rows and
                    row_num not in out_of_range_rows):

                self.accepted_ap_bands.append({
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
                message += f"• Row(s) {', '.join(map(str, out_of_range_rows))}: frequency range must be within the broadband range ({current_min:.1f}–{current_max:.1f} Hz).\n"

            message += "\nCorrect the above issues and try again."
            QtWidgets.QMessageBox.warning(self, "Invalid Table Entries", message)
            return

        if self.parameters_widget:
            self.parameters_widget.update_band_ap_label(self.accepted_ap_bands)
        self.close()

    def _center_widget(self, widget):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        return container


