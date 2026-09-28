import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd

from medusa_analyzer.backend.experiments import eeg_run_pipeline


class EEGRunPipelineParameterTests(unittest.TestCase):
    def test_duration_segmentation_uses_duration_normalization_key_and_returns_ms(self):
        signal = np.ones((250, 2), dtype=float)
        times = np.arange(250) / 250
        events = pd.DataFrame([{"onset": 0.0, "duration": 1.0, "trial_type": "trial"}])
        state = {
            "segmentation_strategy": "window-based",
            "event_groups": [{"base_event": None, "duration_events": ["trial"], "instant_events": []}],
            "epoch_parameters": {
                "duration_events": {"duration_epoch_length_ms": 400, "stride_percent": 0},
                "instant_events": {},
            },
            "normalization": {
                "duration": {"enabled": True, "mode": "mean_std"},
                "instant": {},
            },
        }

        def fake_segment_signal(signal_evt, segment_samples, stride, norm=None):
            self.assertEqual(segment_samples, 100)
            self.assertIsNone(stride)
            self.assertEqual(norm, "z")
            return np.ones((1, 100, 2), dtype=float)

        with patch.object(eeg_run_pipeline.segmentation, "segment_signal", side_effect=fake_segment_signal):
            epochs, times_epochs = eeg_run_pipeline.segment_signal(signal, times, 250, events, state)

        self.assertIn("full_recording", epochs)
        self.assertIn("trial", epochs["full_recording"])
        np.testing.assert_allclose(times_epochs[:3], [0.0, 4.0, 8.0])

    def test_compute_parameters_uses_current_band_power_feature_ids(self):
        epochs = np.ones((2, 8, 2), dtype=float)
        state = {
            "selected_features": ["absolute_band_power", "relative_band_power"],
            "feature_params": {
                "psd": {
                    "segment_percent": 80,
                    "overlap_percent": 50,
                    "window": "hamming",
                },
                "relative_band_power": {
                    "selected_frequency_bands": [
                        {"id": "alpha", "title": "Alpha", "low_cut": 8.0, "high_cut": 13.0},
                        {"id": "broadband", "title": "Broadband", "low_cut": 0.5, "high_cut": 45.0},
                    ],
                },
            },
        }
        broadband = {"id": "broadband", "low_cut": 0.5, "high_cut": 45.0}
        psd = np.ones((2, 4, 2), dtype=float)
        calls = []

        def fake_power_spectral_density(signal, fs, segment, overlap, window):
            self.assertEqual(signal.shape, epochs.shape)
            self.assertEqual((segment, overlap, window), (0.8, 0.5, "hamming"))
            return np.asarray([0.0, 10.0, 20.0, 30.0]), psd

        def fake_band_power(psd_value, fs, band, power_type="absolute", norm_range=None):
            calls.append((tuple(band), power_type, tuple(norm_range) if norm_range else None))
            value = 2.0 if power_type == "absolute" else 0.25
            return np.full((psd_value.shape[0], psd_value.shape[2]), value)

        with patch.object(eeg_run_pipeline.transforms, "power_spectral_density",
            side_effect=fake_power_spectral_density), patch.object(eeg_run_pipeline.spectral, "band_power",
            side_effect=fake_band_power):
            params = eeg_run_pipeline.compute_parameters(epochs, 100.0, broadband, state)

        self.assertIn("absolute_band_power", params)
        self.assertIn("relative_band_power", params)
        self.assertEqual(set(params), {"absolute_band_power", "relative_band_power"})
        np.testing.assert_allclose(params["absolute_band_power"], np.full((2, 2), 2.0))
        self.assertEqual(len(params["relative_band_power"]), 1)
        self.assertEqual(params["relative_band_power"][0]["band"], "alpha")
        np.testing.assert_allclose(params["relative_band_power"][0]["value"], np.full((2, 2), 0.25))
        self.assertEqual(calls, [((8.0, 13.0), "relative", (0.5, 45.0)),
            ((0.5, 45.0), "absolute", None)])

    def test_save_outputs_does_not_require_saved_psd_for_band_power_only(self):
        with TemporaryDirectory() as tmp_dir:
            derivatives = Path(tmp_dir) / "derivatives"
            file = {"relative_path": "sub-01/ses-01/eeg/sub-01_ses-01_task-test_run-1_eeg.mpl"}
            state = {"output_derivatives_path": str(derivatives)}

            eeg_run_pipeline.save_outputs({"absolute_band_power": np.asarray([[1.0, 2.0]])}, file,
                "broadband", "rest", "parameters", state)

            absolute_band_power_path = derivatives / "parameters" / file["relative_path"]
            absolute_band_power_path = absolute_band_power_path.with_stem(
                "sub-01_ses-01_task-test_run-1_eeg_param-absolutebandpower_band-broadband_segment-rest")
            psd_path = derivatives / "parameters" / file["relative_path"]
            psd_path = psd_path.with_stem("sub-01_ses-01_task-test_run-1_eeg_param-psd_band-broadband_segment-rest")

            self.assertTrue(absolute_band_power_path.is_file())
            self.assertFalse(psd_path.is_file())


if __name__ == "__main__":
    unittest.main()
