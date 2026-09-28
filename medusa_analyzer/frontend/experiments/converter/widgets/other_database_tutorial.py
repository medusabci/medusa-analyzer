from __future__ import annotations

from PySide6.QtWidgets import QWidget

from medusa_analyzer.frontend.widgets.tutorial_overlay import (
    TutorialExample,
    TutorialOverlay,
    TutorialStep,
)


class OtherDatabaseTutorialOverlay(TutorialOverlay):
    """Short onboarding carousel for the Other DB converter flow."""

    def __init__(self, parent: QWidget):
        super().__init__(
            parent=parent,
            title="Other DB conversion",
            steps=(
                TutorialStep(
                    title="Convert a generic database to BIDS",
                    body=(
                        "This flow copies a generic EEG/MEG database into a BIDS-like folder structure. "
                        "It does not infer the study design from file contents; it reads the structure from "
                        "folder and file-name tokens."
                    ),
                    bullets=(
                        "Choose the database root folder.",
                        "Choose one representative recording.",
                        "Map detected path tokens to BIDS fields such as sub, task and run.",
                    ),
                ),
                TutorialStep(
                    title="The database should follow a repeated layout",
                    body=(
                        "The selected representative record defines how the rest of the database will be interpreted. "
                        "Files can differ in values, but their folder and file-name pattern should mean the same thing."
                    ),
                    examples=(
                        TutorialExample(
                            "Consistent layout",
                            "S01/R1.rec.bson\nS01/R2.rec.bson\nS02/R1.rec.bson\nS02/R2.rec.bson",
                            "positive",
                        ),
                        TutorialExample(
                            "Risky layout",
                            "S01/R1.rec.bson\nSession_A/S02/game/R1.rec.bson\nnotes/config.json",
                            "warning",
                        ),
                    ),
                ),
                TutorialStep(
                    title="Understand the assumptions",
                    body=(
                        "MEDUSA will scan matching recording files and split each relative path into tokens. "
                        "The same token positions are then used for every file in the conversion."
                    ),
                    bullets=(
                        "sub and task are required.",
                        "ses, acq and run are optional.",
                        "Warnings do not block the flow, but they may mean some files need a different mapping.",
                    ),
                ),
                TutorialStep(
                    title="Preview before converting",
                    body=(
                        "Before running the conversion, review the preview table. If two source files resolve to the "
                        "same BIDS path, the mapping must be adjusted before continuing."
                    ),
                    bullets=(
                        "Right-click token chips to assign or reassign fields.",
                        "Add a custom token for constant values such as a shared task name.",
                        "Leave unused tokens unassigned.",
                    ),
                ),
            ),
        )
