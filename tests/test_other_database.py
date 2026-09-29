import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from medusa_analyzer.backend.converter.other_database import (
    build_other_database_bids,
    preview_other_database_mapping,
    scan_other_database,
    tokenize_relative_path,
)


def _scan(tokens):
    return {
        "files": [{
            "source_path": "root/study/S01/runA.edf",
            "relative_path": "study/S01/runA.edf",
            "extension": ".edf",
            "datatype": "eeg",
            "tokens": tokens,
        }],
    }


class OtherDatabaseMappingTests(unittest.TestCase):
    def test_tokenize_relative_path_splits_dots_before_extension(self):
        tokens = tokenize_relative_path("study/S01/17.rec.edf")

        self.assertEqual(tokens, ["study", "S01", "17", "rec"])

    def test_scan_other_database_lists_all_matching_records(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "S01").mkdir()
            first = root / "S01" / "first.edf"
            second = root / "S01" / "second.edf"
            ignored = root / "S01" / "notes.txt"
            first.write_text("", encoding="utf-8")
            second.write_text("", encoding="utf-8")
            ignored.write_text("", encoding="utf-8")

            scan = scan_other_database(root, first)

        self.assertEqual(scan["file_count"], 2)
        self.assertEqual(
            [record["relative_path"] for record in scan["files"]],
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

            scan = scan_other_database(root, sample)

        self.assertEqual(scan["file_count"], 3)
        self.assertEqual(
            [record["relative_path"] for record in scan["files"]],
            ["S1/R16.rec.json", "S2/R16.rec.json", "S31 (fNIRS)/R16.rec.json"],
        )
        self.assertEqual(scan["record_name_suffix"], ".rec.json")
        self.assertEqual(len(scan["layout_warnings"]), 1)
        self.assertIn("do not match '*.rec.json'", scan["layout_warnings"][0])

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

        result = preview_other_database_mapping(_scan(["study", "S01", "runA"]), mapping)

        self.assertTrue(result["valid"])
        row = result["rows"][0]
        self.assertEqual(row["entities"], {"sub": "S01", "task": "rest", "run": "runA01"})
        self.assertEqual(row["bids_name"], "sub-S01_task-rest_run-runA01")
        self.assertEqual(row["target_relative_path"], "sub-S01/eeg/sub-S01_task-rest_run-runA01_eeg.edf")

    def test_legacy_indices_and_fixed_value_mapping_still_work(self):
        mapping = {
            "sub": {"indices": [1]},
            "task": {"value": "eyes open"},
        }

        result = preview_other_database_mapping(_scan(["study", "S01", "runA"]), mapping)

        self.assertTrue(result["valid"])
        row = result["rows"][0]
        self.assertEqual(row["entities"], {"sub": "S01", "task": "eyesopen"})
        self.assertEqual(row["target_relative_path"], "sub-S01/eeg/sub-S01_task-eyesopen_eeg.edf")

    def test_collisions_are_warnings_not_errors(self):
        scan = {
            "files": [
                {
                    "source_path": "root/S01/a.edf",
                    "relative_path": "S01/a.edf",
                    "extension": ".edf",
                    "datatype": "eeg",
                    "tokens": ["S01", "a"],
                },
                {
                    "source_path": "root/S02/b.edf",
                    "relative_path": "S02/b.edf",
                    "extension": ".edf",
                    "datatype": "eeg",
                    "tokens": ["S02", "b"],
                },
            ],
        }
        mapping = {
            "sub": {"value": "same"},
            "task": {"value": "rest"},
        }

        result = preview_other_database_mapping(scan, mapping)

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertTrue(any(warning.startswith("Collision:") for warning in result["warnings"]))

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
            scan = scan_other_database(root, first)
            mapping = {
                "sub": {"value": "same"},
                "task": {"value": "rest"},
            }

            result = build_other_database_bids(scan, mapping, output)

            copied_edfs = sorted(output.rglob("*.edf"))
            self.assertEqual(result["copied_files"], 1)
            self.assertEqual(result["skipped_collisions"], 1)
            self.assertEqual(len(copied_edfs), 1)
            self.assertEqual(copied_edfs[0].read_text(encoding="utf-8"), "first")


if __name__ == "__main__":
    unittest.main()
