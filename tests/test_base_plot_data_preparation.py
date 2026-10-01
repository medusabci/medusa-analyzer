import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from matplotlib.colors import to_hex
from matplotlib.figure import Figure

from medusa_analyzer.frontend.widgets.plots import BasePlot, PlotDataIndex, PSDPlot, ScatterPlot, ViolinPlot


def _recording_id(session: str) -> str:
    return f"{session}_task-test_run-1_eeg"


def _write_param(derivatives: Path, subject: str, session: str, feature_token: str, band: str,
    value, freqs: list[float] | None = None) -> None:
    folder = derivatives / "parameters" / subject / session / "eeg"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}_{session}_task-test_run-1_eeg_param-{feature_token}_band-{band}_segment-rest"
    path = folder / f"{stem}.mpl"
    payload = {"param": {"values": value, "freqs": freqs}} if freqs is not None else {
        "param": value,
        "info": feature_token,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_state(derivatives: Path, analysis_mode: str) -> dict:
    return {
        "derivatives_path": str(derivatives),
        "analysis_mode": analysis_mode,
        "channel_names": ["C1", "C2"],
    }


class BasePlotDataPreparationTests(unittest.TestCase):
    def test_within_subject_observations_are_subjects_after_channel_and_recording_average(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            rec_2 = _recording_id("ses-02")
            _write_param(derivatives, "sub-01", "ses-01", "absolutebandpower", "alpha", [[1.0, 3.0]])
            _write_param(derivatives, "sub-02", "ses-01", "absolutebandpower", "alpha", [[5.0, 7.0]])
            _write_param(derivatives, "sub-01", "ses-02", "absolutebandpower", "alpha", [[9.0, 11.0]])
            _write_param(derivatives, "sub-02", "ses-02", "absolutebandpower", "alpha", [[13.0, 15.0]])
            _write_param(derivatives, "sub-01", "ses-01", "absolutebandpower", "beta", [[1000.0, 1000.0]])

            state = _base_state(derivatives, "within")
            state["plot_selected_subjects"] = ["sub-01", "sub-02"]
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": [],
                    "files": [rec_1, rec_2],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "absolute_band_power", "alpha", [0, 1])
            observations = prepared.groups[0].observations

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual([observation.id for observation in observations], ["sub-01", "sub-02"])
            np.testing.assert_allclose([float(observation.values) for observation in observations], [6.0, 10.0])
            self.assertEqual(prepared.colors_by_name(), {"Group A": "#123456"})

    def test_relative_band_power_averages_epochs_channels_and_subjects(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_param(derivatives, "sub-01", "ses-01", "relativebandpower", "alpha",
                [[0.1, 0.3], [0.5, 0.7]])
            _write_param(derivatives, "sub-02", "ses-01", "relativebandpower", "alpha",
                [[0.9, 1.1], [1.3, 1.5]])
            _write_param(derivatives, "sub-01", "ses-01", "relativebandpower", "broadband",
                [[1000.0, 1000.0]])

            state = _base_state(derivatives, "within")
            state["plot_selected_subjects"] = ["sub-01", "sub-02"]
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": [],
                    "files": [rec_1],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "relative_band_power", "alpha", [0, 1])
            observations = prepared.groups[0].observations

            self.assertEqual([observation.id for observation in observations], ["sub-01", "sub-02"])
            np.testing.assert_allclose([float(observation.values) for observation in observations], [0.4, 1.2])

    def test_band_power_features_stay_empty_when_parameter_files_are_missing(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            freqs = [0.0, 5.0, 10.0, 15.0, 20.0]
            for subject in ["sub-01", "sub-02"]:
                alpha_psd = [
                    [[1.0, 1.0], [1.0, 1.0], [2.0, 2.0], [1.0, 1.0], [1.0, 1.0]],
                    [[1.0, 1.0], [1.0, 1.0], [3.0, 3.0], [1.0, 1.0], [1.0, 1.0]],
                ]
                _write_param(derivatives, subject, "ses-01", "psd", "alpha", alpha_psd, freqs)
                _write_param(derivatives, subject, "ses-01", "psd", "broadband", alpha_psd, freqs)

            state = _base_state(derivatives, "within")
            state["plot_selected_subjects"] = ["sub-01", "sub-02"]
            state["plot_features_config"] = {
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
            }
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": [],
                    "files": [rec_1],
                },
            }

            data_index = PlotDataIndex.from_state(state)
            absolute_data = BasePlot.prepare_grouped_plot_data(state, "absolute_band_power", "alpha", [0, 1],
                data_index)
            relative_data = BasePlot.prepare_grouped_plot_data(state, "relative_band_power", "alpha", [0, 1],
                data_index)

            self.assertFalse(absolute_data.has_observations())
            self.assertFalse(relative_data.has_observations())
            self.assertEqual(absolute_data.groups[0].observations, [])
            self.assertEqual(relative_data.groups[0].observations, [])

    def test_between_subject_observations_are_subjects_after_channel_and_recording_average(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            rec_2 = _recording_id("ses-02")
            _write_param(derivatives, "sub-01", "ses-01", "mean", "alpha", [[1.0, 3.0]])
            _write_param(derivatives, "sub-01", "ses-02", "mean", "alpha", [[5.0, 7.0]])
            _write_param(derivatives, "sub-02", "ses-01", "mean", "alpha", [[9.0, 11.0]])
            _write_param(derivatives, "sub-02", "ses-02", "mean", "alpha", [[13.0, 15.0]])

            state = _base_state(derivatives, "between")
            state["plot_selected_recordings"] = [rec_1, rec_2]
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": ["sub-01", "sub-02"],
                    "files": [],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "mean", "alpha", [0, 1])
            observations = prepared.groups[0].observations

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual([observation.id for observation in observations], ["sub-01", "sub-02"])
            np.testing.assert_allclose([float(observation.values) for observation in observations], [4.0, 12.0])

    def test_prepared_data_is_consumed_by_violin_scatter_and_psd_with_group_colors(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            rec_2 = _recording_id("ses-02")
            state = _base_state(derivatives, "within")
            state["plot_selected_subjects"] = ["sub-01", "sub-02"]
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": [],
                    "files": [rec_1, rec_2],
                },
            }

            for subject, session, mean_value, median_value in [
                ("sub-01", "ses-01", [[1.0, 3.0]], [[10.0, 12.0]]),
                ("sub-02", "ses-01", [[5.0, 7.0]], [[14.0, 16.0]]),
                ("sub-01", "ses-02", [[9.0, 11.0]], [[18.0, 20.0]]),
                ("sub-02", "ses-02", [[13.0, 15.0]], [[22.0, 24.0]]),
            ]:
                _write_param(derivatives, subject, session, "mean", "alpha", mean_value)
                _write_param(derivatives, subject, session, "median", "alpha", median_value)

            freqs = [10.0, 20.0, 30.0]
            _write_param(derivatives, "sub-01", "ses-01", "psd", "alpha",
                [[[1.0, 3.0], [2.0, 4.0], [3.0, 5.0]]], freqs)
            _write_param(derivatives, "sub-02", "ses-01", "psd", "alpha",
                [[[5.0, 7.0], [6.0, 8.0], [7.0, 9.0]]], freqs)

            data_index = PlotDataIndex.from_state(state)
            y_data = BasePlot.prepare_grouped_plot_data(state, "mean", "alpha", [0, 1], data_index)
            x_data = BasePlot.prepare_grouped_plot_data(state, "median", "alpha", [0, 1], data_index)
            psd_data = BasePlot.prepare_grouped_plot_data(state, "psd", "alpha", [0, 1], data_index)

            violin_ax = Figure().add_subplot(111)
            violin = ViolinPlot(violin_ax, {"plot_boxplot": True, "plot_strip": False})
            violin.load_prepared_data(y_data)
            violin.draw(y_data.colors_by_name())
            self.assertEqual(to_hex(violin_ax.collections[0].get_facecolor()[0]).upper(), "#123456")
            self.assertIn("#123456", {to_hex(line.get_color()).upper() for line in violin_ax.lines})

            scatter_ax = Figure().add_subplot(111)
            scatter = ScatterPlot(scatter_ax, {"marker_size": 40})
            scatter.load_prepared_data(y_data, x_data)
            scatter.draw(y_data.colors_by_name())
            np.testing.assert_allclose(scatter._points["Group A"][0], [15.0, 19.0])
            np.testing.assert_allclose(scatter._points["Group A"][1], [6.0, 10.0])
            self.assertEqual(to_hex(scatter_ax.collections[0].get_facecolor()[0]).upper(), "#123456")

            psd_ax = Figure().add_subplot(111)
            psd = PSDPlot(psd_ax, {"plot_error": True})
            psd.load_prepared_data(psd_data)
            psd.draw(psd_data.colors_by_name())
            np.testing.assert_allclose(psd._psd_data["Group A"]["mean"], [4.0, 5.0, 6.0])
            self.assertEqual(to_hex(psd_ax.lines[0].get_color()).upper(), "#123456")

    def test_between_subject_psd_plot_error_uses_subject_ci(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            freqs = [10.0, 20.0, 30.0]
            _write_param(derivatives, "sub-01", "ses-01", "psd", "alpha",
                [[[1.0, 3.0], [2.0, 4.0], [3.0, 5.0]]], freqs)
            _write_param(derivatives, "sub-02", "ses-01", "psd", "alpha",
                [[[5.0, 7.0], [6.0, 8.0], [7.0, 9.0]]], freqs)

            state = _base_state(derivatives, "between")
            state["plot_selected_recordings"] = [rec_1]
            state["groups"] = {
                "group_1": {
                    "group_name": "Group A",
                    "group_color": "#123456",
                    "subjects": ["sub-01", "sub-02"],
                    "files": [],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "psd", "alpha", [0, 1])
            psd_ax = Figure().add_subplot(111)
            psd = PSDPlot(psd_ax, {"plot_error": True})
            psd.load_prepared_data(prepared)
            psd.draw(prepared.colors_by_name())

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual(psd._psd_data["Group A"]["n"], 2)
            self.assertGreaterEqual(len(psd_ax.collections), 1)


if __name__ == "__main__":
    unittest.main()
