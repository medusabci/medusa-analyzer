import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from medusa_analyzer.frontend.widgets.plots import BasePlot
from medusa_analyzer.frontend.experiments.plot_features.widgets.plot_features_load_data_widget import (
    PlotFeaturesLoadDataWidget,
)
from medusa_analyzer.frontend.widgets.plots.recording_ids import (
    normalize_recording_id,
    recording_ignored_prefixes_from_recordings,
)


def _write_param(derivatives: Path, subject: str, session: str | None, value, segment: str = "rest",
    extra_entities: str = "") -> None:
    folder = derivatives / "parameters" / subject
    if session:
        folder = folder / session
    folder = folder / "eeg"
    folder.mkdir(parents=True, exist_ok=True)

    session_part = f"_{session}" if session else ""
    stem = f"{subject}{session_part}_task-rest_eeg_param-absolutebandpower_band-alpha_segment-{segment}{extra_entities}"
    path = folder / f"{stem}.mpl"
    path.write_text(json.dumps({"param": value, "info": "absolutebandpower"}), encoding="utf-8")


class PlotRecordingIdTests(unittest.TestCase):
    def test_single_session_mixed_with_sessionless_recordings_collapses_to_task(self):
        recordings = [
            {"subject": "04", "session": "", "relative_path": r"sub-04\eeg\sub-04_task-rest_eeg.mpl"},
            {
                "subject": "03",
                "session": "Session1",
                "relative_path": r"sub-03\ses-Session1\eeg\sub-03_ses-Session1_task-rest_eeg.mpl",
            },
            {"subject": "02", "session": "", "relative_path": r"sub-02\eeg\sub-02_task-rest_eeg.mpl"},
            {"subject": "01", "session": "", "relative_path": r"sub-01\eeg\sub-01_task-rest_eeg.mpl"},
        ]

        ignored_prefixes = recording_ignored_prefixes_from_recordings(recordings)
        names = {
            normalize_recording_id(str(recording["relative_path"]), ignored_prefixes)
            for recording in recordings
        }

        self.assertEqual(ignored_prefixes, ("ses",))
        self.assertEqual(names, {"task-rest_eeg"})

    def test_parameter_recording_id_keeps_segment_and_future_entities(self):
        name = (
            "sub-01_task-rest_eeg_param-mean_band-alpha_segment-fullrecordingeyesopen"
            "_condition-baseline.mpl"
        )

        self.assertEqual(
            normalize_recording_id(name),
            "task-rest_eeg_segment-fullrecordingeyesopen_condition-baseline",
        )

    def test_multiple_sessions_remain_distinct(self):
        recordings = [
            {"session": "01", "relative_path": r"sub-01\ses-01\eeg\sub-01_ses-01_task-rest_eeg.mpl"},
            {"session": "02", "relative_path": r"sub-01\ses-02\eeg\sub-01_ses-02_task-rest_eeg.mpl"},
        ]

        ignored_prefixes = recording_ignored_prefixes_from_recordings(recordings)

        self.assertEqual(ignored_prefixes, ())
        self.assertEqual(
            normalize_recording_id(recordings[0]["relative_path"], ignored_prefixes),
            "ses-01_task-rest_eeg",
        )

    def test_consistent_single_session_is_preserved(self):
        recordings = [
            {
                "session": "Session1",
                "relative_path": r"sub-01\ses-Session1\eeg\sub-01_ses-Session1_task-rest_eeg.mpl",
            },
            {
                "session": "Session1",
                "relative_path": r"sub-02\ses-Session1\eeg\sub-02_ses-Session1_task-rest_eeg.mpl",
            },
        ]

        ignored_prefixes = recording_ignored_prefixes_from_recordings(recordings)

        self.assertEqual(ignored_prefixes, ())
        self.assertEqual(
            normalize_recording_id(recordings[0]["relative_path"], ignored_prefixes),
            "ses-Session1_task-rest_eeg",
        )

    def test_collapsed_recording_id_matches_parameter_files_with_and_without_session(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            _write_param(derivatives, "sub-01", None, [[1.0, 3.0]])
            _write_param(derivatives, "sub-03", "ses-Session1", [[5.0, 7.0]])

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01", "sub-03"],
                "groups": {
                    "group_1": {
                        "group_name": "Rest",
                        "group_color": "#123456",
                        "subjects": [],
                        "files": ["task-rest_eeg"],
                    },
                },
                "plot_features_config": {
                    "selected_recordings": [
                        {"subject": "01", "session": "", "relative_path": r"sub-01\eeg\sub-01_task-rest_eeg.mpl"},
                        {
                            "subject": "03",
                            "session": "Session1",
                            "relative_path": (
                                r"sub-03\ses-Session1\eeg\sub-03_ses-Session1_task-rest_eeg.mpl"
                            ),
                        },
                    ],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "absolute_band_power", "alpha", [0, 1])

            self.assertEqual([observation.id for observation in prepared.groups[0].observations], ["sub-01", "sub-03"])
            np.testing.assert_allclose([float(observation.values) for observation in prepared.groups[0].observations],
                [2.0, 6.0])

    def test_segment_recording_id_selects_only_that_condition(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            _write_param(derivatives, "sub-01", None, [[1.0, 3.0]], "fullrecordingeyesopen")
            _write_param(derivatives, "sub-01", None, [[101.0, 103.0]], "fullrecordingeyesclosed")

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01"],
                "groups": {
                    "group_1": {
                        "group_name": "Eyes open",
                        "group_color": "#123456",
                        "subjects": [],
                        "files": ["task-rest_eeg_segment-fullrecordingeyesopen"],
                    },
                },
                "plot_features_config": {
                    "selected_recordings": [
                        {"subject": "01", "session": "", "relative_path": r"sub-01\eeg\sub-01_task-rest_eeg.mpl"},
                    ],
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "absolute_band_power", "alpha", [0, 1])

            self.assertEqual(
                [observation.id for observation in prepared.groups[0].observations],
                ["sub-01"],
            )
            np.testing.assert_allclose([float(observation.values) for observation in prepared.groups[0].observations],
                [2.0])

    def test_loader_uses_parameter_segments_for_available_recordings(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            _write_param(derivatives, "sub-01", None, [[1.0, 3.0]], "fullrecordingeyesopen")
            _write_param(derivatives, "sub-01", None, [[101.0, 103.0]], "fullrecordingeyesclosed")

            recordings = PlotFeaturesLoadDataWidget._recordings_from_parameter_files(derivatives, ())

            self.assertEqual(recordings, [
                "task-rest_eeg_segment-fullrecordingeyesclosed",
                "task-rest_eeg_segment-fullrecordingeyesopen",
            ])

    def test_plot_index_keeps_non_segment_condition_entities_after_band(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            _write_param(derivatives, "sub-01", None, [[1.0, 3.0]], "rest", "_condition-baseline")

            state = {
                "derivatives_path": str(derivatives),
                "analysis_mode": "within",
                "channel_names": ["C1", "C2"],
                "plot_selected_subjects": ["sub-01"],
                "groups": {
                    "group_1": {
                        "group_name": "Baseline",
                        "group_color": "#123456",
                        "subjects": [],
                        "files": ["task-rest_eeg_segment-rest_condition-baseline"],
                    },
                },
            }

            prepared = BasePlot.prepare_grouped_plot_data(state, "absolute_band_power", "alpha", [0, 1])

            self.assertEqual(
                [observation.id for observation in prepared.groups[0].observations],
                ["sub-01"],
            )
            np.testing.assert_allclose([float(observation.values) for observation in prepared.groups[0].observations],
                [2.0])


if __name__ == "__main__":
    unittest.main()
