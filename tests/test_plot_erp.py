import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from matplotlib.colors import to_hex
from matplotlib.figure import Figure

from medusa_analyzer.frontend.experiments import discover_experiments
from medusa_analyzer.frontend.experiments.plot_erp.widgets.plot_erp_visualization_widget import PlotERPVisualizationWidget
from medusa_analyzer.frontend.widgets.plots import epoch_data as epoch_data_module
from medusa_analyzer.frontend.widgets.plots import (
    ERPPlot,
    EpochDataIndex,
    prepare_grouped_epoch_data,
)


def _recording_id(session: str, segment: str = "stimulus") -> str:
    return f"{session}_task-test_run-1_eeg_segment-{segment}"


def _write_epoch(derivatives: Path, subject: str, session: str, band: str, signal,
    times: list[float] | None = None, time_unit: str = "ms", segment: str = "stimulus") -> None:
    folder = derivatives / "segmented" / subject / session / "eeg"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}_{session}_task-test_run-1_eeg_band-{band}_segment-{segment}"
    payload = {
        "fs": 250,
        "channels": ["C1", "C2"],
        "times": times or [-100.0, 0.0, 100.0],
        "time_unit": time_unit,
        "signal": signal,
    }
    (folder / f"{stem}.mpl").write_text(json.dumps(payload), encoding="utf-8")


class PlotERPTests(unittest.TestCase):
    def test_plot_erp_experiment_is_discovered(self):
        discovered = {experiment.id: experiment.info["title"] for experiment in discover_experiments()}

        self.assertEqual(discovered["plot_erp"], "Plot ERP")

    def test_visualization_defaults_to_first_channel_when_selection_is_missing_or_empty(self):
        self.assertEqual(PlotERPVisualizationWidget._channel_indices_from_config(None, 3), [0])
        self.assertEqual(PlotERPVisualizationWidget._channel_indices_from_config([], 3), [0])
        self.assertEqual(PlotERPVisualizationWidget._channel_indices_from_config(["2", "bad", 5], 3), [2])
        self.assertEqual(PlotERPVisualizationWidget._channel_indices_from_config([1, 1, 0], 3), [0, 1])

    def test_initial_plot_calculation_message_changes_after_first_calculation(self):
        widget = SimpleNamespace(_has_started_plot_calculation=False)

        self.assertEqual(PlotERPVisualizationWidget._plot_calculation_message(widget), "Calculating plot...")
        widget._has_started_plot_calculation = True
        self.assertEqual(PlotERPVisualizationWidget._plot_calculation_message(widget), "Recalculating plot...")

    def test_epoch_index_uses_discovered_files_and_caches_reduced_values(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband",
                [[[1.0, 3.0], [3.0, 5.0], [5.0, 7.0]]])
            epoch_file = next((derivatives / "segmented").rglob("*.mpl"))
            state = {
                "derivatives_path": str(Path(tmp_dir) / "missing_derivatives"),
                "epoch_files": [str(epoch_file)],
            }

            data_index = EpochDataIndex.from_state(state)

            self.assertEqual(len(data_index.records), 1)
            with patch.object(epoch_data_module, "_load_epoch_file",
                wraps=epoch_data_module._load_epoch_file) as load_epoch:
                first_values = data_index.values_for("broadband", "sub-01", rec_1, [0], 2)
                cached_values = data_index.values_for("broadband", "sub-01", rec_1, [0], 2)
                second_channel_values = data_index.values_for("broadband", "sub-01", rec_1, [1], 2)

            self.assertEqual(load_epoch.call_count, 1)
            np.testing.assert_allclose(first_values[0].values, [1.0, 3.0, 5.0])
            np.testing.assert_allclose(cached_values[0].values, [1.0, 3.0, 5.0])
            np.testing.assert_allclose(second_channel_values[0].values, [3.0, 5.0, 7.0])

    def test_within_subject_epoch_data_averages_epochs_channels_and_recordings(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband", [
                [[1.0, 3.0], [3.0, 5.0], [5.0, 7.0]],
                [[3.0, 5.0], [5.0, 7.0], [7.0, 9.0]],
            ])
            _write_epoch(derivatives, "sub-02", "ses-01", "broadband", [
                [[5.0, 7.0], [7.0, 9.0], [9.0, 11.0]],
                [[7.0, 9.0], [9.0, 11.0], [11.0, 13.0]],
            ])
            _write_epoch(derivatives, "sub-01", "ses-01", "alpha", [
                [[100.0, 100.0], [100.0, 100.0], [100.0, 100.0]],
            ])

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01", "sub-02"],
                "groups": {
                    "group_1": {
                        "group_name": "Stimulus",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [rec_1],
                    },
                },
            }

            data_index = EpochDataIndex.from_state(state)
            prepared = prepare_grouped_epoch_data(state, "broadband", [0, 1], data_index)

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual([observation.id for observation in prepared.groups[0].observations],
                ["sub-01", "sub-02"])
            np.testing.assert_allclose(prepared.groups[0].observations[0].values, [3.0, 5.0, 7.0])
            np.testing.assert_allclose(prepared.groups[0].observations[1].values, [7.0, 9.0, 11.0])
            np.testing.assert_allclose(prepared.times, [-100.0, 0.0, 100.0])
            self.assertTrue(data_index.has_band("broadband"))
            self.assertTrue(data_index.has_band("alpha"))

    def test_between_subject_epoch_data_uses_subjects_as_observations(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            rec_2 = _recording_id("ses-02")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband", [[[1.0, 3.0], [3.0, 5.0]]],
                times=[-0.1, 0.0], time_unit="s")
            _write_epoch(derivatives, "sub-02", "ses-01", "broadband", [[[5.0, 7.0], [7.0, 9.0]]],
                times=[-0.1, 0.0], time_unit="s")
            _write_epoch(derivatives, "sub-01", "ses-02", "broadband", [[[9.0, 11.0], [11.0, 13.0]]],
                times=[-100.0, 0.0])
            _write_epoch(derivatives, "sub-02", "ses-02", "broadband", [[[13.0, 15.0], [15.0, 17.0]]],
                times=[-100.0, 0.0])

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "between",
                "channel_names": ["C1", "C2"],
                "plot_selected_recordings": [rec_1, rec_2],
                "groups": {
                    "group_1": {
                        "group_name": "Patients",
                        "group_color": "#123456",
                        "subjects": ["sub-01", "sub-02"],
                        "files": [],
                    },
                },
            }

            prepared = prepare_grouped_epoch_data(state, "broadband", [0, 1])

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual([observation.id for observation in prepared.groups[0].observations],
                ["sub-01", "sub-02"])
            np.testing.assert_allclose(prepared.groups[0].observations[0].times, [-100.0, 0.0])
            np.testing.assert_allclose(prepared.groups[0].observations[0].values, [6.0, 8.0])
            np.testing.assert_allclose(prepared.groups[0].observations[1].values, [10.0, 12.0])

    def test_plot_erp_plot_draws_group_color_and_ci(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband", [[[1.0, 3.0], [3.0, 5.0]]],
                times=[-100.0, 0.0])
            _write_epoch(derivatives, "sub-02", "ses-01", "broadband", [[[5.0, 7.0], [7.0, 9.0]]],
                times=[-100.0, 0.0])
            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01", "sub-02"],
                "groups": {
                    "group_1": {
                        "group_name": "Stimulus",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [rec_1],
                    },
                },
            }

            prepared = prepare_grouped_epoch_data(state, "broadband", [0, 1])
            ax = Figure().add_subplot(111)
            plot = ERPPlot(ax, {"plot_error": True, "title": "Plot ERP"})
            plot.load_prepared_data(prepared)
            plot.draw(prepared.colors_by_name())

            self.assertEqual(to_hex(ax.lines[0].get_color()).upper(), "#33AA77")
            self.assertGreaterEqual(len(ax.collections), 1)
            np.testing.assert_allclose(plot._group_epochs["Stimulus"]["mean"], [4.0, 6.0])

    def test_plot_erp_between_subject_plot_error_uses_subject_ci(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband", [[[1.0, 3.0], [3.0, 5.0]]],
                times=[-100.0, 0.0])
            _write_epoch(derivatives, "sub-02", "ses-01", "broadband", [[[5.0, 7.0], [7.0, 9.0]]],
                times=[-100.0, 0.0])
            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "between",
                "channel_names": ["C1", "C2"],
                "plot_selected_recordings": [rec_1],
                "groups": {
                    "group_1": {
                        "group_name": "Patients",
                        "group_color": "#33AA77",
                        "subjects": ["sub-01", "sub-02"],
                        "files": [],
                    },
                },
            }

            prepared = prepare_grouped_epoch_data(state, "broadband", [0, 1])
            ax = Figure().add_subplot(111)
            plot = ERPPlot(ax, {"plot_error": True})
            plot.load_prepared_data(prepared)
            plot.draw(prepared.colors_by_name())

            self.assertEqual(prepared.observation_unit, "subject")
            self.assertEqual(plot._group_epochs["Patients"]["n"], 2)
            self.assertGreaterEqual(len(ax.collections), 1)

    def test_plot_erp_draws_groups_without_vertical_offset(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            rec_1 = _recording_id("ses-01")
            _write_epoch(derivatives, "sub-01", "ses-01", "broadband", [[[1.0, 1.0], [2.0, 2.0]]],
                times=[-100.0, 0.0])
            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01"],
                "groups": {
                    "group_1": {
                        "group_name": "A",
                        "group_color": "#33AA77",
                        "subjects": [],
                        "files": [rec_1],
                    },
                    "group_2": {
                        "group_name": "B",
                        "group_color": "#AA3377",
                        "subjects": [],
                        "files": [rec_1],
                    },
                },
            }

            prepared = prepare_grouped_epoch_data(state, "broadband", [0, 1])
            ax = Figure().add_subplot(111)
            plot = ERPPlot(ax)
            plot.load_prepared_data(prepared)
            plot.draw(prepared.colors_by_name())

            plotted_signals = [line.get_ydata() for line in ax.lines if line.get_label() in {"A", "B"}]
            self.assertEqual(len(plotted_signals), 2)
            np.testing.assert_allclose(plotted_signals[0], [1.0, 2.0])
            np.testing.assert_allclose(plotted_signals[1], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
