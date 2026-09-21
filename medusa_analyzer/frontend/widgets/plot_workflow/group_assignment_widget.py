from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMenu, QScrollArea, QStyledItemDelegate, QStyleOptionViewItem, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)
from medusa_analyzer.frontend.validation import Validation

_target_titles = {"subjects": "Subjects", "recordings": "Files"}
_target_item_names = {"subjects": "subject", "recordings": "file"}
_target_by_analysis_mode = {"within": "recordings", "between": "subjects"}


class _GroupAssignmentDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any) -> None:
        """Pinta con el color del grupo cuando la celda tiene fondo asignado."""
        background = index.data(Qt.ItemDataRole.BackgroundRole)
        if not isinstance(background, QBrush) or background.style() == Qt.BrushStyle.NoBrush:
            super().paint(painter, option, index)
            return

        cell_option = QStyleOptionViewItem(option)
        self.initStyleOption(cell_option, index)
        foreground = index.data(Qt.ItemDataRole.ForegroundRole)

        painter.save()
        painter.fillRect(cell_option.rect, background)
        if isinstance(foreground, QBrush) and foreground.style() != Qt.BrushStyle.NoBrush:
            painter.setPen(foreground.color())
        else:
            painter.setPen(cell_option.palette.text().color())
        text_rect = cell_option.rect.adjusted(7, 0, -7, 0)
        painter.drawText(text_rect, cell_option.displayAlignment | Qt.AlignmentFlag.AlignVCenter, cell_option.text)
        painter.restore()


def _available_items_for_target(state: dict[str, Any], target: str) -> list[str]:
    key = "plot_features_subjects" if target == "subjects" else "plot_features_recordings"
    values = state.get(key)
    return [str(value) for value in values] if isinstance(values, list) else []


def _groups_from_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups = state.get("groups")
    if isinstance(groups, dict):
        return {str(group_id): dict(group) for group_id, group in groups.items() if isinstance(group, dict)}
    return {}


def _item_name_for_table_row(table: QTableWidget, row: int) -> str | None:
    item = table.item(row, 0)
    if item is None:
        return None
    value = item.data(Qt.ItemDataRole.UserRole)
    return str(value) if value is not None else item.text()


def _filter_table_items(table: QTableWidget, text: str) -> None:
    needle = text.lower().strip()
    for row in range(table.rowCount()):
        item_name = _item_name_for_table_row(table, row) or ""
        table.setRowHidden(row, bool(needle) and needle not in item_name.lower())


def _group_color_brush(group: dict[str, Any] | None) -> QBrush:
    """Crea el pincel con el color del grupo para pintar filas asignadas."""
    brush = QBrush()
    if group:
        color = QColor(str(group.get("group_color") or ""))
        if color.isValid():
            brush = QBrush(color)
    return brush


def _group_text_brush(group: dict[str, Any] | None) -> QBrush:
    """Elige texto claro u oscuro para que se lea encima del color del grupo."""
    if not group:
        return QBrush()

    color = QColor(str(group.get("group_color") or ""))
    if not color.isValid():
        return QBrush()

    luminance = _relative_luminance(color)
    return QBrush(QColor("#1F171B" if luminance > 0.179 else "#FFF7FA"))


def _relative_luminance(color: QColor) -> float:
    channels = []
    for component in (color.redF(), color.greenF(), color.blueF()):
        if component <= 0.03928:
            channels.append(component / 12.92)
        else:
            channels.append(((component + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _set_table_row_background(table: QTableWidget, row: int, background: QBrush,
                              foreground: QBrush | None = None) -> None:
    """Aplica el fondo y el texto directamente sobre los items de una fila."""
    for col in range(table.columnCount()):
        table_item = table.item(row, col)
        if table_item is not None:
            table_item.setBackground(background)
            table_item.setForeground(foreground or QBrush())
    table.viewport().update()


def _group_for_item(state: dict[str, Any], target: str, item_name: str | None) -> dict[str, Any] | None:
    if item_name is None:
        return None

    group_item_key = "subjects" if target == "subjects" else "files"
    for group in _groups_from_state(state).values():
        values = group.get(group_item_key)
        if isinstance(values, (list, tuple, set)) and item_name in {str(value) for value in values}:
            return group
    return None


class PlotGroupAssignmentWidget(QScrollArea):
    changed = Signal()

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        del experiment_info, defaults
        super().__init__()

        self.state = state
        self.validation = Validation()
        self.validation_errors: list[str] = []
        self.items: list[str] = []  # guarda elementos que hay que asignar
        self.assignment_by_item: dict[str, str] = {}  # guarda a qué grupo se asigna cada elemento
        self.current_target = "recordings"  # guarda si se están asignando subjects o recordings

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.setWidget(self.content)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(18)

        self.title = QLabel("Group assignment")
        self.title.setObjectName("pageTitle")
        self.description = QLabel("")
        self.description.setObjectName("muted")
        self.description.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.description)

        root.addWidget(self._build_assignment_panel())  # panel principal
        root.addStretch()

        self.on_step_activated()  # lee estado y refresca la pantalla a lo que exista de antes

    def _build_assignment_panel(self) -> QFrame:
        # Bloque de asignación
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        search_row = QHBoxLayout()  # Barra de búsqueda
        search_row.setContentsMargins(0, 0, 0, 0)
        search_label = QLabel("Search")
        search_label.setObjectName("panelTitle")
        self.search_input = QLineEdit()  # Crea el cuadro de búsqueda
        self.search_input.setPlaceholderText("Find items...")  # Texto guía
        self.search_input.setClearButtonEnabled(True)  # Añade 'x' para borrar el texto
        self.search_input.textChanged.connect(
            lambda text: _filter_table_items(self.table, text))  # Oculta filas que no coinciden con la búsqueda
        search_row.addWidget(search_label)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        self.table = QTableWidget()  # Tabla de asignación
        self.table.setProperty("role", "assignment-table")
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Item", "Group"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setItemDelegate(_GroupAssignmentDelegate(self.table))
        layout.addWidget(self.table)

        self.summary_layout = QHBoxLayout()
        self.summary_layout.setContentsMargins(0, 2, 0, 0)
        self.summary_layout.setSpacing(10)
        layout.addLayout(self.summary_layout)

        self.instruction_label = QLabel("")
        self.instruction_label.setObjectName("assignmentInstruction")
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("selectionStatus")
        self.status_label.setProperty("status", "idle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        return panel

    def on_step_activated(self) -> None:
        analysis_mode = str(self.state.get("analysis_mode") or "within")  # modo de análisis
        target = _target_by_analysis_mode[analysis_mode]
        self.current_target = target

        target_title = _target_titles[target]
        item_name = _target_item_names[target]
        self.items = _available_items_for_target(self.state,
                                                 self.current_target)  # Buscamos sujetos o recordings disponibles
        self.description.setText(f"Assign {target_title.lower()} to the groups defined in the previous step.")
        self.instruction_label.setText(f"Select one or more {item_name}s, then right-click to assign them to a group.")
        self.assignment_by_item = self._stored_assignment_for_target(target)  # recupera asignaciones previas
        self._populate_table()  # rellena la tabla
        self._sync(emit_changed=False)

    def _populate_table(self) -> None:
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(self.items))  # tantas filas como elementos existan
            target_title = _target_titles[self.current_target]
            self.table.setHorizontalHeaderLabels([target_title[:-1], "Group"])  # título
            for row, item_name in enumerate(self.items):  # recorremos cada sujeto/recording y su índice de fila
                item = QTableWidgetItem(item_name)  # celda del nombre
                item.setData(Qt.ItemDataRole.UserRole, item_name)
                group_item = QTableWidgetItem("")  # celda del grupo
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, group_item)
                self._render_assignment_for_row(row)  # si el elemento ya tenía el grupo asignado, lo dibuja
        finally:
            self.table.blockSignals(False)
        _filter_table_items(self.table, self.search_input.text())

    def _show_context_menu(self, pos: Any) -> None:
        """Función que maneja el botón derecho"""
        index = self.table.indexAt(pos)  # fila sobre la que se hace click
        if index.isValid() and not self.table.selectionModel().isRowSelected(index.row()):
            self.table.selectRow(index.row())
        # Vemos cuales son todas las filas seleccionadas
        selected_rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not selected_rows:
            return
        groups = _groups_from_state(self.state)
        if not groups:
            return
        menu = QMenu(self)  # creamos menú conceptual
        for group_id, group in groups.items():  # recorremos todos los grupos
            # Añadimos una opción por grupo
            action = menu.addAction(str(group.get("group_name") or group_id))
            action.triggered.connect(
                lambda checked=False, selected_group_id=group_id: self._assign_selected(selected_group_id))
        menu.addSeparator()
        reset_action = menu.addAction("Reset assignment")  # opción de quitar asignación
        reset_action.triggered.connect(lambda checked=False: self._assign_selected(None))
        menu.exec(self.table.viewport().mapToGlobal(pos))  # muestra el menú en la posición del ratón

    def _assign_selected(self, group_id: str | None) -> None:
        for row in sorted({index.row() for index in
                           self.table.selectionModel().selectedRows()}):  # recorremos filas seleccionadas
            # Función para averiguar qué sujeto/archivo corresponde a una fila.
            item = self.table.item(row, 0)
            if item is None:
                continue
            value = item.data(Qt.ItemDataRole.UserRole)
            item_name = str(value) if value is not None else item.text()  # obtiene el sujeto/archivo de esa fila
            if group_id is None:
                self.assignment_by_item.pop(item_name, None)  # elimina la asignación
            else:
                self.assignment_by_item[item_name] = group_id  # guardamos la asignación de cada elemento
            self._render_assignment_for_row(row)  # actualiza visualmente la fila
        self._sync()
        self.table.clearSelection()
        self._render_all_assignments()

    def _render_all_assignments(self) -> None:
        """Repinta todas las filas segun la asignacion guardada en memoria."""
        for row in range(self.table.rowCount()):
            self._render_assignment_for_row(row)

    def _render_assignment_for_row(self, row: int) -> None:
        """Función que dibuja la asignación."""
        # Función para averiguar qué sujeto/archivo corresponde a una fila.
        item = self.table.item(row, 0)
        if item is None:
            return
        value = item.data(Qt.ItemDataRole.UserRole)
        item_name = str(value) if value is not None else item.text()  # obtiene el elemento

        group_id = self.assignment_by_item.get(item_name)  # mira qué grupo tiene asignado
        groups = _groups_from_state(self.state)
        group = groups.get(group_id or "")
        group_name = str(group.get("group_name") or "") if group else ""  # nombre del grupo
        background = _group_color_brush(group)
        foreground = _group_text_brush(group)

        group_item = self.table.item(row, 1)  # obtenemos la celda de la columna group
        if group_item is None:
            group_item = QTableWidgetItem("")
            self.table.setItem(row, 1, group_item)
        group_item.setText(group_name)  # ponemos nombre del grupo
        _set_table_row_background(self.table, row, background, foreground)  # pintamos toda la fila del color del grupo

    def _refresh_assignment_summary(self) -> None:
        """Reconstruye las chips con el numero de elementos asignados a cada grupo."""
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        groups = _groups_from_state(self.state)
        item_name = _target_item_names[self.current_target]
        for group_id, group in groups.items():
            assigned_count = sum(1 for assigned_group_id in self.assignment_by_item.values()
                                 if assigned_group_id == group_id)
            chip = self._build_group_summary_chip(group, assigned_count, item_name)
            self.summary_layout.addWidget(chip)
        self.summary_layout.addStretch()

    def _build_group_summary_chip(self, group: dict[str, Any], assigned_count: int, item_name: str) -> QFrame:
        """Crea una chip coloreada con el contador de elementos asignados."""
        chip = QFrame()
        chip.setProperty("role", "group-assignment-summary-chip")

        color = QColor(str(group.get("group_color") or ""))
        if not color.isValid():
            color = QColor("#3E3036")
        text_color = _group_text_brush({"group_color": color.name()}).color().name()
        border_color = color.darker(120).name()
        chip.setStyleSheet(f"background: {color.name()}; border: 1px solid {border_color}; border-radius: 7px;")

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(f"{group.get('group_name') or 'Group'}: {assigned_count} {item_name}(s)")
        label.setStyleSheet(f"color: {text_color}; font-weight: 700;")
        layout.addWidget(label)
        return chip

    def _sync(self, emit_changed: bool = True) -> None:
        target = self.current_target  # obtiene qué estamos asignando

        groups = _groups_from_state(self.state)
        assignment_by_group = {group_id: [] for group_id in groups}  # dic grupo - elemento
        group_by_item: dict[str, str] = {}  # dic elemento - grupo
        for item_name in self.items:  # recorremos todos los elementos
            group_id = self.assignment_by_item.get(item_name)  # mira su grupo
            if group_id in groups:
                assignment_by_group[group_id].append(item_name)
                group_by_item[item_name] = group_id

        self.assignment_by_item = dict(group_by_item)
        self.state["group_assignment"] = {"target": target,
                                          "items_by_group": assignment_by_group,
                                          "group_by_item": group_by_item}
        self._sync_groups_state(target, assignment_by_group)
        self._render_all_assignments()
        self._refresh_assignment_summary()
        self.validation_errors = self._validate_assignment()
        self._update_status_label()

        if emit_changed:
            self.changed.emit()

    def _sync_groups_state(self, target: str, assignment_by_group: dict[str, list[str]]) -> None:
        groups = _groups_from_state(self.state)
        group_assignment_key = "files" if target == "recordings" else "subjects"
        for group_id, group in groups.items():
            group[group_assignment_key] = list(assignment_by_group.get(group_id) or [])
        self.state["groups"] = groups

    def _validate_assignment(self) -> list[str]:
        target = self.current_target

        errors: list[str] = []
        groups = _groups_from_state(self.state)
        # Comprueba que haya al menos un grupo
        errors.extend(self.validation.validate_many(groups, [("minimum_length", {"minimum": 1,
                                                                                 "item_name": "group",
                                                                                 "action": "contain"})],
                                                    label="Groups"))
        # Comprueba que haya al menos un sujeto o archivo disponible
        errors.extend(self.validation.validate_many(self.items, [("minimum_length", {"minimum": len(groups),
                                                                                     "item_name": _target_item_names[
                                                                                         target],
                                                                                     "action": "contain",
                                                                                     "minimum_text": "the number of groups defined"})],
                                                    label=_target_titles[target]))
        # # Mira si queda algún elemento sin asignar
        # if [item_name for item_name in self.items if item_name not in self.assignment_by_item]:
        #     item_name = _target_item_names[target]
        #     errors.append(f"{_target_titles[target]}: assign every {item_name} before continuing.")
        return errors

    def _update_status_label(self) -> None:
        if self.validation_errors:
            self.status_label.setText(self.validation_errors[0])
            self.status_label.setProperty("status", "error")
        else:
            self.status_label.setText(f"All {_target_item_names[self.current_target]}s assigned.")
            self.status_label.setProperty("status", "ready")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _stored_assignment_for_target(self, target: str) -> dict[str, str]:
        """Función para recuperar asignaciones antiguas."""
        assignment = self.state.get("group_assignment")
        if not isinstance(assignment, dict) or assignment.get("target") != target:
            return {}

        group_by_item = assignment.get("group_by_item")
        if not isinstance(group_by_item, dict):
            return {}

        groups = _groups_from_state(self.state)
        return {str(item): str(group_id) for item, group_id in group_by_item.items()
                if str(item) in self.items and str(group_id) in groups}

    def can_continue(self) -> bool:
        self.validation_errors = self._validate_assignment()
        self._update_status_label()
        return not self.validation_errors


PlotFeaturesGroupAssignmentWidget = PlotGroupAssignmentWidget

__all__ = ["PlotFeaturesGroupAssignmentWidget", "PlotGroupAssignmentWidget"]
