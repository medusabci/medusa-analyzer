from PySide6 import QtWidgets, QtCore
import os

class ExperimentTreeDialog(QtWidgets.QDialog):
    def __init__(self, rec_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select recordings to load")
        self.resize(600, 400)

        layout = QtWidgets.QVBoxLayout(self)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Experiment structure"])
        self.tree.setColumnCount(1)
        layout.addWidget(self.tree)

        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # Nodes od the tree
        self.populate_tree(rec_files)
        self.tree.itemChanged.connect(self.on_item_changed)


    def populate_tree(self, rec_files):
        '''Populates the tree with the directory structure of the recordings.'''
        root_items = {}

        for path in rec_files:
            parts = path.split(os.sep) # divide path into parts (for example: ["sub-01", "ses-01", "eeg", "task-rest", "R2.rec.bson"]
            current_parent = self.tree.invisibleRootItem()

            # Loop to create the tree structure with different nodes (one for folder and one for file)
            for i, part in enumerate(parts):
                key = os.sep.join(parts[:i+1])
                if key not in root_items: # if the item does not exist, create it
                    item = QtWidgets.QTreeWidgetItem([part])
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                    # item.setCheckState(0, QtCore.Qt.Checked if i == len(parts)-1 else QtCore.Qt.PartiallyChecked)
                    item.setCheckState(0, QtCore.Qt.Checked)
                    current_parent.addChild(item)
                    root_items[key] = item
                current_parent = root_items[key]

    def on_item_changed(self, item, column):
        """Propagate the check state to children."""
        state = item.checkState(0)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)

    def get_selected_files(self):
        """Iter through the tree and collect checked files. Returns a list of selected .rec.bson files. """
        selected = []
        def recurse(parent, path_parts):
            for i in range(parent.childCount()):
                item = parent.child(i)
                part = item.text(0)
                new_path = os.path.join(*path_parts, part)
                if item.childCount() == 0:  # file
                    if item.checkState(0) == QtCore.Qt.Checked and new_path.endswith(".rec.bson"):
                        selected.append(new_path)
                else:
                    recurse(item, path_parts + [part])
        recurse(self.tree.invisibleRootItem(), [])
        return selected