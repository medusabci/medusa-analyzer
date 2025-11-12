
---
# How to run MEDUSA© Analyzer
Once the installation is complete, follow these steps to start **MEDUSA© Analyzer**.

---Si
## 1. Activate the virtual environment
From your Analyzer folder (```C:/Users/Your_Useer/Documents/Medusa_Analyzer/Analyzer```), 
open a **command prompt** as in step 4 of the installation guide and run:
```bash
venv/Scripts/activate
```
You should see ```(venv)``` at the beginning of the command line, indicating that the environment is active.

## 2. Launch the application
Run de following command:
````bash
python main_window.py
````
This will launch the MEDUSA© Analyzer interface. 

## When the Analyzer starts 
You will see the **Main Interface**, divided intro two main sections: 
- **Top section** - selection of available experiments (EEG/ECG)
- **Bottom section** - access to Plots and Statistical Analysis

!!! info "Tip"
    You can pin the CMD window open while using the Analyzer — it will display logs and debugging information from the backend.