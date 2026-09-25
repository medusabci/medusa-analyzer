from __future__ import annotations
from copy import deepcopy
from math import ceil, pi, sin
from typing import Any
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpinBox, QVBoxLayout, QWidget)
from medusa_analyzer.frontend.validation import Validation


class WindowSegmentationDiagram(QWidget):
    VISUAL_MIN_EPOCH_MS = 100
    VISUAL_FULL_WIDTH_EPOCH_MS = 60000
    EPOCH_COUNT = 5
    MIN_VISIBLE_EPOCH_WIDTH = 56.0
    EPOCH_LABEL_MIN_WIDTH = 48.0
    OVERLAP_LABEL_MIN_WIDTH = 10.0
    MAX_DRAWN_WINDOWS = 260

    def __init__(self) -> None:
        super().__init__()
        self.epoch_length_ms = 1000
        self.overlap_percent = 0
        self.setMinimumHeight(315)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, epoch_length_ms: int, overlap_percent: int) -> None:
        self.epoch_length_ms = int(epoch_length_ms)
        self.overlap_percent = int(overlap_percent)
        self.update()

    def paintEvent(self, event: Any) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        painter.fillRect(rect, QColor("#1F171B"))

        text_color = QColor("#F8EEF2")
        muted_color = QColor("#B8A7AF")
        border_color = QColor("#3A2931")
        accent_color = QColor("#E35A82")
        signal_color = QColor("#9BE7E8")

        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(rect, 10, 10)

        signal_start_x = rect.left() + 28
        signal_end_x = rect.right() - 92
        signal_width = max(1.0, signal_end_x - signal_start_x)
        signal_y = rect.top() + 72
        windows_top = rect.top() + 128
        windows_height = 58

        painter.setPen(QPen(border_color, 1.3))
        painter.drawLine(QPointF(signal_start_x, signal_y), QPointF(signal_end_x, signal_y))

        signal_path = QPainterPath(QPointF(signal_start_x, signal_y))
        samples = 220
        for index in range(samples + 1):
            ratio = index / samples
            x = signal_start_x + ratio * signal_width
            y = signal_y - 28 * sin(ratio * pi * 10)
            if index == 0:
                signal_path.moveTo(x, y)
            else:
                signal_path.lineTo(x, y)
        painter.setPen(QPen(signal_color, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(signal_path)

        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        painter.setPen(text_color)
        painter.drawText(QRectF(signal_end_x + 14, signal_y - 16, 76, 32), Qt.AlignmentFlag.AlignVCenter, "Signal")

        epoch_width = self._epoch_width(signal_width, self.epoch_length_ms)
        overlap_ratio = max(0, min(100, self.overlap_percent)) / 100
        start_step = max(0.1, epoch_width * (1 - overlap_ratio))
        window_count = max(1, ceil(signal_width / start_step))
        window_fill = QColor(accent_color)
        window_fill.setAlpha(34)
        guide_pen = QPen(accent_color, 1.2, Qt.PenStyle.DashLine)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        for index in self._visible_window_indices(window_count):
            start_x = signal_start_x + index * start_step
            if start_x >= signal_end_x:
                break
            visible_width = max(1.0, min(epoch_width, signal_end_x - start_x))
            window_rect = QRectF(start_x, windows_top, visible_width, windows_height)
            painter.setBrush(window_fill)
            painter.setPen(QPen(accent_color, 1.6))
            painter.drawRoundedRect(window_rect, 7, 7)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(guide_pen)
            painter.drawLine(QPointF(start_x, signal_y + 38), QPointF(start_x, windows_top + windows_height))
            if visible_width >= self.EPOCH_LABEL_MIN_WIDTH and start_step >= self.EPOCH_LABEL_MIN_WIDTH:
                painter.setPen(text_color)
                painter.drawText(window_rect, Qt.AlignmentFlag.AlignCenter, f"Epoch {index + 1}")

        self._draw_measurement(
            painter,
            signal_start_x,
            signal_start_x + epoch_width,
            rect.top() + 216,
            f"epoch length ({self.epoch_length_ms} ms)",
            windows_top + windows_height,
            muted_color,
            text_color,
        )

        if self.overlap_percent > 0:
            second_start_x = signal_start_x + start_step
            overlap_end_x = signal_start_x + epoch_width
            if overlap_end_x > second_start_x:
                self._draw_measurement(
                    painter,
                    second_start_x,
                    overlap_end_x,
                    rect.top() + 250,
                    f"overlap ({self.overlap_percent}%)",
                    windows_top,
                    muted_color,
                    text_color,
                    self.OVERLAP_LABEL_MIN_WIDTH,
                )

    def _draw_measurement(self, painter: QPainter, x1: float, x2: float, y: float, label: str,
        guide_top: float, muted_color: QColor, text_color: QColor, label_min_width: float = 0.0) -> None:
        painter.setPen(QPen(muted_color, 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(x1, guide_top), QPointF(x1, y - 7))
        painter.drawLine(QPointF(x2, guide_top), QPointF(x2, y - 7))

        width = abs(x2 - x1)
        if width >= 18:
            painter.setPen(QPen(muted_color, 1.5))
            painter.drawLine(QPointF(x1 + 7, y), QPointF(x2 - 7, y))
            self._draw_arrow_head(painter, QPointF(x1 + 7, y), -1, muted_color)
            self._draw_arrow_head(painter, QPointF(x2 - 7, y), 1, muted_color)

        if width >= label_min_width:
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.setPen(text_color)
            painter.drawText(QRectF(x1 - 80, y + 7, width + 160, 22), Qt.AlignmentFlag.AlignHCenter, label)

    @classmethod
    def _epoch_width(cls, signal_width: float, epoch_length_ms: int) -> float:
        max_epoch_width = signal_width / cls.EPOCH_COUNT
        min_epoch_width = min(cls.MIN_VISIBLE_EPOCH_WIDTH, max_epoch_width)
        bounded_epoch = max(cls.VISUAL_MIN_EPOCH_MS, min(int(epoch_length_ms), cls.VISUAL_FULL_WIDTH_EPOCH_MS))
        epoch_ratio = (
            (bounded_epoch - cls.VISUAL_MIN_EPOCH_MS)
            / (cls.VISUAL_FULL_WIDTH_EPOCH_MS - cls.VISUAL_MIN_EPOCH_MS)
        ) ** 0.5
        return min_epoch_width + epoch_ratio * (max_epoch_width - min_epoch_width)

    @classmethod
    def _visible_window_indices(cls, window_count: int) -> list[int]:
        if window_count <= cls.MAX_DRAWN_WINDOWS:
            return list(range(window_count))

        step = ceil(window_count / cls.MAX_DRAWN_WINDOWS)
        indices = list(range(0, window_count, step))
        if indices[-1] != window_count - 1:
            indices.append(window_count - 1)
        return indices

    @staticmethod
    def _draw_arrow_head(painter: QPainter, point: QPointF, direction: int, color: QColor) -> None:
        size = 6
        polygon = QPolygonF([
            QPointF(point.x(), point.y()),
            QPointF(point.x() + direction * size, point.y() - size / 2),
            QPointF(point.x() + direction * size, point.y() + size / 2),
        ])
        painter.setBrush(color)
        painter.setPen(QPen(color, 1))
        painter.drawPolygon(polygon)
        painter.setBrush(Qt.BrushStyle.NoBrush)


class WindowSegmentationWidget(QFrame):
    MAX_EPOCH_LENGTH_MS = 2147483647

    epoch_length_changed = Signal(int)
    overlap_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._syncing = False
        self.setProperty("role", "segmentation-visual-widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(12)
        layout.addLayout(controls)

        epoch_card, self.epoch_slider = self._epoch_length_control()
        overlap_card, self.overlap_slider, self.overlap_value = self._control(
            "Overlap", 0, 99, 1, 0, "%",
            "Percentage of each epoch shared with the next epoch.")

        controls.addWidget(epoch_card, 0, 0)
        controls.addWidget(overlap_card, 0, 1)

        self.diagram = WindowSegmentationDiagram()
        layout.addWidget(self.diagram)

        self.epoch_slider.valueChanged.connect(self._epoch_slider_changed)
        self.overlap_slider.valueChanged.connect(self._overlap_slider_changed)
        self.set_values(1000, 0)

    def _epoch_length_control(self) -> tuple[QFrame, QSpinBox]:
        card = QFrame()
        card.setProperty("role", "segmentation-visual-control")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel("Epoch length")
        label.setObjectName("subgroupTitle")
        header.addWidget(label)
        header.addStretch()
        layout.addLayout(header)

        spin = QSpinBox()
        spin.setRange(100, self.MAX_EPOCH_LENGTH_MS)
        spin.setSingleStep(100)
        spin.setValue(1000)
        spin.setSuffix(" ms")
        layout.addWidget(spin)

        hint_label = QLabel("Duration of each window used to segment duration events.")
        hint_label.setObjectName("muted")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        return card, spin

    def _control(self, title: str, minimum: int, maximum: int, step: int, value: int,
        suffix: str, hint: str) -> tuple[QFrame, QSlider, QLabel]:
        card = QFrame()
        card.setProperty("role", "segmentation-visual-control")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("subgroupTitle")
        value_label = QLabel(f"{value} {suffix}" if suffix == "ms" else f"{value}{suffix}")
        value_label.setObjectName("segmentationVisualBadge")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(value_label)
        layout.addLayout(header)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setSingleStep(step)
        slider.setPageStep(step)
        slider.setValue(value)
        layout.addWidget(slider)

        hint_label = QLabel(hint)
        hint_label.setObjectName("muted")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        return card, slider, value_label

    def set_values(self, epoch_length_ms: int, overlap_percent: int) -> None:
        previous = self._syncing
        self._syncing = True
        try:
            self.epoch_slider.setValue(max(100, int(epoch_length_ms)))
            self.overlap_slider.setValue(int(overlap_percent))
            self._update_labels()
            self.diagram.set_values(max(100, int(epoch_length_ms)), int(overlap_percent))
        finally:
            self._syncing = previous

    def _update_labels(self) -> None:
        self.overlap_value.setText(f"{self.overlap_slider.value()}%")

    def _epoch_slider_changed(self, value: int) -> None:
        self._update_labels()
        self.diagram.set_values(value, self.overlap_slider.value())
        if not self._syncing:
            self.epoch_length_changed.emit(value)

    def _overlap_slider_changed(self, value: int) -> None:
        self._update_labels()
        self.diagram.set_values(self.epoch_slider.value(), value)
        if not self._syncing:
            self.overlap_changed.emit(value)


class OnsetSegmentationDiagram(QWidget):
    VISUAL_TIME_LIMIT_MS = 60000

    def __init__(self) -> None:
        super().__init__()
        self.window_start_ms = -300
        self.window_end_ms = 700
        self.baseline_start_ms = -300
        self.baseline_end_ms = 0
        self.window_invalid = False
        self.baseline_invalid = False
        self.setMinimumHeight(330)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, window_start_ms: int, window_end_ms: int,
        baseline_start_ms: int, baseline_end_ms: int, window_invalid: bool = False,
        baseline_invalid: bool = False) -> None:
        self.window_start_ms = int(window_start_ms)
        self.window_end_ms = int(window_end_ms)
        self.baseline_start_ms = int(baseline_start_ms)
        self.baseline_end_ms = int(baseline_end_ms)
        self.window_invalid = bool(window_invalid)
        self.baseline_invalid = bool(baseline_invalid)
        self.update()

    def paintEvent(self, event: Any) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        painter.fillRect(rect, QColor("#1F171B"))

        text_color = QColor("#F8EEF2")
        muted_color = QColor("#B8A7AF")
        border_color = QColor("#3A2931")
        signal_color = QColor("#9BE7E8")
        onset_color = QColor("#FF6B7A")
        window_color = QColor("#E35A82")
        baseline_color = QColor("#F6C177")

        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(rect, 10, 10)

        signal_start_x = rect.left() + 34
        signal_end_x = rect.right() - 100
        signal_width = max(1.0, signal_end_x - signal_start_x)
        signal_y = rect.top() + 72
        onset_positions = [
            signal_start_x + signal_width * 0.25,
            signal_start_x + signal_width * 0.74,
        ]
        visual_span = self._visual_span(onset_positions, signal_start_x, signal_end_x)
        window_row_y = rect.top() + 168
        baseline_row_y = rect.top() + 248

        painter.setPen(QPen(border_color, 1.3))
        painter.drawLine(QPointF(signal_start_x, signal_y), QPointF(signal_end_x, signal_y))

        signal_path = QPainterPath(QPointF(signal_start_x, self._signal_y(signal_start_x, signal_start_x, signal_width, signal_y)))
        samples = 320
        for index in range(samples + 1):
            ratio = index / samples
            x = signal_start_x + ratio * signal_width
            y = self._signal_y(x, signal_start_x, signal_width, signal_y)
            if index == 0:
                signal_path.moveTo(x, y)
            else:
                signal_path.lineTo(x, y)
        painter.setPen(QPen(signal_color, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(signal_path)

        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        painter.setPen(text_color)
        painter.drawText(QRectF(signal_end_x + 14, signal_y - 16, 78, 32), Qt.AlignmentFlag.AlignVCenter, "Signal")

        for onset_x in onset_positions:
            onset_y = self._signal_y(onset_x, signal_start_x, signal_width, signal_y)
            painter.setPen(QPen(onset_color, 1.3, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(onset_x, onset_y), QPointF(onset_x, baseline_row_y + 45))
            painter.setBrush(onset_color)
            painter.setPen(QPen(QColor("#1F171B"), 1.6))
            painter.drawEllipse(QPointF(onset_x, onset_y), 5.8, 5.8)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(onset_color)
            painter.drawText(QRectF(onset_x - 36, onset_y - 30, 72, 18), Qt.AlignmentFlag.AlignCenter, "onset")

            if not self.window_invalid:
                window_start_x = self._offset_to_x(onset_x, self.window_start_ms, visual_span)
                window_end_x = self._offset_to_x(onset_x, self.window_end_ms, visual_span)
                self._draw_interval(
                    painter,
                    window_start_x,
                    window_end_x,
                    window_row_y,
                    window_color,
                    "segmentation window",
                    f"start {self.window_start_ms} ms",
                    f"end {self.window_end_ms} ms",
                )
            if not self.baseline_invalid:
                baseline_start_x = self._offset_to_x(onset_x, self.baseline_start_ms, visual_span)
                baseline_end_x = self._offset_to_x(onset_x, self.baseline_end_ms, visual_span)
                self._draw_interval(
                    painter,
                    baseline_start_x,
                    baseline_end_x,
                    baseline_row_y,
                    baseline_color,
                    "baseline",
                    f"baseline start {self.baseline_start_ms} ms",
                    f"baseline end {self.baseline_end_ms} ms",
                )

    @staticmethod
    def _signal_y(x: float, start_x: float, width: float, middle_y: float) -> float:
        ratio = (x - start_x) / width
        return middle_y - 28 * sin(ratio * pi * 8.5) - 8 * sin(ratio * pi * 21)

    @staticmethod
    def _visual_span(onset_positions: list[float], minimum: float, maximum: float) -> float:
        available_spans: list[float] = []
        for onset_x in onset_positions:
            available_spans.append(onset_x - (minimum + 5))
            available_spans.append((maximum - 5) - onset_x)
        return max(1.0, min(available_spans))

    @classmethod
    def _offset_to_x(cls, onset_x: float, offset_ms: int, visual_span: float) -> float:
        limit = cls.VISUAL_TIME_LIMIT_MS
        bounded_offset = max(-limit, min(limit, int(offset_ms)))
        if bounded_offset == 0:
            return onset_x

        visual_ratio = (abs(bounded_offset) / limit) ** 0.5
        if bounded_offset < 0:
            return onset_x - visual_span * visual_ratio

        return onset_x + visual_span * visual_ratio

    def _draw_interval(self, painter: QPainter, x1: float, x2: float, y: float, color: QColor,
        title: str, start_label: str, end_label: str) -> None:
        left_x = min(x1, x2)
        right_x = max(x1, x2)
        interval_width = max(2.0, right_x - left_x)

        fill = QColor(color)
        fill.setAlpha(38)
        painter.setBrush(fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(left_x, y - 13, interval_width, 16), 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QPen(color, 1.2, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(left_x, y - 18), QPointF(left_x, y + 34))
        painter.drawLine(QPointF(right_x, y - 18), QPointF(right_x, y + 34))

        painter.setPen(QPen(color, 2.0))
        painter.drawPath(self._brace_path(left_x, right_x, y, 22))

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(color)
        painter.drawText(QRectF(left_x - 50, y + 27, interval_width + 100, 18), Qt.AlignmentFlag.AlignCenter, title)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        painter.drawText(QRectF(left_x - 118, y - 32, 110, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, start_label)
        painter.drawText(QRectF(right_x + 8, y - 32, 118, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, end_label)

    @staticmethod
    def _brace_path(x1: float, x2: float, y: float, height: float) -> QPainterPath:
        left_x = min(x1, x2)
        right_x = max(x1, x2)
        width = max(1.0, right_x - left_x)
        middle_x = (left_x + right_x) / 2
        curve_width = min(24.0, max(8.0, width * 0.18))

        path = QPainterPath(QPointF(left_x, y))
        path.cubicTo(left_x, y, left_x, y + height * 0.55, left_x + curve_width, y + height * 0.55)
        path.cubicTo(left_x + curve_width * 1.5, y + height * 0.55,
            middle_x - curve_width * 0.8, y + height, middle_x, y + height)
        path.cubicTo(middle_x + curve_width * 0.8, y + height,
            right_x - curve_width * 1.5, y + height * 0.55, right_x - curve_width, y + height * 0.55)
        path.cubicTo(right_x, y + height * 0.55, right_x, y, right_x, y)
        return path


class OnsetSegmentationWidget(QFrame):
    MIN_TIME_MS = -2147483647
    MAX_TIME_MS = 2147483647
    INTERVAL_GAP_MS = 1

    values_changed = Signal(int, int, int, int)

    def __init__(self) -> None:
        super().__init__()
        self._syncing = False
        self.validation = Validation()
        self.setProperty("role", "segmentation-visual-widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        controls = QGridLayout()
        controls.setHorizontalSpacing(12)
        controls.setVerticalSpacing(12)
        layout.addLayout(controls)

        start_card, self.window_start_slider = self._control(
            "Start", self.MIN_TIME_MS, self.MAX_TIME_MS, 25, -300,
            "Beginning of the segmentation window relative to the onset.")
        end_card, self.window_end_slider = self._control(
            "End", self.MIN_TIME_MS, self.MAX_TIME_MS, 25, 700,
            "End of the segmentation window relative to the onset.")
        baseline_start_card, self.baseline_start_slider = self._control(
            "Baseline start", self.MIN_TIME_MS, self.MAX_TIME_MS, 25, -300,
            "Beginning of the baseline interval relative to the onset.")
        baseline_end_card, self.baseline_end_slider = self._control(
            "Baseline end", self.MIN_TIME_MS, self.MAX_TIME_MS, 25, 0,
            "End of the baseline interval relative to the onset.")

        controls.addWidget(start_card, 0, 0)
        controls.addWidget(end_card, 0, 1)
        controls.addWidget(baseline_start_card, 1, 0)
        controls.addWidget(baseline_end_card, 1, 1)

        self.diagram = OnsetSegmentationDiagram()
        layout.addWidget(self.diagram)

        for slider in (self.window_start_slider, self.window_end_slider, self.baseline_start_slider, self.baseline_end_slider):
            slider.valueChanged.connect(self._value_changed)

        self.set_values(-300, 700, -300, 0)

    def _control(self, title: str, minimum: int, maximum: int, step: int, value: int,
        hint: str) -> tuple[QFrame, QSpinBox]:
        card = QFrame()
        card.setProperty("role", "segmentation-visual-control")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("subgroupTitle")
        header.addWidget(label)
        header.addStretch()
        layout.addLayout(header)

        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setSuffix(" ms")
        layout.addWidget(spin)

        hint_label = QLabel(hint)
        hint_label.setObjectName("muted")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        return card, spin

    def set_values(self, window_start_ms: int, window_end_ms: int,
        baseline_start_ms: int, baseline_end_ms: int) -> None:
        previous = self._syncing
        self._syncing = True
        try:
            self._reset_interval_constraints()
            self.window_start_slider.setValue(self._clamp_to_control(self.window_start_slider, window_start_ms))
            self.window_end_slider.setValue(self._clamp_to_control(self.window_end_slider, window_end_ms))
            self.baseline_start_slider.setValue(self._clamp_to_control(self.baseline_start_slider, baseline_start_ms))
            self.baseline_end_slider.setValue(self._clamp_to_control(self.baseline_end_slider, baseline_end_ms))
            self._apply_interval_constraints()
            values = self._current_values()
            self._apply_values_to_preview(values)
        finally:
            self._syncing = previous

    def _value_changed(self, *_: Any) -> None:
        self._apply_interval_constraints()
        values = self._current_values()
        self._apply_values_to_preview(values)

        if not self._syncing:
            self.values_changed.emit(*values)

    def _apply_values_to_preview(self, values: tuple[int, int, int, int]) -> None:
        window_invalid, baseline_invalid = self._invalid_interval_flags(values)
        self._update_control_status(window_invalid, baseline_invalid)
        self.diagram.set_values(*values, window_invalid=window_invalid, baseline_invalid=baseline_invalid)

    def _update_control_status(self, window_invalid: bool = False, baseline_invalid: bool = False) -> None:
        for control, invalid in (
            (self.window_start_slider, window_invalid),
            (self.window_end_slider, window_invalid),
            (self.baseline_start_slider, baseline_invalid),
            (self.baseline_end_slider, baseline_invalid),
        ):
            control.setProperty("status", "error" if invalid else "ok")
            control.style().unpolish(control)
            control.style().polish(control)

    def _invalid_interval_flags(self, values: tuple[int, int, int, int]) -> tuple[bool, bool]:
        window_start_ms, window_end_ms, baseline_start_ms, baseline_end_ms = values
        window_errors = [
            *self.validation.validate_many(window_start_ms, ["integer"], label="Epoch start"),
            *self.validation.validate_many(window_end_ms, ["integer"], label="Epoch end"),
        ]
        baseline_errors = [
            *self.validation.validate_many(baseline_start_ms, ["integer"], label="Baseline start"),
            *self.validation.validate_many(baseline_end_ms, ["integer"], label="Baseline end"),
        ]

        try:
            window_start_ms = self.validation.coerce_int(window_start_ms)
            window_end_ms = self.validation.coerce_int(window_end_ms)
        except ValueError:
            window_errors.append("Epoch window is invalid.")

        try:
            baseline_start_ms = self.validation.coerce_int(baseline_start_ms)
            baseline_end_ms = self.validation.coerce_int(baseline_end_ms)
        except ValueError:
            baseline_errors.append("Baseline window is invalid.")

        if not window_errors and window_end_ms <= window_start_ms:
            window_errors.append("Epoch window: end must be greater than start.")
        if not baseline_errors and baseline_end_ms <= baseline_start_ms:
            baseline_errors.append("Baseline window: end must be greater than start.")

        return bool(window_errors), bool(baseline_errors)

    def _reset_interval_constraints(self) -> None:
        self._reset_interval_controls(self.window_start_slider, self.window_end_slider)
        self._reset_interval_controls(self.baseline_start_slider, self.baseline_end_slider)

    def _apply_interval_constraints(self) -> None:
        self._constrain_interval_controls(self.window_start_slider, self.window_end_slider)
        self._constrain_interval_controls(self.baseline_start_slider, self.baseline_end_slider)

    @classmethod
    def _reset_interval_controls(cls, start_control: QSpinBox, end_control: QSpinBox) -> None:
        previous_start = start_control.blockSignals(True)
        previous_end = end_control.blockSignals(True)
        try:
            start_control.setRange(cls.MIN_TIME_MS, cls.MAX_TIME_MS)
            end_control.setRange(cls.MIN_TIME_MS, cls.MAX_TIME_MS)
        finally:
            start_control.blockSignals(previous_start)
            end_control.blockSignals(previous_end)

    @classmethod
    def _constrain_interval_controls(cls, start_control: QSpinBox, end_control: QSpinBox) -> None:
        previous_start = start_control.blockSignals(True)
        previous_end = end_control.blockSignals(True)
        try:
            start_control.setRange(cls.MIN_TIME_MS, cls.MAX_TIME_MS)
            end_control.setRange(cls.MIN_TIME_MS, cls.MAX_TIME_MS)
            start = start_control.value()
            end = end_control.value()

            if start >= cls.MAX_TIME_MS:
                start_control.setValue(cls.MAX_TIME_MS - cls.INTERVAL_GAP_MS)
                start = start_control.value()
            if end <= cls.MIN_TIME_MS:
                end_control.setValue(cls.MIN_TIME_MS + cls.INTERVAL_GAP_MS)
                end = end_control.value()
            if end <= start:
                if start + cls.INTERVAL_GAP_MS <= cls.MAX_TIME_MS:
                    end_control.setValue(start + cls.INTERVAL_GAP_MS)
                    end = end_control.value()
                else:
                    start_control.setValue(end - cls.INTERVAL_GAP_MS)
                    start = start_control.value()

            start_control.setRange(cls.MIN_TIME_MS, end - cls.INTERVAL_GAP_MS)
            end_control.setRange(start + cls.INTERVAL_GAP_MS, cls.MAX_TIME_MS)
        finally:
            start_control.blockSignals(previous_start)
            end_control.blockSignals(previous_end)

    @staticmethod
    def _clamp_to_control(control: QSpinBox, value: int) -> int:
        return max(control.minimum(), min(control.maximum(), int(value)))

    def _current_values(self) -> tuple[int, int, int, int]:
        return (
            self.window_start_slider.value(),
            self.window_end_slider.value(),
            self.baseline_start_slider.value(),
            self.baseline_end_slider.value(),
        )


class EEGSegmentationWidget(QScrollArea):
    changed = Signal()
    MAX_TARGET_SAMPLING_FREQUENCY_HZ = 2_147_483_647

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        super().__init__()
        step_config = next((step for step in experiment_info.get("workflow", []) if step.get("id") == "segmentation"), {})
        self.config = defaults.get("segmentation", {})
        self.state = state
        self.validation = Validation()
        self.validation_errors: list[str] = []
        self.source_sampling_frequency: float | None = None
        self._updating_events = False
        self._updating_mode = False
        self._updating_strategy = False
        self._syncing_parameter_controls = False
        self._epoch_target = "instant"
        self._normalization_target = "instant"
        self._last_event_signature: tuple[tuple[str, ...], tuple[str, ...]] | None = None
        self._event_specs_by_label: dict[str, Any] = {}

        self.state["segmentation"] = self._initial_segmentation_state(self.state.get("segmentation") or {})
        self._ensure_parameter_state()

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(4, 4, 12, 4)
        root.setSpacing(16)

        title = QLabel(str(step_config.get("title", "Segmentation")))
        title.setObjectName("pageTitle")
        subtitle = QLabel(str(step_config.get("subtitle", "Select events and epoch settings.")))
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        # ------------------------------------------------------------------
        # Signal events
        # ------------------------------------------------------------------
        events_panel = self._panel("Signal events")

        mode_label = QLabel("Segmentation mode")
        mode_label.setObjectName("subgroupTitle")
        events_panel.layout().addWidget(mode_label)

        mode_row = QHBoxLayout()
        self.independent_mode_button = QPushButton("Independent events")
        self.nested_mode_button = QPushButton("Nested events")
        for button in (self.independent_mode_button, self.nested_mode_button):
            button.setCheckable(True)
            button.setProperty("role", "segmentation-mode-button")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.independent_mode_button)
        self.mode_group.addButton(self.nested_mode_button)

        mode_row.addWidget(self.independent_mode_button)
        mode_row.addWidget(self.nested_mode_button)
        events_panel.layout().addLayout(mode_row)

        self.mode_help = QLabel()
        self.mode_help.setObjectName("muted")
        self.mode_help.setWordWrap(True)
        events_panel.layout().addWidget(self.mode_help)

        self.segment_by_response_checkbox = QCheckBox("Segment by response")
        events_panel.layout().addWidget(self.segment_by_response_checkbox)

        self.events_message = QLabel("Load and select a BIDS configuration first.")
        self.events_message.setObjectName("muted")
        self.events_message.setWordWrap(True)
        events_panel.layout().addWidget(self.events_message)

        # Independent mode
        self.independent_panel = QFrame()
        independent_layout = QVBoxLayout(self.independent_panel)
        independent_layout.setContentsMargins(0, 8, 0, 0)

        independent_grid = QGridLayout()
        independent_grid.setHorizontalSpacing(24)

        self.duration_events_list = QListWidget()
        self.instant_events_list = QListWidget()
        self.duration_events_list.setObjectName("durationEventsList")
        self.instant_events_list.setObjectName("instantEventsList")
        for list_widget in (self.duration_events_list, self.instant_events_list):
            list_widget.setProperty("role", "file-list")
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            list_widget.setMinimumHeight(128)

        duration_title = QLabel("Duration events")
        duration_title.setObjectName("subgroupTitle")
        instant_title = QLabel("Instant events")
        instant_title.setObjectName("subgroupTitle")

        independent_grid.addWidget(duration_title, 0, 0)
        independent_grid.addWidget(instant_title, 0, 1)
        independent_grid.addWidget(self.duration_events_list, 1, 0)
        independent_grid.addWidget(self.instant_events_list, 1, 1)
        independent_layout.addLayout(independent_grid)
        events_panel.layout().addWidget(self.independent_panel)

        # Nested mode
        self.nested_panel = QFrame()
        nested_layout = QVBoxLayout(self.nested_panel)
        nested_layout.setContentsMargins(0, 8, 0, 0)
        nested_layout.setSpacing(12)

        nested_note = QLabel(
            "Add duration events as bases, then choose either duration or instant nested events for all bases."
        )
        nested_note.setObjectName("muted")
        nested_note.setWordWrap(True)
        nested_layout.addWidget(nested_note)

        self.add_base_event_button = QPushButton("+ Add base duration event")
        self.add_base_event_button.setProperty("variant", "secondary")
        self.add_base_event_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        nested_layout.addWidget(self.add_base_event_button)

        self.nested_groups_layout = QVBoxLayout()
        self.nested_groups_layout.setContentsMargins(0, 0, 0, 0)
        self.nested_groups_layout.setSpacing(10)
        nested_layout.addLayout(self.nested_groups_layout)
        events_panel.layout().addWidget(self.nested_panel)

        root.addWidget(events_panel)

        self.status_label = QLabel("Select at least one event.")
        self.status_label.setObjectName("selectionStatus")
        self.status_label.setProperty("status", "idle")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.summary_panel = self._panel("Segmentation summary")
        self.summary_layout = QVBoxLayout()
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_panel.layout().addLayout(self.summary_layout)
        root.addWidget(self.summary_panel)

        # ------------------------------------------------------------------
        # Segmentation strategy
        # ------------------------------------------------------------------
        self.strategy_panel = self._panel("Segmentation strategy")
        strategy_row = QHBoxLayout()
        self.window_strategy_button = QPushButton("Window-based segmentation")
        self.onset_strategy_button = QPushButton("Onset-based segmentation")
        for button in (self.window_strategy_button, self.onset_strategy_button):
            button.setCheckable(True)
            button.setProperty("role", "segmentation-strategy-button")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.strategy_group = QButtonGroup(self)
        self.strategy_group.setExclusive(True)
        self.strategy_group.addButton(self.window_strategy_button)
        self.strategy_group.addButton(self.onset_strategy_button)
        strategy_row.addWidget(self.window_strategy_button)
        strategy_row.addWidget(self.onset_strategy_button)
        self.strategy_panel.layout().addLayout(strategy_row)

        self.window_segmentation_widget = WindowSegmentationWidget()
        self.strategy_panel.layout().addWidget(self.window_segmentation_widget)

        self.onset_segmentation_widget = OnsetSegmentationWidget()
        self.strategy_panel.layout().addWidget(self.onset_segmentation_widget)
        root.addWidget(self.strategy_panel)

        # ------------------------------------------------------------------
        # Normalization
        # ------------------------------------------------------------------
        normalization_panel = self._panel("Normalization")
        (self.normalization_target_panel, self.normalization_duration_target_button,
            self.normalization_instant_target_button) = self._target_selector("Edit normalization for")
        normalization_panel.layout().addWidget(self.normalization_target_panel)
        normalization_grid = QGridLayout()
        normalization_panel.layout().addLayout(normalization_grid)

        self.normalization_enabled = QCheckBox("Normalize epochs")
        self.normalization_mode = QComboBox()
        self.normalization_mode.addItem("Mean", "mean")
        self.normalization_mode.addItem("Z-score", "mean_std")
        self.normalization_baseline_hint = QLabel(
            "For onset-based segmentation, normalization uses the baseline interval defined in the segmentation strategy widget."
        )
        self.normalization_baseline_hint.setObjectName("muted")
        self.normalization_baseline_hint.setWordWrap(True)

        normalization_grid.addWidget(self.normalization_enabled, 0, 0, 1, 2)
        normalization_grid.addWidget(QLabel("Mode"), 1, 0)
        normalization_grid.addWidget(self.normalization_mode, 1, 1)
        normalization_grid.addWidget(self.normalization_baseline_hint, 2, 0, 1, 2)
        root.addWidget(normalization_panel)

        # ------------------------------------------------------------------
        # Thresholding
        # ------------------------------------------------------------------
        threshold_panel = self._panel("Thresholding")
        threshold_grid = QGridLayout()
        threshold_panel.layout().addLayout(threshold_grid)

        self.threshold_enabled = QCheckBox("Discard epochs exceeding threshold")
        threshold_note = QLabel("Reject epochs when enough samples/channels exceed the sigma threshold.")
        threshold_note.setObjectName("muted")
        threshold_note.setWordWrap(True)

        self.threshold_sigma = QDoubleSpinBox()
        self.threshold_sigma.setRange(0.1, 1000.0)
        self.threshold_sigma.setDecimals(2)
        self.threshold_sigma.setSingleStep(0.1)

        self.threshold_samples = self._spin(1, 100000, int(self.config["thresholding"]["samples"]))
        self.threshold_channels = self._spin(1, 100000, int(self.config["thresholding"]["channels"]))

        threshold_grid.addWidget(self.threshold_enabled, 0, 0, 1, 2)
        threshold_grid.addWidget(threshold_note, 1, 0, 1, 2)
        threshold_grid.addWidget(QLabel("Sigma"), 2, 0)
        threshold_grid.addWidget(self.threshold_sigma, 2, 1)
        threshold_grid.addWidget(QLabel("Samples"), 3, 0)
        threshold_grid.addWidget(self.threshold_samples, 3, 1)
        threshold_grid.addWidget(QLabel("Channels"), 4, 0)
        threshold_grid.addWidget(self.threshold_channels, 4, 1)
        root.addWidget(threshold_panel)

        # ------------------------------------------------------------------
        # Resampling
        # ------------------------------------------------------------------
        resampling_panel = self._panel("Resampling epochs")
        resampling_grid = QGridLayout()
        resampling_panel.layout().addLayout(resampling_grid)

        self.resampling_enabled = QCheckBox("Resample epochs")
        self.target_sampling_frequency = self._spin(1, self.MAX_TARGET_SAMPLING_FREQUENCY_HZ,
            int(self.config["resampling"]["target_sampling_frequency"]), suffix=" Hz")
        resampling_grid.addWidget(self.resampling_enabled, 0, 0, 1, 2)
        resampling_grid.addWidget(QLabel("Target sample frequency"), 1, 0)
        resampling_grid.addWidget(self.target_sampling_frequency, 1, 1)
        root.addWidget(resampling_panel)
        root.addStretch()
        self.setWidget(content)

        self._load_state()

        for widget in [self.normalization_enabled, self.normalization_mode,
            self.threshold_enabled, self.threshold_sigma, self.threshold_samples, self.threshold_channels,
            self.resampling_enabled, self.target_sampling_frequency]:
            signal = (widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.toggled
                if isinstance(widget, QCheckBox) else widget.valueChanged)
            signal.connect(self._sync)

        self.independent_mode_button.toggled.connect(self._segmentation_mode_changed)
        self.nested_mode_button.toggled.connect(self._segmentation_mode_changed)
        self.window_strategy_button.toggled.connect(lambda checked: self._segmentation_strategy_changed("window-based") if checked else None)
        self.onset_strategy_button.toggled.connect(lambda checked: self._segmentation_strategy_changed("onset-based") if checked else None)
        self.window_segmentation_widget.epoch_length_changed.connect(self._window_preview_epoch_length_changed)
        self.window_segmentation_widget.overlap_changed.connect(self._window_preview_overlap_changed)
        self.onset_segmentation_widget.values_changed.connect(self._onset_preview_values_changed)
        self.normalization_duration_target_button.toggled.connect(lambda checked: self._normalization_target_changed("duration") if checked else None)
        self.normalization_instant_target_button.toggled.connect(lambda checked: self._normalization_target_changed("instant") if checked else None)
        self.segment_by_response_checkbox.toggled.connect(self._segment_by_response_changed)
        self.duration_events_list.itemSelectionChanged.connect(lambda group="duration": self._independent_event_changed(group))
        self.instant_events_list.itemSelectionChanged.connect(lambda group="instant": self._independent_event_changed(group))
        self.add_base_event_button.clicked.connect(self._add_base_events)

        self.on_step_activated()

    def _panel(self, title: str) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)
        return panel

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int, suffix: str = " ms") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _target_or_default(value: Any, default: str = "instant") -> str:
        return str(value) if value in {"duration", "instant"} else default

    @staticmethod
    def _strategy_or_default(value: Any, default: str = "window") -> str:
        if value in {"window-based", "window"}:
            return "window-based"
        if value in {"onset-based", "onset"}:
            return "onset-based"
        return "onset-based" if default in {"onset-based", "onset"} else "window-based"

    @staticmethod
    def _set_button_checked(button: QPushButton, checked: bool) -> None:
        previous = button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(previous)

    def _target_selector(self, label_text: str) -> tuple[QFrame, QPushButton, QPushButton]:
        panel = QFrame()
        panel.setProperty("role", "segmentation-target-panel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("segmentationTargetLabel")
        duration_button = QPushButton("Duration events")
        instant_button = QPushButton("Instant events")
        for button in (duration_button, instant_button):
            button.setCheckable(True)
            button.setProperty("role", "segmentation-target-button")

        button_group = QButtonGroup(panel)
        button_group.setExclusive(True)
        button_group.addButton(duration_button)
        button_group.addButton(instant_button)
        panel.button_group = button_group

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(duration_button)
        layout.addWidget(instant_button)
        return panel, duration_button, instant_button

    def _initial_segmentation_state(self, current: dict[str, Any]) -> dict[str, Any]:
        mode = current.get("segmentation_mode", self.config.get("segmentation_mode", "independent"))
        if mode not in {"independent", "nested"}:
            mode = "independent"

        epoch_parameters = current.get("epoch_parameters")
        if not isinstance(epoch_parameters, dict):
            epoch_parameters = {}
        normalization = current.get("normalization")
        segment_by_response = bool(current.get("segment_by_response", False))
        event_groups = self._initial_event_groups(current, mode, segment_by_response)

        return {
            "segmentation_mode": mode,
            "segmentation_strategy": self._strategy_or_default(
                current.get("segmentation_strategy", self.config.get("segmentation_strategy", "window-based"))
            ),
            "segment_by_response": segment_by_response,
            "event_groups": event_groups,
            "epoch_parameters": {
                "duration_events": deepcopy(epoch_parameters.get("duration_events") or {}),
                "instant_events": deepcopy(epoch_parameters.get("instant_events") or {}),
            },
            "normalization": self._normalized_normalization_state(normalization),
            "thresholding": {
                **deepcopy(self.config.get("thresholding", {})),
                **deepcopy(current.get("thresholding") or {}),
            },
            "resampling": {
                **deepcopy(self.config.get("resampling", {})),
                **deepcopy(current.get("resampling") or {}),
            },
        }

    @staticmethod
    def _event_has_response(event: Any) -> bool:
        if not isinstance(event, dict) or "response" not in event:
            return False
        response = event.get("response")
        if response is None:
            return False
        try:
            if response != response:
                return False
        except TypeError:
            pass
        return str(response).strip().lower() not in {"", "n/a", "na", "nan", "none", "null"}

    @staticmethod
    def _event_trial_type(event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("trial_type") or "").strip()
        return str(event)

    @classmethod
    def _event_label(cls, event: Any) -> str:
        trial_type = cls._event_trial_type(event)
        if isinstance(event, dict) and cls._event_has_response(event):
            return f"{trial_type}_{event.get('response')}"
        return trial_type

    def _event_label_for_current_mode(self, event: Any) -> str:
        if self._segment_by_response_enabled():
            return self._event_label(event)
        return self._event_trial_type(event)

    def _segment_by_response_enabled(self) -> bool:
        if hasattr(self, "segment_by_response_checkbox"):
            return self.segment_by_response_checkbox.isChecked()
        return bool((self.state.get("segmentation") or {}).get("segment_by_response", False))

    def _event_for_storage(self, event: Any, segment_by_response: bool | None = None) -> Any:
        if segment_by_response is None:
            segment_by_response = self._segment_by_response_enabled()

        if isinstance(event, dict):
            trial_type = self._event_trial_type(event)
            if segment_by_response and trial_type and self._event_has_response(event):
                return {"trial_type": trial_type, "response": event.get("response")}
            return trial_type

        label = str(event)
        if segment_by_response:
            spec = self._event_specs_by_label.get(label)
            if isinstance(spec, dict) and self._event_has_response(spec):
                return {"trial_type": self._event_trial_type(spec), "response": spec.get("response")}
        return label

    def _events_for_storage(self, events: list[Any] | None, segment_by_response: bool | None = None) -> list[Any]:
        return [self._event_for_storage(event, segment_by_response) for event in (events or [])]

    def _event_group(self, base_event: Any | None, duration_events: list[Any] | None,
        instant_events: list[Any] | None, segment_by_response: bool | None = None) -> dict[str, Any]:
        return {
            "base_event": self._event_for_storage(base_event, segment_by_response) if base_event else None,
            "duration_events": self._events_for_storage(duration_events, segment_by_response),
            "instant_events": self._events_for_storage(instant_events, segment_by_response),
        }

    def _initial_event_groups(self, current: dict[str, Any], mode: str,
        segment_by_response: bool) -> list[dict[str, Any]]:
        del mode
        event_groups = current.get("event_groups")
        if isinstance(event_groups, list):
            return [self._event_group(group.get("base_event"), group.get("duration_events"),
                group.get("instant_events"), segment_by_response) for group in event_groups if isinstance(group, dict)]
        return []

    @staticmethod
    def _is_broadband_band(band: Any) -> bool:
        if not isinstance(band, dict):
            return False
        band_id = str(band.get("id") or "").lower()
        title = str(band.get("title") or "").lower()
        return band_id == "broadband" or title == "broadband"

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sync_broadband_rows(self, rows: Any, high_cut: float, fallback_broadband: dict[str, Any] | None = None) -> None:
        if not isinstance(rows, list):
            return

        valid_rows: list[dict[str, Any]] = []
        found_broadband = False
        for row in rows:
            if self._is_broadband_band(row):
                row["high_cut"] = high_cut
                found_broadband = True
                valid_rows.append(row)
                continue

            low_cut = self._float_or_none(row.get("low_cut")) if isinstance(row, dict) else None
            row_high_cut = self._float_or_none(row.get("high_cut")) if isinstance(row, dict) else None
            if low_cut is None or row_high_cut is None:
                continue
            if low_cut < row_high_cut <= high_cut:
                valid_rows.append(row)

        if not found_broadband and fallback_broadband is not None:
            valid_rows.append(deepcopy(fallback_broadband))

        rows[:] = valid_rows

    @staticmethod
    def _clamped_filter_low_cut(original_low: float, original_high: float, high_cut: float, minimum_low_cut: float) -> float:
        original_width = max(original_high - original_low, 0.1)
        if original_low < high_cut:
            return max(minimum_low_cut, original_low)

        fallback_width = min(original_width, max(0.1, high_cut - minimum_low_cut))
        low_cut = high_cut - fallback_width
        if low_cut >= high_cut:
            low_cut = high_cut - min(0.1, high_cut / 2.0)
        return max(0.0, min(low_cut, high_cut - 1e-9))

    def _sync_resampling_filters(self, preprocessing: dict[str, Any], high_cut: float, minimum_low_cut: float) -> None:
        filters = preprocessing.get("filters")
        if not isinstance(filters, dict):
            return

        for filter_config in filters.values():
            if not isinstance(filter_config, dict):
                continue
            low_cut = self._float_or_none(filter_config.get("low_cut"))
            filter_high_cut = self._float_or_none(filter_config.get("high_cut"))
            if low_cut is None or filter_high_cut is None:
                continue

            original_high_cut = filter_high_cut
            if filter_high_cut > high_cut:
                filter_config["high_cut"] = high_cut
                filter_high_cut = high_cut

            if low_cut >= filter_high_cut:
                filter_config["low_cut"] = self._clamped_filter_low_cut(
                    low_cut,
                    original_high_cut,
                    high_cut,
                    minimum_low_cut,
                )

    def _sync_resampling_broadband(self) -> None:
        segmentation = self.state.get("segmentation") or {}
        resampling = segmentation.get("resampling") or {}
        if not resampling.get("enabled", False):
            return

        high_cut = float(resampling.get("target_sampling_frequency", self.target_sampling_frequency.value())) / 2.0
        fallback_broadband: dict[str, Any] | None = None
        minimum_low_cut = 0.0

        broadband = self.state.get("broadband")
        if isinstance(broadband, dict):
            broadband_low_cut = self._float_or_none(broadband.get("low_cut"))
            if broadband_low_cut is not None:
                if broadband_low_cut >= high_cut:
                    minimum_low_cut = max(0.0, high_cut - min(0.1, high_cut / 2.0))
                    broadband["low_cut"] = minimum_low_cut
                else:
                    minimum_low_cut = broadband_low_cut
            broadband["high_cut"] = high_cut
            fallback_broadband = deepcopy(broadband)

        preprocessing = self.state.get("preprocessing")
        if isinstance(preprocessing, dict):
            self._sync_resampling_filters(preprocessing, high_cut, minimum_low_cut)
            selected_frequency_bands = preprocessing.get("selected_frequency_bands")
            if not isinstance(selected_frequency_bands, list):
                selected_frequency_bands = []
                preprocessing["selected_frequency_bands"] = selected_frequency_bands
            self._sync_broadband_rows(
                selected_frequency_bands,
                high_cut,
                fallback_broadband,
            )

        feature_params = self.state.get("feature_params")
        if isinstance(feature_params, dict):
            relative_band_power = feature_params.get("relative_band_power")
            if isinstance(relative_band_power, dict):
                self._sync_broadband_rows(
                    relative_band_power.get("selected_frequency_bands"),
                    high_cut,
                )

    def _default_onset_epoch_state(self) -> dict[str, int]:
        defaults = ((self.config.get("epoch_parameters") or {}).get("instant_events") or {})
        return {
            "start": int(defaults.get("start", -300)),
            "end": int(defaults.get("end", 700)),
            "baseline_start": int(defaults.get("baseline_start", -300)),
            "baseline_end": int(defaults.get("baseline_end", 0)),
        }

    def _normalized_onset_epoch_state(self, value: Any | None = None) -> dict[str, int]:
        state = self._default_onset_epoch_state()
        if not isinstance(value, dict):
            return state
        state["start"] = int(value.get("start", state["start"]))
        state["end"] = int(value.get("end", state["end"]))
        state["baseline_start"] = int(value.get("baseline_start", state["baseline_start"]))
        state["baseline_end"] = int(value.get("baseline_end", state["baseline_end"]))
        return state

    def _current_state_strategy(self) -> str:
        if self._segment_by_response_enabled():
            return "onset-based"
        segmentation = self.state.get("segmentation") or {}
        return self._strategy_or_default(segmentation.get("segmentation_strategy"), "window-based")

    def _target_uses_window(self, target: str) -> bool:
        return self._target_or_default(target) == "duration" and self._current_state_strategy() == "window-based"

    def _target_uses_onset(self, target: str) -> bool:
        target = self._target_or_default(target)
        return target == "instant" or (target == "duration" and self._current_state_strategy() == "onset-based")

    def _default_epoch_state(self, target: str) -> dict[str, Any]:
        target = self._target_or_default(target)
        epoch_key = "duration_events" if target == "duration" else "instant_events"
        defaults = ((self.config.get("epoch_parameters") or {}).get(epoch_key) or {})
        if self._target_uses_window(target):
            return {
                "duration_epoch_length_ms": int(defaults.get("duration_epoch_length_ms", 1000)),
                "stride_percent": int(defaults.get("stride_percent", 0)),
            }
        return self._default_onset_epoch_state()

    def _normalized_epoch_state(self, target: str, value: Any | None = None) -> dict[str, Any]:
        target = self._target_or_default(target)
        state = self._default_epoch_state(target)
        if not isinstance(value, dict):
            return state
        if self._target_uses_window(target):
            state["duration_epoch_length_ms"] = int(value.get("duration_epoch_length_ms", state["duration_epoch_length_ms"]))
        else:
            state = self._normalized_onset_epoch_state(value)
            return state
        state["stride_percent"] = int(value.get("stride_percent", state["stride_percent"]))
        return state

    def _default_normalization_state(self) -> dict[str, Any]:
        defaults = self.config.get("normalization") or {}
        state = {
            "enabled": bool(defaults.get("enabled", False)),
            "mode": str(defaults.get("mode", "mean_std")),
        }
        return state

    def _normalized_normalization_state(self, value: Any | None = None) -> dict[str, Any]:
        state = self._default_normalization_state()
        if value is None or value == {}:
            return state
        if not isinstance(value, dict):
            raise ValueError("Segmentation normalization must be a dictionary with 'enabled' and 'mode'.")
        if "duration" in value or "instant" in value:
            raise ValueError("Segmentation normalization must not be stored per event type.")
        missing_keys = {"enabled", "mode"} - set(value)
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Segmentation normalization is missing required key(s): {missing}.")
        state["enabled"] = bool(value["enabled"])
        state["mode"] = str(value["mode"])
        return state

    def _active_event_types_from_state(self) -> tuple[bool, bool]:
        segmentation = self.state["segmentation"]
        if segmentation.get("segmentation_mode") == "nested":
            return self._nested_event_types()
        duration_events, instant_events = self._independent_events_from_state()
        return bool(duration_events), bool(instant_events)

    def _ensure_parameter_state(self, has_duration: bool | None = None, has_instant: bool | None = None) -> None:
        if has_duration is None or has_instant is None:
            has_duration, has_instant = self._active_event_types_from_state()

        segmentation = self.state["segmentation"]
        epoch_parameters = segmentation.get("epoch_parameters") if isinstance(segmentation.get("epoch_parameters"), dict) else {}
        normalization = segmentation.get("normalization")
        strategy = self._strategy_for_active_types(
            bool(has_duration),
            bool(has_instant),
            segmentation.get("segmentation_strategy", self.config.get("segmentation_strategy", "window-based")),
        )
        segmentation["segmentation_strategy"] = strategy
        if has_duration or has_instant:
            if strategy == "window-based" and has_duration:
                segmentation["epoch_parameters"] = {
                    "duration_events": self._normalized_epoch_state("duration", epoch_parameters.get("duration_events")),
                    "instant_events": {},
                }
            else:
                onset_parameters = epoch_parameters.get("instant_events") or epoch_parameters.get("duration_events")
                segmentation["epoch_parameters"] = {
                    "duration_events": {},
                    "instant_events": self._normalized_epoch_state("instant", onset_parameters),
                }
        else:
            segmentation["epoch_parameters"] = {"duration_events": {}, "instant_events": {}}
        segmentation["normalization"] = self._normalized_normalization_state(normalization)

    def _epoch_state(self, target: str, create: bool = True) -> dict[str, Any]:
        target = self._target_or_default(target)
        epoch_parameters = self.state["segmentation"].setdefault("epoch_parameters", {"duration_events": {}, "instant_events": {}})
        parameter_key = "duration_events" if self._target_uses_window(target) else "instant_events"
        current = epoch_parameters.get(parameter_key)
        if create:
            current = self._normalized_epoch_state(target, current)
            epoch_parameters[parameter_key] = current
            if parameter_key == "duration_events":
                epoch_parameters["instant_events"] = {}
            else:
                epoch_parameters["duration_events"] = {}
        return current if isinstance(current, dict) and current else self._default_epoch_state(target)

    def _normalization_state(self, target: str, create: bool = True) -> dict[str, Any]:
        del target
        normalization = self.state["segmentation"].get("normalization")
        current = self._normalized_normalization_state(normalization)
        if create:
            self.state["segmentation"]["normalization"] = current
        return current

    def _set_normalization_target_buttons(self) -> None:
        self._set_button_checked(self.normalization_duration_target_button, self._normalization_target == "duration")
        self._set_button_checked(self.normalization_instant_target_button, self._normalization_target == "instant")

    def _store_epoch_controls(self, target: str) -> None:
        if self._syncing_parameter_controls:
            return
        target = self._target_or_default(target)
        epoch_parameters = self.state["segmentation"].setdefault("epoch_parameters", {"duration_events": {}, "instant_events": {}})
        if self._target_uses_window(target):
            epoch_parameters["duration_events"] = {
                "duration_epoch_length_ms": self.window_segmentation_widget.epoch_slider.value(),
                "stride_percent": self.window_segmentation_widget.overlap_slider.value(),
            }
            epoch_parameters["instant_events"] = {}
        else:
            epoch_parameters["duration_events"] = {}
            epoch_parameters["instant_events"] = {
                "start": self.onset_segmentation_widget.window_start_slider.value(),
                "end": self.onset_segmentation_widget.window_end_slider.value(),
                "baseline_start": self.onset_segmentation_widget.baseline_start_slider.value(),
                "baseline_end": self.onset_segmentation_widget.baseline_end_slider.value(),
            }

    def _set_normalization_controls_from_state(self, target: str) -> None:
        state = self._normalization_state(target, create=False)
        default = self._default_normalization_state()
        previous = self._syncing_parameter_controls
        self._syncing_parameter_controls = True
        try:
            self.normalization_enabled.setChecked(bool(state.get("enabled", default["enabled"])))
            index = self.normalization_mode.findData(state.get("mode", default["mode"]))
            self.normalization_mode.setCurrentIndex(max(0, index))
        finally:
            self._syncing_parameter_controls = previous

    def _store_normalization_controls(self, target: str) -> None:
        if self._syncing_parameter_controls:
            return
        state = self._normalization_state(target)
        state["enabled"] = self.normalization_enabled.isChecked()
        state["mode"] = self.normalization_mode.currentData()

    def _selection_mode_for_state(self, mode: str, selected_duration_events: list[str], selected_instant_events: list[str]) -> str:
        if mode == "nested":
            return "nested"
        if selected_duration_events:
            return "duration"
        if selected_instant_events:
            return "instant"
        return "none"

    def _target_for_mode(self, mode: str, selection_mode: str, current_target: str) -> str:
        if mode == "nested":
            has_duration, has_instant = self._nested_event_types()
            if has_duration and not has_instant:
                return "duration"
            if has_instant and not has_duration:
                return "instant"
            return self._target_or_default(current_target)
        if selection_mode == "duration":
            return "duration"
        return "instant"

    def _current_segmentation_strategy(self) -> str:
        if self._segment_by_response_enabled():
            return "onset-based"
        return "window-based" if self.window_strategy_button.isChecked() else "onset-based"

    def _strategy_for_active_types(self, has_duration: bool, has_instant: bool, current_strategy: str) -> str:
        if self._segment_by_response_enabled():
            return "onset-based"
        if has_instant and not has_duration:
            return "onset-based"
        if has_duration and not has_instant:
            return self._strategy_or_default(current_strategy, "window-based")
        return self._strategy_or_default(current_strategy, "window-based")

    def _set_strategy_buttons(self, strategy: str) -> None:
        previous = self._updating_strategy
        self._updating_strategy = True
        try:
            self._set_button_checked(self.window_strategy_button, strategy == "window-based")
            self._set_button_checked(self.onset_strategy_button, strategy == "onset-based")
        finally:
            self._updating_strategy = previous

    def _align_segmentation_strategy(self, has_duration: bool, has_instant: bool) -> str:
        current_strategy = self.state["segmentation"].get("segmentation_strategy", self._current_segmentation_strategy())
        strategy = self._strategy_for_active_types(has_duration, has_instant, current_strategy)
        self.state["segmentation"]["segmentation_strategy"] = strategy
        self._set_strategy_buttons(strategy)
        return strategy

    def _align_parameter_targets(self, mode: str, selection_mode: str) -> None:
        epoch_target = self._target_for_mode(mode, selection_mode, self._epoch_target)
        normalization_target = self._target_for_mode(mode, selection_mode, self._normalization_target)

        if epoch_target != self._epoch_target:
            self._epoch_target = epoch_target

        if normalization_target != self._normalization_target:
            self._normalization_target = normalization_target
            self._set_normalization_target_buttons()
            self._set_normalization_controls_from_state(normalization_target)

    def _segmentation_strategy_changed(self, strategy: str) -> None:
        if self._updating_strategy:
            return
        if self._segment_by_response_enabled():
            self._set_strategy_buttons("onset-based")
            self.state["segmentation"]["segmentation_strategy"] = "onset-based"
            return
        strategy = self._strategy_or_default(strategy)
        if strategy == self.state["segmentation"].get("segmentation_strategy"):
            return
        self._store_epoch_controls(self._epoch_target)
        self._store_normalization_controls(self._normalization_target)
        self.state["segmentation"]["segmentation_strategy"] = strategy
        self._set_normalization_controls_from_state(self._normalization_target)
        self._sync_strategy_preview()
        self._sync()

    def _window_preview_epoch_length_changed(self, value: int) -> None:
        del value
        if self._syncing_parameter_controls or self._current_state_strategy() != "window-based":
            return
        if self._epoch_target == "duration":
            self._sync()

    def _window_preview_overlap_changed(self, value: int) -> None:
        del value
        if self._syncing_parameter_controls or self._current_state_strategy() != "window-based":
            return
        if self._epoch_target == "duration":
            self._sync()

    def _onset_preview_values_changed(self, window_start: int, window_end: int,
        baseline_start: int, baseline_end: int) -> None:
        del window_start, window_end, baseline_start, baseline_end
        if self._syncing_parameter_controls or not self._target_uses_onset(self._epoch_target):
            return
        self._sync()

    def _sync_strategy_preview(self) -> None:
        if self._target_uses_window(self._epoch_target):
            state = self._epoch_state(self._epoch_target, create=False)
            default = self._default_epoch_state("duration")
            self.window_segmentation_widget.set_values(
                int(state.get("duration_epoch_length_ms", default["duration_epoch_length_ms"])),
                int(state.get("stride_percent", default["stride_percent"])),
            )
        if self._target_uses_onset(self._epoch_target):
            state = self._epoch_state(self._epoch_target, create=False)
            self.onset_segmentation_widget.set_values(
                int(state.get("start", self._default_onset_epoch_state()["start"])),
                int(state.get("end", self._default_onset_epoch_state()["end"])),
                int(state.get("baseline_start", self._default_onset_epoch_state()["baseline_start"])),
                int(state.get("baseline_end", self._default_onset_epoch_state()["baseline_end"])),
            )

    def _normalization_target_changed(self, target: str) -> None:
        target = self._target_or_default(target)
        if self._syncing_parameter_controls or target == self._normalization_target:
            return
        self._store_normalization_controls(self._normalization_target)
        self._normalization_target = target
        self._set_normalization_controls_from_state(target)
        self._sync()

    def _segment_by_response_changed(self, checked: bool) -> None:
        self.state["segmentation"]["segment_by_response"] = bool(checked)
        if checked:
            self.state["segmentation"]["segmentation_strategy"] = "onset-based"
            self._set_strategy_buttons("onset-based")
        self._last_event_signature = None
        self._refresh_events()
        self._sync()

    def _load_state(self) -> None:
        segmentation = self.state["segmentation"]
        thresholding = segmentation.get("thresholding", {})
        resampling = segmentation.get("resampling", {})

        self.threshold_enabled.setChecked(bool(thresholding.get("enabled", self.config["thresholding"]["enabled"])))
        self.threshold_sigma.setValue(float(thresholding.get("sigma", self.config["thresholding"]["sigma"])))
        self.threshold_samples.setValue(int(thresholding.get("samples", self.config["thresholding"]["samples"])))
        self.threshold_channels.setValue(int(thresholding.get("channels", self.config["thresholding"]["channels"])))
        self.resampling_enabled.setChecked(bool(resampling.get("enabled", self.config["resampling"]["enabled"])))
        self.target_sampling_frequency.setValue(int(resampling.get("target_sampling_frequency",
                    self.config["resampling"]["target_sampling_frequency"])))
        self.segment_by_response_checkbox.setChecked(bool(segmentation.get("segment_by_response", False)))

        requested_mode = segmentation.get("segmentation_mode")
        if requested_mode not in {"independent", "nested"}:
            requested_mode = "nested" if any(group.get("base_event") for group in segmentation.get("event_groups", [])) else "independent"

        self._updating_mode = True
        self.independent_mode_button.setChecked(requested_mode == "independent")
        self.nested_mode_button.setChecked(requested_mode == "nested")
        self._updating_mode = False

        has_duration, has_instant = self._active_event_types_from_state()
        default_target = "duration" if has_duration and not has_instant else "instant"
        strategy = self._strategy_for_active_types(
            has_duration,
            has_instant,
            segmentation.get("segmentation_strategy", self.config.get("segmentation_strategy", "window-based")),
        )
        segmentation["segmentation_strategy"] = strategy
        self._epoch_target = default_target
        self._normalization_target = default_target
        self._set_strategy_buttons(strategy)
        self._ensure_parameter_state(has_duration, has_instant)
        self._set_normalization_target_buttons()
        self._set_normalization_controls_from_state(self._normalization_target)
        self._sync_strategy_preview()

    @staticmethod
    def _valid_response_value(response: Any) -> bool:
        if response is None:
            return False
        try:
            if response != response:
                return False
        except TypeError:
            pass
        return str(response).strip().lower() not in {"", "n/a", "na", "nan", "none", "null"}

    def _responses_for_event(self, event_name: str) -> list[Any]:
        event_responses = self.state.get("event_responses")
        if not isinstance(event_responses, dict):
            return []
        responses = event_responses.get(event_name) or []
        if not isinstance(responses, list):
            return []
        return [response for response in responses if self._valid_response_value(response)]

    def _expand_events_by_response(self, event_names: list[str]) -> list[str]:
        expanded_events: list[str] = []
        for event_name in event_names:
            responses = self._responses_for_event(event_name)
            if not responses:
                self._event_specs_by_label[event_name] = event_name
                expanded_events.append(event_name)
                continue

            for response in responses:
                event_spec = {"trial_type": event_name, "response": response}
                event_label = self._event_label(event_spec)
                self._event_specs_by_label[event_label] = event_spec
                expanded_events.append(event_label)
        return expanded_events

    def _event_names(self) -> tuple[list[str], list[str]]:
        duration_events = list(self.state.get("duration_events") or [])
        instant_events = list(self.state.get("instant_events") or [])
        if not duration_events and not instant_events:
            instant_events = list(self.state.get("event_types") or [])
        duration_events = [str(event) for event in duration_events]
        instant_events = [str(event) for event in instant_events]

        self._event_specs_by_label = {}
        if not self._segment_by_response_enabled():
            for event_name in duration_events + instant_events:
                self._event_specs_by_label[event_name] = event_name
            return duration_events, instant_events

        duration_events = self._expand_events_by_response(duration_events)
        instant_events = self._expand_events_by_response(instant_events)
        return duration_events, instant_events

    def _current_segmentation_mode(self) -> str:
        return "nested" if self.nested_mode_button.isChecked() else "independent"

    def _nested_mode_available(self) -> bool:
        duration_events, instant_events = self._event_names()
        if not duration_events and not instant_events:
            return False
        # Nested mode only has no meaningful relationship when there is a
        # single duration event and no instant event to place inside it.
        return not (len(duration_events) == 1 and not instant_events)

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            if item.layout():
                self._clear_layout(item.layout())

    def _clear_event_group(self, group: str) -> None:
        list_widget = (self.instant_events_list if group == "instant" else self.duration_events_list)
        list_widget.blockSignals(True)
        list_widget.clearSelection()
        list_widget.blockSignals(False)

    def _independent_events_from_state(self) -> tuple[list[str], list[str]]:
        duration_events: list[str] = []
        instant_events: list[str] = []
        for group in self.state["segmentation"].get("event_groups") or []:
            if group.get("base_event"):
                continue
            duration_events.extend(self._event_label_for_current_mode(event) for event in group.get("duration_events") or [])
            instant_events.extend(self._event_label_for_current_mode(event) for event in group.get("instant_events") or [])
        return list(dict.fromkeys(duration_events)), list(dict.fromkeys(instant_events))

    def _refresh_events(self) -> None:
        duration_events, instant_events = self._event_names()
        signature = (tuple(duration_events), tuple(instant_events))
        segmentation = self.state["segmentation"]

        saved_duration, saved_instant = self._independent_events_from_state()
        saved_duration = set(saved_duration)
        saved_instant = set(saved_instant)

        if signature != self._last_event_signature:
            saved_duration &= set(duration_events)
            saved_instant &= set(instant_events)

            if saved_duration and saved_instant:
                saved_instant.clear()

            valid_event_groups = []
            for group in segmentation.get("event_groups") or []:
                base_event = group.get("base_event")
                if not base_event:
                    if saved_duration or saved_instant:
                        valid_event_groups.append(self._event_group(None, list(saved_duration), list(saved_instant)))
                    continue
                base_event_label = self._event_label_for_current_mode(base_event)
                if base_event_label not in duration_events:
                    continue

                nested_duration = [
                    self._event_label_for_current_mode(event)
                    for event in group.get("duration_events") or []
                    if self._event_label_for_current_mode(event) in duration_events
                    and self._event_label_for_current_mode(event) != base_event_label
                ]
                nested_instant = [
                    self._event_label_for_current_mode(event)
                    for event in group.get("instant_events") or []
                    if self._event_label_for_current_mode(event) in instant_events
                ]
                valid_event_groups.append(self._event_group(base_event_label, list(dict.fromkeys(nested_duration)),
                    list(dict.fromkeys(nested_instant))))
            segmentation["event_groups"] = valid_event_groups

        self._updating_events = True
        self.duration_events_list.blockSignals(True)
        self.instant_events_list.blockSignals(True)

        self.duration_events_list.clear()
        self.instant_events_list.clear()

        self.events_message.setVisible(not (duration_events or instant_events))

        for event_name in duration_events:
            item = QListWidgetItem(str(event_name))
            item.setData(Qt.ItemDataRole.UserRole, self._event_specs_by_label.get(event_name, event_name))
            self.duration_events_list.addItem(item)
            item.setSelected(event_name in saved_duration)

        for event_name in instant_events:
            item = QListWidgetItem(str(event_name))
            item.setData(Qt.ItemDataRole.UserRole, self._event_specs_by_label.get(event_name, event_name))
            self.instant_events_list.addItem(item)
            item.setSelected(event_name in saved_instant)

        self.duration_events_list.blockSignals(False)
        self.instant_events_list.blockSignals(False)

        self._last_event_signature = signature
        self._updating_events = False

        self._update_nested_mode_availability()
        self._refresh_nested_groups_editor()

    def _update_nested_mode_availability(self) -> None:
        available = self._nested_mode_available()
        self.nested_mode_button.setEnabled(available)

        if available:
            self.nested_mode_button.setToolTip("Create relationships between a base duration event and nested duration or instant events.")
        else:
            self.nested_mode_button.setToolTip("Nested mode requires either an instant event or at least two duration events.")

        if not available and self.nested_mode_button.isChecked():
            self._updating_mode = True
            self.independent_mode_button.setChecked(True)
            self._updating_mode = False
            self.state["segmentation"]["event_groups"] = []

    def _current_event_selection(self) -> tuple[list[str], list[str]]:
        duration = [item.text() for item in self.duration_events_list.selectedItems()]
        instant = [item.text() for item in self.instant_events_list.selectedItems()]
        return duration, instant

    def _independent_event_changed(self, group: str) -> None:
        if self._updating_events or self._current_segmentation_mode() != "independent":
            return

        duration_events, instant_events = self._current_event_selection()
        if group == "duration" and duration_events:
            self._clear_event_group("instant")
        elif group == "instant" and instant_events:
            self._clear_event_group("duration")

        self._sync()

    def _segmentation_mode_changed(self, checked: bool) -> None:
        if self._updating_mode or not checked:
            return

        if self.nested_mode_button.isChecked() and not self._nested_mode_available():
            self._updating_mode = True
            self.independent_mode_button.setChecked(True)
            self._updating_mode = False

        self._sync()

    def _event_groups(self) -> list[dict[str, Any]]:
        return self.state["segmentation"].setdefault("event_groups", [])

    def _nested_groups(self) -> list[dict[str, Any]]:
        event_groups = self._event_groups()
        event_groups[:] = [group for group in event_groups if group.get("base_event")]
        return event_groups

    def _available_base_events(self) -> list[str]:
        duration_events, _ = self._event_names()
        existing_bases = {self._event_label_for_current_mode(group.get("base_event"))
            for group in self._nested_groups()}
        return [event for event in duration_events if event not in existing_bases]

    def _nested_group_for(self, base_event: str) -> dict[str, Any] | None:
        return next((nested_group for nested_group in self._nested_groups()
            if self._event_label_for_current_mode(nested_group.get("base_event")) == base_event), None)

    def _available_nested_events(self, group: dict[str, Any], kind: str) -> list[str]:
        nested_child_type = self._nested_child_type()
        if nested_child_type == "mixed" or (
            nested_child_type in {"duration", "instant"} and nested_child_type != kind
        ):
            return []

        duration_events, instant_events = self._event_names()
        base_event = self._event_label_for_current_mode(group.get("base_event"))
        state_key = ("duration_events" if kind == "duration" else "instant_events")
        already_selected = {self._event_label_for_current_mode(event) for event in group.get(state_key) or []}

        if kind == "duration":
            return [event for event in duration_events if event != base_event and event not in already_selected]

        return [event for event in instant_events if event not in already_selected]

    @staticmethod
    def _set_add_button_state(button: QPushButton, available_events: list[str], available_tooltip: str,
        unavailable_tooltip: str) -> None:
        has_available_events = bool(available_events)
        button.setEnabled(has_available_events)
        button.setToolTip(available_tooltip if has_available_events else unavailable_tooltip)

    def _add_base_events(self) -> None:
        available_events = self._available_base_events()
        if not available_events:
            return

        selected_events = self._select_multiple_events(title="Add base duration events",
            description="Select one or more duration events to use as bases.", events=available_events, kind="duration")
        if not selected_events:
            return

        for event_name in selected_events:
            self._nested_groups().append(self._event_group(event_name, [], []))
        self._sync()

    def _add_nested_events(self, base_event: str, kind: str) -> None:
        kind = self._target_or_default(kind)
        nested_child_type = self._nested_child_type()
        if nested_child_type == "mixed" or (
            nested_child_type in {"duration", "instant"} and nested_child_type != kind
        ):
            return

        group = self._nested_group_for(base_event)
        if group is None:
            return

        state_key = ("duration_events" if kind == "duration" else "instant_events")
        available_events = self._available_nested_events(group, kind)
        if not available_events:
            return

        if kind == "duration":
            description = f"Select duration events contained within {base_event}."
            title = "Add nested duration events"
        else:
            description = f"Select instant events contained within {base_event}."
            title = "Add nested instant events"

        selected_events = self._select_multiple_events(title=title, description=description, events=available_events,
            kind=kind)
        if not selected_events:
            return
        existing_events = [self._event_label_for_current_mode(event) for event in group.get(state_key) or []]
        group[state_key] = self._events_for_storage(list(dict.fromkeys([*existing_events, *selected_events])))
        self._sync()

    def _remove_base_event(self, base_event: str) -> None:
        self.state["segmentation"]["event_groups"] = [group for group in self._nested_groups()
            if self._event_label_for_current_mode(group.get("base_event")) != base_event]
        self._sync()

    def _remove_nested_event(self, base_event: str, event_name: str, kind: str) -> None:
        state_key = ("duration_events" if kind == "duration" else "instant_events")
        for group in self._nested_groups():
            if self._event_label_for_current_mode(group.get("base_event")) == base_event:
                group[state_key] = [event for event in group.get(state_key) or []
                    if self._event_label_for_current_mode(event) != event_name]
                break
        self._sync()

    def _select_multiple_events(self, title: str, description: str, events: list[str], kind: str) -> list[str]:
        if not events:
            return []

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        message = QLabel(description)
        message.setWordWrap(True)
        layout.addWidget(message)

        event_list = QListWidget()
        event_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        event_list.setMinimumHeight(180)
        event_list.setProperty("role", "file-list")
        event_list.setObjectName("durationEventsList" if kind == "duration" else "instantEventsList")
        event_list.addItems(events)
        layout.addWidget(event_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []

        return [item.text() for item in event_list.selectedItems()]

    def _refresh_nested_groups_editor(self) -> None:
        self._clear_layout(self.nested_groups_layout)
        if self._current_segmentation_mode() != "nested":
            return
        available_base_events = self._available_base_events()
        self._set_add_button_state(self.add_base_event_button, available_base_events,"Add duration events as base events.",
            "All available duration events are already configured as base events.")
        nested_groups = self._nested_groups()
        nested_child_type = self._nested_child_type()

        if not nested_groups:
            empty = QLabel("No base events added.")
            empty.setObjectName("muted")
            self.nested_groups_layout.addWidget(empty)
            return

        for group in nested_groups:
            base_event = self._event_label_for_current_mode(group.get("base_event"))
            group_container = QFrame()
            group_container.setProperty("role", "nested-group-editor")
            group_layout = QVBoxLayout(group_container)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(8)

            card = QFrame()
            card.setProperty("role", "nested-base-event")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)

            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 0)
            header.setSpacing(8)
            base_title = QLabel(base_event)
            base_title.setObjectName("nestedBaseEventTitle")
            base_title.setWordWrap(True)
            header.addWidget(base_title)
            header.addStretch()

            remove_base_button = QPushButton("Remove")
            remove_base_button.setProperty("variant", "ghost")
            remove_base_button.clicked.connect(lambda _=False, event=base_event: self._remove_base_event(event))
            header.addWidget(remove_base_button)
            card_layout.addLayout(header)

            children_container = QFrame()
            children_container.setProperty("role", "nested-contained-events")
            children_row = QHBoxLayout(children_container)
            children_row.setContentsMargins(10, 8, 10, 8)
            children_row.setSpacing(6)
            nested_duration = [self._event_label_for_current_mode(event)
                for event in group.get("duration_events") or []]
            nested_instant = [self._event_label_for_current_mode(event)
                for event in group.get("instant_events") or []]

            for event_name in nested_duration:
                children_row.addWidget(self._summary_chip(event_name, "duration", removable=True,
                    on_remove=lambda _=False, event=event_name, base=base_event: self._remove_nested_event(base, event, "duration"), compact=True))

            for event_name in nested_instant:
                children_row.addWidget(self._summary_chip(event_name, "instant", removable=True,
                    on_remove=lambda _=False, event=event_name, base=base_event: self._remove_nested_event(base, event,"instant"), compact=True))

            if not nested_duration and not nested_instant:
                empty = QLabel("No nested events selected.")
                empty.setObjectName("muted")
                children_row.addWidget(empty)

            children_row.addStretch()
            card_layout.addWidget(children_container)
            group_layout.addWidget(card)

            actions = QHBoxLayout()
            actions.setContentsMargins(0, 0, 0, 0)
            actions.setSpacing(8)
            add_duration_button = QPushButton("+ Add duration event")
            add_instant_button = QPushButton("+ Add instant event")
            add_duration_button.setProperty("variant", "secondary")
            add_duration_button.setProperty("role", "segmentation-duration-action")
            add_instant_button.setProperty("variant", "secondary")
            add_instant_button.setProperty("role", "segmentation-instant-action")
            available_nested_duration = self._available_nested_events(group, "duration")
            available_nested_instant = self._available_nested_events(group, "instant")
            mixed_tooltip = (
                "Nested mode already contains both duration and instant events. Remove one type before adding more."
            )
            duration_unavailable_tooltip = (
                mixed_tooltip if nested_child_type == "mixed"
                else "Nested mode is already using instant nested events."
                if nested_child_type == "instant"
                else "No additional duration events are available for this base event."
            )
            instant_unavailable_tooltip = (
                mixed_tooltip if nested_child_type == "mixed"
                else "Nested mode is already using duration nested events."
                if nested_child_type == "duration"
                else "No additional instant events are available for this base event."
            )
            self._set_add_button_state(add_duration_button, available_nested_duration,
                f"Add duration events contained within {base_event}.",
                duration_unavailable_tooltip)
            self._set_add_button_state(add_instant_button, available_nested_instant,
                f"Add instant events contained within {base_event}.",
                instant_unavailable_tooltip)

            add_duration_button.clicked.connect(lambda _=False, base=base_event: self._add_nested_events(base, "duration"))
            add_instant_button.clicked.connect(lambda _=False, base=base_event: self._add_nested_events(base, "instant"))

            actions.addWidget(add_duration_button)
            actions.addWidget(add_instant_button)
            actions.addStretch()
            group_layout.addLayout(actions)

            self.nested_groups_layout.addWidget(group_container)

    def _nested_event_types(self) -> tuple[bool, bool]:
        nested_groups = self._nested_groups()
        has_duration = any(group.get("duration_events") for group in nested_groups)
        has_instant = any(group.get("instant_events") for group in nested_groups)
        return has_duration, has_instant

    def _nested_child_type(self) -> str | None:
        has_duration, has_instant = self._nested_event_types()
        if has_duration and has_instant:
            return "mixed"
        if has_duration:
            return "duration"
        if has_instant:
            return "instant"
        return None

    @staticmethod
    def _set_visible(widgets: list[QWidget], visible: bool) -> None:
        for widget in widgets:
            widget.setVisible(visible)

    def _set_dependent_enabled(self, mode: str) -> None:
        independent = mode == "independent"
        nested = mode == "nested"

        self.independent_panel.setVisible(independent)
        self.nested_panel.setVisible(nested)

        if independent:
            duration_events, instant_events = self._current_event_selection()
            has_duration_epochs = bool(duration_events)
            has_instant_epochs = bool(instant_events)
        else:
            has_duration_epochs, has_instant_epochs = self._nested_event_types()

        strategy = self._strategy_for_active_types(has_duration_epochs, has_instant_epochs, self._current_state_strategy())
        has_active_events = has_duration_epochs or has_instant_epochs
        segment_by_response = self._segment_by_response_enabled()
        duration_strategy_available = has_duration_epochs and not has_instant_epochs and not segment_by_response
        self.strategy_panel.setVisible(has_active_events)
        self.window_strategy_button.setVisible(duration_strategy_available)
        self.window_strategy_button.setEnabled(duration_strategy_available)
        self.onset_strategy_button.setEnabled(has_active_events)
        self.window_segmentation_widget.setVisible(duration_strategy_available and strategy == "window-based")
        self.onset_segmentation_widget.setVisible(has_active_events and strategy == "onset-based")

        self.normalization_target_panel.setVisible(False)

        thresholding = self.threshold_enabled.isChecked()
        resampling = self.resampling_enabled.isChecked()
        normalization_target = self._target_or_default(self._normalization_target)

        normalization = self.normalization_enabled.isChecked()
        self.normalization_mode.setEnabled(normalization)
        self.normalization_baseline_hint.setVisible(
            has_instant_epochs and normalization_target == "instant"
            or has_duration_epochs and normalization_target == "duration" and strategy == "onset-based"
        )

        for widget in (self.threshold_sigma, self.threshold_samples, self.threshold_channels):
            widget.setEnabled(thresholding)

        self.target_sampling_frequency.setEnabled(resampling)

        if independent:
            self.mode_help.setText("Select either duration events or instant events. The two lists are mutually exclusive.")
        else:
            self.mode_help.setText("Create parent-child relationships using one nested event type across all base events.")

    def _refresh_status_style(self) -> None:
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _update_status_label(self, mode: str, duration_events: list[str], instant_events: list[str]) -> None:
        available_duration_events, available_instant_events = self._event_names()

        if not available_duration_events and not available_instant_events:
            text = "Load and select a BIDS configuration first."
            status = "idle"
        elif self.validation_errors:
            text = self.validation_errors[0]
            status = "idle"
        elif mode == "nested":
            nested_groups = self._nested_groups()
            relation_count = sum(len(group.get("duration_events") or []) + len(group.get("instant_events") or [])
                for group in nested_groups)
            text = (f"{len(nested_groups)} nested group(s) with " f"{relation_count} relationship(s) configured.")
            status = "ready"
        elif duration_events:
            text = f"{len(duration_events)} duration event(s) selected."
            status = "ready"
        elif instant_events:
            text = f"{len(instant_events)} instant event(s) selected."
            status = "ready"
        else:
            text = "Select at least one event."
            status = "idle"

        self.status_label.setText(text)
        self.status_label.setProperty("status", status)
        self._refresh_status_style()

    def _summary_chip(self, text: str, kind: str, removable: bool = False, on_remove: Any | None = None,
        base: bool = False, compact: bool = False) -> QFrame:
        chip = QFrame()
        if compact:
            chip.setProperty("compact", "true")
        chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        if base and kind == "duration":
            chip.setObjectName("summaryBaseDurationChip")
        elif kind == "duration":
            chip.setObjectName("summaryDurationChip")
        else:
            chip.setObjectName("summaryInstantChip")

        use_corner_remove = compact and removable and on_remove is not None
        if use_corner_remove:
            layout = QGridLayout(chip)
            layout.setContentsMargins(8, 5, 3, 4)
            layout.setHorizontalSpacing(4)
            layout.setVerticalSpacing(0)
        else:
            layout = QHBoxLayout(chip)
            if compact:
                layout.setContentsMargins(8, 3, 8, 3)
                layout.setSpacing(3)
            else:
                layout.setContentsMargins(10, 6, 10, 6)
                layout.setSpacing(5)

        label = QLabel(text)
        label.setWordWrap(True)
        if use_corner_remove:
            layout.addWidget(label, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            layout.addWidget(label)

        if removable and on_remove is not None:
            remove_button = QPushButton("x")
            remove_button.setObjectName("chipRemoveButton")
            remove_button.setProperty("role", "chip-remove-button")
            remove_button.setFixedSize(16 if compact else 20, 16 if compact else 20)
            remove_button.setToolTip(f"Remove {text}")
            remove_button.clicked.connect(on_remove)
            if use_corner_remove:
                layout.addWidget(
                    remove_button,
                    0,
                    1,
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
                )
            else:
                layout.addWidget(remove_button)

        return chip

    def _refresh_summary(self, mode: str, duration_events: list[str], instant_events: list[str]) -> None:
        self.summary_panel.setVisible(mode != "nested")
        self._clear_layout(self.summary_layout)

        if mode == "nested":
            return

        if not (duration_events or instant_events):
            empty = QLabel("No events selected.")
            empty.setObjectName("muted")
            self.summary_layout.addWidget(empty)
            return

        row = QHBoxLayout()
        chip_kind = "duration" if duration_events else "instant"
        for event_name in duration_events + instant_events:
            row.addWidget(self._summary_chip(event_name, chip_kind))
        row.addStretch()
        self.summary_layout.addLayout(row)

    def _active_event_types(self, mode: str, selection_mode: str) -> tuple[bool, bool]:
        if mode == "nested":
            return self._nested_event_types()
        return selection_mode == "duration", selection_mode == "instant"

    def _sync(self, *_: Any) -> None:
        if self._syncing_parameter_controls:
            return

        mode = self._current_segmentation_mode()
        duration_events, instant_events = self._current_event_selection()

        if mode == "nested":
            selected_duration_events: list[str] = []
            selected_instant_events: list[str] = []
            event_groups = deepcopy(self._nested_groups())
        else:
            selected_duration_events = duration_events
            selected_instant_events = instant_events
            event_groups = ([self._event_group(None, selected_duration_events, selected_instant_events)]
                if selected_duration_events or selected_instant_events else [])

        selection_mode = self._selection_mode_for_state(mode, selected_duration_events, selected_instant_events)
        has_duration_epochs, has_instant_epochs = self._active_event_types(mode, selection_mode)
        segmentation_strategy = self._strategy_for_active_types(
            has_duration_epochs,
            has_instant_epochs,
            self._current_segmentation_strategy(),
        )
        previous_segmentation = self.state["segmentation"]
        previous_epoch_parameters = deepcopy(previous_segmentation.get("epoch_parameters") or {})
        previous_normalization = deepcopy(previous_segmentation.get("normalization") or {})

        self.state["segmentation"] = {
            "segmentation_mode": mode,
            "segmentation_strategy": segmentation_strategy,
            "segment_by_response": self.segment_by_response_checkbox.isChecked(),
            "event_groups": event_groups,
            "epoch_parameters": {
                "duration_events": deepcopy(previous_epoch_parameters.get("duration_events") or {}),
                "instant_events": deepcopy(previous_epoch_parameters.get("instant_events") or {}),
            },
            "normalization": self._normalized_normalization_state(previous_normalization),
            "thresholding": {"enabled": self.threshold_enabled.isChecked(),
                "sigma": self.threshold_sigma.value(),
                "samples": self.threshold_samples.value(),
                "channels": self.threshold_channels.value()},
            "resampling": {
                "enabled": self.resampling_enabled.isChecked(),
                "target_sampling_frequency": self.target_sampling_frequency.value()}}

        self._align_segmentation_strategy(has_duration_epochs, has_instant_epochs)

        if self._epoch_target == "duration" and has_duration_epochs:
            self._store_epoch_controls("duration")
        elif self._epoch_target == "instant" and has_instant_epochs:
            self._store_epoch_controls("instant")

        if has_duration_epochs or has_instant_epochs:
            self._store_normalization_controls(self._normalization_target)

        self._ensure_parameter_state(has_duration_epochs, has_instant_epochs)
        self._align_parameter_targets(mode, selection_mode)
        self._ensure_parameter_state(has_duration_epochs, has_instant_epochs)
        self._sync_resampling_broadband()

        self._set_dependent_enabled(mode)
        self._sync_strategy_preview()
        self._refresh_nested_groups_editor()
        self._refresh_summary(mode, selected_duration_events, selected_instant_events)
        self.validation_errors = self._validate()
        self._update_status_label(mode, selected_duration_events, selected_instant_events)
        self.changed.emit()

    def _validate(self) -> list[str]:
        segmentation = self.state["segmentation"]
        mode = segmentation["segmentation_mode"]
        independent_duration_events, independent_instant_events = self._independent_events_from_state()
        selection_mode = self._selection_mode_for_state(mode,
            independent_duration_events,
            independent_instant_events)
        errors: list[str] = []

        if mode == "nested":
            if not self._nested_mode_available():
                errors.append("Nested mode requires either an instant event or at least two duration events.")
            else:
                nested_groups = self._nested_groups()
                errors.extend(self.validation.validate_many(nested_groups, [("minimum_length", {"minimum": 1,
                                    "item_name": "base duration event", "action": "add"})], label="Event groups"))
                has_nested_duration = any(group.get("duration_events") for group in nested_groups)
                has_nested_instant = any(group.get("instant_events") for group in nested_groups)
                if has_nested_duration and has_nested_instant:
                    errors.append("Nested mode supports either duration or instant nested events, not both.")

                seen_bases: set[str] = set()
                for group in nested_groups:
                    base_event = self._event_label_for_current_mode(group.get("base_event"))
                    if not base_event:
                        errors.append("Nested group: base duration event is missing.")
                        continue
                    if base_event in seen_bases:
                        errors.append(f"Nested groups: base event '{base_event}' is duplicated.")
                    seen_bases.add(base_event)
                    nested_duration = [self._event_label_for_current_mode(event)
                        for event in group.get("duration_events") or []]
                    nested_instant = [self._event_label_for_current_mode(event)
                        for event in group.get("instant_events") or []]

                    if base_event in nested_duration:
                        errors.append(f"{base_event}: a base event cannot contain itself.")
                    if not nested_duration and not nested_instant:
                        errors.append(f"{base_event}: select at least one nested event.")

        elif selection_mode == "duration":
            errors.extend(
                self.validation.validate_many(independent_duration_events,[("minimum_length",
                            {"minimum": 1, "item_name": "duration event", "action": "select"})], label="Duration events"))
        elif selection_mode == "instant":
            errors.extend(self.validation.validate_many(independent_instant_events,
                    [("minimum_length", {"minimum": 1, "item_name": "instant event", "action": "select"})], label="Instant events"))
        else:
            errors.append("Signal events: select at least one event.")

        self._ensure_parameter_state()
        duration_epoch = self._epoch_state("duration", create=False)
        onset_epoch = self._epoch_state("instant", create=False)
        normalization = self._normalization_state(self._normalization_target, create=False)

        has_duration_epochs, has_instant_epochs = self._active_event_types(mode, selection_mode)
        strategy = self._current_state_strategy()

        def validate_stride(value: Any, label: str) -> None:
            errors.extend(self.validation.validate_many(value,["integer", ("greater_or_equal", {"minimum": 0, "suffix": " %"}),
                    ("less_or_equal", {"maximum": 99, "suffix": " %"})], label=label, stop_on_first_error=False))

        def validate_duration_epoch() -> int:
            errors.extend(self.validation.validate_many(duration_epoch["duration_epoch_length_ms"],
                    ["integer", ("greater_or_equal", {"minimum": 100, "suffix": " ms"})],
                    label="Duration epoch length" if mode == "nested" else "Epoch length",
                    stop_on_first_error=False))
            validate_stride(duration_epoch["stride_percent"], "Duration overlap" if mode == "nested" else "Overlap")
            return int(duration_epoch["duration_epoch_length_ms"])

        def validate_onset_epoch(epoch_config: dict[str, Any], target: str) -> int:
            start = epoch_config["start"]
            end = epoch_config["end"]
            baseline_start = epoch_config["baseline_start"]
            baseline_end = epoch_config["baseline_end"]
            start_label = "Epoch start"
            end_label = "Epoch end"
            baseline_start_label = "Baseline start"
            baseline_end_label = "Baseline end"
            if mode == "nested" or target == "duration":
                start_label = f"{target.title()} epoch start"
                end_label = f"{target.title()} epoch end"
                baseline_start_label = f"{target.title()} baseline start"
                baseline_end_label = f"{target.title()} baseline end"
            errors.extend(self.validation.validate_many(start, ["integer"],
                            label=start_label))
            errors.extend(self.validation.validate_many(end, ["integer"],
                                    label=end_label))
            errors.extend(self.validation.validate_many(baseline_start, ["integer"],
                            label=baseline_start_label))
            errors.extend(self.validation.validate_many(baseline_end, ["integer"],
                                    label=baseline_end_label))
            try:
                start = self.validation.coerce_int(start)
                end = self.validation.coerce_int(end)
                baseline_start = self.validation.coerce_int(baseline_start)
                baseline_end = self.validation.coerce_int(baseline_end)
            except ValueError:
                return 0
            if end <= start:
                prefix = f"{target.title()} epoch window" if mode == "nested" or target == "duration" else "Epoch window"
                errors.append(f"{prefix}: end must be greater than start.")
                return 0
            if baseline_end <= baseline_start:
                prefix = f"{target.title()} baseline window" if mode == "nested" or target == "duration" else "Baseline window"
                errors.append(f"{prefix}: end must be greater than start.")
            return int(end - start)

        def validate_normalization(normalization: dict[str, Any], target: str, epoch_config: dict[str, int] | None) -> None:
            if not normalization.get("enabled", False):
                return
            prefix = (
                f"{target.title()} normalization"
                if mode == "nested" and target in {"duration", "instant"}
                else "Normalization"
            )
            errors.extend(self.validation.validate_many(normalization.get("mode"),
                    [("one_of", {"options": ["mean", "mean_std"]})], label=f"{prefix} mode"))
            if epoch_config is None:
                return
            try:
                base_start = self.validation.coerce_int(epoch_config["baseline_start"])
                base_end = self.validation.coerce_int(epoch_config["baseline_end"])
                epoch_start = self.validation.coerce_int(epoch_config["start"])
                epoch_end = self.validation.coerce_int(epoch_config["end"])
            except ValueError:
                return
            if base_start < epoch_start or base_end > epoch_end:
                errors.append(f"{prefix} baseline window must be inside the onset epoch window.")

        epoch_lengths_ms: list[int] = []
        if has_duration_epochs:
            epoch_length = validate_duration_epoch() if strategy == "window-based" else validate_onset_epoch(onset_epoch, "duration")
            if epoch_length > 0:
                epoch_lengths_ms.append(epoch_length)

        if has_instant_epochs:
            epoch_length = validate_onset_epoch(onset_epoch, "instant")
            if epoch_length > 0:
                epoch_lengths_ms.append(epoch_length)

        if mode == "nested":
            if has_duration_epochs and not has_instant_epochs:
                validate_normalization(normalization, "duration", onset_epoch if strategy == "onset-based" else None)
            elif has_instant_epochs and not has_duration_epochs:
                validate_normalization(normalization, "instant", onset_epoch)
            elif has_duration_epochs or has_instant_epochs:
                validate_normalization(normalization, "normalization", None)
        else:
            if selection_mode == "duration":
                validate_normalization(normalization, "duration", onset_epoch if strategy == "onset-based" else None)
            elif selection_mode == "instant":
                validate_normalization(normalization, "instant", onset_epoch)

        smallest_epoch_ms = min(epoch_lengths_ms) if epoch_lengths_ms else 0
        epoch_samples = (int(smallest_epoch_ms * float(self.source_sampling_frequency or 0)/ 1000) if smallest_epoch_ms > 0
            else 0)
        n_channels = int((self.state.get("metadata") or {}).get("n_channels") or 0)
        thresholding = segmentation["thresholding"]

        if thresholding["enabled"]:
            errors.extend(self.validation.validate_many(thresholding["sigma"], ["finite_number", ("greater_than", {"minimum": 0})],
                    label="Threshold sigma", stop_on_first_error=False))
            errors.extend(self.validation.validate_many(thresholding["samples"], ["integer", ("greater_or_equal", {"minimum": 1})],
                    label="Threshold samples", stop_on_first_error=False))
            errors.extend(self.validation.validate_many(thresholding["channels"], ["integer", ("greater_or_equal", {"minimum": 1})],
                    label="Threshold channels", stop_on_first_error=False))
            if epoch_samples and thresholding["samples"] > epoch_samples:
                errors.append("Threshold samples cannot exceed the smallest configured epoch sample count.")
            if n_channels and thresholding["channels"] > n_channels:
                errors.append("Threshold channels cannot exceed the loaded channel count.")

        resampling = segmentation["resampling"]
        if resampling["enabled"]:
            target = resampling["target_sampling_frequency"]
            errors.extend(self.validation.validate_many(target,["integer", ("greater_or_equal", {"minimum": 1, "suffix": " Hz"})],
                    label="Target sample frequency", stop_on_first_error=False))

        return errors

    def on_step_activated(self) -> None:
        metadata = self.state.get("metadata") or {}
        self.source_sampling_frequency = metadata.get("sampling_frequency")

        self._refresh_events()
        self._sync()

    def can_continue(self) -> bool:
        return not self.validation_errors

__all__ = ["EEGSegmentationWidget"]
