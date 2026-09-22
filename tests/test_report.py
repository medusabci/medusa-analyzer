import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication, QLabel

from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_features_widget import (
    EEGFeaturesWidget,
)
from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_preprocessing_widget import (
    EEGPreprocessingWidget,
)
from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_report_widget import (
    EEGReportWidget,
)
from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_segmentation_widget import (
    EEGSegmentationWidget,
)
from medusa_analyzer.frontend.widgets.report import ReportWidget


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


def _loaded_state() -> dict:
    return {
        "metadata": {
            "n_recordings": 1,
            "subjects": ["01"],
            "sessions": ["01"],
            "datatype": "eeg",
            "task": "test",
            "sampling_frequency": 256.0,
            "n_channels": 2,
            "channel_set": ["C3", "C4"],
        },
        "broadband": {"id": "broadband", "title": "Broadband", "enabled": True,
            "low_cut": 0.1, "high_cut": 128.0},
    }


def _segmentation_state(selection_mode: str, event_groups: list[dict] | None = None,
    strategy: str = "window-based") -> dict:
    has_duration = selection_mode == "duration" or any(
        group.get("duration_events") for group in (event_groups or [])
    )
    has_instant = selection_mode == "instant" or any(
        group.get("instant_events") for group in (event_groups or [])
    )
    if strategy in {"window", "window-based"}:
        strategy = "window-based"
    elif strategy in {"onset", "onset-based"}:
        strategy = "onset-based"
    if has_instant and not has_duration:
        strategy = "onset-based"
    duration_epoch = {
        "duration_epoch_length_ms": 1500 if selection_mode == "duration" else 2000,
        "stride_percent": 20 if selection_mode == "duration" else 25,
    }
    onset_epoch = {
        "start": -100 if selection_mode in {"duration", "instant"} else -120,
        "end": 400 if selection_mode in {"duration", "instant"} else 380,
        "baseline_start": -50,
        "baseline_end": 0,
    }
    normalization = {
        "enabled": True,
        "mode": "mean" if selection_mode == "nested" and has_duration and not has_instant else "mean_std",
    }
    return {
        "segmentation_mode": "nested" if selection_mode == "nested" else "independent",
        "segmentation_strategy": strategy,
        "event_groups": event_groups or ([{
            "base_event": None,
            "duration_events": ["duration_event"] if selection_mode == "duration" else [],
            "instant_events": ["instant_event"] if selection_mode == "instant" else [],
        }] if selection_mode in {"duration", "instant"} else []),
        "epoch_parameters": {
            "duration_events": duration_epoch if has_duration and strategy == "window-based" else {},
            "instant_events": onset_epoch if has_instant or strategy == "onset-based" else {},
        },
        "normalization": normalization,
        "thresholding": {"enabled": False},
        "resampling": {"enabled": False},
    }


class DummyReportWidget(ReportWidget):
    def _preprocessing_section(self):
        return self._section("Dummy pre-processing", [("Status", "Ready")])

    def _features_section(self):
        return self._section("Dummy features", [("Choice", "Enabled")])


class ReportWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_report_widget_supports_sections_from_subclasses(self):
        widget = DummyReportWidget(
            config={
                "include_metadata": True,
                "include_preprocessing_summary": True,
                "include_selected_features": True,
            },
            state=_loaded_state(),
            title="Report",
            description="Description",
        )
        widget.show()
        self.app.processEvents()

        texts = [label.text() for label in widget.findChildren(QLabel)]
        self.assertIn("Metadata", texts)
        self.assertIn("Dummy pre-processing", texts)
        self.assertIn("Dummy features", texts)

    def test_eeg_report_rejects_legacy_normalization_shape(self):
        defaults = _eeg_defaults()
        state = _loaded_state()
        state["segmentation"] = _segmentation_state("duration")
        state["segmentation"]["normalization"] = {
            "duration": {"enabled": True, "mode": "mean_std"},
            "instant": {},
        }

        with self.assertRaisesRegex(ValueError, "must not be stored per event type"):
            EEGReportWidget({}, defaults, state)

    def test_report_widget_defaults_output_to_input_parent_derivatives(self):
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "recording.edf"
            input_path.write_text("", encoding="utf-8")
            state = {"input_data": [str(input_path)]}

            widget = DummyReportWidget(
                config={"include_metadata": False},
                state=state,
                title="Report",
                description="Description",
            )
            widget.show()
            self.app.processEvents()

            expected_output = str(Path(temp_dir) / "derivatives")
            self.assertEqual(state["output_root_path"], str(Path(temp_dir)))
            self.assertEqual(state["output_path"], expected_output)
            self.assertEqual(state["output_path_mode"], "default")
            self.assertTrue(widget.can_continue())

            texts = [label.text() for label in widget.findChildren(QLabel)]
            self.assertIn("Output", texts)
            self.assertIn(expected_output, texts)

    def test_report_run_pipeline_writes_config_json_to_selected_output_path(self):
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "recording.edf"
            input_path.write_text("", encoding="utf-8")
            state = {
                "input_data": [str(input_path)],
                "completion_status": "incompleted",
                "feature_params": {
                    "relative_band_power": {"selected_frequency_bands": [{"id": "delta"}]},
                    "psd": {"segment_percent": 60},
                },
                "nested": {"path": Path(temp_dir), "choices": {"beta", "alpha"}},
                "preprocessing": {
                    "selected_frequency_bands": [{"id": "delta"}],
                    "filters": {},
                },
                "segmentation": {
                    "segmentation_mode": "nested",
                    "epoch_parameters": {"duration_events": {}, "instant_events": {}},
                    "normalization": {"enabled": True, "mode": "mean"},
                },
                "selected_recordings": [
                    {
                        "path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "relative_path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "subject": "01",
                        "datatype": "eeg",
                    }
                ],
            }
            widget = DummyReportWidget(
                config={"include_metadata": False},
                state=state,
                title="Report",
                description="Description",
            )

            widget.run_pipeline()

            config_path = Path(temp_dir) / "derivatives" / "config.json"
            self.assertTrue(config_path.exists())
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["input_data"], [str(input_path)])
            self.assertEqual(saved["output_path"], str(Path(temp_dir) / "derivatives"))
            self.assertEqual(saved["completion_status"], "completed")
            self.assertEqual(saved["pipeline_config_path"], str(config_path))
            self.assertEqual(saved["nested"], {"choices": ["alpha", "beta"], "path": str(Path(temp_dir))})
            self.assertEqual(saved["preprocessing"]["selected_frequency_bands"], [{"id": "delta"}])
            self.assertEqual(
                saved["feature_params"]["relative_band_power"],
                {"selected_frequency_bands": [{"id": "delta"}]},
            )
            self.assertEqual(saved["feature_params"]["psd"], {"segment_percent": 60})
            self.assertIn("normalization", saved["segmentation"])
            self.assertEqual(saved["segmentation"]["normalization"], {"enabled": True, "mode": "mean"})
            self.assertNotIn("duration", saved["segmentation"]["normalization"])
            self.assertNotIn("instant", saved["segmentation"]["normalization"])
            self.assertNotIn("nested_normalization", saved["segmentation"])
            self.assertEqual(
                saved["selected_recordings"],
                [
                    {
                        "datatype": "eeg",
                        "path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "relative_path": "sub-01/eeg/sub-01_task-test_eeg.edf",
                        "subject": "01",
                    }
                ],
            )
            self.assertEqual(state["completion_status"], "completed")

    def test_eeg_report_run_pipeline_writes_full_state_config_to_derivatives(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            state = _loaded_state()
            state["bids_root"] = temp_dir
            state["completion_status"] = "incompleted"
            state["segmentation"] = _segmentation_state(
                "nested",
                [
                    {
                        "base_event": "base",
                        "duration_events": [],
                        "instant_events": ["instant_child"],
                    }
                ],
            )
            report = EEGReportWidget({}, defaults, state)

            report.run_pipeline()

            config_path = Path(temp_dir) / "derivatives" / "config.json"
            self.assertTrue(config_path.exists())
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["bids_root"], temp_dir)
            self.assertEqual(saved["output_derivatives_path"], str(Path(temp_dir) / "derivatives"))
            self.assertEqual(saved["segmentation"]["segmentation_mode"], "nested")
            self.assertEqual(saved["segmentation"]["segmentation_strategy"], "onset-based")
            self.assertNotIn("selection_mode", saved["segmentation"])
            self.assertEqual(
                saved["segmentation"]["event_groups"][0]["instant_events"],
                ["instant_child"],
            )
            self.assertIn("epoch_parameters", saved["segmentation"])
            self.assertEqual(
                saved["segmentation"]["epoch_parameters"],
                {
                    "duration_events": {},
                    "instant_events": {
                        "start": -120,
                        "end": 380,
                        "baseline_start": -50,
                        "baseline_end": 0,
                    },
                },
            )
            self.assertIn("normalization", saved["segmentation"])
            self.assertNotIn("baseline_window_ms", saved["segmentation"]["normalization"])
            self.assertNotIn("duration", saved["segmentation"]["normalization"])
            self.assertNotIn("instant", saved["segmentation"]["normalization"])
            self.assertNotIn("selected_duration_events", saved["segmentation"])
            self.assertNotIn("selected_instant_events", saved["segmentation"])
            self.assertNotIn("nested_groups", saved["segmentation"])
            self.assertNotIn("nested_epoch", saved["segmentation"])
            self.assertNotIn("nested_normalization", saved["segmentation"])
            self.assertEqual(saved["completion_status"], "completed")

    def test_eeg_report_nested_segmentation_reports_only_duration_parameters_when_only_duration_children_exist(self):
        defaults = _eeg_defaults()
        state = _loaded_state()
        state["segmentation"] = _segmentation_state(
            "nested",
            [{"base_event": "base", "duration_events": ["duration_child"], "instant_events": []}],
        )

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        texts = [label.text() for label in report.findChildren(QLabel)]
        self.assertTrue(any("Duration window 2000 ms, overlap 25%" in text for text in texts))
        self.assertTrue(any("Duration: Mean" in text for text in texts))
        self.assertFalse(any("Instant onset -120 to 380 ms" in text for text in texts))
        self.assertFalse(any("Instant: Z-score, baseline -50 to 0 ms" in text for text in texts))

    def test_eeg_report_nested_segmentation_reports_only_instant_parameters_when_only_instant_children_exist(self):
        defaults = _eeg_defaults()
        state = _loaded_state()
        state["segmentation"] = _segmentation_state(
            "nested",
            [{"base_event": "base", "duration_events": [], "instant_events": ["instant_child"]}],
        )

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        texts = [label.text() for label in report.findChildren(QLabel)]
        self.assertTrue(any("Instant onset -120 to 380 ms" in text for text in texts))
        self.assertTrue(any("Instant: Z-score, baseline -50 to 0 ms" in text for text in texts))
        self.assertFalse(any("Duration window 2000 ms, overlap 25%" in text for text in texts))
        self.assertFalse(any("Duration: Mean" in text for text in texts))

    def test_eeg_report_nested_segmentation_marks_mixed_child_types_as_unsupported(self):
        defaults = _eeg_defaults()
        state = _loaded_state()
        state["segmentation"] = _segmentation_state(
            "nested",
            [
                {
                    "base_event": "base",
                    "duration_events": ["duration_child"],
                    "instant_events": ["instant_child"],
                }
            ],
        )

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        texts = [label.text() for label in report.findChildren(QLabel)]
        self.assertIn("Mixed nested event types are not supported", texts)
        self.assertFalse(any("Duration window 2000 ms" in text for text in texts))
        self.assertFalse(any("Instant onset -120 to 380 ms" in text for text in texts))

    def test_eeg_report_duration_onset_strategy_reports_onset_parameters_and_baseline(self):
        defaults = _eeg_defaults()
        state = _loaded_state()
        state["segmentation"] = _segmentation_state("duration", strategy="onset")

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        texts = [label.text() for label in report.findChildren(QLabel)]
        self.assertIn("Onset-based", texts)
        self.assertTrue(any("-100 to 400 ms" in text for text in texts))
        self.assertTrue(any("Z-score, baseline -50 to 0 ms" in text for text in texts))

    def test_eeg_report_independent_segmentation_reports_only_selected_event_type_parameters(self):
        defaults = _eeg_defaults()
        cases = [
            ("duration", "1500 ms, overlap 20%", "Z-score", "baseline -50 to 0 ms"),
            ("instant", "-100 to 400 ms", "Z-score, baseline -50 to 0 ms", "1500 ms"),
        ]

        for selection_mode, expected_epoch, expected_normalization, forbidden_text in cases:
            with self.subTest(selection_mode=selection_mode):
                state = _loaded_state()
                state["segmentation"] = _segmentation_state(selection_mode)

                report = EEGReportWidget({}, defaults, state)
                report.show()
                self.app.processEvents()

                texts = [label.text() for label in report.findChildren(QLabel)]
                self.assertTrue(any(expected_epoch in text for text in texts))
                self.assertTrue(any(expected_normalization in text for text in texts))
                self.assertFalse(any(forbidden_text in text for text in texts))

    def test_eeg_report_widget_groups_selected_features_by_category_and_parameters(self):
        defaults = _eeg_defaults()
        state = _loaded_state()

        preprocessing = EEGPreprocessingWidget({}, defaults, state)
        preprocessing.show()
        self.app.processEvents()
        preprocessing.filters["bandpass"].low.setValue(1.0)
        preprocessing.filters["bandpass"].high.setValue(50.0)
        self.app.processEvents()

        features = EEGFeaturesWidget({}, defaults, state)
        features.show()
        self.app.processEvents()
        features.checkboxes["absolute_band_power"].setChecked(True)
        features.checkboxes["relative_band_power"].setChecked(True)
        features.param_widgets["psd"]["segment_percent"].setValue(60)
        features.param_widgets["psd"]["window"].setCurrentIndex(1)
        features.checkboxes["sample_entropy"].setChecked(True)
        self.app.processEvents()

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        texts = [label.text() for label in report.findChildren(QLabel)]
        self.assertIn("Metadata", texts)
        self.assertIn("Pre-processing", texts)
        self.assertIn("Features", texts)
        self.assertIn("Spectral features", texts)
        self.assertIn("Basic statistical features", texts)
        self.assertIn("Non-linear features", texts)
        self.assertTrue(
            any(
                "Absolute band power" in text
                and "Absolute band power (bands=" not in text
                and "Relative band power (bands=Delta 0.5 Hz-4 Hz" in text
                and "PSD (Segment (%)=60, Overlap (%)=50, Window=Bartlett)" in text
                for text in texts
            )
        )
        self.assertTrue(
            any(
                "Sample entropy (m=1, r=0.1)" in text
                for text in texts
            )
        )
        self.assertTrue(
            any(
                "Delta (0.5 Hz-4 Hz)" in text
                and "Broadband (1 Hz-50 Hz)" in text
                for text in texts
            )
        )

    def test_eeg_report_widget_uses_metadata_broadband_and_custom_bands_without_preprocessing(self):
        defaults = _eeg_defaults()
        state = _loaded_state()

        features = EEGFeaturesWidget({}, defaults, state)
        features.show()
        self.app.processEvents()

        report = EEGReportWidget({}, defaults, state)
        report.show()
        self.app.processEvents()

        self.assertEqual(
            report._feature_summary("absolute_band_power"),
            "Absolute band power",
        )
        self.assertEqual(
            report._feature_summary("relative_band_power"),
            "Relative band power (bands=Delta 0.5 Hz-4 Hz, Theta 4 Hz-8 Hz, Alpha 8 Hz-13 Hz, Beta 13 Hz-30 Hz, Gamma 30 Hz-45 Hz)",
        )

    def test_eeg_report_config_keeps_only_broadband_when_no_preprocessing_band_is_enabled(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            state = _loaded_state()
            state["bids_root"] = temp_dir
            preprocessing = EEGPreprocessingWidget({}, defaults, state)
            preprocessing.show()
            self.app.processEvents()

            for row_widgets in preprocessing.bands.row_widgets:
                row_widgets["enabled"].setChecked(False)
            self.app.processEvents()

            report = EEGReportWidget({}, defaults, state)
            report.run_pipeline()

            config_path = Path(temp_dir) / "derivatives" / "config.json"
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["preprocessing"]["selected_frequency_bands"],
                [saved["broadband"]],
            )
            self.assertTrue(saved["preprocessing"]["car"])
            self.assertEqual(
                set(saved["preprocessing"]),
                {"car", "filters", "selected_frequency_bands"},
            )
            self.assertEqual(
                set(saved["preprocessing"]["filters"]["bandpass"]),
                {"enabled", "filter_type", "filter_design", "low_cut", "high_cut", "order", "window"},
            )
            self.assertEqual(saved["preprocessing"]["filters"]["bandpass"]["filter_type"], "bandpass")
            self.assertEqual(saved["preprocessing"]["filters"]["bandpass"]["filter_design"], "fir")

    def test_eeg_report_config_uses_resampled_broadband_state(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            state = _loaded_state()
            state["bids_root"] = temp_dir
            state["duration_events"] = ["recording"]
            state["instant_events"] = []
            state["preprocessing"] = {
                "filters": {
                    "bandpass": {
                        "enabled": True,
                        "filter_type": "bandpass",
                        "filter_design": "fir",
                        "low_cut": 1.0,
                        "high_cut": 70.0,
                        "order": 1000,
                        "window": "hamming",
                    },
                    "notch": {
                        "enabled": True,
                        "filter_type": "bandstop",
                        "filter_design": "fir",
                        "low_cut": 75.0,
                        "high_cut": 77.0,
                        "order": 1001,
                        "window": "hamming",
                    },
                },
                "selected_frequency_bands": [
                    {"id": "high_beta", "title": "High beta", "enabled": True, "low_cut": 55.0, "high_cut": 75.0},
                    {"id": "broadband", "title": "Broadband", "enabled": True, "low_cut": 0.1, "high_cut": 128.0},
                ],
            }

            segmentation = EEGSegmentationWidget({}, defaults, state)
            segmentation.show()
            self.app.processEvents()
            segmentation.duration_events_list.item(0).setSelected(True)
            segmentation.resampling_enabled.setChecked(True)
            segmentation.target_sampling_frequency.setValue(120)
            self.app.processEvents()

            report = EEGReportWidget({}, defaults, state)
            report.run_pipeline()

            config_path = Path(temp_dir) / "derivatives" / "config.json"
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["segmentation"]["resampling"]["target_sampling_frequency"], 120)
            self.assertEqual(saved["broadband"]["high_cut"], 60.0)
            self.assertEqual(saved["preprocessing"]["filters"]["bandpass"]["high_cut"], 60.0)
            self.assertEqual(saved["preprocessing"]["filters"]["notch"]["high_cut"], 60.0)
            self.assertEqual(saved["preprocessing"]["selected_frequency_bands"], [saved["broadband"]])

    def test_eeg_report_defaults_output_to_bids_derivatives(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            state = _loaded_state()
            state["bids_root"] = temp_dir

            report = EEGReportWidget({}, defaults, state)
            report.show()
            self.app.processEvents()

            expected_output = str(Path(temp_dir) / "derivatives")
            self.assertEqual(state["output_root_path"], str(Path(temp_dir)))
            self.assertEqual(state["output_derivatives_path"], expected_output)
            self.assertEqual(state["output_path_mode"], "default")
            self.assertTrue(report.can_continue())

            texts = [label.text() for label in report.findChildren(QLabel)]
            self.assertIn("Output", texts)
            self.assertIn(expected_output, texts)

    def test_eeg_report_custom_output_root_stores_derivatives_child(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            bids_root = Path(temp_dir) / "bids"
            custom_root = Path(temp_dir) / "custom-output"
            bids_root.mkdir()
            custom_root.mkdir()
            state = _loaded_state()
            state["bids_root"] = str(bids_root)
            report = EEGReportWidget({}, defaults, state)

            report._set_output_root_path(custom_root, "custom")
            report.refresh()
            self.app.processEvents()

            self.assertEqual(state["output_root_path"], str(custom_root))
            self.assertEqual(state["output_derivatives_path"], str(custom_root / "derivatives"))
            self.assertEqual(state["output_path_mode"], "custom")
            self.assertTrue(report.can_continue())

    def test_eeg_report_disables_run_until_output_root_is_valid(self):
        defaults = _eeg_defaults()
        with TemporaryDirectory() as temp_dir:
            missing_root = Path(temp_dir) / "missing"
            state = _loaded_state()
            state["bids_root"] = temp_dir
            state["output_root_path"] = str(missing_root)
            state["output_derivatives_path"] = str(missing_root / "derivatives")
            state["output_path_mode"] = "custom"

            report = EEGReportWidget({}, defaults, state)
            report.show()
            self.app.processEvents()

            self.assertFalse(report.can_continue())
            texts = [label.text() for label in report.findChildren(QLabel)]
            self.assertIn("Selected output folder does not exist.", texts)


if __name__ == "__main__":
    unittest.main()
