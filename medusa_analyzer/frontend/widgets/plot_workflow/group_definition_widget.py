from __future__ import annotations

from functools import partial
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)
from medusa_analyzer.frontend.validation import Validation


_INITIAL_GROUP_HUES = (0, 120, 240)


def _maximally_spaced_hues(count: int) -> list[int]:
    """Build a stable red/green/blue-first hue sequence by splitting the largest gaps."""
    if count <= 0:
        return []

    hues = [float(hue) for hue in _INITIAL_GROUP_HUES[:count]]
    while len(hues) < count:
        ordered_hues = sorted(hues)
        gaps = []
        for index, start_hue in enumerate(ordered_hues):
            end_hue = ordered_hues[(index + 1) % len(ordered_hues)]
            gap = (end_hue - start_hue) % 360
            gaps.append((gap or 360, start_hue))

        largest_gap, start_hue = max(gaps, key=lambda item: item[0])
        hues.append((start_hue + largest_gap / 2) % 360)

    return [int(round(hue)) % 360 for hue in hues]


class PlotGroupDefinitionWidget(QScrollArea):
    changed = Signal() # cada vez que cambie algo emitimos señal

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        del experiment_info
        super().__init__()

        self.state = state
        self.config = defaults.get("group_definition", {})
        self.validation = Validation()
        self.validation_errors: list[str] = []
        # Creamos una variable para guardar la info del widget asociado a cada grupo; la interfaz visual de cada grupo
        self.group_rows: dict[str, dict[str, Any]] = {}

        self.min_groups = int(self.config.get("min_groups", 1))
        self.max_groups = int(self.config.get("max_groups", 20))
        self.default_group_count = int(self.config.get("default_group_count", 2))

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.setWidget(self.content)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(18)

        title = QLabel("Group definition")
        title.setObjectName("pageTitle")
        description = QLabel("Create the groups that will be used in the following assignment steps.")
        description.setObjectName("muted")
        description.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(description)

        root.addWidget(self._build_controls_panel()) # panel para elegir nº de grupos
        root.addWidget(self._build_groups_panel()) # # panel donde aparecen los grupos
        root.addStretch()

        self._restore_group_count() # Intentamos restaurar los grupos que hubiera guardados en state
        self._sync(emit_changed=False)

    def _build_controls_panel(self) -> QFrame:
        """Panel para elegir el número de grupos"""
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        label = QLabel("Number of groups")
        label.setObjectName("panelTitle")
        self.group_count = QSpinBox()
        self.group_count.setRange(self.min_groups, self.max_groups)
        self.group_count.setValue(self.default_group_count)
        self.group_count.valueChanged.connect(self._group_count_changed)

        layout.addWidget(label)
        layout.addWidget(self.group_count)
        layout.addStretch()
        return panel

    def _build_groups_panel(self) -> QFrame:
        """Construye el panel donde aparecerán los grupos."""
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        heading = QLabel("Groups")
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)

        self.groups_grid = QGridLayout()
        self.groups_grid.setHorizontalSpacing(12)
        self.groups_grid.setVerticalSpacing(12)
        layout.addLayout(self.groups_grid)

        self.status_label = QLabel("")
        self.status_label.setObjectName("selectionStatus")
        self.status_label.setProperty("status", "idle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        return panel

    def _restore_group_count(self) -> None:
        """Intenta recuperar grupos previamente creados."""
        stored_groups = self._stored_groups()
        if stored_groups:
            group_count = len(stored_groups) # Vemos el nº de grupos que hay
        else:
            group_count = self.default_group_count

        self.group_count.blockSignals(True)
        self.group_count.setValue(max(self.min_groups, min(self.max_groups, group_count))) # limitamos rango
        self.group_count.blockSignals(False)
        self._rebuild_group_chips() # Creamos visualmente los grupos

    def _group_count_changed(self) -> None:
        self._rebuild_group_chips(reassign_colors=True) # Reconstruimos las chips
        self._sync() # Actualizamos la interfaz

    def _rebuild_group_chips(self, reassign_colors: bool = False) -> None:
        while self.groups_grid.count(): # borramos widgets actuales
            item = self.groups_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.group_rows = {} # vacíamos dic que gaurdaba los widgets

        group_count = self.group_count.value() # obtenemos cuántos grupos queremos
        stored_groups = self._stored_groups() # recuperamos configuraciones de grupos previas
        default_colors = self._default_colors(group_count) # generamos color diferente para cada grupo

        for index in range(group_count):
            group_id = f"group_{index + 1}"
            stored_group = stored_groups.get(group_id, {}) # buscamos si ese grupo existía
            group_name = str(stored_group.get("group_name") or f"Group {index + 1}") # si tenía nombre, lo reutiliza
            group_color = str(stored_group.get("group_color") or default_colors[index]) # si tenía color, lo reutiliza

            if reassign_colors:
                group_color = default_colors[index]

            chip = self._create_group_chip(group_id, group_name, group_color) # creamos visualmente el grupo
            self.groups_grid.addWidget(chip, index // 2, index % 2)

        self.groups_grid.setColumnStretch(0, 1)
        self.groups_grid.setColumnStretch(1, 1)

    def _create_group_chip(self, group_id: str, group_name: str, group_color: str) -> QFrame:
        chip = QFrame()
        chip.setProperty("role", "group-definition-chip")
        chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        swatch = QFrame() # circulito/cuadradito de color
        swatch.setProperty("role", "group-color-swatch")
        swatch.setFixedSize(22, 22)
        swatch.setStyleSheet(f"background: {group_color}; border-radius: 11px;")

        name_input = QLineEdit() # campo editable de nombre
        name_input.setText(group_name)
        name_input.setPlaceholderText("Group name")
        name_input.textChanged.connect(self._sync) # cada vez que el usuario escriba el nombre, sincroniza state

        color_button = QPushButton(group_color.upper())
        color_button.setProperty("variant", "secondary")
        color_button.setProperty("role", "group-color-button")
        color_button.clicked.connect(partial(self._select_group_color, group_id))

        layout.addWidget(swatch)
        layout.addWidget(name_input, 1)
        layout.addWidget(color_button)

        # Actualizamos la información de los widgets
        self.group_rows[group_id] = {"name_input": name_input, "color": group_color.upper(),
            "color_button": color_button, "swatch": swatch}
        return chip

    def _select_group_color(self, group_id: str) -> None:
        """Función para seleccionar el color de cada grupo. """
        row = self.group_rows.get(group_id) # buscamos el widget correspondiente a ese grupo
        if row is None:
            return

        selected_color = QColorDialog.getColor(QColor(str(row["color"])), self, "Select group color")
        if not selected_color.isValid():
            return

        color = selected_color.name().upper() # convertimos el color a hexadecimal
        row["color"] = color
        row["color_button"].setText(color) # texto del botón
        row["swatch"].setStyleSheet(f"background: {color}; border-radius: 11px;") # círculo visual
        self._sync() # sincronizamos para guardar en state

    def _sync(self, *_: Any, emit_changed: bool = True) -> None:
        stored_groups = self._stored_groups()
        groups: dict[str, dict[str, Any]] = {}
        for group_id, row in self.group_rows.items():
            stored_group = stored_groups.get(group_id, {})
            groups[group_id] = {"group_name": row["name_input"].text().strip(),
                "group_color": str(row["color"]).upper(),
                "subjects": list(stored_group.get("subjects") or []), # viene del widget anterior
                "files": list(stored_group.get("files") or [])} # viene del widget anterior

        self.state["groups"] = groups
        self.validation_errors = self._validate_groups()
        self._update_status_label() # actualizamos mensaje de la pantalla

        if emit_changed:
            self.changed.emit()

    def _validate_groups(self) -> list[str]:
        errors: list[str] = []
        groups = self._stored_groups() # Obtenemos grupos
        # Validamos que haya al menos un grupo mínimo de grupos (definido en defaults) en los grupos creados.
        errors.extend(self.validation.validate_many(groups, [("minimum_length", {"minimum": self.min_groups,
            "item_name": "group", "action": "contain"})], label="Groups"))
        # Validamos que ninguno de los nombres de grupo esté vacío
        for index, group in enumerate(groups.values(), start=1):
            errors.extend(self.validation.validate_many(group.get("group_name", ""), ["required_text"],
                label=f"Group {index} name"))
        return errors

    def _update_status_label(self) -> None:
        if self.validation_errors: # formato error
            self.status_label.setText(self.validation_errors[0])
            self.status_label.setProperty("status", "error")
        else: # formato OK
            self.status_label.setText(f"{len(self._stored_groups())} group(s) configured.")
            self.status_label.setProperty("status", "ready")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _stored_groups(self) -> dict[str, dict[str, Any]]:
        groups = self.state.get("groups")
        if isinstance(groups, dict):
            return {str(group_id): dict(group) for group_id, group in groups.items() if isinstance(group, dict)}
        return {}

    def _default_colors(self, group_count: int) -> list[str]:
        """Genera automáticamente colores diferentes para cada grupo."""
        saturation = int(self.config.get("default_color_saturation", 220))
        value = int(self.config.get("default_color_value", 225))
        return [QColor.fromHsv(hue, saturation, value).name().upper()
            for hue in _maximally_spaced_hues(group_count)]

    def on_step_activated(self) -> None:
        self._sync()

    def can_continue(self) -> bool:
        self.validation_errors = self._validate_groups()
        return not self.validation_errors

GroupDefinitionWidget = PlotGroupDefinitionWidget

__all__ = ["GroupDefinitionWidget", "PlotGroupDefinitionWidget"]
