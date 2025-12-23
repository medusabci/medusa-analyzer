def do_conversion(controller, files, converter, output_path, names_idx, elements):

    # Create the thread
    output_path = _select_output_directory(controller)
    experiment_type = getattr(controller.view.main_window, "selected_experiment", "").split('_')[0].upper()
    controller.view.worker = ConverterWorker(files, converter, output_path, names_idx, elements)

    # Connect the signals to the functions
    controller.view.worker.progress.connect(controller.view.convertProgressBar.setValue, type=Qt.QueuedConnection)
    controller.view.worker.log.connect(controller.view._log_message, type=Qt.QueuedConnection)

    # Clean up when done
    controller.view.worker.finished.connect(controller.view.worker.deleteLater)

    # When the worker is finished, enable the button and change its text
    def on_finished(converted_files, error_found):
        if error_found:
            QtWidgets.QMessageBox.critical(
                controller.view,
                "Conversion Error",
                f"❌ An unexpected error occurred during conversion:\n\n"
            )
        else:
            QtWidgets.QMessageBox.information(
                controller.view,
                "Conversion Complete",
                f"✅ Successfully converted {len(converted_files)} file(s)."
            )

    def _select_output_directory(controller):
        """Ask the user for output directory and prepare folders."""
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Select output path")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(
            f"Select a folder to save files in BIDS format.\n\n"
            "Original files will not be modified."
        )
        msg.exec()

        output_path = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select destination folder for converted files (BIDS root)"
        )
        if not output_path:
            controller.view._log_message("🚫 Conversion cancelled (no output folder selected).")
            return None

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        controller.view._log_message(f"📁 Output path selected: {output_dir}")
        return output_dir


def _log_conversion_summary(counters, worker):
    """Print final summary."""
    summary = (
        "<hr><b>Summary:</b><br>"
        f"🟢 Converted: {counters['converted']} file(s)<br>"
        f"🔵 Accepted (already correct): {counters['accepted']} file(s)<br>"
    )
    if counters["skipped"]:
        summary += f"⚠️ Skipped: {counters['skipped']} file(s)"
    worker.log.emit(summary)


# Worker class to run the converter in a separate thread
class ConverterWorker(QThread):
    # Emit when the processing is finished
    finished = Signal(list, bool)
    # For updating the progress bar in the GUI
    progress = Signal(int)
    # For updating log messages in the GUI
    log = Signal(str)

    def __init__(self, files, converter, output_dir, names_idx, elements):
        super().__init__()
        self.files = files
        self.converter = converter
        self.output_dir = output_dir
        self.names_idx = names_idx
        self.elements = elements

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        error_found = False
        try:
            # Call the main pipeline function
            converted_files = self.converter_main(self.files, self.converter, self.output_dir, self.names_idx, self.elements)
        except Exception as e: # if error
            self.log.emit(f"Error in conversion: {e}")
            converted_files = []
            error_found = True
        self.finished.emit(converted_files, error_found)

    def converter_main(self, files, converter, output_dir, names_idx, elements):
        """
        Convert different file types to .rec.bson format and arrange them in BIDS structure.
        - If a file is .rec.bson and already contains data.marks -> skip.
        - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
        - For other supported extensions -> run their converters.
        """

        if not output_dir:
            return []

        counters = {"converted": 0, "accepted": 0, "skipped": 0}
        total_steps = len(files)

        converter_func = get_converter_function_by_name(converter)
        converter_func(parameters)

        converted_files = []

        for i, file in enumerate(files):
            bids_path = self.generate_bids_name(file, names_idx, elements)

            file, result = self.process_file(file, bids_path, converter, self)
            counters[result] += 1
            if result == "accepted":
                converted_files.append(file)

            self.progress.emit(int((i + 1) / total_steps * 100))

        self.progress.emit(100)
        _log_conversion_summary(counters, self)
        return converted_files


    def get_converter_function_by_name(name):
        for converters in CONVERTERS.values():
            for conv in converters:
                if conv["name"] == name:
                    return conv["function"]
        return None


    def process_file(file, bids_name, converter, worker):

        bids_name = Path(bids_name)
        bids_path = bids_name.parent
        bids_path.mkdir(parents=True, exist_ok=True)
        ext = ''.join(p.suffixes)

        if ext == ".rec.bson":  # Check if the rec.bson file is valid
            """Handle existing .rec.bson files."""
            try:
                data = Recording.load(file)
            except Exception as e:
                worker.log.emit(f"❌ <b>{file}</b> → Error loading .rec.bson: {e}")
                return [], 'skipped'

            if getattr(data, "marks", None):
                shutil.copy2(file, bids_name)
                worker.log.emit(f"ℹ️ {file} → Already contains 'marks', skipped conversion.")
                return file, 'accepted'

        worker.log.emit(f"⚙️ {file} → Converting...")
        try:
            # Run the converter
            result = converter(file, bids_name, worker)
            if not result:
                raise ValueError("Conversion function returned None or failed.")

            worker.log.emit(f"✅ {file} → Converting successful.")
            return file, 'converted'
        except Exception as e:
            worker.log.emit(f"❌ {file} → Error during conversion: {e}")
            return [], 'skipped'


    def generate_bids_name(file, names_idx):
        """
        Generate BIDS-compliant filenames based on user-defined elements and indices.
        """
        elements = [e for e in re.split(r"[\\/ _]+", file) if e]

        # Extract the name elements
        subject_name = ''.join(elements[names_idx["Subject"]])
        if names_idx["Session"]:
            session_name = ''.join(elements[names_idx["Session"]])
        recording_name = ''.join(elements[names_idx["Recording"]])
        if names_idx["Task"]:
            task_name = ''.join(elements[names_idx["Task"]])

        # Set the folder structure
        bids_name = ['sub-' + subject_name + '/']
        if names_idx["Session"]:
            bids_name.append('ses-' + session_name + '/')
        bids_name.append('eeg/')
        # Set the name structure
        bids_name.append('sub-' + subject_name)
        if names_idx["Session"]:
            bids_name.append('_ses-' + session_name)
        if names_idx["Task"]:
            bids_name.append('_task-' + task_name)
        bids_name.append('_rec-' + recording_name)

        return bids_name