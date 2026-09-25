import json
from math import ceil
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFrame, QGridLayout, QLabel, QPushButton, QWidget

from medusa_analyzer.frontend.experiments.eeg.widgets.eeg_segmentation_widget import (
    EEGSegmentationWidget,
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


def _loaded_state() -> dict:
    return {
        "metadata": {
            "n_recordings": 1,
            "subjects": ["01"],
            "sessions": ["01"],
            "datatype": "eeg",
            "task": "test",
            "sampling_frequency": 250.0,
            "n_channels": 2,
            "channel_set": ["C3", "C4"],
        },
        "selected_bids_group": "group-1",
        "duration_events": ["full_recording", "trial"],
        "instant_events": ["stimulus"],
    }


def _loaded_state_with_events(duration_events: list[str], instant_events: list[str]) -> dict:
    state = _loaded_state()
    state["duration_events"] = duration_events
    state["instant_events"] = instant_events
    return state


def _has_ancestor_with_role(widget, role: str) -> bool:
    parent = widget.parent()
    while parent is not None:
        if hasattr(parent, "property") and parent.property("role") == role:
            return True
        parent = parent.parent()
    return False


class EEGSegmentationWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_segmentation_widget_rejects_legacy_normalization_shape(self):
        state = _loaded_state()
        state["segmentation"] = {
            "normalization": {
                "duration": {"enabled": True, "mode": "mean"},
                "instant": {},
            }
        }

        with self.assertRaisesRegex(ValueError, "must not be stored per event type"):
            EEGSegmentationWidget({}, _eeg_defaults(), state)

    def test_nested_mode_uses_single_child_type_without_dual_parameter_selectors(self):
        state = _loaded_state_with_events(["full_recording", "trial"], ["stimulus", "response"])
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        self.assertFalse(hasattr(widget, "_epoch_parameters"))
        self.assertFalse(hasattr(widget, "_normalization_parameters"))
        self.assertEqual(state["segmentation"]["epoch_parameters"], {"duration_events": {}, "instant_events": {}})
        self.assertEqual(state["segmentation"]["normalization"], {"enabled": False, "mode": "mean_std"})
        self.assertEqual(widget.independent_mode_button.property("role"), "segmentation-mode-button")
        self.assertFalse(hasattr(widget, "epoch_target_panel"))
        self.assertFalse(hasattr(widget, "epoch_start"))
        self.assertFalse(hasattr(widget, "duration_epoch_length"))
        self.assertTrue(widget.nested_mode_button.isEnabled())

        widget.nested_mode_button.click()
        state["segmentation"]["event_groups"] = [
            {
                "base_event": "trial",
                "duration_events": [],
                "instant_events": ["stimulus"],
            }
        ]
        widget._sync()
        self.app.processEvents()

        self.assertFalse(hasattr(widget, "epoch_target_panel"))
        self.assertFalse(widget.normalization_target_panel.isVisible())
        add_instant_buttons = [
            button
            for button in widget.findChildren(QPushButton)
            if button.text() == "+ Add instant event"
        ]
        add_duration_buttons = [
            button
            for button in widget.findChildren(QPushButton)
            if button.text() == "+ Add duration event"
        ]
        self.assertTrue(add_duration_buttons)
        self.assertEqual(
            add_duration_buttons[0].property("role"),
            "segmentation-duration-action",
        )
        self.assertFalse(_has_ancestor_with_role(add_duration_buttons[0], "nested-base-event"))
        self.assertFalse(add_duration_buttons[0].isEnabled())
        self.assertIn("already using instant", add_duration_buttons[0].toolTip())
        self.assertTrue(add_instant_buttons)
        self.assertEqual(
            add_instant_buttons[0].property("role"),
            "segmentation-instant-action",
        )
        self.assertFalse(_has_ancestor_with_role(add_instant_buttons[0], "nested-base-event"))
        self.assertTrue(add_instant_buttons[0].isEnabled())
        self.assertTrue(
            any(
                label.objectName() == "nestedBaseEventTitle"
                and label.text() == "trial"
                for label in widget.findChildren(QLabel)
            )
        )
        self.assertFalse(widget.summary_panel.isVisible())
        self.assertTrue(
            any(
                frame.property("role") == "nested-base-event"
                for frame in widget.findChildren(QFrame)
            )
        )
        self.assertTrue(
            any(
                child.property("role") == "nested-group-editor"
                for child in widget.findChildren(QWidget)
            )
        )
        self.assertTrue(
            any(
                frame.property("role") == "nested-contained-events"
                for frame in widget.findChildren(QFrame)
            )
        )
        self.assertTrue(
            any(
                frame.objectName() == "summaryInstantChip"
                and frame.property("compact") == "true"
                and _has_ancestor_with_role(frame, "nested-contained-events")
                and _has_ancestor_with_role(frame, "nested-base-event")
                for frame in widget.findChildren(QFrame)
            )
        )
        self.assertFalse(any(frame.objectName() == "summaryDurationChip" for frame in widget.findChildren(QFrame)))

        self.assertTrue(widget.onset_segmentation_widget.isVisible())
        self.assertFalse(widget.window_segmentation_widget.isVisible())
        widget.onset_segmentation_widget.window_start_slider.setValue(-120)
        widget.onset_segmentation_widget.window_end_slider.setValue(380)
        self.app.processEvents()

        segmentation = state["segmentation"]
        self.assertEqual(segmentation["segmentation_mode"], "nested")
        self.assertNotIn("selection_mode", segmentation)
        self.assertNotIn("selected_duration_events", segmentation)
        self.assertNotIn("selected_instant_events", segmentation)
        self.assertNotIn("nested_epoch", segmentation)
        self.assertNotIn("nested_normalization", segmentation)
        self.assertNotIn("nested_groups", segmentation)
        self.assertNotIn("epoch_window_ms", segmentation)
        self.assertNotIn("duration_epoch_length_ms", segmentation)
        self.assertNotIn("stride_percent", segmentation)
        self.assertEqual(segmentation["epoch_parameters"]["duration_events"], {})
        self.assertEqual(
            segmentation["epoch_parameters"]["instant_events"],
            {"start": -120, "end": 380, "baseline_start": -300, "baseline_end": 0},
        )
        self.assertEqual(segmentation["segmentation_strategy"], "onset-based")

        widget.normalization_enabled.setChecked(True)
        widget.normalization_mode.setCurrentIndex(widget.normalization_mode.findData("mean_std"))
        widget.onset_segmentation_widget.baseline_start_slider.setValue(-50)
        widget.onset_segmentation_widget.baseline_end_slider.setValue(0)
        self.app.processEvents()
        self.assertFalse(hasattr(widget, "baseline_start"))
        self.assertFalse(hasattr(widget, "baseline_end"))
        self.assertTrue(widget.normalization_baseline_hint.isVisible())

        segmentation = state["segmentation"]
        self.assertEqual(
            segmentation["normalization"],
            {
                "enabled": True,
                "mode": "mean_std",
            },
        )
        self.assertNotIn("duration", segmentation["normalization"])
        self.assertNotIn("instant", segmentation["normalization"])
        self.assertEqual(
            segmentation["epoch_parameters"]["instant_events"],
            {"start": -120, "end": 380, "baseline_start": -50, "baseline_end": 0},
        )
        self.assertEqual(widget.normalization_mode.itemText(widget.normalization_mode.findData("mean_std")), "Z-score")
        self.assertTrue(widget.can_continue())

    def test_segmentation_widget_has_no_inline_stylesheet(self):
        widget_path = (
            Path(__file__).resolve().parents[1]
            / "medusa_analyzer"
            / "frontend"
            / "experiments"
            / "eeg"
            / "widgets"
            / "eeg_segmentation_widget.py"
        )
        widget_source = widget_path.read_text(encoding="utf-8")
        self.assertNotIn("setStyleSheet", widget_source)
        self.assertNotIn("Minimum 250 Hz (Nyquist).", widget_source)
        self.assertNotIn("Increasing overlap makes consecutive epochs overlap more.", widget_source)
        self.assertNotIn("By default, the baseline ends at the onset.", widget_source)
        self.assertIn("Duration of each window used to segment duration events.", widget_source)
        self.assertIn("Percentage of each epoch shared with the next epoch.", widget_source)
        self.assertIn("End of the baseline interval relative to the onset.", widget_source)
        segmentation_defaults = _eeg_defaults()["segmentation"]
        self.assertNotIn("selection_mode", segmentation_defaults)
        self.assertNotIn("selected_duration_events", segmentation_defaults)
        self.assertNotIn("selected_instant_events", segmentation_defaults)
        self.assertNotIn("nested_groups", segmentation_defaults)
        self.assertNotIn("nested_epoch", segmentation_defaults)
        self.assertNotIn("nested_normalization", segmentation_defaults)
        self.assertNotIn("epoch_window_ms", segmentation_defaults)
        self.assertNotIn("duration_epoch_length_ms", segmentation_defaults)
        self.assertNotIn("stride_percent", segmentation_defaults)
        self.assertEqual(segmentation_defaults["segmentation_strategy"], "window-based")
        self.assertEqual(
            segmentation_defaults["epoch_parameters"]["instant_events"],
            {"start": -300, "end": 700, "baseline_start": -300, "baseline_end": 0},
        )
        self.assertEqual(segmentation_defaults["normalization"], {"enabled": False, "mode": "mean_std"})
        self.assertNotIn("duration", segmentation_defaults["normalization"])
        self.assertNotIn("instant", segmentation_defaults["normalization"])
        self.assertNotIn("duration", segmentation_defaults["epoch_parameters"])
        self.assertNotIn("instant", segmentation_defaults["epoch_parameters"])

    def test_independent_mode_stores_selection_as_event_group(self):
        state = _loaded_state()
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.duration_events_list.item(0).setSelected(True)
        self.app.processEvents()

        segmentation = state["segmentation"]
        self.assertEqual(segmentation["segmentation_mode"], "independent")
        self.assertEqual(segmentation["segmentation_strategy"], "window-based")
        self.assertTrue(widget.strategy_panel.isVisible())
        self.assertTrue(widget.window_strategy_button.isVisible())
        self.assertTrue(widget.window_strategy_button.isChecked())
        self.assertTrue(widget.window_segmentation_widget.isVisible())
        self.assertFalse(hasattr(widget, "epoch_start"))
        self.assertFalse(hasattr(widget, "duration_epoch_length"))
        self.assertEqual(
            segmentation["event_groups"],
            [{
                "base_event": None,
                "duration_events": ["full_recording"],
                "instant_events": [],
            }],
        )
        self.assertNotIn("selected_duration_events", segmentation)
        self.assertNotIn("selected_instant_events", segmentation)
        self.assertNotIn("nested_groups", segmentation)

    def test_segment_by_response_forces_onset_strategy(self):
        state = _loaded_state_with_events(["baseline", "imgaa"], [])
        state["event_responses"] = {"imgaa": [1, -1]}
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.duration_events_list.item(1).setSelected(True)
        self.app.processEvents()
        self.assertEqual(state["segmentation"]["segmentation_strategy"], "window-based")
        self.assertTrue(widget.window_strategy_button.isVisible())

        widget.segment_by_response_checkbox.setChecked(True)
        self.app.processEvents()
        for index in range(widget.duration_events_list.count()):
            item = widget.duration_events_list.item(index)
            item.setSelected(item.text() == "imgaa_1")
        self.app.processEvents()

        self.assertEqual(state["segmentation"]["segmentation_strategy"], "onset-based")
        self.assertFalse(widget.window_strategy_button.isVisible())
        self.assertFalse(widget.window_strategy_button.isEnabled())
        self.assertTrue(widget.onset_strategy_button.isChecked())
        self.assertTrue(widget.onset_segmentation_widget.isVisible())
        self.assertEqual(
            state["segmentation"]["event_groups"],
            [{
                "base_event": None,
                "duration_events": [{"trial_type": "imgaa", "response": 1}],
                "instant_events": [],
            }],
        )

    def test_duration_strategy_switches_controls_and_window_preview_stays_in_sync(self):
        state = _loaded_state()
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.duration_events_list.item(0).setSelected(True)
        self.app.processEvents()

        self.assertEqual(widget.window_segmentation_widget.epoch_slider.minimum(), 100)
        self.assertGreater(widget.window_segmentation_widget.epoch_slider.maximum(), 1_000_000)
        self.assertEqual(widget.window_segmentation_widget.diagram.VISUAL_FULL_WIDTH_EPOCH_MS, 60000)
        self.assertGreaterEqual(widget.window_segmentation_widget.diagram.minimumHeight(), 315)
        self.assertEqual(widget.window_segmentation_widget.overlap_slider.maximum(), 99)
        self.assertFalse(hasattr(widget.window_segmentation_widget, "epoch_value"))
        diagram = widget.window_segmentation_widget.diagram
        self.assertEqual(diagram._epoch_width(1000, 60000), 1000 / diagram.EPOCH_COUNT)
        self.assertLessEqual(ceil(1000 / diagram._epoch_width(1000, 1000)), 18)
        self.assertGreater(ceil(1000 / diagram._epoch_width(1000, 1000)), diagram.EPOCH_COUNT)
        visible_indices = diagram._visible_window_indices(1000)
        self.assertEqual(visible_indices[-1], 999)
        self.assertLessEqual(len(visible_indices), diagram.MAX_DRAWN_WINDOWS + 1)
        self.assertEqual(diagram.OVERLAP_LABEL_MIN_WIDTH, 10.0)
        visual_span = widget.onset_segmentation_widget.diagram._visual_span([250, 740], 0, 1000)
        left_negative = 250 - widget.onset_segmentation_widget.diagram._offset_to_x(250, -300, visual_span)
        left_positive = widget.onset_segmentation_widget.diagram._offset_to_x(250, 300, visual_span) - 250
        right_negative = 740 - widget.onset_segmentation_widget.diagram._offset_to_x(740, -300, visual_span)
        right_positive = widget.onset_segmentation_widget.diagram._offset_to_x(740, 300, visual_span) - 740
        self.assertAlmostEqual(left_negative, left_positive)
        self.assertAlmostEqual(left_negative, right_negative)
        self.assertAlmostEqual(left_negative, right_positive)

        widget.window_segmentation_widget.epoch_slider.setValue(1400)
        widget.window_segmentation_widget.overlap_slider.setValue(35)
        self.app.processEvents()
        self.assertEqual(widget.window_segmentation_widget.epoch_slider.value(), 1400)
        self.assertEqual(widget.window_segmentation_widget.overlap_slider.value(), 35)
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"]["duration_epoch_length_ms"], 1400)
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"]["stride_percent"], 35)

        widget.window_segmentation_widget.epoch_slider.setValue(1800)
        widget.window_segmentation_widget.overlap_slider.setValue(99)
        self.app.processEvents()
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"]["duration_epoch_length_ms"], 1800)
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"]["stride_percent"], 99)

        widget.window_segmentation_widget.epoch_slider.setValue(125000)
        self.app.processEvents()
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"]["duration_epoch_length_ms"], 125000)

        widget.onset_strategy_button.click()
        self.app.processEvents()
        self.assertEqual(state["segmentation"]["segmentation_strategy"], "onset-based")
        self.assertFalse(widget.window_segmentation_widget.isVisible())
        self.assertTrue(widget.onset_segmentation_widget.isVisible())
        self.assertFalse(hasattr(widget, "epoch_start"))
        self.assertFalse(hasattr(widget, "duration_epoch_length"))
        self.assertLess(widget.onset_segmentation_widget.window_start_slider.minimum(), -1_000_000)
        self.assertGreater(widget.onset_segmentation_widget.window_end_slider.maximum(), 1_000_000)
        self.assertLess(widget.onset_segmentation_widget.baseline_start_slider.minimum(), -1_000_000)
        self.assertGreater(widget.onset_segmentation_widget.baseline_end_slider.maximum(), 1_000_000)
        self.assertEqual(widget.onset_segmentation_widget.diagram.VISUAL_TIME_LIMIT_MS, 60000)
        self.assertEqual(widget.onset_segmentation_widget.window_start_slider.value(), -300)
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.value(), 700)
        self.assertEqual(widget.onset_segmentation_widget.baseline_start_slider.value(), -300)
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.value(), 0)
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"], {})
        self.assertEqual(
            state["segmentation"]["epoch_parameters"]["instant_events"],
            {"start": -300, "end": 700, "baseline_start": -300, "baseline_end": 0},
        )

        widget.onset_segmentation_widget.window_start_slider.setValue(-200)
        widget.onset_segmentation_widget.window_end_slider.setValue(600)
        widget.normalization_enabled.setChecked(True)
        widget.onset_segmentation_widget.baseline_start_slider.setValue(-100)
        widget.onset_segmentation_widget.baseline_end_slider.setValue(0)
        self.app.processEvents()

        self.assertEqual(
            state["segmentation"]["epoch_parameters"]["instant_events"],
            {"start": -200, "end": 600, "baseline_start": -100, "baseline_end": 0},
        )
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"], {})
        self.assertEqual(
            state["segmentation"]["normalization"],
            {"enabled": True, "mode": "mean_std"},
        )
        self.assertNotIn("duration", state["segmentation"]["normalization"])
        self.assertNotIn("instant", state["segmentation"]["normalization"])
        self.assertEqual(widget.onset_segmentation_widget.window_start_slider.value(), -200)
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.value(), 600)
        self.assertEqual(widget.onset_segmentation_widget.baseline_start_slider.value(), -100)
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.value(), 0)
        self.assertEqual(
            widget.onset_segmentation_widget.baseline_start_slider.maximum(),
            widget.onset_segmentation_widget.baseline_end_slider.value() - 1,
        )
        self.assertEqual(
            widget.onset_segmentation_widget.baseline_end_slider.minimum(),
            widget.onset_segmentation_widget.baseline_start_slider.value() + 1,
        )

        widget.onset_segmentation_widget.window_start_slider.setValue(-150)
        widget.onset_segmentation_widget.window_end_slider.setValue(500)
        widget.onset_segmentation_widget.baseline_start_slider.setValue(-125)
        widget.onset_segmentation_widget.baseline_end_slider.setValue(-25)
        self.app.processEvents()

        self.assertEqual(
            state["segmentation"]["epoch_parameters"]["instant_events"],
            {"start": -150, "end": 500, "baseline_start": -125, "baseline_end": -25},
        )
        self.assertNotIn("baseline_window_ms", state["segmentation"]["normalization"])
        self.assertTrue(widget.normalization_baseline_hint.isVisible())
        self.assertTrue(widget.can_continue())
        self.assertEqual(
            widget.onset_segmentation_widget.window_start_slider.maximum(),
            widget.onset_segmentation_widget.window_end_slider.value() - 1,
        )
        self.assertEqual(
            widget.onset_segmentation_widget.window_end_slider.minimum(),
            widget.onset_segmentation_widget.window_start_slider.value() + 1,
        )

        widget.normalization_enabled.setChecked(False)
        self.app.processEvents()
        widget.onset_segmentation_widget.window_end_slider.setValue(-200)
        self.app.processEvents()
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.value(), -149)
        self.assertEqual(widget.onset_segmentation_widget.diagram.window_end_ms, -149)
        self.assertFalse(widget.onset_segmentation_widget.diagram.window_invalid)
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.property("status"), "ok")
        self.assertTrue(widget.can_continue())

        widget.onset_segmentation_widget.window_end_slider.setValue(500)
        widget.normalization_enabled.setChecked(True)
        widget.onset_segmentation_widget.baseline_end_slider.setValue(-200)
        self.app.processEvents()
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.value(), -124)
        self.assertEqual(widget.onset_segmentation_widget.diagram.baseline_end_ms, -124)
        self.assertFalse(widget.onset_segmentation_widget.diagram.baseline_invalid)
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.property("status"), "ok")
        self.assertTrue(widget.can_continue())

    def test_resampling_allows_any_target_frequency_and_updates_broadband(self):
        state = _loaded_state()
        state["broadband"] = {
            "id": "broadband",
            "title": "Broadband",
            "enabled": True,
            "low_cut": 0.1,
            "high_cut": 125.0,
        }
        state["preprocessing"] = {
            "selected_frequency_bands": [
                {"id": "alpha", "title": "Alpha", "enabled": True, "low_cut": 8.0, "high_cut": 13.0},
                {"id": "broadband", "title": "Broadband", "enabled": True, "low_cut": 0.1, "high_cut": 125.0},
            ],
        }
        state["feature_params"] = {
            "relative_band_power": {
                "selected_frequency_bands": [
                    {"id": "broadband", "title": "Broadband", "enabled": True, "low_cut": 0.1, "high_cut": 125.0},
                ],
            },
        }
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        self.assertEqual(widget.target_sampling_frequency.minimum(), 1)
        self.assertEqual(
            widget.target_sampling_frequency.maximum(),
            widget.MAX_TARGET_SAMPLING_FREQUENCY_HZ,
        )

        widget.duration_events_list.item(0).setSelected(True)
        widget.resampling_enabled.setChecked(True)
        widget.target_sampling_frequency.setValue(1000)
        self.app.processEvents()

        self.assertEqual(
            state["segmentation"]["resampling"],
            {"enabled": True, "target_sampling_frequency": 1000},
        )
        self.assertEqual(state["broadband"]["high_cut"], 500.0)
        preprocessing_broadband = next(
            band for band in state["preprocessing"]["selected_frequency_bands"]
            if band["id"] == "broadband"
        )
        self.assertEqual(preprocessing_broadband["high_cut"], 500.0)
        relative_broadband = state["feature_params"]["relative_band_power"]["selected_frequency_bands"][0]
        self.assertEqual(relative_broadband["high_cut"], 500.0)
        self.assertTrue(widget.can_continue())

    def test_threshold_counts_have_no_time_suffix(self):
        state = _loaded_state()
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        self.assertEqual(widget.threshold_samples.suffix(), "")
        self.assertEqual(widget.threshold_channels.suffix(), "")

    def test_resampling_clamps_filters_and_removes_out_of_range_bands(self):
        state = _loaded_state()
        state["broadband"] = {
            "id": "broadband",
            "title": "Broadband",
            "enabled": True,
            "low_cut": 0.1,
            "high_cut": 125.0,
        }
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
                {"id": "alpha", "title": "Alpha", "enabled": True, "low_cut": 8.0, "high_cut": 13.0},
                {"id": "high_beta", "title": "High beta", "enabled": True, "low_cut": 55.0, "high_cut": 75.0},
                {"id": "broadband", "title": "Broadband", "enabled": True, "low_cut": 0.1, "high_cut": 125.0},
            ],
        }
        state["feature_params"] = {
            "relative_band_power": {
                "selected_frequency_bands": [
                    {"id": "alpha", "title": "Alpha", "enabled": True, "low_cut": 8.0, "high_cut": 13.0},
                    {"id": "high_beta", "title": "High beta", "enabled": True, "low_cut": 55.0, "high_cut": 75.0},
                    {"id": "broadband", "title": "Broadband", "enabled": True, "low_cut": 0.1, "high_cut": 125.0},
                ],
            },
        }
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.duration_events_list.item(0).setSelected(True)
        widget.resampling_enabled.setChecked(True)
        widget.target_sampling_frequency.setValue(120)
        self.app.processEvents()

        self.assertEqual(state["broadband"]["high_cut"], 60.0)
        self.assertEqual(state["preprocessing"]["filters"]["bandpass"]["high_cut"], 60.0)
        self.assertEqual(state["preprocessing"]["filters"]["notch"]["high_cut"], 60.0)
        self.assertLess(state["preprocessing"]["filters"]["notch"]["low_cut"], 60.0)
        self.assertEqual(
            [band["id"] for band in state["preprocessing"]["selected_frequency_bands"]],
            ["alpha", "broadband"],
        )
        self.assertEqual(state["preprocessing"]["selected_frequency_bands"][-1]["high_cut"], 60.0)
        self.assertEqual(
            [band["id"] for band in state["feature_params"]["relative_band_power"]["selected_frequency_bands"]],
            ["alpha", "broadband"],
        )
        self.assertTrue(widget.can_continue())

    def test_instant_events_force_onset_strategy_without_window_preview(self):
        state = _loaded_state()
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.instant_events_list.item(0).setSelected(True)
        self.app.processEvents()

        self.assertEqual(state["segmentation"]["segmentation_strategy"], "onset-based")
        self.assertFalse(widget.window_strategy_button.isVisible())
        self.assertTrue(widget.onset_strategy_button.isChecked())
        self.assertFalse(widget.window_segmentation_widget.isVisible())
        self.assertTrue(widget.onset_segmentation_widget.isVisible())
        self.assertFalse(hasattr(widget, "epoch_start"))
        self.assertFalse(hasattr(widget, "duration_epoch_length"))
        self.assertFalse(hasattr(widget, "baseline_start"))
        self.assertFalse(hasattr(widget, "baseline_end"))
        self.assertEqual(widget.onset_segmentation_widget.window_start_slider.value(), -300)
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.value(), 700)
        self.assertEqual(widget.onset_segmentation_widget.baseline_start_slider.value(), -300)
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.value(), 0)
        self.assertEqual(state["segmentation"]["epoch_parameters"]["duration_events"], {})
        self.assertEqual(
            state["segmentation"]["epoch_parameters"]["instant_events"],
            {"start": -300, "end": 700, "baseline_start": -300, "baseline_end": 0},
        )
        self.assertFalse(hasattr(widget.onset_segmentation_widget, "window_start_value"))
        self.assertFalse(hasattr(widget.onset_segmentation_widget, "window_end_value"))
        self.assertFalse(hasattr(widget.onset_segmentation_widget, "baseline_start_value"))
        self.assertFalse(hasattr(widget.onset_segmentation_widget, "baseline_end_value"))

        widget.onset_segmentation_widget.window_end_slider.setValue(-350)
        self.app.processEvents()
        self.assertEqual(widget.onset_segmentation_widget.window_end_slider.value(), -299)
        self.assertEqual(widget.onset_segmentation_widget.diagram.window_end_ms, -299)
        self.assertFalse(widget.onset_segmentation_widget.diagram.window_invalid)
        self.assertEqual(widget.onset_segmentation_widget.window_start_slider.property("status"), "ok")
        self.assertTrue(widget.can_continue())

        widget.onset_segmentation_widget.window_end_slider.setValue(700)
        widget.normalization_enabled.setChecked(True)
        widget.onset_segmentation_widget.baseline_end_slider.setValue(-350)
        self.app.processEvents()
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.value(), -299)
        self.assertEqual(widget.onset_segmentation_widget.diagram.baseline_end_ms, -299)
        self.assertFalse(widget.onset_segmentation_widget.diagram.baseline_invalid)
        self.assertEqual(widget.onset_segmentation_widget.baseline_end_slider.property("status"), "ok")
        self.assertTrue(widget.can_continue())

    def test_nested_mode_is_unavailable_only_for_single_duration_without_instant_events(self):
        invalid_state = _loaded_state_with_events(["full_recording"], [])
        invalid_widget = EEGSegmentationWidget({}, _eeg_defaults(), invalid_state)
        invalid_widget.show()
        self.app.processEvents()
        self.assertFalse(invalid_widget.nested_mode_button.isEnabled())

        instant_state = _loaded_state_with_events(["full_recording"], ["stimulus"])
        instant_widget = EEGSegmentationWidget({}, _eeg_defaults(), instant_state)
        instant_widget.show()
        self.app.processEvents()
        self.assertTrue(instant_widget.nested_mode_button.isEnabled())

        duration_state = _loaded_state_with_events(["full_recording", "trial"], [])
        duration_widget = EEGSegmentationWidget({}, _eeg_defaults(), duration_state)
        duration_widget.show()
        self.app.processEvents()
        self.assertTrue(duration_widget.nested_mode_button.isEnabled())

    def test_nested_add_buttons_follow_global_child_type_lock(self):
        state = _loaded_state_with_events(["full_recording", "trial"], ["stimulus", "response"])
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.nested_mode_button.click()
        state["segmentation"]["event_groups"] = [
            {
                "base_event": "full_recording",
                "duration_events": [],
                "instant_events": ["stimulus"],
            },
            {
                "base_event": "trial",
                "duration_events": [],
                "instant_events": [],
            }
        ]
        widget._sync()
        self.app.processEvents()

        add_duration_buttons = [
            button
            for button in widget.findChildren(QPushButton)
            if button.text() == "+ Add duration event"
        ]
        add_instant_buttons = [
            button
            for button in widget.findChildren(QPushButton)
            if button.text() == "+ Add instant event"
        ]

        self.assertFalse(widget.add_base_event_button.isEnabled())
        self.assertIn("already configured", widget.add_base_event_button.toolTip())
        self.assertTrue(add_duration_buttons)
        self.assertTrue(all(button.property("role") == "segmentation-duration-action" for button in add_duration_buttons))
        self.assertTrue(all(not button.isEnabled() for button in add_duration_buttons))
        self.assertTrue(all("already using instant" in button.toolTip() for button in add_duration_buttons))
        self.assertTrue(add_instant_buttons)
        self.assertTrue(all(button.property("role") == "segmentation-instant-action" for button in add_instant_buttons))
        self.assertTrue(all(button.isEnabled() for button in add_instant_buttons))

        widget._add_nested_events("full_recording", "duration")
        self.assertEqual(state["segmentation"]["event_groups"][0]["duration_events"], [])

    def test_nested_chip_close_button_removes_only_that_nested_event(self):
        state = _loaded_state_with_events(["full_recording", "trial"], ["stimulus", "response"])
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.nested_mode_button.click()
        state["segmentation"]["event_groups"] = [
            {
                "base_event": "trial",
                "duration_events": [],
                "instant_events": ["stimulus", "response"],
            }
        ]
        widget._sync()
        self.app.processEvents()

        nested_chips = [
            frame
            for frame in widget.findChildren(QFrame)
            if frame.objectName() == "summaryInstantChip"
            and frame.property("compact") == "true"
            and _has_ancestor_with_role(frame, "nested-contained-events")
        ]
        self.assertEqual(len(nested_chips), 2)
        self.assertTrue(all(isinstance(chip.layout(), QGridLayout) for chip in nested_chips))

        stimulus_remove_button = next(
            button
            for button in widget.findChildren(QPushButton)
            if button.property("role") == "chip-remove-button"
            and button.toolTip() == "Remove stimulus"
        )
        stimulus_remove_button.click()
        self.app.processEvents()

        self.assertEqual(
            state["segmentation"]["event_groups"],
            [
                {
                    "base_event": "trial",
                    "duration_events": [],
                    "instant_events": ["response"],
                }
            ],
        )

    def test_nested_parameter_selectors_stay_hidden_and_targets_follow_child_type(self):
        duration_events = [f"base_{index}" for index in range(7)] + [f"duration_child_{index}" for index in range(7)]
        duration_state = _loaded_state_with_events(duration_events, [])
        duration_widget = EEGSegmentationWidget({}, _eeg_defaults(), duration_state)
        duration_widget.show()
        self.app.processEvents()

        duration_widget.nested_mode_button.click()
        duration_widget._epoch_target = "instant"
        duration_widget._normalization_target = "instant"
        duration_state["segmentation"]["event_groups"] = [
            {
                "base_event": f"base_{index}",
                "duration_events": [f"duration_child_{index}"],
                "instant_events": [],
            }
            for index in range(7)
        ]
        duration_widget._sync()
        self.app.processEvents()

        self.assertFalse(hasattr(duration_widget, "epoch_target_panel"))
        self.assertFalse(duration_widget.normalization_target_panel.isVisible())
        self.assertTrue(duration_widget.window_segmentation_widget.isVisible())
        self.assertFalse(duration_widget.onset_segmentation_widget.isVisible())
        self.assertEqual(duration_state["segmentation"]["segmentation_strategy"], "window-based")
        self.assertTrue(duration_widget.window_segmentation_widget.isVisible())
        self.assertEqual(duration_widget._epoch_target, "duration")
        self.assertEqual(duration_widget._normalization_target, "duration")
        self.assertEqual(duration_state["segmentation"]["epoch_parameters"]["instant_events"], {})
        self.assertNotIn("duration", duration_state["segmentation"]["normalization"])
        self.assertNotIn("instant", duration_state["segmentation"]["normalization"])

        instant_events = [f"instant_child_{index}" for index in range(7)]
        instant_state = _loaded_state_with_events([f"base_{index}" for index in range(7)], instant_events)
        instant_widget = EEGSegmentationWidget({}, _eeg_defaults(), instant_state)
        instant_widget.show()
        self.app.processEvents()

        instant_widget.nested_mode_button.click()
        instant_widget._epoch_target = "duration"
        instant_widget._normalization_target = "duration"
        instant_state["segmentation"]["event_groups"] = [
            {
                "base_event": f"base_{index}",
                "duration_events": [],
                "instant_events": [f"instant_child_{index}"],
            }
            for index in range(7)
        ]
        instant_widget._sync()
        instant_widget.normalization_enabled.setChecked(True)
        self.app.processEvents()

        self.assertFalse(hasattr(instant_widget, "epoch_target_panel"))
        self.assertFalse(instant_widget.normalization_target_panel.isVisible())
        self.assertTrue(instant_widget.onset_segmentation_widget.isVisible())
        self.assertFalse(instant_widget.window_segmentation_widget.isVisible())
        self.assertTrue(instant_widget.normalization_baseline_hint.isVisible())
        self.assertEqual(instant_state["segmentation"]["segmentation_strategy"], "onset-based")
        self.assertFalse(instant_widget.window_segmentation_widget.isVisible())
        self.assertEqual(instant_widget._epoch_target, "instant")
        self.assertEqual(instant_widget._normalization_target, "instant")
        self.assertEqual(instant_state["segmentation"]["epoch_parameters"]["duration_events"], {})
        self.assertNotIn("duration", instant_state["segmentation"]["normalization"])
        self.assertNotIn("instant", instant_state["segmentation"]["normalization"])

    def test_nested_mode_rejects_mixed_child_event_types(self):
        state = _loaded_state()
        widget = EEGSegmentationWidget({}, _eeg_defaults(), state)
        widget.show()
        self.app.processEvents()

        widget.nested_mode_button.click()
        state["segmentation"]["event_groups"] = [
            {
                "base_event": "trial",
                "duration_events": ["full_recording"],
                "instant_events": ["stimulus"],
            }
        ]
        widget._sync()
        self.app.processEvents()

        self.assertFalse(hasattr(widget, "epoch_target_panel"))
        self.assertFalse(widget.normalization_target_panel.isVisible())
        self.assertFalse(widget.can_continue())
        self.assertIn(
            "Nested mode supports either duration or instant nested events, not both.",
            widget.validation_errors,
        )


if __name__ == "__main__":
    unittest.main()
