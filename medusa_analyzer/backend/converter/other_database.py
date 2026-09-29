from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


BIDS_ENTITY_ORDER = ("sub", "ses", "task", "acq", "run")
REQUIRED_BIDS_ENTITIES = ("sub", "task")
TOKEN_SPLIT_RE = re.compile(r"[\\/._-]+")
TOKEN_TEXT_RE = re.compile(r"[^A-Za-z0-9]+")

EEG_EXTENSIONS = {".bdf", ".bson", ".cnt", ".edf", ".eeg", ".json", ".set", ".vhdr"}
MEG_EXTENSIONS = {".fif", ".ds"}
SUPPORTED_EXTENSIONS = tuple(sorted(EEG_EXTENSIONS | MEG_EXTENSIONS))


@dataclass(slots=True)
class ConversionRecord:
    """One source recording and its resolved BIDS target."""

    id: str
    source_path: str
    source_relative_path: str
    extension: str
    datatype: str
    tokens: list[str] = field(default_factory=list)
    entities: dict[str, str] = field(default_factory=dict)
    bids_name: str = ""
    target_relative_path: str = ""
    status: str = "pending"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConversionContext:
    """Canonical state for an Other DB conversion."""

    source_root: str
    output_root: str = ""
    records: list[ConversionRecord] = field(default_factory=list)
    sample_record_id: str = ""
    target_extension: str = ""
    record_name_suffix: str | None = None
    mapping_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors and all(not record.errors for record in self.records)

    @property
    def file_count(self) -> int:
        return len(self.records)

    @property
    def sample_record(self) -> ConversionRecord | None:
        for record in self.records:
            if record.id == self.sample_record_id:
                return record
        return self.records[0] if self.records else None


def tokenize_relative_path(relative_path: str | Path) -> list[str]:
    """Split a relative recording path into path/name tokens."""
    path = Path(relative_path)
    without_suffix = path.with_suffix("")
    return [token for token in TOKEN_SPLIT_RE.split(without_suffix.as_posix()) if token]


def scan_other_database(root_path: str | Path, sample_record_path: str | Path | None = None,
    extensions: tuple[str, ...] | None = None,
    progress_callback: Callable[[int], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None) -> ConversionContext:
    """Inspect one representative record from a homogeneous non-BIDS EEG/MEG database."""
    del extensions
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Input folder does not exist: {root}")

    sample_path = Path(sample_record_path) if sample_record_path else None
    if sample_path is None:
        raise ValueError("Select a representative record before mapping the database.")
    sample_path = sample_path.resolve()
    try:
        sample_relative_path = sample_path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("Selected record must be inside the selected database folder.") from exc
    if not sample_path.exists() or not sample_path.is_file():
        raise ValueError(f"Selected record does not exist: {sample_path}")

    sample_extension = sample_path.suffix.lower()
    sample_tokens = tokenize_relative_path(sample_relative_path)
    _progress(progress_callback, 5)
    record_name_suffix = _record_name_suffix(sample_path.name, sample_extension)
    records, scan_stats = _records_for_scan_filter(
        root,
        sample_extension,
        record_name_suffix=record_name_suffix,
        representative_token_count=len(sample_tokens),
        progress_callback=progress_callback,
    )
    _progress(progress_callback, 90)
    layout_warnings = _scan_warnings(scan_stats, sample_extension, record_name_suffix)

    result = ConversionContext(
        source_root=str(root),
        records=records,
        sample_record_id=_record_id(sample_relative_path),
        target_extension=sample_extension,
        record_name_suffix=record_name_suffix,
        metadata={
            "extension_counts": {sample_extension: len(records)},
            "supported_extensions": sorted(set(SUPPORTED_EXTENSIONS) | {sample_extension}),
            "scan_stats": scan_stats,
        },
        warnings=layout_warnings,
    )
    _log(log_callback, f"Representative record selected: {sample_relative_path.as_posix()}", "")
    _log(log_callback, f"Found {len(records)} matching recording file(s) with extension '{sample_extension}'.", "")
    for warning in layout_warnings:
        _log(log_callback, warning, "warning")
    _progress(progress_callback, 100)
    return result


def parse_mapping_text(text: str) -> list[int]:
    """Parse user-entered token indices such as '0, 2 + 5'."""
    if not text.strip():
        return []
    values = []
    for raw_value in re.split(r"[,+;\s]+", text.strip()):
        if not raw_value:
            continue
        if not raw_value.isdigit():
            raise ValueError(f"Token index '{raw_value}' is not a non-negative integer.")
        values.append(int(raw_value))
    return values


def normalize_mapping(mapping: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize entity mappings into token indices plus optional fixed values."""
    normalized: dict[str, dict[str, Any]] = {}
    for entity in BIDS_ENTITY_ORDER:
        raw_value = mapping.get(entity, {})
        fixed_value = ""
        raw_indices: Any = []
        raw_parts: Any = []
        if isinstance(raw_value, dict):
            raw_indices = raw_value.get("indices", [])
            fixed_value = str(raw_value.get("value", "")).strip()
            raw_parts = raw_value.get("parts", [])
        elif isinstance(raw_value, str):
            raw_indices = raw_value
        else:
            raw_indices = raw_value

        if isinstance(raw_indices, str):
            indices = parse_mapping_text(raw_indices)
        else:
            indices = [int(index) for index in raw_indices]

        parts = _normalize_mapping_parts(raw_parts)
        normalized[entity] = {
            "indices": indices,
            "value": fixed_value,
            "parts": parts,
        }
    return normalized


def _normalize_mapping_parts(raw_parts: Any) -> list[dict[str, Any]]:
    parts = []
    if not isinstance(raw_parts, list):
        return parts
    for raw_part in raw_parts:
        if isinstance(raw_part, dict):
            source = raw_part.get("source")
            if source == "path":
                parts.append({"source": "path", "index": int(raw_part.get("index", 0))})
            elif source == "literal":
                value = str(raw_part.get("value", "")).strip()
                if value:
                    parts.append({"source": "literal", "value": value})
        elif isinstance(raw_part, int):
            parts.append({"source": "path", "index": raw_part})
        elif isinstance(raw_part, str) and raw_part.strip():
            parts.append({"source": "literal", "value": raw_part.strip()})
    return parts


def apply_other_database_mapping(context: ConversionContext, mapping: dict[str, Any]) -> ConversionContext:
    """Resolve BIDS entities and targets once for every record in a context."""
    normalized_mapping = normalize_mapping(mapping)
    errors: list[str] = []
    warnings: list[str] = list(context.warnings)

    for entity in REQUIRED_BIDS_ENTITIES:
        rule = normalized_mapping.get(entity, {})
        if not _mapping_rule_has_value(rule):
            errors.append(f"Mapping for '{entity}' is required.")

    target_sources: dict[str, list[str]] = defaultdict(list)
    mapped_records = [_map_record(record, normalized_mapping) for record in context.records]
    for record in mapped_records:
        if record.errors:
            for issue in record.errors:
                errors.append(f"{record.source_relative_path}: {issue}")
        else:
            target_sources[record.target_relative_path].append(record.source_relative_path)

    collision_targets: set[str] = set()
    for target_path, source_paths in target_sources.items():
        if len(source_paths) > 1:
            collision_targets.add(target_path)
            warnings.append(
                f"Collision: {target_path} would be created from {', '.join(source_paths[:4])}."
            )

    if collision_targets:
        for record in mapped_records:
            if record.target_relative_path in collision_targets:
                record.warnings.append(f"Target path collides with another source: {record.target_relative_path}")

    task_values = {record.entities.get("task") for record in mapped_records if record.entities.get("task")}
    if len(task_values) == 1 and len(mapped_records) > 1:
        warnings.append("All files resolve to the same task value.")

    return ConversionContext(
        source_root=context.source_root,
        output_root=context.output_root,
        records=mapped_records,
        sample_record_id=context.sample_record_id,
        target_extension=context.target_extension,
        record_name_suffix=context.record_name_suffix,
        mapping_rules=normalized_mapping,
        metadata=dict(context.metadata),
        warnings=_unique(warnings),
        errors=_unique(errors),
    )


def preview_other_database_mapping(context: ConversionContext, limit: int = 25) -> dict[str, Any]:
    """Return UI preview rows from already mapped records."""
    rows = [record_to_preview_row(record) for record in context.records[:max(limit, 0)]]
    return {
        "valid": context.valid,
        "errors": list(context.errors),
        "warnings": list(context.warnings),
        "rows": rows,
        "summary": _summary_from_records(context.records),
    }


def build_other_database_bids(context: ConversionContext, output_path: str | Path | None = None,
    dataset_name: str | None = None,
    progress_callback: Callable[[int], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None) -> dict[str, Any]:
    """Build a BIDS-like dataset by copying original EEG/MEG files unchanged."""
    if not context.valid:
        message = "Other DB mapping is not valid:\n" + "\n".join(context.errors[:12])
        _log(log_callback, message, "error")
        raise ValueError(message)

    if not context.records:
        raise ValueError(f"No files with extension '{context.target_extension}' were found in the selected database.")

    target_output = output_path if output_path is not None else context.output_root
    if not target_output:
        raise ValueError("Output path is required.")
    output_root = Path(target_output)
    context.output_root = str(output_root)

    output_root.mkdir(parents=True, exist_ok=True)
    _progress(progress_callback, 0)
    _log(log_callback, "Building BIDS structure from mapped Other DB files...", "")
    for warning in context.warnings:
        _log(log_callback, warning, "warning")
    _write_dataset_description(output_root, dataset_name or output_root.name)
    _write_readme(output_root)

    participants: set[str] = set()
    scans_by_folder: dict[Path, list[dict[str, str]]] = defaultdict(list)
    copied = 0

    copied_targets: set[str] = set()
    skipped_collisions = 0
    for index, record in enumerate(context.records):
        target_relative_path = record.target_relative_path
        if target_relative_path in copied_targets:
            skipped_collisions += 1
            record.status = "skipped_collision"
            _log(
                log_callback,
                f"[{record.source_relative_path}] skipped because it collides with {target_relative_path}",
                "warning",
            )
            _progress(progress_callback, int(5 + 90 * ((index + 1) / len(context.records))))
            continue

        source = Path(record.source_path)
        destination = output_root / target_relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_targets.add(target_relative_path)
        copied += 1
        record.status = "copied"

        for companion in _companion_files(source):
            companion_destination = destination.with_suffix(companion.suffix)
            shutil.copy2(companion, companion_destination)

        participants.add(f"sub-{record.entities['sub']}")
        scans_folder = destination.parent.parent
        scans_by_folder[scans_folder].append({
            "filename": destination.relative_to(scans_folder).as_posix(),
            "acq_time": "n/a",
        })
        _write_recording_sidecar(destination, record.entities, record.datatype)

        _progress(progress_callback, int(5 + 90 * ((index + 1) / len(context.records))))
        _log(log_callback, f"[{record.source_relative_path}] copied to {record.target_relative_path}", "")

    _write_participants(output_root, participants)
    for folder, rows in scans_by_folder.items():
        _write_scans(folder, rows)

    _progress(progress_callback, 100)
    _log(log_callback, f"Other DB BIDS build finished: {copied} file(s) copied.", "")
    return {
        "valid": True,
        "copied_files": copied,
        "skipped_collisions": skipped_collisions,
        "output_path": str(output_root),
    }


def _records_for_scan_filter(root: Path, target_extension: str, record_name_suffix: str | None = None,
    representative_token_count: int | None = None,
    progress_callback: Callable[[int], None] | None = None) -> tuple[list[ConversionRecord], dict[str, int]]:
    files = []
    scanned = 0
    for file in root.rglob("*"):
        scanned += 1
        if scanned % 250 == 0:
            _progress(progress_callback, min(65, 10 + scanned // 250))
        if (
            file.is_file()
            and file.suffix.lower() == target_extension
            and not any(part.startswith(".") for part in file.relative_to(root).parts)
        ):
            files.append(file)
    files.sort()
    _progress(progress_callback, 70)
    extension_file_count = len(files)
    if record_name_suffix:
        files = [file for file in files if file.name.lower().endswith(record_name_suffix)]
    pattern_file_count = len(files)

    records = []
    for file in files:
        relative_path = file.relative_to(root)
        tokens = tokenize_relative_path(relative_path)
        extension = file.suffix.lower()
        records.append(ConversionRecord(
            id=_record_id(relative_path),
            source_path=str(file),
            source_relative_path=relative_path.as_posix(),
            extension=extension,
            datatype=_datatype_from_extension(extension),
            tokens=tokens,
        ))
    token_layout_warning_count = 0
    if representative_token_count is not None:
        token_layout_warning_count = sum(
            1 for record in records if len(record.tokens) != representative_token_count
        )

    stats = {
        "extension_file_count": extension_file_count,
        "pattern_excluded_count": extension_file_count - pattern_file_count,
        "token_layout_warning_count": token_layout_warning_count,
    }
    return records, stats


def _record_name_suffix(sample_name: str, extension: str) -> str | None:
    rec_suffix = f".rec{extension.lower()}"
    return rec_suffix if sample_name.lower().endswith(rec_suffix) else None


def _scan_warnings(stats: dict[str, int], extension: str, record_name_suffix: str | None) -> list[str]:
    warnings = []
    if record_name_suffix and stats.get("pattern_excluded_count", 0):
        warnings.append(
            f"Ignored {stats['pattern_excluded_count']} {extension} file(s) that do not match '*{record_name_suffix}'."
        )
    if stats.get("token_layout_warning_count", 0):
        warnings.append(
            f"{stats['token_layout_warning_count']} file(s) have a different token layout than the representative record and may be converted incorrectly."
        )
    return warnings


def _map_record(record: ConversionRecord, mapping: dict[str, dict[str, Any]]) -> ConversionRecord:
    tokens = list(record.tokens)
    issues = []
    entities: dict[str, str] = {}

    for entity in BIDS_ENTITY_ORDER:
        rule = mapping.get(entity, {})
        indices = list(rule.get("indices", []))
        fixed_value = str(rule.get("value", "")).strip()
        parts = list(rule.get("parts", []))
        if parts:
            part_values = []
            missing_part = False
            for part in parts:
                if part.get("source") == "literal":
                    part_values.append(str(part.get("value", "")))
                    continue
                index = int(part.get("index", -1))
                if index < 0 or index >= len(tokens):
                    issues.append(f"{entity} references missing token index/indices [{index}].")
                    missing_part = True
                    continue
                part_values.append(str(tokens[index]))
            if missing_part:
                continue
            value = sanitize_bids_label(" ".join(part_values))
        elif fixed_value:
            value = sanitize_bids_label(fixed_value)
        elif indices:
            missing = [index for index in indices if index < 0 or index >= len(tokens)]
            if missing:
                issues.append(f"{entity} references missing token index/indices {missing}.")
                continue
            value = sanitize_bids_label(" ".join(tokens[index] for index in indices))
        else:
            continue
        if not value:
            issues.append(f"{entity} resolves to an empty BIDS label.")
            continue
        entities[entity] = value

    for entity in REQUIRED_BIDS_ENTITIES:
        if entity not in entities:
            issues.append(f"{entity} is missing.")

    target_relative_path = ""
    bids_name = ""
    if not issues:
        bids_name = bids_basename(entities)
        target_relative_path = bids_relative_path(entities, record.datatype, record.extension)

    return ConversionRecord(
        id=record.id,
        source_path=record.source_path,
        source_relative_path=record.source_relative_path,
        extension=record.extension,
        datatype=record.datatype,
        tokens=tokens,
        entities=entities,
        bids_name=bids_name,
        target_relative_path=target_relative_path,
        status="invalid" if issues else "mapped",
        warnings=list(record.warnings),
        errors=_unique(issues),
    )


def record_to_preview_row(record: ConversionRecord) -> dict[str, Any]:
    return {
        "record_id": record.id,
        "source_relative_path": record.source_relative_path,
        "target_relative_path": record.target_relative_path,
        "bids_name": record.bids_name,
        "datatype": record.datatype,
        "extension": record.extension,
        "entities": dict(record.entities),
        "issues": list(record.errors),
        "warnings": list(record.warnings),
        "status": record.status,
    }


def _mapping_rule_has_value(rule: dict[str, Any]) -> bool:
    return bool(rule.get("parts") or rule.get("indices") or rule.get("value"))


def sanitize_bids_label(value: str) -> str:
    return TOKEN_TEXT_RE.sub("", value)


def bids_basename(entities: dict[str, str]) -> str:
    parts = [f"{entity}-{entities[entity]}" for entity in BIDS_ENTITY_ORDER if entities.get(entity)]
    return "_".join(parts)


def bids_relative_path(entities: dict[str, str], datatype: str, extension: str) -> str:
    subject_folder = f"sub-{entities['sub']}"
    parts = [subject_folder]
    if entities.get("ses"):
        parts.append(f"ses-{entities['ses']}")
    parts.append(datatype)
    filename = f"{bids_basename(entities)}_{datatype}{extension}"
    return str(Path(*parts, filename)).replace("\\", "/")


def _record_id(relative_path: str | Path) -> str:
    normalized = Path(relative_path).as_posix()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"rec_{digest}"


def _summary_from_records(records: list[ConversionRecord]) -> dict[str, Any]:
    subject_values = {record.entities.get("sub") for record in records if record.entities.get("sub")}
    task_values = {record.entities.get("task") for record in records if record.entities.get("task")}
    return {
        "Total files": len(records),
        "Number of subjects": len(subject_values),
        "Number of tasks": len(task_values),
        "Task list": sorted(task_values),
    }


def _datatype_from_extension(extension: str) -> str:
    return "meg" if extension.lower() in MEG_EXTENSIONS else "eeg"


def _companion_files(source: Path) -> list[Path]:
    if source.suffix.lower() == ".vhdr":
        return [path for path in (source.with_suffix(".vmrk"), source.with_suffix(".eeg")) if path.exists()]
    if source.suffix.lower() == ".set":
        companion = source.with_suffix(".fdt")
        return [companion] if companion.exists() else []
    return []


def _write_dataset_description(output_root: Path, dataset_name: str) -> None:
    description = {
        "Name": dataset_name,
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "GeneratedBy": [{
            "Name": "MEDUSA Analyzer Other DB Builder",
            "Description": "Token-based mapping from one representative non-BIDS EEG/MEG record.",
        }],
    }
    with open(output_root / "dataset_description.json", "w", encoding="utf-8") as file:
        json.dump(description, file, indent=4)


def _write_readme(output_root: Path) -> None:
    text = (
        "This dataset was generated from a homogeneous non-BIDS EEG/MEG folder structure using one representative record.\n"
        "Original recording file contents were copied without internal conversion.\n"
    )
    (output_root / "README").write_text(text, encoding="utf-8")


def _write_participants(output_root: Path, participants: set[str]) -> None:
    with open(output_root / "participants.tsv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["participant_id"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for participant in sorted(participants):
            writer.writerow({"participant_id": participant})


def _write_scans(folder: Path, rows: list[dict[str, str]]) -> None:
    scans_prefix = folder.name
    if folder.name.startswith("ses-") and folder.parent.name.startswith("sub-"):
        scans_prefix = f"{folder.parent.name}_{folder.name}"
    scans_file = folder / f"{scans_prefix}_scans.tsv"
    with open(scans_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["filename", "acq_time"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item["filename"]):
            writer.writerow(row)


def _write_recording_sidecar(recording_path: Path, entities: dict[str, str], datatype: str) -> None:
    sidecar = {
        "TaskName": entities.get("task", "n/a"),
        "InstitutionName": "n/a",
        "Manufacturer": "n/a",
        "PowerLineFrequency": "n/a",
        "RecordingType": "continuous",
    }
    sidecar_name = f"{recording_path.stem}.json"
    if recording_path.suffix.lower() == ".json":
        sidecar_name = f"{recording_path.stem}_metadata.json"
    sidecar_path = recording_path.with_name(sidecar_name)
    if datatype == "meg":
        sidecar["DewarPosition"] = "n/a"
    with open(sidecar_path, "w", encoding="utf-8") as file:
        json.dump(sidecar, file, indent=4)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _progress(callback: Callable[[int], None] | None, value: int) -> None:
    if callback is not None:
        callback(value)


def _log(callback: Callable[[str, str], None] | None, message: str, role: str) -> None:
    if callback is not None:
        callback(message, role)
