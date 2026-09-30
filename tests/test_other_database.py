import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from medusa_analyzer.backend.converter.other_database import (
    ConversionContext,
    ConversionRecord,
    apply_other_database_mapping,
    build_other_database_bids,
    preview_other_database_mapping,
    scan_other_database,
    tokenize_relative_path,
)
from medusa_analyzer.backend.converter.prune_output import prune_output
from medusa_analyzer.backend.converter.run_conversion import (
    _convert_mne_to_medusa,
    _json_safe,
    _write_events_files,
    file_to_bids,
)


def _context(tokens, source_path="root/study/S01/runA.edf", relative_path="study/S01/runA.edf"):
    record = ConversionRecord(
        id="rec_test",
        source_path=source_path,
        source_relative_path=relative_path,
        extension=".edf",
        datatype="eeg",
        tokens=list(tokens),
    )
    return ConversionContext(
        source_root="root",
        records=[record],
        sample_record_id=record.id,
        target_extension=".edf",
    )


def _mapped_context(source_context, mapping):
    return apply_other_database_mapping(source_context, mapping)


class OtherDatabaseMappingTests(unittest.TestCase):
    def test_tokenize_relative_path_splits_dots_before_extension(self):
        tokens = tokenize_relative_path("study/S01/17.rec.edf")

        self.assertEqual(tokens, ["study", "S01", "17", "rec"])

    def test_scan_other_database_generates_context_with_all_matching_records(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "S01").mkdir()
            first = root / "S01" / "first.edf"
            second = root / "S01" / "second.edf"
            ignored = root / "S01" / "notes.txt"
            first.write_text("", encoding="utf-8")
            second.write_text("", encoding="utf-8")
            ignored.write_text("", encoding="utf-8")

            context = scan_other_database(root, first)

        self.assertIsInstance(context, ConversionContext)
        self.assertEqual(context.file_count, 2)
        self.assertEqual(
            [record.source_relative_path for record in context.records],
            ["S01/first.edf", "S01/second.edf"],
        )

    def test_scan_other_database_filters_rec_json_noise_but_keeps_different_layouts(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Configs").mkdir()
            (root / "S1").mkdir()
            (root / "S2").mkdir()
            (root / "S31 (fNIRS)").mkdir()
            sample = root / "S1" / "R16.rec.json"
            second = root / "S2" / "R16.rec.json"
            config = root / "Configs" / "asteroids_exp.json"
            different_layout = root / "S31 (fNIRS)" / "R16.rec.json"
            for file in (sample, second, config, different_layout):
                file.write_text("", encoding="utf-8")

            context = scan_other_database(root, sample)

        self.assertEqual(context.file_count, 3)
        self.assertEqual(
            [record.source_relative_path for record in context.records],
            ["S1/R16.rec.json", "S2/R16.rec.json", "S31 (fNIRS)/R16.rec.json"],
        )
        self.assertEqual(context.record_name_suffix, ".rec.json")
        self.assertEqual(len(context.warnings), 1)
        self.assertIn("do not match '*.rec.json'", context.warnings[0])

    def test_mapping_parts_mix_path_tokens_and_custom_literals(self):
        mapping = {
            "sub": {"parts": [{"source": "path", "index": 1}]},
            "task": {"parts": [{"source": "literal", "value": "rest"}]},
            "run": {
                "parts": [
                    {"source": "path", "index": 2},
                    {"source": "literal", "value": "01"},
                ],
            },
        }

        mapped = _mapped_context(_context(["study", "S01", "runA"]), mapping)
        result = preview_other_database_mapping(mapped)

        self.assertTrue(result["valid"])
        row = result["rows"][0]
        self.assertEqual(row["entities"], {"sub": "S01", "task": "rest", "run": "runA01"})
        self.assertEqual(row["bids_name"], "sub-S01_task-rest_run-runA01")
        self.assertEqual(row["target_relative_path"], "sub-S01/eeg/sub-S01_task-rest_run-runA01_eeg.mpl")

    def test_legacy_indices_and_fixed_value_mapping_still_work(self):
        mapping = {
            "sub": {"indices": [1]},
            "task": {"value": "eyes open"},
        }

        mapped = _mapped_context(_context(["study", "S01", "runA"]), mapping)
        result = preview_other_database_mapping(mapped)

        self.assertTrue(result["valid"])
        row = result["rows"][0]
        self.assertEqual(row["entities"], {"sub": "S01", "task": "eyesopen"})
        self.assertEqual(row["target_relative_path"], "sub-S01/eeg/sub-S01_task-eyesopen_eeg.mpl")

    def test_each_record_has_unique_persistent_bids_mapping(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "S01").mkdir()
            (root / "S02").mkdir()
            first = root / "S01" / "a.edf"
            second = root / "S02" / "b.edf"
            first.write_text("", encoding="utf-8")
            second.write_text("", encoding="utf-8")
            context = scan_other_database(root, first)

        mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})
        targets_before_preview = [record.target_relative_path for record in mapped.records]

        preview_other_database_mapping(mapped)

        self.assertEqual(len(set(targets_before_preview)), 2)
        self.assertEqual(targets_before_preview, [record.target_relative_path for record in mapped.records])

    def test_preview_limit_does_not_trim_context_records(self):
        records = [
            ConversionRecord(
                id=f"rec_{index:02d}",
                source_path=f"root/S{index:02d}/rest.edf",
                source_relative_path=f"S{index:02d}/rest.edf",
                extension=".edf",
                datatype="eeg",
                tokens=[f"S{index:02d}", "rest"],
            )
            for index in range(45)
        ]
        context = ConversionContext(source_root="root", records=records, target_extension=".edf")
        mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})

        result = preview_other_database_mapping(mapped, limit=40)

        self.assertEqual(len(result["rows"]), 40)
        self.assertEqual(len(mapped.records), 45)

    def test_collisions_are_warnings_not_errors(self):
        context = ConversionContext(
            source_root="root",
            records=[
                ConversionRecord("rec_1", "root/S01/a.edf", "S01/a.edf", ".edf", "eeg", ["S01", "a"]),
                ConversionRecord("rec_2", "root/S02/b.edf", "S02/b.edf", ".edf", "eeg", ["S02", "b"]),
            ],
            target_extension=".edf",
        )
        mapping = {
            "sub": {"value": "same"},
            "task": {"value": "rest"},
        }

        mapped = _mapped_context(context, mapping)
        result = preview_other_database_mapping(mapped)

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertTrue(any(warning.startswith("Collision:") for warning in result["warnings"]))

    def test_build_uses_same_mapping_as_preview(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)
            mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})
            preview_target = preview_other_database_mapping(mapped)["rows"][0]["target_relative_path"]

            converted_targets = []

            def fake_convert(record, output_root):
                converted_targets.append(record.target_relative_path)
                destination = output_root / record.target_relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text("converted", encoding="utf-8")

            with patch(
                "medusa_analyzer.backend.converter.other_database._convert_record_to_bids",
                side_effect=fake_convert,
            ), patch("medusa_analyzer.backend.converter.other_database._prune_converted_output"):
                result = build_other_database_bids(mapped, output)

            self.assertTrue((output / preview_target).exists())
            self.assertEqual((output / preview_target).read_text(encoding="utf-8"), "converted")
            self.assertEqual(converted_targets, [preview_target])
            self.assertEqual(result["converted_files"], 1)

    def test_build_rejects_unmapped_scan_context(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)

            with self.assertRaises(ValueError):
                build_other_database_bids(context, output)

    def test_build_rejects_output_inside_source_context(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = root / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)
            mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})

            with self.assertRaisesRegex(ValueError, "outside"):
                build_other_database_bids(mapped, output)

    def test_build_does_not_reconstruct_mapping(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)
            mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})

            with patch(
                "medusa_analyzer.backend.converter.other_database.normalize_mapping",
                side_effect=AssertionError("mapping was reconstructed"),
            ), patch(
                "medusa_analyzer.backend.converter.other_database.bids_relative_path",
                side_effect=AssertionError("target path was reconstructed"),
            ), patch(
                "medusa_analyzer.backend.converter.other_database._convert_record_to_bids",
            ) as convert, patch("medusa_analyzer.backend.converter.other_database._prune_converted_output"):
                result = build_other_database_bids(mapped, output)

            self.assertEqual(result["converted_files"], 1)
            self.assertEqual(convert.call_args.args[0].target_relative_path, mapped.records[0].target_relative_path)

    def test_build_reports_conversion_errors_by_record(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)
            mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})

            with patch(
                "medusa_analyzer.backend.converter.other_database._convert_record_to_bids",
                side_effect=RuntimeError("cannot read file"),
            ), patch("medusa_analyzer.backend.converter.other_database._prune_converted_output") as prune:
                result = build_other_database_bids(mapped, output)

            self.assertFalse(result["valid"])
            self.assertEqual(result["converted_files"], 0)
            self.assertEqual(result["failed_files"], 1)
            self.assertEqual(result["errors"], ["S01/rest.edf: cannot read file"])
            prune.assert_not_called()

    def test_build_keeps_conversion_result_when_pruning_fails(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            source = root / "S01" / "rest.edf"
            source.write_text("recording", encoding="utf-8")
            context = scan_other_database(root, source)
            mapped = _mapped_context(context, {"sub": {"indices": [0]}, "task": {"indices": [1]}})

            def fake_convert(record, output_root):
                destination = output_root / record.target_relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text("converted", encoding="utf-8")
                destination.with_suffix(".json").write_text('{"TaskName": ', encoding="utf-8")

            with patch(
                "medusa_analyzer.backend.converter.other_database._convert_record_to_bids",
                side_effect=fake_convert,
            ):
                result = build_other_database_bids(mapped, output)

            self.assertTrue(result["valid"])
            self.assertEqual(result["converted_files"], 1)
            self.assertTrue(any("Skipped inheritance-based file pruning" in warning for warning in result["warnings"]))

    def test_prune_output_reports_invalid_json_path(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "sub-S01" / "eeg"
            target.mkdir(parents=True)
            invalid = target / "sub-S01_task-rest_eeg.json"
            invalid.write_text('{"TaskName": ', encoding="utf-8")

            with self.assertRaises(ValueError) as caught:
                prune_output(root)
            self.assertIn(str(invalid), str(caught.exception))

    def test_record_ids_are_different_and_stable(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "S01").mkdir()
            (root / "S02").mkdir()
            first = root / "S01" / "a.edf"
            second = root / "S02" / "b.edf"
            first.write_text("", encoding="utf-8")
            second.write_text("", encoding="utf-8")

            first_scan = scan_other_database(root, first)
            second_scan = scan_other_database(root, first)

        first_ids = [record.id for record in first_scan.records]
        second_ids = [record.id for record in second_scan.records]
        self.assertEqual(first_ids, second_ids)
        self.assertEqual(len(set(first_ids)), 2)

    def test_build_skips_later_colliding_files_without_overwriting(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "root"
            output = Path(folder) / "out"
            (root / "S01").mkdir(parents=True)
            (root / "S02").mkdir(parents=True)
            first = root / "S01" / "a.edf"
            second = root / "S02" / "b.edf"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            context = scan_other_database(root, first)
            mapping = {
                "sub": {"value": "same"},
                "task": {"value": "rest"},
            }
            mapped = _mapped_context(context, mapping)

            def fake_convert(record, output_root):
                destination = output_root / record.target_relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(record.source_relative_path, encoding="utf-8")

            with patch(
                "medusa_analyzer.backend.converter.other_database._convert_record_to_bids",
                side_effect=fake_convert,
            ), patch("medusa_analyzer.backend.converter.other_database._prune_converted_output"):
                result = build_other_database_bids(mapped, output)

            converted_mpls = sorted(output.rglob("*.mpl"))
            self.assertEqual(result["converted_files"], 1)
            self.assertEqual(result["skipped_collisions"], 1)
            self.assertEqual(len(converted_mpls), 1)
            self.assertEqual(converted_mpls[0].read_text(encoding="utf-8"), "S01/a.edf")

    def test_file_to_bids_passes_mapping_entities_to_mne_conversion(self):
        output = Path("out")
        raw = object()
        medusa_recording = object()
        entities = {"sub": "S01", "ses": "A", "task": "rest", "acq": "cap", "run": "1"}

        with patch("medusa_analyzer.backend.converter.run_conversion._read_raw_mne", return_value=raw), patch(
            "medusa_analyzer.backend.converter.run_conversion._convert_mne_to_medusa",
            return_value=medusa_recording,
        ) as convert, patch("medusa_analyzer.backend.converter.run_conversion._convert_medusa_to_mpl") as export:
            file_to_bids(Path("record.edf"), output, bids_entities=entities)

        convert.assert_called_once_with(
            raw,
            subject="S01",
            session="A",
            task="rest",
            acquisition="cap",
            run="1",
            task_name="rest",
        )
        export.assert_called_once_with(medusa_recording, output)

    def test_file_to_bids_overrides_medusa_recording_bids_from_mapping(self):
        output = Path("out")
        recording = SimpleNamespace(
            bids=SimpleNamespace(participant={"age": 30}, scan={"acq_time": "n/a"})
        )
        entities = {"sub": "S01", "task": "rest", "run": "1"}

        with patch(
            "medusa_analyzer.backend.converter.run_conversion.Recording.load",
            return_value=recording,
        ), patch("medusa_analyzer.backend.converter.run_conversion._convert_medusa_to_mpl") as export:
            file_to_bids(Path("record.rec.json"), output, bids_entities=entities)

        self.assertEqual(recording.bids.subject, "S01")
        self.assertEqual(recording.bids.task, "rest")
        self.assertEqual(recording.bids.run, "1")
        self.assertEqual(recording.bids.participant, {"age": 30})
        self.assertEqual(recording.bids.scan, {"acq_time": "n/a"})
        export.assert_called_once_with(recording, output)

    def test_mne_metadata_dates_are_json_safe(self):
        payload = _json_safe({"subject_info": {"birthday": date(1990, 1, 2)}})

        self.assertEqual(payload, {"subject_info": {"birthday": "1990-01-02"}})

    def test_mne_raw_without_annotations_does_not_create_events(self):
        raw = SimpleNamespace(
            annotations=[],
            info={
                "sfreq": 100.0,
                "meas_date": None,
                "highpass": 0.1,
                "lowpass": 40.0,
                "description": "test",
                "subject_info": {"birthday": date(1990, 1, 2)},
            },
            times=np.array([0.0, 0.01, 0.02]),
            first_samp=0,
            ch_names=["Cz"],
            get_channel_types=lambda: ["eeg"],
            get_data=lambda picks: np.array([[1.0, 2.0, 3.0]]),
        )

        recording = _convert_mne_to_medusa(raw, subject="S01", task="rest")

        self.assertIsNone(recording.events)

    def test_events_are_written_inside_datatype_folder(self):
        with TemporaryDirectory() as folder:
            output_path = Path(folder) / "sub-S01" / "eeg"
            output_path.mkdir(parents=True)
            events = SimpleNamespace(
                df=pd.DataFrame([{"onset": 0.1, "duration": 0.0, "trial_type": "5"}]),
                descriptions={"trial_type": {"Description": "Event code"}},
            )

            _write_events_files(events, output_path, "sub-S01_task-rest")

            self.assertTrue((output_path / "sub-S01_task-rest_events.tsv").exists())
            self.assertTrue((output_path / "sub-S01_task-rest_events.json").exists())


if __name__ == "__main__":
    unittest.main()
