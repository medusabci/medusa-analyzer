from PySide6 import QtWidgets, QtCore
import os


class BaseTreeDialog(QtWidgets.QDialog):
    """
    Base class for tree-based file selection dialogs.
    Handles tree construction, checkbox propagation, and file collection.
    """

    def __init__(self, file_paths, title="Select files", header="Files", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(650, 450)

        # Layout setup
        layout = QtWidgets.QVBoxLayout(self)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels([header])
        layout.addWidget(self.tree)

        # Button box (OK / Cancel)
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # Populate tree
        self.populate_tree(file_paths)
        self.tree.itemChanged.connect(self.on_item_changed)

    # Methods meant to be overridden by subclasses if needed
    def should_include_path(self, path):
        """Return True if a file path should be included in the tree."""
        return True

    def is_valid_file(self, path):
        """Return True if a file should be considered as a selectable leaf."""
        return True

    # Common reusable functionality
    def populate_tree(self, file_paths):
        """Creates a hierarchical tree structure based on input file paths."""
        root_items = {}

        for path in sorted(file_paths):
            if not self.should_include_path(path):
                continue

            parts = path.split(os.sep)
            current_parent = self.tree.invisibleRootItem()

            for i, part in enumerate(parts):
                key = os.sep.join(parts[:i + 1])
                if key not in root_items:
                    item = QtWidgets.QTreeWidgetItem([part])
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                    # Default all nodes to checked
                    item.setCheckState(0, QtCore.Qt.Checked)
                    current_parent.addChild(item)
                    root_items[key] = item
                current_parent = root_items[key]

    def on_item_changed(self, item, column):
        """Propagate check state changes to all child nodes."""
        state = item.checkState(0)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)

    def get_selected_files(self):
        """Recursively collect all checked file paths."""
        selected = []

        def recurse(parent, path_parts):
            for i in range(parent.childCount()):
                item = parent.child(i)
                part = item.text(0)
                new_path = os.path.join(*path_parts, part)
                if item.childCount() == 0:
                    if item.checkState(0) == QtCore.Qt.Checked and self.is_valid_file(new_path):
                        selected.append(new_path)
                else:
                    recurse(item, path_parts + [part])

        recurse(self.tree.invisibleRootItem(), [])
        return selected

# Specialized implementations
class ExperimentTreeDialog(BaseTreeDialog):
    """
    Specialized tree dialog for experiment-based .rec.bson structures.
    Filters by experiment_id and only returns .rec.bson files.
    """

    def __init__(self, rec_files, experiment_id=None, parent=None):
        self.experiment_id = None
        if experiment_id:
            self.experiment_id = experiment_id.split("_")[0].lower()
        super().__init__(
            rec_files,
            title="Select recordings to load",
            header="Experiment structure",
            parent=parent,
        )

    def should_include_path(self, path):
        """Include only files relevant to the experiment_id if provided."""
        if not self.experiment_id:
            return True
        parts_lower = [p.lower() for p in path.split(os.sep)]
        return self.experiment_id in parts_lower

    def is_valid_file(self, path):
        """Only .rec.bson files are valid selections."""
        return path.endswith(".rec.bson")


# class GenericFileTreeDialog(BaseTreeDialog):
#     """
#     Generic file tree dialog for arbitrary file conversion.
#     Includes all detected files, regardless of extension.
#     """
#
#     def __init__(self, file_paths, parent=None):
#         super().__init__(
#             file_paths,
#             title="Select files to convert",
#             header="Detected file structure",
#             parent=parent,
#         )
#
#     def is_valid_file(self, path):
#         """All files are valid selections."""
#         return True
