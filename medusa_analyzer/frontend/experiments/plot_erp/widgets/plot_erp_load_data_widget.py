from __future__ import annotations

from pathlib import Path
from typing import Any

from medusa_analyzer.frontend.widgets.plot_workflow.load_data_widget import PlotWorkflowLoadDataWidget


class PlotERPLoadDataWidget(PlotWorkflowLoadDataWidget):
    @classmethod
    def page_title(cls) -> str:
        return "Load segmented epochs"

    @classmethod
    def page_description(cls) -> str:
        return "Select the derivatives folder that contains segmented epoch files."

    @classmethod
    def data_files_state_key(cls) -> str:
        return "epoch_files"

    def _discover_data_files(self, derivatives_path: Path) -> list[str]:
        allowed_extensions = {str(ext).lower() for ext in self.config.get("allowed_extensions", [])}
        segmented_path = derivatives_path / "segmented"
        if not segmented_path.is_dir():
            return []
        files = []
        for file_path in segmented_path.rglob("*"):
            stem = file_path.stem
            if not file_path.is_file() or "_band-" not in stem or "_segment-" not in stem:
                continue
            if allowed_extensions and file_path.suffix.lower() not in allowed_extensions:
                continue
            files.append(str(file_path))
        return sorted(files)

    def _build_metadata(self, derivatives_path: Path, config_path: Path, config_data: dict[str, Any],
        channel_names: list[str], feature_files: list[str]) -> dict[str, Any]:
        metadata = super()._build_metadata(derivatives_path, config_path, config_data, channel_names, feature_files)
        metadata.pop("Selected features", None)
        metadata.pop("Feature files", None)
        metadata["Segmented files"] = len(feature_files)
        return metadata

    @classmethod
    def _recordings_from_derivatives(cls, derivatives_path: Path | None,
        ignored_prefixes: tuple[str, ...]) -> list[str]:
        return cls._recordings_from_segmented_files(derivatives_path, ignored_prefixes)

    def can_continue(self) -> bool:
        return (super().can_continue()
            and bool(self.state.get(self.data_files_state_key()))
            and bool(self.state.get("plot_features_recordings")))


__all__ = ["PlotERPLoadDataWidget"]
