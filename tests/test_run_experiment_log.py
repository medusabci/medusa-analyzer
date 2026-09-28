import unittest

from PySide6.QtWidgets import QApplication

from medusa_analyzer.frontend.widgets.run_experiment import RunExperimentWidget


def _text_color_name(widget: RunExperimentWidget, text: str) -> str:
    cursor = widget.log_area.document().find(text)
    if cursor.isNull():
        raise AssertionError(f"Log text not found: {text}")
    return cursor.charFormat().foreground().color().name()


class RunExperimentLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_info_log_after_warning_does_not_inherit_warning_color(self):
        widget = RunExperimentWidget(
            {"title": "Pipeline", "subtitle": "Test pipeline"},
            {},
            {},
        )

        widget.log_callback("warning message", "warning")
        widget.log_callback("info message", "")
        self.app.processEvents()

        warning_color = widget.log_colors.warningColor.name()
        self.assertEqual(_text_color_name(widget, "warning message"), warning_color)
        self.assertNotEqual(_text_color_name(widget, "info message"), warning_color)


if __name__ == "__main__":
    unittest.main()
