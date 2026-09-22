from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .recording_ids import normalize_recording_id, recording_ignored_prefixes_from_state


_BAND_RE = re.compile(r"_band-([^_]+)")
_SUBJECT_RE = re.compile(r"(?:^|[\\/])sub-([^_\\/]+)|(?:^|_)sub-([^_\\/]+)")


@dataclass(frozen=True, slots=True)
class PreparedEpochValue:
    values: np.ndarray
    times: np.ndarray


@dataclass(frozen=True, slots=True)
class PreparedEpochObservation:
    id: str
    values: np.ndarray
    times: np.ndarray


@dataclass(slots=True)
class PreparedEpochGroupData:
    group_id: str
    name: str
    color: str | None
    observations: list[PreparedEpochObservation] = field(default_factory=list)


@dataclass(slots=True)
class PreparedEpochData:
    band_id: str
    analysis_mode: str
    observation_unit: str
    groups: list[PreparedEpochGroupData]
    times: np.ndarray | None = None

    def has_observations(self) -> bool:
        return any(group.observations for group in self.groups)

    def colors_by_name(self) -> dict[str, str]:
        return {group.name: group.color for group in self.groups if group.color}


@dataclass(frozen=True, slots=True)
class _EpochRecord:
    path: Path
    subject_id: str
    recording_id: str
    band_id: str
    band_token: str


@dataclass(frozen=True, slots=True)
class _LoadedEpoch:
    values: np.ndarray
    times: np.ndarray
    channels: tuple[str, ...]


class EpochDataIndex:
    """Index segmented epoch files by band, subject and logical recording id."""

    def __init__(self, records: list[_EpochRecord], ignored_recording_prefixes: tuple[str, ...] = ()):
        self.records = records
        self.ignored_recording_prefixes = ignored_recording_prefixes
        self._records_by_key: dict[tuple[str, str, str], list[_EpochRecord]] = {}
        self._loaded_by_path: dict[Path, _LoadedEpoch | None] = {}
        for record in records:
            key = (record.band_token, record.subject_id, record.recording_id)
            self._records_by_key.setdefault(key, []).append(record)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "EpochDataIndex":
        derivatives_path = Path(str(state.get("derivatives_path") or ""))
        segmented_path = derivatives_path / "segmented"
        records: list[_EpochRecord] = []
        ignored_recording_prefixes = recording_ignored_prefixes_from_state(state)

        if not segmented_path.is_dir():
            return cls(records, ignored_recording_prefixes)

        for path in segmented_path.rglob("*"):
            if not path.is_file():
                continue
            record = _epoch_record_from_path(path, ignored_recording_prefixes)
            if record is not None:
                records.append(record)

        return cls(records, ignored_recording_prefixes)

    def values_for(self, band_id: str, subject_id: str, recording_id: str,
        selected_channels: list[int], channel_count: int) -> list[PreparedEpochValue]:
        band_token = _token(band_id)
        subject_key = _normalize_subject_id(subject_id)
        recording_key = self.normalize_recording_id(recording_id)
        values: list[PreparedEpochValue] = []

        for record in self._records_by_key.get((band_token, subject_key, recording_key), []):
            loaded = self._load(record.path)
            if loaded is None:
                continue
            reduced = _reduce_loaded_epoch(loaded, selected_channels, channel_count)
            if reduced is not None:
                values.append(reduced)
        return values

    def available_band_ids(self) -> set[str]:
        return {record.band_id for record in self.records}

    def has_band(self, band_id: str) -> bool:
        return _token(band_id) in {record.band_token for record in self.records}

    def normalize_recording_id(self, value: Any) -> str:
        return normalize_recording_id(value, self.ignored_recording_prefixes)

    def _load(self, path: Path) -> _LoadedEpoch | None:
        if path not in self._loaded_by_path:
            self._loaded_by_path[path] = _load_epoch_file(path)
        return self._loaded_by_path[path]


def prepare_grouped_epoch_data(state: dict[str, Any], band_id: str, selected_channels: list[int],
    data_index: EpochDataIndex | None = None) -> PreparedEpochData:
    analysis_mode = _analysis_mode(state)
    groups = _groups_from_state(state)
    channel_count = len(_channel_names(state))
    channels = _normalize_channel_indices(selected_channels, channel_count)
    data_index = data_index or EpochDataIndex.from_state(state)
    prepared_groups: list[PreparedEpochGroupData] = []
    times: np.ndarray | None = None

    if analysis_mode == "between":
        selected_recordings = _unique_ordered(
            data_index.normalize_recording_id(item) for item in _selected_recordings(state))
        observation_unit = "recording"
        for group_id, group in groups.items():
            prepared_group = _prepared_group_shell(group_id, group)
            group_subjects = [_normalize_subject_id(item) for item in group.get("subjects", [])]
            for recording_id in selected_recordings:
                averaged_values = []
                for subject_id in group_subjects:
                    combo_values = data_index.values_for(band_id, subject_id, recording_id, channels, channel_count)
                    combo_value = _average_epoch_values(combo_values)
                    if combo_value is not None:
                        averaged_values.append(combo_value)
                observation = _average_epoch_values(averaged_values)
                if observation is not None:
                    times = times if times is not None else observation.times
                    prepared_group.observations.append(PreparedEpochObservation(
                        recording_id, observation.values, observation.times))
            prepared_groups.append(prepared_group)
    else:
        selected_subjects = [_normalize_subject_id(item) for item in _selected_subjects(state)]
        observation_unit = "subject"
        for group_id, group in groups.items():
            prepared_group = _prepared_group_shell(group_id, group)
            group_recordings = _unique_ordered(
                data_index.normalize_recording_id(item) for item in group.get("files", []))
            for subject_id in selected_subjects:
                averaged_values = []
                for recording_id in group_recordings:
                    combo_values = data_index.values_for(band_id, subject_id, recording_id, channels, channel_count)
                    combo_value = _average_epoch_values(combo_values)
                    if combo_value is not None:
                        averaged_values.append(combo_value)
                observation = _average_epoch_values(averaged_values)
                if observation is not None:
                    times = times if times is not None else observation.times
                    prepared_group.observations.append(PreparedEpochObservation(
                        subject_id, observation.values, observation.times))
            prepared_groups.append(prepared_group)

    return PreparedEpochData(band_id=band_id, analysis_mode=analysis_mode, observation_unit=observation_unit,
        groups=prepared_groups, times=times)


def _epoch_record_from_path(path: Path, ignored_recording_prefixes: tuple[str, ...]) -> _EpochRecord | None:
    band_match = _BAND_RE.search(path.stem)
    if band_match is None:
        return None
    return _EpochRecord(
        path=path,
        subject_id=_normalize_subject_id(str(path)),
        recording_id=normalize_recording_id(str(path), ignored_recording_prefixes),
        band_id=band_match.group(1),
        band_token=_token(band_match.group(1)),
    )


def _load_epoch_file(path: Path) -> _LoadedEpoch | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    values = _as_float_array(payload.get("signal") if isinstance(payload, dict) else None)
    times = _time_vector_ms(payload)
    if values is None or times is None:
        return None

    channels = payload.get("channels") if isinstance(payload, dict) else []
    channel_names = tuple(str(channel) for channel in channels) if isinstance(channels, list) else ()
    return _LoadedEpoch(values=values, times=times, channels=channel_names)


def _time_vector_ms(payload: Any) -> np.ndarray | None:
    if not isinstance(payload, dict):
        return None
    times = _as_float_array(payload.get("times"))
    if times is None:
        return None
    times = np.asarray(times, dtype=float).squeeze()
    if times.ndim != 1 or times.size == 0:
        return None

    unit = str(payload.get("time_unit") or "").strip().lower()
    if unit in {"ms", "millisecond", "milliseconds"}:
        return times
    if unit in {"s", "sec", "second", "seconds"}:
        return times * 1000

    # Legacy segmented files did not store time_unit and used seconds.
    return times * 1000 if np.nanmax(np.abs(times)) <= 50 else times


def _reduce_loaded_epoch(loaded: _LoadedEpoch, selected_channels: list[int],
    channel_count: int) -> PreparedEpochValue | None:
    epochs = _normalize_epoch_array(loaded.values, len(loaded.channels) or channel_count, loaded.times.size)
    if epochs is None:
        return None

    channels = selected_channels or list(range(epochs.shape[2]))
    valid_channels = [channel for channel in channels if 0 <= channel < epochs.shape[2]]
    if not valid_channels:
        return None

    channel_mean = _nanmean_axis(np.take(epochs, valid_channels, axis=2), 2)
    epoch_mean = _nanmean_axis(channel_mean, 0)
    epoch_mean = np.asarray(epoch_mean, dtype=float).squeeze()
    if epoch_mean.ndim != 1 or epoch_mean.size == 0 or not np.isfinite(epoch_mean).any():
        return None

    times = loaded.times
    if epoch_mean.size != times.size:
        min_len = min(epoch_mean.size, times.size)
        epoch_mean = epoch_mean[:min_len]
        times = times[:min_len]
    return PreparedEpochValue(values=epoch_mean, times=times)


def _normalize_epoch_array(values: np.ndarray, channel_count: int, times_size: int) -> np.ndarray | None:
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        return array.reshape(1, array.shape[0], 1)
    if array.ndim == 2:
        if channel_count == 1 and array.shape[1] == times_size:
            return array[:, :, None]
        if array.shape[0] == times_size and (not channel_count or array.shape[1] == channel_count):
            return array[None, :, :]
        if array.shape[1] == times_size:
            return array[:, :, None]
        if array.shape[0] == times_size:
            return array.T[None, :, :]
        return None
    if array.ndim == 3:
        axes = list(range(3))
        time_axes = [axis for axis in axes if array.shape[axis] == times_size]
        if not time_axes:
            return None
        time_axis = time_axes[0]
        remaining = [axis for axis in axes if axis != time_axis]
        channel_axes = [axis for axis in remaining if channel_count and array.shape[axis] == channel_count]
        channel_axis = channel_axes[-1] if channel_axes else remaining[-1]
        epoch_axis = next(axis for axis in axes if axis not in {time_axis, channel_axis})
        return np.moveaxis(array, [epoch_axis, time_axis, channel_axis], [0, 1, 2])
    return None


def _average_epoch_values(values: list[PreparedEpochValue]) -> PreparedEpochValue | None:
    if not values:
        return None

    reference_times = values[0].times
    signals = []
    for value in values:
        signal = np.asarray(value.values, dtype=float).squeeze()
        times = np.asarray(value.times, dtype=float).squeeze()
        if signal.ndim != 1 or times.ndim != 1 or signal.size == 0 or times.size == 0:
            continue
        if signal.size != times.size:
            min_len = min(signal.size, times.size)
            signal = signal[:min_len]
            times = times[:min_len]
        if times.size != reference_times.size or not np.allclose(times, reference_times):
            signal = np.interp(reference_times, times, signal)
        signals.append(signal)

    if not signals:
        return None
    mean_signal = _nanmean_axis(np.stack(signals), 0)
    if not np.isfinite(mean_signal).any():
        return None
    return PreparedEpochValue(values=np.asarray(mean_signal, dtype=float), times=reference_times)


def _prepared_group_shell(group_id: str, group: dict[str, Any]) -> PreparedEpochGroupData:
    name = str(group.get("group_name") or group_id)
    color = str(group.get("group_color") or "").strip() or None
    return PreparedEpochGroupData(group_id=group_id, name=name, color=color)


def _analysis_mode(state: dict[str, Any]) -> str:
    mode = str(state.get("analysis_mode") or "within").lower()
    return "between" if mode == "between" else "within"


def _selected_subjects(state: dict[str, Any]) -> list[str]:
    selected = state.get("plot_selected_subjects")
    if isinstance(selected, list) and selected:
        return [str(item) for item in selected]
    assignment = state.get("data_assignment")
    if isinstance(assignment, dict) and assignment.get("target") == "subjects":
        items = assignment.get("selected_items")
        if isinstance(items, list):
            return [str(item) for item in items]
    return []


def _selected_recordings(state: dict[str, Any]) -> list[str]:
    selected = state.get("plot_selected_recordings")
    if isinstance(selected, list) and selected:
        return [str(item) for item in selected]
    assignment = state.get("data_assignment")
    if isinstance(assignment, dict) and assignment.get("target") == "recordings":
        items = assignment.get("selected_items")
        if isinstance(items, list):
            return [str(item) for item in items]
    return []


def _groups_from_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups = state.get("groups")
    if isinstance(groups, dict):
        return {str(group_id): dict(group) for group_id, group in groups.items() if isinstance(group, dict)}
    return {}


def _channel_names(state: dict[str, Any]) -> list[str]:
    channels = state.get("channel_names")
    if isinstance(channels, list):
        return [str(channel) for channel in channels]
    config_data = state.get("plot_features_config")
    metadata = config_data.get("metadata") if isinstance(config_data, dict) else {}
    channel_set = metadata.get("channel_set") if isinstance(metadata, dict) else []
    return [str(channel) for channel in channel_set] if isinstance(channel_set, list) else []


def _normalize_channel_indices(selected_channels: list[int], channel_count: int) -> list[int]:
    channels = []
    for channel in selected_channels:
        try:
            channel_index = int(channel)
        except (TypeError, ValueError):
            continue
        if channel_index < 0:
            continue
        if channel_count and channel_index >= channel_count:
            continue
        channels.append(channel_index)
    return sorted(set(channels))


def _normalize_subject_id(value: Any) -> str:
    text = str(value).replace("\\", "/")
    match = _SUBJECT_RE.search(text)
    if match:
        subject = next(group for group in match.groups() if group)
    else:
        subject = text.rsplit("/", 1)[-1]
        if subject.startswith("sub-"):
            subject = subject[4:]
    return f"sub-{subject.strip()}"


def _unique_ordered(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _as_float_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    return array if array.size else None


def _nanmean_axis(values: np.ndarray, axis: int | tuple[int, ...]) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(values, axis=axis)


__all__ = [
    "EpochDataIndex",
    "PreparedEpochData",
    "PreparedEpochGroupData",
    "PreparedEpochObservation",
    "PreparedEpochValue",
    "prepare_grouped_epoch_data",
]
