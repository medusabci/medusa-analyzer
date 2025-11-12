# What is MEDUSA© Analyzer

**MEDUSA© Analyzer** is the graphical user interface (GUI) component of the **MEDUSA© Ecosystem** — a modular framework for biomedical signal processing and analysis.  
It allows researchers, engineers, and clinicians to **load, preprocess, segment, and extract features** from various biosignals such as **EEG (electroencephalography)** and **ECG (electrocardiography)**.

---

## The MEDUSA© Ecosystem
MEDUSA© Analyzer works in conjunction with other components of the MEDUSA© framework:

| Component | Description |
|------------|--------------|
| **MEDUSA© Kernel** | The core Python backend that performs signal processing, filtering, segmentation, and feature extraction. |
| **MEDUSA© Platform** | A set of scripts and services that allow integration of MEDUSA© modules into larger pipelines or distributed systems. |
| **MEDUSA© Analyzer** | The graphical interface (GUI) that allows non-programmatic interaction with the MEDUSA© Kernel. |

All three modules are designed to be **interoperable**, using a common data format (`.rec.bson`) and a **semi-BIDS structure** for reproducible data organization.

---

## Main features
- 🧠 EEG and ECG feature extraction workflows  
- ⚙️ Configurable preprocessing (filters, CAR, Notch, Bandpass, etc.)  
- 🪄 Automatic epoch segmentation (by conditions or events)  
- 📈 Built-in feature computation: temporal, spectral, non-linear, connectivity metrics  
- 💾 Semi-BIDS compliant data saving and settings export (JSON)  
- 📊 Integrated plotting and statistical analysis tools  

---
!!! info "Note"
    This manual will guide you through every step — from installing the software to running complete analyses and exporting your results.
