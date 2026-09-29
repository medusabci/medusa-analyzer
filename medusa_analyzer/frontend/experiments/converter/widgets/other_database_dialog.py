from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import (QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QLayout, QLineEdit, QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from medusa_analyzer.backend.converter.other_database import (BIDS_ENTITY_ORDER, ConversionContext,
    SUPPORTED_EXTENSIONS, apply_other_database_mapping, preview_other_database_mapping, scan_other_database)
from medusa_analyzer.frontend.window_theme import apply_windows_title_bar_theme
from medusa_analyzer.frontend.worker import TaskRunner, Worker
from medusa_analyzer.frontend.widgets.progress_overlay import ProgressOverlay


class FlowLayout(QLayout):
    """Small wrapping layout used for token chips."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + spacing
            if next_x - spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y += line_height + spacing
                next_x = x + item_size.width() + spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + bottom


class OtherDatabaseMappingDialog(QDialog):
    """Dialog for mapping a homogeneous non-BIDS EEG/MEG database from one representative record."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Other DB")
        self.resize(1080, 760)

        self.root_path: str = ""
        self.sample_record_path: str = ""
        self.scan_result: ConversionContext | None = None
        self.conversion_context: ConversionContext | None = None
        self.validation_result: dict[str, Any] | None = None
        self.accepted_payload: dict[str, Any] | None = None
        self.tokens: list[dict[str, Any]] = []
        self.custom_token_counter = 0
        self.assignments: dict[str, list[str]] = {entity: [] for entity in BIDS_ENTITY_ORDER}
        self.entity_chip_layouts: dict[str, FlowLayout] = {}
        self.entity_clear_buttons: dict[str, QPushButton] = {}
        self.token_flow: FlowLayout | None = None
        self.runner = TaskRunner()
        self.scan_running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Load Other DB")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Select the database folder and one representative recording. Tokens from that recording define the mapping used for the whole homogeneous database.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.source_panel = self._build_source_panel()
        self.inspect_panel = self._build_inspect_panel()
        self.mapping_panel = self._build_mapping_panel()
        self.preview_panel = self._build_preview_panel()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)
        scroll_layout.addWidget(self.source_panel)
        scroll_layout.addWidget(self.inspect_panel)
        scroll_layout.addWidget(self.mapping_panel)
        scroll_layout.addWidget(self.preview_panel)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        root.addWidget(scroll_area, 1)

        actions = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setProperty("variant", "ghost")
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton("Use Mapping")
        self.apply_button.setProperty("variant", "primary")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._accept_mapping)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.apply_button)
        root.addLayout(actions)

        self.overlay = ProgressOverlay(self)
        self.inspect_panel.setEnabled(False)
        self.mapping_panel.setEnabled(False)
        self.preview_panel.setEnabled(False)

    def showEvent(self, event):
        super().showEvent(event)
        apply_windows_title_bar_theme(self)

    def reject(self) -> None:
        if self.scan_running:
            return
        super().reject()

    def _build_source_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        heading = QLabel("Select database and representative record")
        heading.setObjectName("panelTitle")
        self.root_display = QLineEdit()
        self.root_display.setReadOnly(True)
        self.record_display = QLineEdit()
        self.record_display.setReadOnly(True)

        browse_root_button = QPushButton("Browse DB")
        browse_root_button.setProperty("variant", "secondary")
        browse_root_button.clicked.connect(self._select_root_folder)
        self.browse_record_button = QPushButton("Browse Record")
        self.browse_record_button.setProperty("variant", "secondary")
        self.browse_record_button.setEnabled(False)
        self.browse_record_button.clicked.connect(self._select_sample_record)

        layout.addWidget(heading, 0, 0, 1, 3)
        layout.addWidget(QLabel("Database root:"), 1, 0)
        layout.addWidget(self.root_display, 1, 1)
        layout.addWidget(browse_root_button, 1, 2)
        layout.addWidget(QLabel("Representative record:"), 2, 0)
        layout.addWidget(self.record_display, 2, 1)
        layout.addWidget(self.browse_record_button, 2, 2)
        layout.setColumnStretch(1, 1)
        return panel

    def _build_inspect_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(10)

        heading = QLabel("Inspect selected record")
        heading.setObjectName("panelTitle")
        self.scan_summary = QLabel("Select a database folder and a representative record.")
        self.scan_summary.setObjectName("muted")
        self.scan_summary.setWordWrap(True)

        top = QHBoxLayout()
        token_heading = QLabel("Detected and custom tokens")
        token_heading.setObjectName("subgroupTitle")
        self.add_token_button = QPushButton("Add New Token")
        self.add_token_button.setProperty("variant", "secondary")
        self.add_token_button.setToolTip("Create a constant token that is not read from the path.")
        self.add_token_button.clicked.connect(self._add_custom_token)
        top.addWidget(token_heading)
        top.addStretch()
        top.addWidget(self.add_token_button)

        self.token_container = QWidget()
        self.token_container.setProperty("role", "token-chip-area")
        self.token_flow = FlowLayout(self.token_container, spacing=8)
        self.token_container.setMinimumHeight(92)

        layout.addWidget(heading, 0, 0)
        layout.addWidget(self.scan_summary, 1, 0)
        layout.addLayout(top, 2, 0)
        layout.addWidget(self.token_container, 3, 0)
        return panel

    def _build_mapping_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        heading = QLabel("Map tokens to BIDS")
        heading.setObjectName("panelTitle")
        hint = QLabel("Right-click a token chip to assign it to a BIDS field. sub and task are required; ses, acq and run can stay empty.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(hint)

        required_entities = {"sub", "task"}
        for entity in BIDS_ENTITY_ORDER:
            row = QFrame()
            row.setProperty("role", "mapping-entity-row")
            row_layout = QGridLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setHorizontalSpacing(10)
            row_layout.setVerticalSpacing(8)

            entity_label = QLabel(entity)
            entity_label.setObjectName("mappingEntityName")
            required_label = QLabel("Required" if entity in required_entities else "Optional")
            required_label.setProperty("role", "entity-badge")
            required_label.setProperty("required", "true" if entity in required_entities else "false")

            chip_area = QWidget()
            chip_area.setProperty("role", "entity-chip-area")
            chip_layout = FlowLayout(chip_area, spacing=6)
            self.entity_chip_layouts[entity] = chip_layout

            clear_button = QPushButton("Clear")
            clear_button.setProperty("variant", "ghost")
            clear_button.setToolTip(f"Clear {entity}")
            clear_button.clicked.connect(lambda _checked=False, current_entity=entity: self._clear_entity(current_entity))
            clear_button.setVisible(entity not in required_entities)
            self.entity_clear_buttons[entity] = clear_button

            row_layout.addWidget(entity_label, 0, 0)
            row_layout.addWidget(required_label, 0, 1)
            row_layout.addWidget(chip_area, 0, 2)
            row_layout.addWidget(clear_button, 0, 3)
            row_layout.setColumnStretch(2, 1)
            layout.addWidget(row)

        return panel

    def _build_preview_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        heading = QLabel("Preview and validation")
        heading.setObjectName("panelTitle")
        validate_button = QPushButton("Validate")
        validate_button.setProperty("variant", "secondary")
        validate_button.clicked.connect(self._refresh_preview)
        top.addWidget(heading)
        top.addStretch()
        top.addWidget(validate_button)

        self.validation_status = QLabel("Map the required entities to preview BIDS names.")
        self.validation_status.setObjectName("selectionStatus")
        self.validation_status.setProperty("status", "idle")
        self.validation_status.setWordWrap(True)

        self.conversion_summary = self._build_conversion_summary()

        self.preview_table = QTableWidget(0, 8)
        self.preview_table.setProperty("role", "assignment-table")
        self.preview_table.setHorizontalHeaderLabels([
            "Source", "sub", "ses", "task", "acq", "run", "BIDS path", "Issue",
        ])
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setAlternatingRowColors(False)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4, 5, 7):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        layout.addLayout(top)
        layout.addWidget(self.validation_status)
        layout.addWidget(self.conversion_summary)
        layout.addWidget(self.preview_table, 1)
        return panel

    def _build_conversion_summary(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "conversion-summary")
        layout = QGridLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(7)

        self.summary_source_value = QLabel("-")
        self.summary_bids_value = QLabel("-")
        self.summary_target_value = QLabel("-")
        for row, (label, value_label) in enumerate((
            ("Original path", self.summary_source_value),
            ("BIDS basename", self.summary_bids_value),
            ("Converted path", self.summary_target_value),
        )):
            title = QLabel(label)
            title.setProperty("role", "conversion-step-title")
            value_label.setProperty("role", "conversion-step-value")
            value_label.setWordWrap(True)
            layout.addWidget(title, row, 0)
            layout.addWidget(value_label, row, 1)
        layout.setColumnStretch(1, 1)
        return panel

    def _select_root_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Other DB root folder", "")
        if not folder:
            return
        self.root_path = folder
        self.root_display.setText(folder)
        self.sample_record_path = ""
        self.record_display.clear()
        self.scan_result = None
        self.conversion_context = None
        self.validation_result = None
        self._reset_tokens()
        self.preview_table.setRowCount(0)
        self._populate_conversion_summary(None)
        self.inspect_panel.setEnabled(False)
        self.mapping_panel.setEnabled(False)
        self.preview_panel.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.browse_record_button.setEnabled(True)
        self._set_validation_status("Select a representative record inside the database folder.", "idle")

    def _select_sample_record(self) -> None:
        if not self.root_path:
            return
        paths, _ = QFileDialog.getOpenFileName(
            self,
            "Select representative recording",
            self.root_path,
            self._record_dialog_filter(),
        )
        if not paths:
            return
        self.sample_record_path = paths
        self.record_display.setText(paths)
        self._start_sample_record_scan(paths)

    def _start_sample_record_scan(self, record_path: str) -> None:
        self.scan_running = True
        self._set_scan_controls_enabled(False)
        self.scan_result = None
        self.conversion_context = None
        self.validation_result = None
        self._reset_tokens()
        self.preview_table.setRowCount(0)
        self._populate_conversion_summary(None)
        self.inspect_panel.setEnabled(False)
        self.mapping_panel.setEnabled(False)
        self.preview_panel.setEnabled(False)
        self.apply_button.setEnabled(False)
        self._set_validation_status("Inspecting representative record...", "idle")

        self.overlay.start_process("Inspecting representative record and scanning matching files...")
        worker = Worker(scan_other_database, self.root_path, record_path)
        worker.signals.progress.connect(self.overlay.progress.setValue)
        worker.signals.logging.connect(self.overlay.add_log_message)
        worker.signals.result.connect(self._scan_loaded)
        worker.signals.error.connect(self._scan_failed)
        worker.signals.finished.connect(self._scan_finished)
        self.runner.start(worker)

    def _scan_failed(self, error: str) -> None:
        self.overlay.hide()
        QMessageBox.critical(self, "Unable to inspect record", error.splitlines()[0])
        self.record_display.clear()
        self.sample_record_path = ""
        self._set_validation_status("Select a representative record inside the database folder.", "idle")

    def _scan_finished(self) -> None:
        self.scan_running = False
        self._set_scan_controls_enabled(True)
        if self.overlay.isVisible():
            self.overlay.hide()

    def _set_scan_controls_enabled(self, enabled: bool) -> None:
        self.cancel_button.setEnabled(enabled)
        self.browse_record_button.setEnabled(enabled and bool(self.root_path))

    def _record_dialog_filter(self) -> str:
        patterns = " ".join(f"*{extension}" for extension in SUPPORTED_EXTENSIONS)
        return f"Known recordings ({patterns});;All files (*.*)"

    def _scan_loaded(self, scan_result: ConversionContext) -> None:
        self.scan_result = scan_result
        self.conversion_context = None
        self.validation_result = None
        self._populate_scan(scan_result)
        self.inspect_panel.setEnabled(True)
        self.mapping_panel.setEnabled(True)
        self.preview_panel.setEnabled(True)
        self._refresh_preview()

    def _populate_scan(self, scan_result: ConversionContext) -> None:
        sample = scan_result.sample_record
        self.scan_summary.setText(
            f"Only files with extension '{scan_result.target_extension}' will be processed.\n"
            f"Representative record: {sample.source_relative_path if sample else ''}"
        )

        self._reset_tokens()
        for token_index, token in enumerate(sample.tokens if sample else []):
            self.tokens.append({
                "id": f"path_{token_index}",
                "text": str(token),
                "source_index": token_index,
                "custom": False,
            })
        self._refresh_token_views()

    def _current_mapping(self) -> dict[str, dict[str, Any]] | None:
        mapping: dict[str, dict[str, Any]] = {}
        token_by_id = self._token_by_id()
        for entity in BIDS_ENTITY_ORDER:
            parts = []
            indices = []
            for token_id in self.assignments.get(entity, []):
                token = token_by_id.get(token_id)
                if not token:
                    continue
                if token.get("custom"):
                    parts.append({"source": "literal", "value": token["text"]})
                else:
                    source_index = int(token["source_index"])
                    indices.append(source_index)
                    parts.append({"source": "path", "index": source_index})
            mapping[entity] = {
                "indices": indices,
                "value": "",
                "parts": parts,
            }
        return mapping

    def _refresh_preview(self) -> None:
        if not self.scan_result:
            self.preview_table.setRowCount(0)
            self._populate_conversion_summary(None)
            self.apply_button.setEnabled(False)
            self.conversion_context = None
            return

        mapping = self._current_mapping()
        if mapping is None:
            return

        self.conversion_context = apply_other_database_mapping(self.scan_result, mapping)
        self.validation_result = preview_other_database_mapping(self.conversion_context, limit=40)
        self._populate_preview_table(self.validation_result["rows"])
        first_row = self.validation_result["rows"][0] if self.validation_result["rows"] else None
        self._populate_conversion_summary(first_row)

        if self.validation_result["valid"]:
            warnings = list(self.conversion_context.warnings if self.conversion_context else [])
            text = "Mapping valid."
            if warnings:
                text += " " + warnings[0]
            self._set_validation_status(text, "ready")
            self.apply_button.setEnabled(True)
        else:
            errors = self.validation_result.get("errors", [])
            self._set_validation_status(errors[0] if errors else "Mapping is not valid.", "error")
            self.apply_button.setEnabled(False)

    def _populate_preview_table(self, rows: list[dict[str, Any]]) -> None:
        self.preview_table.setRowCount(0)
        self.preview_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            entities = row.get("entities", {})
            values = [
                row.get("source_relative_path", ""),
                entities.get("sub", ""),
                entities.get("ses", ""),
                entities.get("task", ""),
                entities.get("acq", ""),
                entities.get("run", ""),
                row.get("target_relative_path", ""),
                "; ".join(row.get("issues", [])),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row_index, column, item)

    def _populate_conversion_summary(self, row: dict[str, Any] | None) -> None:
        if not row:
            self.summary_source_value.setText("-")
            self.summary_bids_value.setText("-")
            self.summary_target_value.setText("-")
            return
        self.summary_source_value.setText(row.get("source_relative_path") or "-")
        self.summary_bids_value.setText(row.get("bids_name") or self._format_entity_values(row.get("entities", {})))
        self.summary_target_value.setText(row.get("target_relative_path") or "-")

    def _format_entity_values(self, entities: dict[str, str]) -> str:
        values = [f"{entity}-{entities[entity]}" for entity in BIDS_ENTITY_ORDER if entities.get(entity)]
        return " / ".join(values) if values else "-"

    def _reset_tokens(self) -> None:
        self.tokens = []
        self.custom_token_counter = 0
        self.assignments = {entity: [] for entity in BIDS_ENTITY_ORDER}
        self._refresh_token_views()

    def _refresh_token_views(self) -> None:
        self._cleanup_assignments()
        self._refresh_token_chips()
        self._refresh_entity_chips()
        self._refresh_preview()

    def _cleanup_assignments(self) -> None:
        known_ids = {token["id"] for token in self.tokens}
        for entity in BIDS_ENTITY_ORDER:
            self.assignments[entity] = [token_id for token_id in self.assignments.get(entity, []) if token_id in known_ids]

    def _refresh_token_chips(self) -> None:
        if self.token_flow is None:
            return
        self._clear_layout(self.token_flow)
        if not self.tokens:
            empty = QLabel("No tokens loaded.")
            empty.setObjectName("muted")
            self.token_flow.addWidget(empty)
            return
        for token in self.tokens:
            self.token_flow.addWidget(self._build_token_chip(token))

    def _build_token_chip(self, token: dict[str, Any]) -> QFrame:
        chip = QFrame()
        chip.setProperty("role", "mapping-token-chip")
        chip.setProperty("custom", "true" if token.get("custom") else "false")
        chip.setProperty("assigned", "true" if self._assigned_entity_for_token(token["id"]) else "false")
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        chip.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        chip.setToolTip("Right-click to assign this token to sub, task, ses, acq or run.")
        chip.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        chip.customContextMenuRequested.connect(
            lambda position, token_id=token["id"], widget=chip: self._show_token_menu(token_id, widget.mapToGlobal(position))
        )

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        prefix = "custom" if token.get("custom") else f"#{token['source_index']}"
        prefix_label = QLabel(prefix)
        prefix_label.setProperty("role", "token-prefix")
        text_label = QLabel(token["text"])
        text_label.setProperty("role", "token-text")
        text_label.setWordWrap(True)
        text_label.setMaximumWidth(240)
        assigned_entity = self._assigned_entity_for_token(token["id"])
        state_label = QLabel(assigned_entity or "unassigned")
        state_label.setProperty("role", "token-state")
        state_label.setProperty("assigned", "true" if assigned_entity else "false")

        layout.addWidget(prefix_label)
        layout.addWidget(text_label)
        layout.addWidget(state_label)

        if token.get("custom"):
            remove_button = QPushButton("x")
            remove_button.setObjectName("chipRemoveButton")
            remove_button.setProperty("role", "chip-remove-button")
            remove_button.setFixedSize(18, 18)
            remove_button.setToolTip(f"Delete {token['text']}")
            remove_button.clicked.connect(lambda _checked=False, token_id=token["id"]: self._delete_custom_token(token_id))
            layout.addWidget(remove_button)

        return chip

    def _refresh_entity_chips(self) -> None:
        token_by_id = self._token_by_id()
        for entity, layout in self.entity_chip_layouts.items():
            self._clear_layout(layout)
            assigned_tokens = [token_by_id[token_id] for token_id in self.assignments.get(entity, []) if token_id in token_by_id]
            if not assigned_tokens:
                empty = QLabel("No tokens")
                empty.setObjectName("muted")
                layout.addWidget(empty)
            else:
                for token in assigned_tokens:
                    layout.addWidget(self._build_assignment_chip(entity, token))
            clear_button = self.entity_clear_buttons.get(entity)
            if clear_button is not None:
                clear_button.setVisible(entity not in {"sub", "task"} and bool(assigned_tokens))

    def _build_assignment_chip(self, entity: str, token: dict[str, Any]) -> QFrame:
        chip = QFrame()
        chip.setProperty("role", "mapping-assignment-chip")
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        chip.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        chip.setToolTip(f"Assigned to {entity}. Use x to remove this assignment.")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(9, 4, 6, 4)
        layout.setSpacing(5)

        label = QLabel(token["text"])
        label.setWordWrap(True)
        label.setMaximumWidth(220)
        layout.addWidget(label)

        remove_button = QPushButton("x")
        remove_button.setObjectName("chipRemoveButton")
        remove_button.setProperty("role", "chip-remove-button")
        remove_button.setFixedSize(16, 16)
        remove_button.setToolTip(f"Remove from {entity}")
        remove_button.clicked.connect(lambda _checked=False, current_entity=entity, token_id=token["id"]: self._unassign_token(current_entity, token_id))
        layout.addWidget(remove_button)
        return chip

    def _show_token_menu(self, token_id: str, global_position: QPoint) -> None:
        token = self._token_by_id().get(token_id)
        if not token:
            return

        menu = QMenu(self)
        current_entity = self._assigned_entity_for_token(token_id)
        for entity in BIDS_ENTITY_ORDER:
            label = f"Assign to {entity}"
            if entity in {"sub", "task"}:
                label += " (required)"
            action = QAction(label, menu)
            action.setCheckable(True)
            action.setChecked(current_entity == entity)
            action.triggered.connect(lambda _checked=False, target_entity=entity: self._assign_token(target_entity, token_id))
            menu.addAction(action)

        if current_entity is not None:
            menu.addSeparator()
            unassign_action = QAction(f"Remove from {current_entity}", menu)
            unassign_action.triggered.connect(lambda _checked=False, entity=current_entity: self._unassign_token(entity, token_id))
            menu.addAction(unassign_action)

        if token.get("custom"):
            menu.addSeparator()
            rename_action = QAction("Rename token", menu)
            rename_action.triggered.connect(lambda _checked=False: self._rename_custom_token(token_id))
            menu.addAction(rename_action)
            delete_action = QAction("Delete token", menu)
            delete_action.triggered.connect(lambda _checked=False: self._delete_custom_token(token_id))
            menu.addAction(delete_action)

        menu.exec(global_position)

    def _add_custom_token(self) -> None:
        text, accepted = QInputDialog.getText(self, "Add New Token", "Token value:")
        text = text.strip()
        if not accepted or not text:
            return
        self.custom_token_counter += 1
        self.tokens.append({
            "id": f"custom_{self.custom_token_counter}",
            "text": text,
            "source_index": None,
            "custom": True,
        })
        self._refresh_token_views()

    def _rename_custom_token(self, token_id: str) -> None:
        token = self._token_by_id().get(token_id)
        if not token or not token.get("custom"):
            return
        text, accepted = QInputDialog.getText(self, "Rename Token", "Token value:", text=token["text"])
        text = text.strip()
        if not accepted or not text:
            return
        token["text"] = text
        self._refresh_token_views()

    def _delete_custom_token(self, token_id: str) -> None:
        token = self._token_by_id().get(token_id)
        if not token or not token.get("custom"):
            return
        self.tokens = [item for item in self.tokens if item["id"] != token_id]
        for entity in BIDS_ENTITY_ORDER:
            self.assignments[entity] = [item for item in self.assignments.get(entity, []) if item != token_id]
        self._refresh_token_views()

    def _assign_token(self, entity: str, token_id: str) -> None:
        if entity not in self.assignments:
            return
        for current_entity in BIDS_ENTITY_ORDER:
            self.assignments[current_entity] = [
                item for item in self.assignments.get(current_entity, []) if item != token_id
            ]
        self.assignments[entity].append(token_id)
        self._refresh_token_views()

    def _unassign_token(self, entity: str, token_id: str) -> None:
        self.assignments[entity] = [item for item in self.assignments.get(entity, []) if item != token_id]
        self._refresh_token_views()

    def _clear_entity(self, entity: str) -> None:
        if entity in {"sub", "task"}:
            return
        self.assignments[entity] = []
        self._refresh_token_views()

    def _assigned_entity_for_token(self, token_id: str) -> str | None:
        for entity, token_ids in self.assignments.items():
            if token_id in token_ids:
                return entity
        return None

    def _token_by_id(self) -> dict[str, dict[str, Any]]:
        return {token["id"]: token for token in self.tokens}

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _set_validation_status(self, text: str, status: str) -> None:
        self.validation_status.setText(text)
        self.validation_status.setProperty("status", status)
        self.validation_status.style().unpolish(self.validation_status)
        self.validation_status.style().polish(self.validation_status)

    def _accept_mapping(self) -> None:
        self._refresh_preview()
        if not self.scan_result or not self.conversion_context or not self.validation_result or not self.validation_result["valid"]:
            return
        self.accepted_payload = {
            "context": self.conversion_context,
        }
        self.accept()
