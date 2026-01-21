import json
from PySide6 import QtCore,QtGui
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QSpinBox, QCheckBox, QColorDialog,
    QComboBox, QLabel, QDialogButtonBox, QWidget,
    QHBoxLayout, QPushButton
)
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



import json
from PySide6 import QtWidgets, QtCore


def build_dynamic_controls(self, container_widget, plot_params, tab):
    """
    Create dynamic controls to edit plot parameters generically.
    Adds at the top a label 'Plot type: <type>'.
    """

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
    scroll_area = QtWidgets.QScrollArea(container_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet(
        """QScrollArea {border: none; background-color: #222;} 
        QWidget {background-color: transparent;}"""
    )

    scroll_content = QtWidgets.QWidget()
    scroll_layout = QtWidgets.QGridLayout(scroll_content)
    scroll_layout.setSpacing(8)
    scroll_layout.setContentsMargins(10, 10, 10, 10)
    scroll_layout.setColumnStretch(0, 0)  # labels
    scroll_layout.setColumnStretch(1, 1)  # widgets

    # Title label
    row = 0
    label_plot_type = QtWidgets.QLabel("Plot Type")
    label_plot_type.setStyleSheet("font-weight:700; color:white; font-size:9pt; background-color: "
                                  "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a0dad, stop:1 #ec407a);"
                                  "padding: 4px 10px; ")
    label_plot_type.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
    scroll_layout.addWidget(label_plot_type, row, 0, 1, 2)
    row += 1

    plot_type_combo = QtWidgets.QComboBox()
    plot_type_combo.addItems(list(tab._available_plot_types.keys()))
    idx = plot_type_combo.findText(tab._current_plot_type)
    if idx >= 0:
        plot_type_combo.setCurrentIndex(idx)
    plot_type_combo.currentTextChanged.connect(lambda ptype: self.on_plot_type_changed(tab, container_widget, ptype))
    plot_type_combo.setStyleSheet("""
        QComboBox {
            background-color: #DCDCDC; 
            color: black; 
            border-radius: 4px; 
            padding: 4px;
        }
    """)
    scroll_layout.addWidget(plot_type_combo, row, 0, 1, 2)
    row += 1

    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    line.setStyleSheet("color: #555555; background-color: #555555;")  # gris oscuro
    scroll_layout.addWidget(line, row, 0, 1, 2)  # ocupa ambas columnas
    row += 1

    tab._param_widgets = {}

    # Loop over plot_params to create specific controls
    for key, meta in plot_params.items():

        if isinstance(meta, dict) and any(
            k in meta for k in ("type", "default", "label")
        ):
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
        scroll_layout.addWidget(label, row, 0)

        widget = None

        if param_type in ("text", "range", "number"):
            widget = QtWidgets.QLineEdit()

            if default_value is None and param_type == "range":
                display_value = "[None, None]"
            elif default_value is None:
                display_value = ""
            elif isinstance(default_value, (list, tuple, dict)):
                display_value = json.dumps(default_value)
            else:
                display_value = str(default_value)

            widget.setText(display_value)
            widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

        elif param_type == "bool":
            widget = QtWidgets.QCheckBox()
            dv = (
                bool(default_value)
                if not isinstance(default_value, str)
                else default_value.lower() in ("1", "true", "yes")
            )
            widget.setChecked(dv)
            widget.setStyleSheet("color:white;")

        elif param_type == "select":
            widget = QtWidgets.QComboBox()
            options = meta.get("options", []) if isinstance(meta, dict) else []

            for opt in options:
                widget.addItem(str(opt))

            if default_value not in (None, "") and str(default_value) not in [
                str(o) for o in options
            ]:
                widget.addItem(str(default_value))

            if default_value is not None and default_value != "":
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
            widget.setDecimals(3)
            widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

        if widget is not None:
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            scroll_layout.addWidget(widget, row, 1)
            tab._param_widgets[key] = (param_type, widget)

        row += 1

    scroll_content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
    spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
    scroll_layout.addItem(spacer, row, 0, 1, 2)
    scroll_content.adjustSize()
    scroll_area.setWidget(scroll_content)

    main_layout = QtWidgets.QVBoxLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll_area)
    container_widget.setLayout(main_layout)

    container_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    container_widget.setMinimumHeight(170)
    container_widget.updateGeometry()


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