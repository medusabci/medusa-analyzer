import importlib
import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel


group_assignment_module = importlib.import_module(
    "medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_group_assignment_widget"
)
data_assignment_module = importlib.import_module(
    "medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_data_assignment_widget"
)
PlotFeaturesGroupAssignmentWidget = group_assignment_module.PlotFeaturesGroupAssignmentWidget
PlotFeaturesDataAssignmentWidget = data_assignment_module.PlotFeaturesDataAssignmentWidget


class PlotFeaturesGroupAssignmentWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_assigned_rows_are_painted_with_group_color(self):
        state = {
            "analysis_mode": "within",
            "plot_features_recordings": ["recording-1", "recording-2"],
            "groups": {
                "group_1": {
                    "group_name": "Control",
                    "group_color": "#33AA77",
                    "subjects": [],
                    "files": [],
                },
            },
        }

        widget = PlotFeaturesGroupAssignmentWidget({}, {}, state)
        widget.show()
        self.app.processEvents()

        widget.table.selectRow(0)
        widget._assign_selected("group_1")
        self.app.processEvents()

        for column in range(widget.table.columnCount()):
            color = widget.table.item(0, column).background().color()
            self.assertEqual(color.name().upper(), "#33AA77")
            self.assertGreater(color.alpha(), 0)
            self.assertIsNone(widget.table.cellWidget(0, column))

        chips = [widget.summary_layout.itemAt(index).widget()
            for index in range(widget.summary_layout.count())
            if widget.summary_layout.itemAt(index).widget() is not None]
        self.assertEqual(len(chips), 1)
        self.assertEqual(chips[0].findChild(QLabel).text(), "Control: 1 file(s)")
        self.assertIsNotNone(widget.summary_layout.itemAt(widget.summary_layout.count() - 1).spacerItem())

        widget.table.selectRow(0)
        widget._assign_selected(None)
        self.app.processEvents()

        for column in range(widget.table.columnCount()):
            self.assertEqual(widget.table.item(0, column).background().style(), Qt.BrushStyle.NoBrush)
            self.assertIsNone(widget.table.cellWidget(0, column))
        self.assertEqual(widget.table.item(0, 1).text(), "")

    def test_data_assignment_rows_are_not_painted_with_group_color(self):
        state = {
            "analysis_mode": "between",
            "plot_features_recordings": ["recording-1"],
            "groups": {
                "group_1": {
                    "group_name": "Control",
                    "group_color": "#33AA77",
                    "subjects": [],
                    "files": ["recording-1"],
                },
            },
        }

        widget = PlotFeaturesDataAssignmentWidget({}, {}, state)
        widget.show()
        self.app.processEvents()

        self.assertIsNone(widget.table.cellWidget(0, 0))
        self.assertEqual(widget.table.item(0, 0).background().style(), Qt.BrushStyle.NoBrush)

    def test_group_text_color_uses_readable_contrast(self):
        bright_brush = group_assignment_module._group_text_brush({"group_color": "#1FE61F"})
        dark_brush = group_assignment_module._group_text_brush({"group_color": "#1F1FE6"})

        self.assertEqual(bright_brush.color().name().upper(), "#1F171B")
        self.assertEqual(dark_brush.color().name().upper(), "#FFF7FA")

    def test_assigned_row_renders_group_color_with_stylesheet(self):
        previous_stylesheet = self.app.styleSheet()
        self.app.setStyleSheet(Path("medusa_analyzer/frontend/styles/main.qss").read_text(encoding="utf-8"))
        try:
            state = {
                "analysis_mode": "within",
                "plot_features_recordings": ["recording-1"],
                "groups": {
                    "group_1": {
                        "group_name": "Control",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [],
                    },
                },
            }

            widget = PlotFeaturesGroupAssignmentWidget({}, {}, state)
            widget.resize(700, 500)
            widget.show()
            self.app.processEvents()

            widget.table.selectRow(0)
            widget._assign_selected("group_1")
            self.app.processEvents()

            painter_pixmap = QPixmap(widget.table.viewport().size())
            widget.table.viewport().render(painter_pixmap)
            image = painter_pixmap.toImage()
            y = widget.table.rowViewportPosition(0) + widget.table.rowHeight(0) // 2
            x = widget.table.columnViewportPosition(0) + widget.table.columnWidth(0) - 20

            self.assertEqual(image.pixelColor(x, y).name().upper(), "#33AA77")
        finally:
            self.app.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
