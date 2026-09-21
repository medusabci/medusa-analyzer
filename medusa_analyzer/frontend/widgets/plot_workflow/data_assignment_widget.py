from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .group_assignment_widget import (_available_items_for_target, _filter_table_items, _item_name_for_table_row,
    _target_item_names, _target_titles)
from medusa_analyzer.frontend.validation import Validation

class PlotDataAssignmentWidget(QScrollArea):
    changed = Signal()

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        del experiment_info, defaults
        super().__init__()

        self.state = state
        self.validation = Validation()
        self.validation_errors: list[str] = []
        self.items: list[str] = []
        self.current_target = "recordings"

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.setWidget(self.content)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(18)

        self.title = QLabel("Data assignment")
        self.title.setObjectName("pageTitle")
        self.description = QLabel("")
        self.description.setObjectName("muted")
        self.description.setWordWrap(True)
        root.addWidget(self.title)
        root.addWidget(self.description)

        root.addWidget(self._build_selection_panel())
        root.addStretch()

        self._refresh_from_state()

    def _build_selection_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        search_label = QLabel("Search")
        search_label.setObjectName("panelTitle")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find items...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda text: _filter_table_items(self.table, text))
        select_all_button = QPushButton("Select all")
        select_all_button.setProperty("variant", "secondary")
        select_all_button.clicked.connect(self.table_select_all)
        clear_selection_button = QPushButton("Clear")
        clear_selection_button.setProperty("variant", "ghost")
        clear_selection_button.clicked.connect(self.table_clear_selection)
        actions.addWidget(search_label)
        actions.addWidget(self.search_input, 1)
        actions.addWidget(select_all_button)
        actions.addWidget(clear_selection_button)
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setProperty("role", "assignment-table")
        self.table.setColumnCount(1)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._sync)
        layout.addWidget(self.table)

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

    def _refresh_from_state(self) -> None:

        """Actualiza la pantalla según toodo lo que haya en el state"""
        analysis_mode = str(self.state.get("analysis_mode") or "within")
        self.current_target = "subjects" if analysis_mode == "within" else "recordings"
        target_title = _target_titles[self.current_target]
        item_name = _target_item_names[self.current_target]
        self.items = _available_items_for_target(self.state, self.current_target)
        self.description.setText(f"Select the {target_title.lower()} to include in the analysis.")
        self.instruction_label.setText(f"Select one or more {item_name}s to include.")
        self._populate_table()
        self._restore_selection()
        self._sync(emit_changed=False)

    def _populate_table(self) -> None:
        """Rellena la tabla"""
        self.table.blockSignals(True)
        try:
            self.table.clearSelection()
            self.table.setRowCount(len(self.items))
            self.table.setHorizontalHeaderLabels([_target_titles[self.current_target][:-1]])
            for row, item_name in enumerate(self.items):
                item = QTableWidgetItem(item_name)
                item.setData(Qt.ItemDataRole.UserRole, item_name)
                self.table.setItem(row, 0, item)
        finally:
            self.table.blockSignals(False)
        _filter_table_items(self.table, self.search_input.text())

    def _restore_selection(self) -> None:
        """Recupera una selección anterior"""
        stored_selection = self._stored_selection_for_target()
        if not stored_selection:
            return

        self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                item_name = _item_name_for_table_row(self.table, row)
                if item_name in stored_selection:
                    self.table.selectRow(row)
        finally:
            self.table.blockSignals(False)

    def table_select_all(self) -> None:
        self.table.selectAll()
        self._sync()

    def table_clear_selection(self) -> None:
        self.table.clearSelection()
        self._sync()

    def _sync(self, *_: Any, emit_changed: bool = True) -> None:
        selected_items = self._selected_items()
        self.state["data_assignment"] = {"target": self.current_target,
            "selected_items": selected_items}
        if self.current_target == "subjects":
            self.state["plot_selected_subjects"] = selected_items
        else:
            self.state["plot_selected_recordings"] = selected_items

        self.validation_errors = self._validate_selection(selected_items)
        self._update_status_label(selected_items)
        if emit_changed:
            self.changed.emit()

    def _validate_selection(self, selected_items: list[str]) -> list[str]:
        errors: list[str] = []
        item_name = _target_item_names[self.current_target]
        errors.extend(self.validation.validate_many(self.items, [("minimum_length", {"minimum": 1,
            "item_name": item_name, "action": "contain"})], label=_target_titles[self.current_target]))
        errors.extend(self.validation.validate_many(selected_items, [("minimum_length", {"minimum": 1,
            "item_name": item_name, "action": "select"})], label=_target_titles[self.current_target]))
        return errors

    def _update_status_label(self, selected_items: list[str]) -> None:
        if self.validation_errors:
            self.status_label.setText(self.validation_errors[0])
            self.status_label.setProperty("status", "error")
        else:
            self.status_label.setText(f"{len(selected_items)} {_target_item_names[self.current_target]}(s) selected.")
            self.status_label.setProperty("status", "ready")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _selected_items(self) -> list[str]:
        selected_items: list[str] = []
        for index in self.table.selectionModel().selectedRows():
            item_name = _item_name_for_table_row(self.table, index.row())
            if item_name:
                selected_items.append(item_name)
        return selected_items

    def _stored_selection_for_target(self) -> set[str]:
        data_assignment = self.state.get("data_assignment")
        if isinstance(data_assignment, dict) and data_assignment.get("target") == self.current_target:
            selected_items = data_assignment.get("selected_items")
            if isinstance(selected_items, list):
                return {str(item) for item in selected_items if str(item) in self.items}
        return set()

    def on_step_activated(self) -> None:
        self._refresh_from_state()

    def can_continue(self) -> bool:
        selected_items = self._selected_items()
        self.validation_errors = self._validate_selection(selected_items)
        self._update_status_label(selected_items)
        return not self.validation_errors


PlotFeaturesDataAssignmentWidget = PlotDataAssignmentWidget

__all__ = ["PlotDataAssignmentWidget", "PlotFeaturesDataAssignmentWidget"]
