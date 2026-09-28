import importlib
import unittest

from PySide6.QtWidgets import QApplication, QScrollArea


feature_selection_module = importlib.import_module(
    "medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_feature_selection_widget"
)
PlotFeaturesFeatureSelectionWidget = feature_selection_module.PlotFeaturesFeatureSelectionWidget


class PlotFeaturesFeatureSelectionWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_reads_config_features_and_stores_plot_selection(self):
        state = {
            "plot_features_config": {
                "selected_features": ["psd", "absolute_band_power", "relative_band_power"],
            },
        }

        widget = PlotFeaturesFeatureSelectionWidget({}, {}, state)
        widget.show()
        self.app.processEvents()

        self.assertIsInstance(widget, QScrollArea)
        self.assertEqual(
            state["plot_selected_features"],
            ["psd", "absolute_band_power", "relative_band_power"],
        )

        widget.table_clear_selection()
        self.app.processEvents()

        self.assertEqual(state["plot_selected_features"], [])
        self.assertFalse(widget.can_continue())

    def test_widget_restores_only_features_available_in_loaded_config(self):
        state = {
            "plot_features_config": {
                "selected_features": ["psd", "mean", "median"],
            },
            "plot_selected_features": ["psd", "missing_feature"],
        }

        widget = PlotFeaturesFeatureSelectionWidget({}, {}, state)
        widget.show()
        self.app.processEvents()

        self.assertEqual(state["plot_selected_features"], ["psd"])
        self.assertTrue(widget.can_continue())


if __name__ == "__main__":
    unittest.main()
