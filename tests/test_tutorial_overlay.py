import unittest

from PySide6.QtWidgets import QApplication, QWidget

from medusa_analyzer.frontend.experiments.converter.widgets.other_database_tutorial import (
    OtherDatabaseTutorialOverlay,
)
from medusa_analyzer.frontend.widgets.tutorial_overlay import TutorialOverlay, TutorialStep


class TutorialOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_overlay_advances_and_calls_completion_callback(self):
        parent = QWidget()
        overlay = TutorialOverlay(
            parent,
            "Test tutorial",
            (
                TutorialStep("First", "Body"),
                TutorialStep("Second", "Body"),
            ),
        )
        calls = []

        overlay.start(lambda: calls.append("done"))
        overlay._next()
        overlay._next()

        self.assertEqual(calls, ["done"])
        self.assertFalse(overlay.isVisible())

    def test_skip_calls_callback_without_advancing(self):
        parent = QWidget()
        overlay = TutorialOverlay(parent, "Test tutorial", (TutorialStep("First", "Body"),))
        calls = []

        overlay.start(lambda: calls.append("skipped"))
        overlay._skip()

        self.assertEqual(calls, ["skipped"])
        self.assertFalse(overlay.isVisible())

    def test_other_database_tutorial_defines_four_steps(self):
        parent = QWidget()
        overlay = OtherDatabaseTutorialOverlay(parent)

        self.assertEqual(len(overlay.steps), 4)
        self.assertEqual(overlay.title, "Other DB conversion")


if __name__ == "__main__":
    unittest.main()
