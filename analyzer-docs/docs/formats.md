# Supported Data Formats

MEDUSA© Analyzer uses specific file structures to ensure compatibility and reproducibility across the Medusa ecosystem.

---

## `.rec.bson` — Native MEDUSA© Format
This is the **core MEDUSA© format** used across the Analyzer, Kernel, and Platform.

- Binary BSON-based container for biosignals and metadata.  
- Stores sampling rate, channel info, events, and annotations.  
- Fully compatible with the MEDUSA© Kernel backend.

---

## BIDS (Brain Imaging Data Structure)
MEDUSA© Analyzer organizes processed data into a **semi-BIDS directory structure** to maintain consistency between sessions, subjects, and signal types.

All processed results are stored inside the folder selected by the user (referred to as `{selected_folder}`), following this hierarchy:

```text
{selected_folder}/
└── derivatives/
    ├── preprocessed/
    ├── segmented/
    └── parameters/
```
Each of these folders may include subfolders for the subject (`sub-XX`), session (`ses-YY`) and anatomy (`EEG`, `ECG`, or other signals).
For example:
```text
{selected_folder}/derivatives/
├── preprocessed/sub-01/ses-01/EEG/
├── segmented/sub-01/ses-01/EEG/
└── parameters/sub-01/ses-01/EEG/
```
---
### preprocessed/
Stores the `.rec.bson` files that contain the original recording object plus the preprocessed signal added to it.
These files preserve all metadata and structure from the original recording, allowing the preprocessed data to be reloaded later without repeating the preprocessing steps.
Example
```lua
sub-01_ses-01_band-delta.rec.bson
```
---
### segmented/
Contains `.mat` files with only the segmented signal (epochs) resulting from event or condition-based segmentation.

Each file corresponds to a specific band, condition, and event, and includes the variable:
```scss
epochs → (n_epochs × n_channels × n_samples)
```
Example:
```lua
sub-01_ses-01_band-alpha_cond-eyesclosed_event-stim01.mat
```
---
### parameters/
Stores one `.mat` file per parameter, band, condition, and event.
These files contain the numerical results of each metric (e.g., PSD, mean, variance, entropy, connectivity).

- **For PSDs**: variables psd and freqs are included. 
- **For other metrics**: the variable name matches the parameter label.

Example:
```lua
sub-01_param-psd_band-delta_cond-eyesClosed_event-stim01.mat
```
## Converting external data
If your raw data is not in `.rec.bson` format, you can use the **Converter** integrated into the MEDUSA© Analyzer main window.

It allows you to:

- Convert supported formats into `.rec.bson`
- Export to **BIDS-compatible** structure automatically

You will find detailed instructions on the Converter later in this manual, in the *Data Loader* section of the EEG and ECG experiments.