from PySide6 import QtWidgets

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """

    view.main_module.controller.param_selection = view.controller.param_selection

    if not view.main_module.controller.param_selection:
        QtWidgets.QMessageBox.warning(
            view,
            "Parameter Selection Error",
            f"Parameter selection failed. Please ensure that you have selected at least one parameter."
        )
        return False

    # Filter files based on selected groups, data and parameters
    view.main_module.controller.filtered_files = filter_files_by_selection(view)


    return True

def filter_files_by_selection(view):

    # Get the files
    files = view.main_module.controller.all_files
    groups = view.main_module.controller.group_assignment
    groups_concatenated = [x for current_group in groups.values() for x in current_group]
    data = view.main_module.controller.data_assignment
    params = view.main_module.controller.param_selection

    # For each file from all files...
    filtered_files = []
    for f in files:

        # Filter out the files that do not match the group assignments
        pass_group = False
        for included_element in groups_concatenated:
            # Split the element with '_'
            parts = included_element.split('_')

            # Check if all parts are present in the file name
            all_present = True
            for part in parts:
                if part not in f:
                    all_present = False
                    break
            # If not all present, skip to the next file
            if not all_present:
                continue
            # If present, mark as passed and break the loop
            else:
                pass_group = True
                break
        # If no group matched, skip to the next file
        if not pass_group:
            continue


        # Filter out the files that do not match the data assignments
        pass_data = False
        for included_element in data:
            # Split the element with '_'
            parts = included_element.split('_')

            # Check if all parts are present in the file name
            all_present = True
            for part in parts:
                if part not in f:
                    all_present = False
                    break
            # If not all present, skip to the next file
            if not all_present:
                continue
            # If present, mark as passed and break the loop
            else:
                pass_data = True
                break
        # If no group matched, skip to the next file
        if not pass_data:
            continue

        # Filter out the files that do not match the parameter selections
        if not any(param in f for param in params):
            continue

        # If all filters passed, add the file to the filtered list
        filtered_files.append(f)

    return filtered_files
