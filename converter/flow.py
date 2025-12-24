from PySide6 import QtWidgets
from converter.converters import CONVERTERS
from converter.utils import do_conversion

def on_next_click(controller):
    """
    Controls the next (and finish) button behaviour
    """
    # idx is the index of the previous widget
    data_loader = controller.view.stackedWidget.widget(0)
    # Get the converter widget
    converter = controller.view.stackedWidget.widget(1)

    # Close the app
    if controller.view.nextButton.text() == "Close":
        controller.view.close()
        return


    # If the button text is "Run conversion", trigger the conversion process
    if controller.view.nextButton.text() == "Run conversion":
        if converter.subjectLabel.text() == '' or converter.recordingLabel.text() == '':
            QtWidgets.QMessageBox.critical(
                controller.view,
                "Naming violation",
                "Both Subject and Recording names must be defined. Verify the naming structure table and try again.",
            )
            return

        do_conversion(controller, data_loader.controller.selected_files, data_loader.converterBox.currentText(),
                      converter.controller.names_idx)

        # Trigger the conversion process
        print('Convertidooo')
        return

    # Get the selected file extensions, and the associated available converters
    selected_exts = ['.' + data_loader.filelistWidget.item(i).text().split('.')[-1]
                     for i in range(data_loader.filelistWidget.count())]
    all_converters = list(CONVERTERS.keys())
    available_converters = list(set(all_converters) & set(selected_exts))
    available_converters_names = [
        conv["name"]
        for ext in available_converters
            for conv in CONVERTERS[ext]
    ]

    # Populate the table with the name structure
    converter.controller.populate_name_structure_table()

    # Set the current index to the converter widget
    controller.view.stackedWidget.setCurrentIndex(1)

    # Modify button states
    controller.view.backButton.setDisabled(False)
    controller.view.nextButton.setText("Run conversion")


def on_back_click(controller):
    """
    Controls the back button behaviour
    """
    # Get the current index
    idx = controller.view.stackedWidget.currentIndex()
    # Set the current index to the previous widget
    controller.view.stackedWidget.setCurrentIndex(idx - 1)

    # Modify button states
    controller.view.backButton.setDisabled(True)
    controller.view.nextButton.setText("Next step")
