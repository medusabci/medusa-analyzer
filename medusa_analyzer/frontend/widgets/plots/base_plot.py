from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import warnings
from typing import Any, Iterable

import numpy as np
from matplotlib.axes import Axes

from .recording_ids import normalize_recording_base_id, normalize_recording_id, recording_ignored_prefixes_from_state


_PARAM_RE = re.compile(r"_param-([^_]+)")
_BAND_RE = re.compile(r"_band-([^_]+)")
_SUBJECT_RE = re.compile(r"(?:^|[\\/])sub-([^_\\/]+)|(?:^|_)sub-([^_\\/]+)")
_CONNECTIVITY_FEATURES = {"aec", "iac", "plv", "pli", "wpli"}
_FEATURE_ALIASES = {
    "lempelzivcomplexity": {"lempelzivcomplexity", "lzc"},
    "multiscalelempelzivcomplexity": {"multiscalelempelzivcomplexity", "multiscalelzc"},
}


@dataclass(frozen=True, slots=True)
class PreparedValue:
    values: np.ndarray
    freqs: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class PreparedObservation:
    id: str
    values: np.ndarray
    freqs: np.ndarray | None = None


@dataclass(slots=True)
class PreparedGroupData:
    group_id: str
    name: str
    color: str | None
    observations: list[PreparedObservation] = field(default_factory=list)


@dataclass(slots=True)
class PreparedPlotData:
    feature_id: str
    band_id: str
    analysis_mode: str
    observation_unit: str
    groups: list[PreparedGroupData]
    freqs: np.ndarray | None = None

    def has_observations(self) -> bool:
        return any(group.observations for group in self.groups)

    def colors_by_name(self) -> dict[str, str]:
        return {group.name: group.color for group in self.groups if group.color}


@dataclass(frozen=True, slots=True)
class _ParameterRecord:
    path: Path
    subject_id: str
    recording_id: str
    recording_aliases: tuple[str, ...]
    feature_token: str
    band_id: str
    band_token: str


@dataclass(frozen=True, slots=True)
class _LoadedParameter:
    values: np.ndarray
    freqs: np.ndarray | None = None


class PlotDataIndex:
    """Index parameter files by feature, band, subject and recording."""

    def __init__(self, records: list[_ParameterRecord], ignored_recording_prefixes: tuple[str, ...] = ()):
        self.records = records
        self.ignored_recording_prefixes = ignored_recording_prefixes
        self._records_by_key: dict[tuple[str, str, str, str], list[_ParameterRecord]] = {}
        self._loaded_by_path: dict[Path, _LoadedParameter | None] = {}
        self._band_tokens_by_feature: dict[str, set[str]] = defaultdict(set)
        self._band_ids_by_feature: dict[str, set[str]] = defaultdict(set)
        for record in records:
            self._band_tokens_by_feature[record.feature_token].add(record.band_token)
            self._band_ids_by_feature[record.feature_token].add(record.band_id)
            for recording_id in (record.recording_id, *record.recording_aliases):
                key = (record.feature_token, record.band_token, record.subject_id, recording_id)
                self._records_by_key.setdefault(key, []).append(record)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "PlotDataIndex":
        derivatives_path = Path(str(state.get("derivatives_path") or ""))
        parameters_path = derivatives_path / "parameters"
        search_path = parameters_path if parameters_path.is_dir() else derivatives_path
        records: list[_ParameterRecord] = []
        ignored_recording_prefixes = recording_ignored_prefixes_from_state(state)

        discovered_files = state.get("feature_files")
        if isinstance(discovered_files, list) and discovered_files:
            candidate_paths = [Path(str(path)) for path in discovered_files]
        elif search_path.is_dir():
            candidate_paths = [path for path in search_path.rglob("*") if path.is_file()]
        else:
            candidate_paths = []

        for path in candidate_paths:
            record = _parameter_record_from_path(path, ignored_recording_prefixes)
            if record is not None:
                records.append(record)

        return cls(records, ignored_recording_prefixes)

    def values_for(self, feature_id: str, band_id: str, subject_id: str, recording_id: str,
        selected_channels: list[int], channel_count: int) -> list[PreparedValue]:
        feature_tokens = _feature_tokens(feature_id)
        band_token = _token(band_id)
        subject_key = _normalize_subject_id(subject_id)
        recording_key = self.normalize_recording_id(recording_id)
        values: list[PreparedValue] = []

        for feature_token in feature_tokens:
            key = (feature_token, band_token, subject_key, recording_key)
            for record in self._records_by_key.get(key, []):
                loaded = self._load(record.path)
                if loaded is None:
                    continue
                reduced = _reduce_loaded_parameter(loaded, feature_id, selected_channels, channel_count)
                if reduced is not None:
                    values.append(reduced)

        return values

    def available_band_tokens(self, feature_id: str) -> set[str]:
        feature_tokens = _feature_tokens(feature_id)
        return set().union(*(self._band_tokens_by_feature.get(token, set()) for token in feature_tokens))

    def available_band_ids(self, feature_id: str) -> set[str]:
        feature_tokens = _feature_tokens(feature_id)
        return set().union(*(self._band_ids_by_feature.get(token, set()) for token in feature_tokens))

    def has_feature_band(self, feature_id: str, band_id: str) -> bool:
        return _token(band_id) in self.available_band_tokens(feature_id)

    def normalize_recording_id(self, value: Any) -> str:
        return _normalize_recording_id(value, self.ignored_recording_prefixes)

    def _load(self, path: Path) -> _LoadedParameter | None:
        if path not in self._loaded_by_path:
            self._loaded_by_path[path] = _load_parameter_file(path)
        return self._loaded_by_path[path]


class BasePlot(ABC):
    """
    Abstract base class for plot types.
    Provides a standard interface for plotting and shared utilities.
    """

    subject_pattern = r"sub-([^\\/]+)"

    def __init__(self, ax: Axes, plot_params: dict[str, Any] | None = None, tabs_widget: Any = None):
        self.ax = ax
        self.plot_params = plot_params or {}
        self.last_limits = {} # save info from the last draw
        self.tabs_widget = tabs_widget

    @staticmethod
    def data_index_from_state(state: dict[str, Any]) -> PlotDataIndex:
        return PlotDataIndex.from_state(state)

    @staticmethod
    def prepare_grouped_plot_data(state: dict[str, Any], feature_id: str, band_id: str,
        selected_channels: list[int], data_index: PlotDataIndex | None = None) -> PreparedPlotData:
        return _prepare_grouped_plot_data(state, feature_id, band_id, selected_channels, data_index)

    def prepare_grouped_data(self, state: dict[str, Any], feature_id: str, band_id: str,
        selected_channels: list[int], data_index: PlotDataIndex | None = None) -> PreparedPlotData:
        return self.prepare_grouped_plot_data(state, feature_id, band_id, selected_channels, data_index)

    @abstractmethod
    def load_data(self, *args, **kwargs) -> None:
        """Load and preprocess data specific to the plot type."""

    @abstractmethod
    def draw(self, colors: dict[str, str] | None = None) -> None:
        """Render the plot on the assigned Axes."""

    def clear(self) -> None:
        """Clear the current axis."""
        self.ax.clear()
        self.apply_labels()
        self.apply_title()

    def apply_labels(self) -> None:
        font_size = self.plot_params.get("font_size", 10)
        font_weight = self.plot_params.get("font_weight", "normal")
        self.ax.set_xlabel(self.plot_params.get("x_label", ""), fontsize=font_size, fontweight=font_weight)
        self.ax.set_ylabel(self.plot_params.get("y_label", ""), fontsize=font_size, fontweight=font_weight)

    def apply_title(self) -> None:
        title = self.plot_params.get("title", "")
        if not title:
            return
        self.ax.set_title(title, fontsize=self.plot_params.get("title_size", 12),
            fontweight=self.plot_params.get("title_weight", "bold"))

    def apply_grid_and_spines(self, axis: str = "both") -> None:
        self.ax.grid(True, axis=axis, linestyle="--", alpha=0.4)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

    def safe_set_lim(self, method: str, lim) -> None:
        if not isinstance(lim, (list, tuple)) or len(lim) != 2:
            return

        lo, hi = lim
        if lo is None and hi is None:
            return

        try:
            ax_method = getattr(self.ax, method)
            cur_lo, cur_hi = ax_method()
            ax_method([lo if lo is not None else cur_lo, hi if hi is not None else cur_hi])
        except Exception as error:
            print(f"[WARN] Could not apply {method}: {error}")

    def save_limits(self) -> None:
        self.last_limits = {"xlim": list(map(float, self.ax.get_xlim())), "ylim": list(map(float, self.ax.get_ylim()))}

    def get_last_limits(self) -> dict[str, list[float]]:
        return self.last_limits

    def normalize_data(self, data) -> np.ndarray | None:
        """
        Normalize data to shape (channels,) or (times, channels).
        Accepted shapes:
        - (channels,)
        - (1, channels)
        - (epochs, channels)
        - (epochs, times, channels)
        """

        if data is None:
            return None

        data = np.asarray(data)
        if data.ndim == 1:
            return data
        if data.ndim == 2:
            if data.shape[0] == 1:
                return data.squeeze()
            return np.mean(data, axis=0) # shape: epochs x channels
        if data.ndim == 3:
            return np.mean(data, axis=0) # shape: times x channels

        raise ValueError(f"[BasePlot] Unsupported data shape: {data.shape}")

    def normalize_data_psd(self, values) -> np.ndarray:
        """
        Normalize PSD data to shape (freqs, channels).
        Accepted shapes:
        - (freqs, channels)
        - (channels, freqs)
        - (epochs, freqs, channels)
        """

        values = np.asarray(values)
        if values.ndim == 2:
            return values
        if values.ndim == 3:
            return np.mean(values, axis=0)

        raise ValueError(f"[PSDPlot] Unsupported PSD shape: {values.shape}")

    def aggregate_subject_data(self, subject_data) -> np.ndarray:
        """
        Receives a list of tuples:
            [(subject_id, value), (subject_id, value), ...]

        where value can be:
        - a scalar
        - a 1D array / signal
        """

        grouped = defaultdict(list)
        for subject_id, value in subject_data:
            if value is None:
                continue

            arr = np.asarray(value).squeeze()
            if arr.ndim > 1 or arr.size == 0:
                continue

            grouped[subject_id].append(arr)

        if not grouped:
            return np.array([])

        first_subject_values = next(iter(grouped.values()))
        first_value = np.asarray(first_subject_values[0]).squeeze()
        if first_value.ndim == 0:
            return np.array([np.mean([float(value) for value in values]) for values in grouped.values()],
                dtype=float)

        per_subject = []
        for values in grouped.values():
            min_len = min(np.asarray(value).shape[0] for value in values)
            aligned = np.array([np.asarray(value)[:min_len] for value in values])
            mean_subject_signal = np.mean(aligned, axis=0)
            per_subject.append(mean_subject_signal)

        min_len = min(signal.shape[0] for signal in per_subject)
        return np.array([signal[:min_len] for signal in per_subject])

    def extract_subject_id(self, filepath: str) -> str:
        match = re.search(self.subject_pattern, filepath)
        if match:
            return match.group(1)
        return os.path.basename(filepath)

    def current_tab(self):
        if self.tabs_widget is None or not hasattr(self.tabs_widget, "tab_widgets"):
            return None
        return next((tab for tab in self.tabs_widget.tab_widgets if getattr(tab, "_plot", None) is self), None)

    @staticmethod
    def prepared_scalar(value) -> float | None:
        try:
            array = np.asarray(value, dtype=float).squeeze()
        except (TypeError, ValueError):
            return None
        if array.size == 0 or not np.isfinite(array).any():
            return None
        return float(np.nanmean(array))


def _prepare_grouped_plot_data(state: dict[str, Any], feature_id: str, band_id: str,
    selected_channels: list[int], data_index: PlotDataIndex | None = None) -> PreparedPlotData:
    analysis_mode = _analysis_mode(state)
    groups = _groups_from_state(state)
    channel_count = len(_channel_names(state))
    channels = _normalize_channel_indices(selected_channels, channel_count)
    data_index = data_index or PlotDataIndex.from_state(state)
    prepared_groups: list[PreparedGroupData] = []
    freqs: np.ndarray | None = None

    if analysis_mode == "between":
        selected_recordings = _unique_ordered(
            data_index.normalize_recording_id(item) for item in _selected_recordings(state))
        observation_unit = "subject"
        for group_id, group in groups.items():
            prepared_group = _prepared_group_shell(group_id, group)
            group_subjects = [_normalize_subject_id(item) for item in group.get("subjects", [])]
            for subject_id in group_subjects:
                averaged_values = []
                for recording_id in selected_recordings:
                    combo_values = data_index.values_for(feature_id, band_id, subject_id, recording_id, channels,
                        channel_count)
                    combo_value = _average_values(combo_values)
                    if combo_value is not None:
                        averaged_values.append(combo_value)

                observation = _average_values(averaged_values)
                if observation is not None:
                    freqs = freqs if freqs is not None else observation.freqs
                    prepared_group.observations.append(PreparedObservation(subject_id, observation.values,
                        observation.freqs))
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
                    combo_values = data_index.values_for(feature_id, band_id, subject_id, recording_id, channels,
                        channel_count)
                    combo_value = _average_values(combo_values)
                    if combo_value is not None:
                        averaged_values.append(combo_value)

                observation = _average_values(averaged_values)
                if observation is not None:
                    freqs = freqs if freqs is not None else observation.freqs
                    prepared_group.observations.append(PreparedObservation(subject_id, observation.values,
                        observation.freqs))
            prepared_groups.append(prepared_group)

    return PreparedPlotData(feature_id=feature_id, band_id=band_id, analysis_mode=analysis_mode,
        observation_unit=observation_unit, groups=prepared_groups, freqs=freqs)


def _parameter_record_from_path(path: Path, ignored_recording_prefixes: tuple[str, ...] = ()) -> _ParameterRecord | None:
    stem = path.stem
    param_match = _PARAM_RE.search(stem)
    band_match = _BAND_RE.search(stem)
    if param_match is None or band_match is None:
        return None

    base_stem = stem[:param_match.start()]
    subject_id = _normalize_subject_id(str(path))
    recording_id = _normalize_recording_id(stem, ignored_recording_prefixes)
    recording_base_id = normalize_recording_base_id(base_stem, ignored_recording_prefixes)
    return _ParameterRecord(path=path, subject_id=subject_id,
        recording_id=recording_id,
        recording_aliases=(recording_base_id,) if recording_base_id and recording_base_id != recording_id else (),
        feature_token=_token(param_match.group(1)), band_id=band_match.group(1), band_token=_token(band_match.group(1)))


def _prepared_group_shell(group_id: str, group: dict[str, Any]) -> PreparedGroupData:
    name = str(group.get("group_name") or group_id)
    color = str(group.get("group_color") or "").strip() or None
    return PreparedGroupData(group_id=group_id, name=name, color=color)


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


def _normalize_recording_id(value: Any, ignored_recording_prefixes: tuple[str, ...] = ()) -> str:
    return normalize_recording_id(value, ignored_recording_prefixes)


def _unique_ordered(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _feature_tokens(feature_id: str) -> set[str]:
    feature_token = _token(feature_id)
    tokens = {feature_token}
    for alias_group, aliases in _FEATURE_ALIASES.items():
        if feature_token == alias_group or feature_token in aliases:
            tokens.update(aliases)
            tokens.add(alias_group)
    return tokens


def _token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _load_parameter_file(path: Path) -> _LoadedParameter | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _loaded_parameter_from_payload(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass

    try:
        import scipy.io

        payload = scipy.io.loadmat(path, squeeze_me=True, struct_as_record=False)
    except Exception:
        return None
    return _loaded_parameter_from_payload(payload)


def _loaded_parameter_from_payload(payload: Any) -> _LoadedParameter | None:
    psd = _extract_psd_payload(payload)
    if psd is not None:
        values, freqs = psd
        return _LoadedParameter(values=values, freqs=freqs)

    values = _extract_numeric_payload(payload)
    if values is None:
        return None
    return _LoadedParameter(values=values)


def _extract_psd_payload(payload: Any) -> tuple[np.ndarray, np.ndarray] | None:
    candidates = []
    for key in ("param", "psd", "psd_struct", "PSD", "PSD_struct"):
        candidate = _field(payload, key)
        if candidate is not None:
            candidates.append(candidate)
    candidates.append(payload)

    for candidate in candidates:
        freqs = _field(candidate, "freqs", "frequency", "frequencies", "f")
        values = _field(candidate, "values", "psd", "PSD")
        values_arr = _as_float_array(values)
        freqs_arr = _as_float_array(freqs)
        if values_arr is not None and freqs_arr is not None:
            return values_arr, np.asarray(freqs_arr).squeeze()
    return None


def _extract_numeric_payload(payload: Any) -> np.ndarray | None:
    for key in ("param", "data", "vector", "values", "valores"):
        value = _field(payload, key)
        if isinstance(value, dict):
            continue
        array = _as_float_array(value)
        if array is not None:
            return array

    if isinstance(payload, dict):
        for value in payload.values():
            array = _as_float_array(value)
            if array is not None:
                return array
    return None


def _field(source: Any, *names: str) -> Any:
    if isinstance(source, dict):
        for name in names:
            if name in source:
                return source[name]
    for name in names:
        if hasattr(source, name):
            return getattr(source, name)
    return None


def _as_float_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    return array if array.size else None


def _reduce_loaded_parameter(loaded: _LoadedParameter, feature_id: str, selected_channels: list[int],
    channel_count: int) -> PreparedValue | None:
    if loaded.freqs is not None:
        return _reduce_psd_value(loaded, feature_id, selected_channels, channel_count)
    return _reduce_scalar_value(loaded.values, feature_id, selected_channels, channel_count)


def _reduce_scalar_value(values: np.ndarray, feature_id: str, selected_channels: list[int],
    channel_count: int) -> PreparedValue | None:
    array = _reduce_channels(values, feature_id, selected_channels, channel_count)
    mean_value = _nanmean(array)
    if mean_value is None:
        return None
    return PreparedValue(values=np.asarray(float(mean_value)))


def _reduce_psd_value(loaded: _LoadedParameter, feature_id: str, selected_channels: list[int],
    channel_count: int) -> PreparedValue | None:
    freqs = np.asarray(loaded.freqs, dtype=float).squeeze()
    if freqs.ndim != 1 or freqs.size == 0:
        return None

    array = _reduce_channels(loaded.values, feature_id, selected_channels, channel_count, freqs.size)
    if array.ndim == 0:
        return None

    freq_axes = [axis for axis, size in enumerate(array.shape) if size == freqs.size]
    if not freq_axes and array.size == freqs.size:
        curve = array.reshape(freqs.size)
    elif freq_axes:
        freq_axis = freq_axes[-1]
        array = np.moveaxis(array, freq_axis, -1)
        axes_to_average = tuple(range(array.ndim - 1))
        curve = _nanmean_axis(array, axes_to_average) if axes_to_average else array
    else:
        return None

    curve = np.asarray(curve, dtype=float).squeeze()
    if curve.ndim != 1 or curve.size != freqs.size or not np.isfinite(curve).any():
        return None
    return PreparedValue(values=curve, freqs=freqs)


def _reduce_channels(values: np.ndarray, feature_id: str, selected_channels: list[int], channel_count: int,
    freqs_size: int | None = None) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0 or not selected_channels:
        return array

    channel_axes = []
    if channel_count:
        channel_axes = [axis for axis, size in enumerate(array.shape)
            if size == channel_count and size != freqs_size]
    if not channel_axes and array.ndim == 1 and max(selected_channels) < array.shape[0]:
        channel_axes = [0]
    if not channel_axes:
        return array

    feature_token = _token(feature_id)
    axes = channel_axes if feature_token in _CONNECTIVITY_FEATURES and len(channel_axes) > 1 else [channel_axes[-1]]
    for axis in sorted(axes, reverse=True):
        valid_channels = [channel for channel in selected_channels if channel < array.shape[axis]]
        if not valid_channels:
            continue
        array = np.take(array, valid_channels, axis=axis)
        array = _nanmean_axis(array, axis)
    return np.asarray(array, dtype=float)


def _average_values(values: list[PreparedValue]) -> PreparedValue | None:
    if not values:
        return None

    reference_freqs = next((value.freqs for value in values if value.freqs is not None), None)
    if reference_freqs is not None:
        curves = []
        for value in values:
            if value.freqs is None:
                continue
            curve = np.asarray(value.values, dtype=float).squeeze()
            freqs = np.asarray(value.freqs, dtype=float).squeeze()
            if curve.ndim != 1 or freqs.ndim != 1:
                continue
            if freqs.size != reference_freqs.size or not np.allclose(freqs, reference_freqs):
                curve = np.interp(reference_freqs, freqs, curve)
            curves.append(curve)
        if not curves:
            return None

        averaged_curve = _nanmean_axis(np.stack(curves), 0)
        if not np.isfinite(averaged_curve).any():
            return None
        return PreparedValue(values=np.asarray(averaged_curve, dtype=float), freqs=reference_freqs)

    scalars = []
    for value in values:
        scalar = _nanmean(value.values)
        if scalar is not None:
            scalars.append(float(scalar))
    if not scalars:
        return None

    return PreparedValue(values=np.asarray(float(_nanmean(np.asarray(scalars, dtype=float)))))


def _nanmean(values: Any) -> float | None:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).any():
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return float(np.nanmean(array))


def _nanmean_axis(values: np.ndarray, axis: int | tuple[int, ...]) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(values, axis=axis)
