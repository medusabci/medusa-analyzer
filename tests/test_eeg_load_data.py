import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_load_data_widget import (
    EEGLoadDataWidget,
)


def _eeg_defaults() -> dict:
    defaults_path = (
        Path(__file__).resolve().parents[1]
        / "medusa_analyzer"
        / "frontend"
        / "experiments"
        / "eeg"
        / "defaults.json"
    )
    return json.loads(defaults_path.read_text(encoding="utf-8"))


def _group() -> dict:
    return {
        "id": "group-1",
        "n_recordings": 1,
        "subjects": ["01"],
        "sessions": ["01"],
        "datatype": "eeg",
        "task": "test",
        "sampling_frequency": 256.0,
        "n_channels": 2,
        "channel_set": ["C3", "C4"],
        "reference": "average",
        "duration_events": ["full_recording"],
        "instant_events": ["stimulus"],
        "recordings": [
            {
                "path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                "relative_path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                "subject": "01",
                "session": "01",
                "datatype": "eeg",
                "extension": ".edf",
                "sidecars": {"TaskName": "test"},
                "json_sidecars": [{"path": "sidecar.json"}],
            }
        ],
    }


class EEGLoadDataWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_loaded_bids_group_is_stored_as_clean_state(self):
        with TemporaryDirectory() as temp_dir:
            state = {"bids_groups": [], "loader_results": []}
            widget = EEGLoadDataWidget({}, _eeg_defaults(), state)
            widget._selected_source = temp_dir

            widget._loaded({"root": temp_dir, "groups": [_group()]})
            self.app.processEvents()

            self.assertEqual(state["input_data"], [temp_dir])
            self.assertEqual(state["bids_root"], temp_dir)
            self.assertEqual(state["selected_bids_group"], "group-1")
            self.assertEqual(state["duration_events"], ["full_recording"])
            self.assertEqual(state["instant_events"], ["stimulus"])
            self.assertNotIn("bids_groups", state)
            self.assertNotIn("loader_results", state)
            self.assertEqual(
                state["selected_recordings"],
                [
                    {
                        "path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "relative_path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "subject": "01",
                        "session": "01",
                        "datatype": "eeg",
                        "extension": ".edf",
                    }
                ],
            )

    def test_group_label_shows_channel_count_instead_of_reference(self):
        label = EEGLoadDataWidget._group_label(_group())

        self.assertIn("2 ch", label)
        self.assertNotIn("average", label)


if __name__ == "__main__":
    unittest.main()
