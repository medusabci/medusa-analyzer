class BandTable(QtWidgets.QWidget):
    def __init__(self, parent=None, min_broad=0.5, max_broad=69.0): # Aquí voy a tener que modificar para que salga el que viene en broadband.
        super().__init__(parent)
        uic.loadUi("bands_table.ui", self)

        # Reemplazamos el QTableWidget original con el customizado
        original_table = self.findChild(QtWidgets.QTableWidget, "bandsTable")
        self.bandsTable = BandTableWidget(self)
        self.bandsTable.setObjectName("bandsTable")

        # Reemplazar en el layout
        layout = original_table.parent().layout()
        if layout:
            index = layout.indexOf(original_table)
            layout.removeWidget(original_table)
            original_table.deleteLater()
            layout.insertWidget(index, self.bandsTable)

        # self.bandsTable = self.findChild(QtWidgets.QTableWidget, "bandsTable")
        self.addButton = self.findChild(QtWidgets.QPushButton, "addButton")
        self.resetButton = self.findChild(QtWidgets.QPushButton, "resetButton")
        self.acceptButton = self.findChild(QtWidgets.QPushButton, "acceptButton")

        self.min_broad = min_broad
        self.max_broad = max_broad
        self.default_bands = [
            {"name": "Delta", "min": 1, "max": 4},
            {"name": "Theta", "min": 4, "max": 8},
            {"name": "Alpha", "min": 8, "max": 13},
            {"name": "Beta", "min": 13, "max": 30},
            {"name": "Gamma", "min": 30, "max": 70},
        ]

        self.accepted_bands = []

        self._setup_table()
        self.addButton.clicked.connect(self._add_band_row)
        self.resetButton.clicked.connect(self._reset_table)
        self.acceptButton.clicked.connect(self._accept_and_close)
        self.bandsTable.cellChanged.connect(self._handle_cell_change)

    def _setup_table(self, min_broad=None, max_broad=None):
        if min_broad is not None:
            self.min_broad = min_broad
        if max_broad is not None:
            self.max_broad = max_broad

        # Eliminar widgets embebidos de la tabla
        for row in range(self.bandsTable.rowCount()):
            for col in range(self.bandsTable.columnCount()):
                widget = self.bandsTable.cellWidget(row, col)
                if widget:
                    widget.deleteLater()

        self.bandsTable.clearContents()
        self.bandsTable.setRowCount(0)
        self.bandsTable.setColumnCount(5)
        self.bandsTable.setHorizontalHeaderLabels(["Enabled", "Name", "Min. Freq.", "Max. Freq.", "Remove"])
        # Estilo de cabecera en negrita
        font = QFont()
        font.setBold(True)
        for i in range(5):
            item = self.bandsTable.horizontalHeaderItem(i)
            item.setFont(font)

        # Permitir reordenar filas (salvo la primera)
        self.bandsTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.bandsTable.setDragDropOverwriteMode(False)
        self.bandsTable.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.bandsTable.setDefaultDropAction(Qt.MoveAction)

        self._add_broadband_row()
        for band in self.default_bands:
            self._add_band_row(band["name"], band["min"], band["max"])

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
        # self.bandsTable.setCellWidget(row, 0, checkbox)

        # Name - not editable
        name_item = QtWidgets.QTableWidgetItem("Broadband")
        name_item.setFlags(Qt.ItemIsEnabled)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{self.min_broad:.1f}")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 2, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{self.max_broad:.1f}")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 3, max_item)

        # Remove (empty)
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 4, item)

    def _add_band_row(self, name="custom", min_freq=0.5, max_freq=0.0):
        row = self.bandsTable.rowCount()
        self.bandsTable.insertRow(row)

        # Enabled
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(True)
        self.bandsTable.setCellWidget(row, 0, self._center_widget(checkbox))
        # self.bandsTable.setCellWidget(row, 0, checkbox)

        # Name
        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 1, name_item)

        # Min freq
        min_item = QtWidgets.QTableWidgetItem(f"{float(min_freq):.1f}")
        min_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 2, min_item)

        # Max freq
        max_item = QtWidgets.QTableWidgetItem(f"{float(max_freq):.1f}")
        max_item.setTextAlignment(Qt.AlignCenter)
        self.bandsTable.setItem(row, 3, max_item)

        # Remove
        remove_button = QtWidgets.QPushButton()
        icon = QtGui.QIcon("media/delete_icon.png")  # o usa tu propia imagen
        remove_button.setIcon(icon)
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("margin-left:auto; margin-right:auto;")
        # remove_button.clicked.connect(lambda: self.bandsTable.removeRow(row))
        remove_button.clicked.connect(lambda _, r=row: self.bandsTable.removeRow(r))
        self.bandsTable.setCellWidget(row, 4, self._center_widget(remove_button))
        # self.bandsTable.setCellWidget(row, 4, remove_button)

    def _reset_table(self):
        try:
            self.bandsTable.cellChanged.disconnect(self._handle_cell_change)
        except TypeError:
            pass  # ya estaba desconectada

        # Obtener valores actuales de Broadband antes de resetear
        current_min_broad = self._get_broadband_value(col=2)
        current_max_broad = self._get_broadband_value(col=3)

        # Usar esos valores en la reconstrucción
        self._setup_table(current_min_broad, current_max_broad)

    def _accept_and_close(self):
        self.accepted_bands = []
        empty_name_rows = []
        zero_max_rows = []
        invalid_value_rows = []
        negative_value_rows = []

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

            if min_val < 0 or max_val < 0:
                negative_value_rows.append(row + 1)

            if max_val == 0:
                zero_max_rows.append(row + 1)

            if (row + 1 not in empty_name_rows and
                    row + 1 not in zero_max_rows and
                    row + 1 not in invalid_value_rows and
                    row + 1 not in negative_value_rows):
                self.accepted_bands.append({
                    "name": name,
                    "min": min_val,
                    "max": max_val
                })

        if empty_name_rows or zero_max_rows or invalid_value_rows or negative_value_rows:
            message = "The following rows contain errors and need to be corrected before proceeding:\n\n"

            if empty_name_rows:
                message += f"• Rows with empty name, minimum or maximum frequency: {', '.join(map(str, empty_name_rows))}\n"
            if zero_max_rows:
                message += f"• Rows where the maximum frequency is 0 (must be greater than 0): {', '.join(map(str, zero_max_rows))}\n"
            if invalid_value_rows:
                message += f"• Rows with non-numeric frequency values: {', '.join(map(str, invalid_value_rows))}\n"
            if negative_value_rows:
                message += f"• Rows with negative frequency values (not allowed): {', '.join(map(str, negative_value_rows))}\n"

            message += "\nPlease correct these issues and try again."
            QtWidgets.QMessageBox.warning(self, "Table Input Errors", message)
            return

        if self.parent():
            self.parent().update_band_label(self.accepted_bands)
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
            # Actualizar en el parent (ParametersWidget)
            if self.parent():
                self.parent().update_broadband_spinboxes(min_val, max_val)

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