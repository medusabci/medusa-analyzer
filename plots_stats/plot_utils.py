import json, os
from PySide6.QtWidgets import (QDialog, QFormLayout, QSpinBox, QCheckBox, QColorDialog, QComboBox, QLabel,
    QDialogButtonBox, QWidget, QHBoxLayout, QPushButton)
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QColor
from functools import partial

class ExportDialog(QDialog):
    """
    Generic export options dialog for plots.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        formats: list[str] | None = None,
        default_width: int = 1200,
        default_height: int = 800,
        default_dpi: int = 300,
        allow_transparency: bool = True,
    ):
        super().__init__(parent)

        self.setWindowTitle("Export options")
        self.setModal(True)

        layout = QFormLayout(self)

        # --- Format ---
        self.format_combo = QComboBox()
        self.format_combo.addItems(formats or ["png", "jpg", "pdf", "svg"])
        layout.addRow(QLabel("Format:"), self.format_combo)

        # --- Width ---
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 8000)
        self.width_spin.setValue(default_width)
        layout.addRow(QLabel("Width (px):"), self.width_spin)

        # --- Height ---
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 8000)
        self.height_spin.setValue(default_height)
        layout.addRow(QLabel("Height (px):"), self.height_spin)

        # --- DPI ---
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(default_dpi)
        layout.addRow(QLabel("DPI:"), self.dpi_spin)

        # --- Transparent background ---
        self.transparent_chk = QCheckBox("Transparent background (if supported)")
        self.transparent_chk.setEnabled(allow_transparency)
        layout.addRow(self.transparent_chk)

        # --- Background color chooser ---
        color_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose color")
        self.color_label = QLabel()
        self.color_label.setAutoFillBackground(True)

        self.bg_color = QColor("white")
        self.update_color_label()

        self.color_button.clicked.connect(self.choose_color)

        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_label)

        layout.addRow(QLabel("Background color:"), color_layout)

        # --- OK / Cancel buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> dict:
        return {
            "format": self.format_combo.currentText(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "dpi": self.dpi_spin.value(),
            "transparent": self.transparent_chk.isChecked(),
            "bg_color": self.bg_color.name(),
        }

    def choose_color(self):
        color = QColorDialog.getColor(self.bg_color, self, "Select background color")
        if color.isValid():
            self.bg_color = color
            self.update_color_label()

    def update_color_label(self):
        palette = self.color_label.palette()
        palette.setColor(self.color_label.backgroundRole(), self.bg_color)
        self.color_label.setPalette(palette)
        self.color_label.setText(self.bg_color.name().upper())

def setup_marks_listwidget(tab, widget_name, items_dict, used_labels, selected_attr, on_change):
    """Configure a QListWidget for conditions/events with multi-selection."""
    list_widget = tab.findChild(QtWidgets.QListWidget, widget_name)

    if list_widget is None:
        print(f"{widget_name} not found.")
        setattr(tab, selected_attr, [])
        return

    if not items_dict or not used_labels:
        list_widget.clear()
        list_widget.setVisible(False)
        setattr(tab, selected_attr, [])
        return

    used_labels = set(int(l) for l in used_labels)
    filtered_names = [ name for name, data in items_dict.items() if data.get("label", None) in used_labels]
    list_widget.clear()
    if not filtered_names:
        list_widget.setVisible(False)
        setattr(tab, selected_attr, [])
        return
    list_widget.setVisible(True)
    list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    for name in filtered_names:
        list_widget.addItem(QtWidgets.QListWidgetItem(name))
    list_widget.selectAll()
    setattr(tab, selected_attr, filtered_names)

    try:
        list_widget.itemSelectionChanged.disconnect()
    except (TypeError, RuntimeError):
        pass

    list_widget.itemSelectionChanged.connect(lambda t=tab: on_change(t))

def build_dynamic_controls(self, container_widget, plot_params, tab):
    """
    Create dynamic controls to edit plot parameters generically.
    Adds at the top a label 'Plot type: <type>'.
    """

    # Update plot type combo box
    type_combo = tab.findChild(QtWidgets.QComboBox, "TypePlotcomboBox")
    if type_combo is not None:
        type_combo.blockSignals(True)
        type_combo.clear()
        type_combo.addItems(list(tab._available_plot_types.keys()))
        idx = type_combo.findText(tab._current_plot_type)
        if idx >= 0:
            type_combo.setCurrentIndex(idx)
        type_combo.currentTextChanged.connect(lambda ptype, cw=container_widget: self.on_plot_type_changed(tab, cw, ptype))
        type_combo.blockSignals(False)

    control_widget = tab.findChild(QtWidgets.QWidget, "controlWidget")
    if control_widget is None:
        return

    tab_widget = tab.findChild(QtWidgets.QWidget, "tabWidget")
    tab_widget.setCurrentIndex(0)

    # Clear old layout if exists to avoid errors
    old_layout = container_widget.layout()
    if old_layout is not None:
        try:
            self._clear_layout(old_layout)
            dummy = QtWidgets.QWidget()
            dummy.setLayout(old_layout)
        except RuntimeError:
            pass

    # Scroll area
    grid = QtWidgets.QGridLayout(control_widget)
    grid.setSpacing(8)
    grid.setContentsMargins(10, 10, 10, 10)
    grid.setColumnStretch(0, 0)  # labels
    grid.setColumnStretch(1, 1)  # widgets

    tab._param_widgets = {}
    row = 0

    for key, meta in plot_params.items():

        if isinstance(meta, dict):
            param_type = meta.get("type", "text")
            label_text = meta.get("label", key)
            default_value = meta.get("default", "")
        else:
            param_type = "text"
            label_text = key
            default_value = meta
        # Plot parameter label (left side)
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("font-weight:600; color:white; font-size:9pt; background-color: #C53189;")
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        # Fixed height for all widgets
        label.setFixedHeight(25)
        grid.addWidget(label, row, 0)

        widget = None

        if param_type in ("text", "range", "number"):
            widget = QtWidgets.QLineEdit()
            widget.setText("" if default_value is None else str(default_value))
            widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

        elif param_type == "bool":
            widget = QtWidgets.QCheckBox()
            widget.setChecked(bool(default_value))
            widget.setStyleSheet("color:white;")

        elif param_type == "select":
            widget = QtWidgets.QComboBox()
            widget.addItems([str(o) for o in meta.get("options", [])])
            if default_value is not None:
                idx = widget.findText(str(default_value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            widget.setStyleSheet("QComboBox {background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;}")

        elif param_type == "color":
            widget = QtWidgets.QPushButton()
            color = default_value or "#000000"

            widget.setText(color)
            widget.setStyleSheet(f"background-color:{color}; color:white; border-radius:4px; padding:4px;")

            def pick_color(btn=widget):
                col = QtWidgets.QColorDialog.getColor(QtGui.QColor(btn.text()), container_widget)
                if col.isValid():
                    hex_color = col.name()
                    btn.setText(hex_color)
                    btn.setStyleSheet(
                        f"background-color:{hex_color}; color:white; border-radius:4px; padding:4px;"
                    )

            widget.clicked.connect(partial(pick_color, widget))

        elif param_type == "spin":
            widget = QtWidgets.QSpinBox()
            widget.setMinimum(meta.get("min", 0))
            widget.setMaximum(meta.get("max", 100))
            widget.setValue(default_value if default_value is not None else 10)
            widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

        elif param_type == "doublespin":
            widget = QtWidgets.QDoubleSpinBox()
            widget.setMinimum(meta.get("min", 0.0))
            widget.setMaximum(meta.get("max", 1.0))
            widget.setSingleStep(meta.get("step", 0.1))

            if default_value is not None:
                widget.setValue(float(default_value))
            else:
                widget.setValue(0.0)
            widget.setDecimals(1)
            widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

        if widget is not None:
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            grid.addWidget(widget, row, 1)
            tab._param_widgets[key] = (param_type, widget)

        row += 1

    grid.setRowStretch(row, 1)
    control_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

def get_widget_value(ptype, widget):
    """Extract typed value from a Qt widget."""
    import json

    if ptype in ("text", "range", "number"):
        text = widget.text().strip()
        try:
            return json.loads(text)
        except Exception:
            return text

    elif ptype == "bool":
        return widget.isChecked()

    elif ptype == "select":
        return widget.currentText()

    elif ptype == "color":
        return widget.text()

    elif ptype == "spin":
        return widget.value()

    elif ptype == "doublespin":
        return widget.value()

    return None

def load_plot_json_files(base_path):
    with open(os.path.join(base_path, "available_data.json"), "r", encoding="utf-8") as f:
        params_json = json.load(f)
    with open(os.path.join(base_path, "type_plots.json"), "r", encoding="utf-8") as f:
        plots_json = json.load(f)
    return params_json, plots_json

def export_figure_generic(view, fig, suggested_name, warn_if_none=False):
    """
    Generic figure export utility.
    """

    if fig is None:
        if warn_if_none:
            QtWidgets.QMessageBox.warning(
                view, "Export", "No plot to export."
            )
        return

    dlg = ExportDialog(view)
    if dlg.exec() != QtWidgets.QDialog.Accepted:
        return

    vals = dlg.get_values()
    fmt = vals["format"]
    dpi = vals["dpi"]
    width_px = vals["width"]
    height_px = vals["height"]
    transparent = vals["transparent"]
    bg_color = vals["bg_color"]

    fname, _ = QtWidgets.QFileDialog.getSaveFileName(view,"Save image", suggested_name,f"{fmt.upper()} (*.{fmt})")
    if not fname:
        return

    inches_width = width_px / dpi
    inches_height = height_px / dpi

    original_size = fig.get_size_inches()
    try:
        fig.set_size_inches(inches_width, inches_height)

        facecolor = "none" if transparent else bg_color
        fig.savefig(fname, dpi=dpi, transparent=transparent, bbox_inches="tight", facecolor=facecolor)
    finally:
        fig.set_size_inches(original_size)

    QtWidgets.QMessageBox.information(view, "Export", f"Saved to:\n{fname}")
