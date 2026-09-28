import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea


visualization_module = importlib.import_module(
    "medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_visualization_widget"
)
PlotFeaturesVisualizationWidget = visualization_module.PlotFeaturesVisualizationWidget


def _defaults() -> dict:
    return {
        "plots": {
            "available_plot_types": [
                {
                    "id": "psd",
                    "title": "PSD Plot",
                    "compatible_experiments": ["eeg"],
                    "allowed_features": ["psd"],
                    "default_params": {"visualization": []},
                },
                {
                    "id": "violin",
                    "title": "Violin plot",
                    "compatible_experiments": ["eeg"],
                    "allowed_features": ["absolute_band_power", "relative_band_power"],
                    "default_params": {"visualization": []},
                },
            ],
        },
    }


def _recording_id(session: str) -> str:
    return f"{session}_task-test_run-1_eeg"


def _write_param(derivatives: Path, subject: str, session: str, feature_token: str, band: str, value,
    freqs: list[float] | None = None) -> None:
    folder = derivatives / "parameters" / subject / session / "eeg"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}_{session}_task-test_run-1_eeg_param-{feature_token}_band-{band}_segment-rest"
    payload = {"param": {"values": value, "freqs": freqs}} if freqs is not None else {
        "param": value,
        "info": feature_token,
    }
    (folder / f"{stem}.mpl").write_text(json.dumps(payload), encoding="utf-8")


class PlotFeaturesVisualizationWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_plot_type_combo_has_select_label(self):
        state = {
            "plot_selected_features": ["psd"],
            "channel_names": ["Fz", "Cz", "Pz"],
        }

        widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
        widget.show()
        self.app.processEvents()

        self.assertIsInstance(widget, QScrollArea)
        labels = [label.text() for label in widget.findChildren(QLabel)
            if label.objectName() == "plotTypeSelectLabel"]
        self.assertEqual(labels, ["Select"])

    def test_channel_table_minimum_height_matches_rendered_rows(self):
        state = {
            "plot_selected_features": ["psd"],
            "channel_names": [f"Ch {index}" for index in range(24)],
        }

        widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
        widget.show()
        self.app.processEvents()

        channel_table = widget.feature_tabs["psd"]["channel_table"]
        rendered_height = channel_table.frameWidth() * 2
        if channel_table.horizontalHeader().isVisible():
            rendered_height += channel_table.horizontalHeader().height()
        rendered_height += sum(channel_table.rowHeight(row) for row in range(channel_table.rowCount()))

        self.assertGreaterEqual(channel_table.minimumHeight(), rendered_height)

    def test_relative_band_power_uses_named_bands_from_feature_params(self):
        state = {
            "plot_selected_features": ["relative_band_power"],
            "channel_names": ["Fz", "Cz", "Pz"],
            "plot_features_config": {
                "experiment_id": "eeg",
                "preprocessing": {
                    "selected_frequency_bands": [
                        {"id": "broadband", "title": "Broadband", "low_cut": 0.5, "high_cut": 45.0},
                    ],
                },
                "feature_params": {
                    "relative_band_power": {
                        "selected_frequency_bands": [
                            {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                            {"id": "beta", "title": "Beta", "low_cut": 13.0, "high_cut": 30.0},
                            {"id": "broadband", "title": "Broadband", "low_cut": 0.5, "high_cut": 45.0},
                        ],
                    },
                },
            },
        }

        widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
        widget.show()
        self.app.processEvents()

        band_combo = widget.feature_tabs["relative_band_power"]["band_combo"]
        self.assertEqual(band_combo.currentData(), "alpha")
        self.assertEqual([band_combo.itemData(index) for index in range(band_combo.count())], ["alpha", "beta"])

    def test_absolute_and_relative_band_power_draw_from_current_parameter_files(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            rec_2 = _recording_id("ses-02")
            for subject, session, absolute_value, relative_value in [
                ("sub-01", "ses-01", [[1.0, 3.0], [5.0, 7.0]], [[0.1, 0.3], [0.5, 0.7]]),
                ("sub-02", "ses-01", [[9.0, 11.0], [13.0, 15.0]], [[0.9, 1.1], [1.3, 1.5]]),
                ("sub-01", "ses-02", [[17.0, 19.0], [21.0, 23.0]], [[1.7, 1.9], [2.1, 2.3]]),
                ("sub-02", "ses-02", [[25.0, 27.0], [29.0, 31.0]], [[2.5, 2.7], [2.9, 3.1]]),
            ]:
                _write_param(derivatives, subject, session, "absolutebandpower", "alpha", absolute_value)
                _write_param(derivatives, subject, session, "relativebandpower", "alpha", relative_value)

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "plot_selected_features": ["absolute_band_power", "relative_band_power"],
                "plot_selected_subjects": ["sub-01", "sub-02"],
                "channel_names": ["Fz", "Cz"],
                "groups": {
                    "group_1": {
                        "group_name": "Condition A",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [rec_1, rec_2],
                    },
                },
                "plot_features_config": {
                    "experiment_id": "eeg",
                    "preprocessing": {
                        "selected_frequency_bands": [
                            {"id": "broadband", "title": "Broadband", "low_cut": 0.5, "high_cut": 45.0},
                            {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                        ],
                    },
                    "feature_params": {
                        "relative_band_power": {
                            "selected_frequency_bands": [
                                {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                            ],
                        },
                    },
                },
            }

            widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
            widget.show()
            self.app.processEvents()

            for feature_id in ("absolute_band_power", "relative_band_power"):
                band_combo = widget.feature_tabs[feature_id]["band_combo"]
                alpha_index = band_combo.findData("alpha")
                self.assertGreaterEqual(alpha_index, 0)
                band_combo.setCurrentIndex(alpha_index)
                self.app.processEvents()

                ax = widget.feature_tabs[feature_id]["figure"].axes[0]
                self.assertGreater(len(ax.collections) + len(ax.lines), 0)
                self.assertFalse(any(text.get_text().startswith("No observations found") for text in ax.texts))

    def test_band_combo_is_filtered_to_parameter_files(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            for subject in ["sub-01", "sub-02"]:
                _write_param(derivatives, subject, "ses-01", "absolutebandpower", "alpha", [[1.0, 3.0]])
                _write_param(derivatives, subject, "ses-01", "absolutebandpower", "broadband", [[5.0, 7.0]])
                _write_param(derivatives, subject, "ses-01", "relativebandpower", "alpha", [[0.1, 0.3]])

            all_default_bands = [
                {"id": "broadband", "title": "Broadband", "low_cut": 0.5, "high_cut": 45.0},
                {"id": "delta", "title": "Delta", "low_cut": 0.5, "high_cut": 4.0},
                {"id": "theta", "title": "Theta", "low_cut": 4.0, "high_cut": 8.0},
                {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                {"id": "beta", "title": "Beta", "low_cut": 13.0, "high_cut": 30.0},
                {"id": "gamma", "title": "Gamma", "low_cut": 30.0, "high_cut": 45.0},
            ]
            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "plot_selected_features": ["absolute_band_power", "relative_band_power"],
                "plot_selected_subjects": ["sub-01", "sub-02"],
                "channel_names": ["Fz", "Cz"],
                "groups": {
                    "group_1": {
                        "group_name": "Condition A",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [_recording_id("ses-01")],
                    },
                },
                "plot_features_config": {
                    "experiment_id": "eeg",
                    "preprocessing": {"selected_frequency_bands": all_default_bands},
                    "feature_params": {
                        "relative_band_power": {"selected_frequency_bands": all_default_bands},
                    },
                },
            }

            widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
            widget.show()
            self.app.processEvents()

            absolute_combo = widget.feature_tabs["absolute_band_power"]["band_combo"]
            relative_combo = widget.feature_tabs["relative_band_power"]["band_combo"]

            self.assertEqual([absolute_combo.itemData(index) for index in range(absolute_combo.count())],
                ["broadband", "alpha"])
            self.assertEqual([relative_combo.itemData(index) for index in range(relative_combo.count())], ["alpha"])

    def test_absolute_and_relative_band_power_stay_empty_without_parameter_files(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            freqs = [0.0, 5.0, 10.0, 15.0, 20.0]
            for subject in ["sub-01", "sub-02"]:
                psd = [
                    [[1.0, 1.0], [1.0, 1.0], [2.0, 2.0], [1.0, 1.0], [1.0, 1.0]],
                    [[1.0, 1.0], [1.0, 1.0], [3.0, 3.0], [1.0, 1.0], [1.0, 1.0]],
                ]
                _write_param(derivatives, subject, "ses-01", "psd", "alpha", psd, freqs)
                _write_param(derivatives, subject, "ses-01", "psd", "broadband", psd, freqs)

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "plot_selected_features": ["absolute_band_power", "relative_band_power"],
                "plot_selected_subjects": ["sub-01", "sub-02"],
                "channel_names": ["Fz", "Cz"],
                "groups": {
                    "group_1": {
                        "group_name": "Condition A",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [_recording_id("ses-01")],
                    },
                },
                "plot_features_config": {
                    "experiment_id": "eeg",
                    "preprocessing": {
                        "selected_frequency_bands": [
                            {"id": "broadband", "title": "Broadband", "low_cut": 0.0, "high_cut": 20.0},
                            {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                        ],
                    },
                    "feature_params": {
                        "relative_band_power": {
                            "selected_frequency_bands": [
                                {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                            ],
                        },
                    },
                },
            }

            widget = PlotFeaturesVisualizationWidget({}, _defaults(), state)
            widget.show()
            self.app.processEvents()

            for feature_id in ("absolute_band_power", "relative_band_power"):
                band_combo = widget.feature_tabs[feature_id]["band_combo"]
                self.app.processEvents()

                ax = widget.feature_tabs[feature_id]["figure"].axes[0]
                self.assertEqual(widget.feature_tabs[feature_id]["band_combo"].currentText(), "No compatible band")
                self.assertTrue(any(text.get_text().startswith("Select a band before plotting") for text in ax.texts))


if __name__ == "__main__":
    unittest.main()
