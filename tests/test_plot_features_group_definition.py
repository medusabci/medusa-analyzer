import importlib
import unittest

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication


group_definition_module = importlib.import_module(
    "medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_group_definition_widget"
)
GroupDefinitionWidget = group_definition_module.GroupDefinitionWidget


def _group_colors(state: dict) -> list[str]:
    def group_index(item: tuple[str, dict]) -> int:
        return int(item[0].rsplit("_", 1)[-1])

    return [group["group_color"] for _, group in sorted(state["groups"].items(), key=group_index)]


def _hues(colors: list[str]) -> list[int]:
    return [QColor(color).hsvHue() for color in colors]


def _hue_distance(first: int, second: int) -> int:
    gap = abs(first - second) % 360
    return min(gap, 360 - gap)


def _minimum_hue_gap(colors: list[str]) -> int:
    hues = sorted(QColor(color).hsvHue() for color in colors)
    gaps = [hues[index + 1] - hues[index] for index in range(len(hues) - 1)]
    gaps.append((hues[0] + 360) - hues[-1])
    return min(gaps)


class PlotFeaturesGroupDefinitionWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_group_count_change_reassigns_stable_high_contrast_palette(self):
        state = {}
        widget = GroupDefinitionWidget({}, {"group_definition": {"default_group_count": 2}}, state)
        widget.show()
        self.app.processEvents()

        self.assertEqual(_group_colors(state), widget._default_colors(2))

        widget.group_count.setValue(3)
        self.app.processEvents()

        self.assertEqual(_group_colors(state), widget._default_colors(3))
        self.assertEqual(_minimum_hue_gap(_group_colors(state)), 120)

        widget.group_count.setValue(4)
        self.app.processEvents()

        self.assertEqual(_hues(_group_colors(state)), [0, 120, 240, 60])
        self.assertGreaterEqual(_hue_distance(_hues(_group_colors(state))[2], _hues(_group_colors(state))[3]), 120)

    def test_many_groups_fill_primary_and_secondary_colors_first(self):
        state = {}
        widget = GroupDefinitionWidget({}, {"group_definition": {"default_group_count": 6}}, state)

        colors = _group_colors(state)

        self.assertEqual(_hues(colors), [0, 120, 240, 60, 180, 300])
        self.assertEqual(_minimum_hue_gap(colors), 60)

    def test_initial_restore_keeps_saved_group_colors(self):
        state = {
            "groups": {
                "group_1": {"group_name": "A", "group_color": "#111111", "subjects": [], "files": []},
                "group_2": {"group_name": "B", "group_color": "#222222", "subjects": [], "files": []},
            },
        }

        GroupDefinitionWidget({}, {"group_definition": {"default_group_count": 2}}, state)

        self.assertEqual(_group_colors(state), ["#111111", "#222222"])


if __name__ == "__main__":
    unittest.main()
