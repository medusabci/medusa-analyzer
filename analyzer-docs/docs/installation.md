# How to Set Up MEDUSA© Analyzer

To get **MEDUSA© Analyzer** up and running, follow these steps:

## 1. Clone the MEDUSA© Analyzer repository
First, download the main branch of MEDUSA©-Analyzer from our [GitHub repository](https://github.com/medusabci/medusa-analyzer) using [this link](https://github.com/medusabci/medusa-analyzer/archive/refs/heads/main.zip). After downloading it, extract it in an empty folder.
Suggestion: Extract it into the following folder **C:/Users/Your_Useer/Documents/Medusa_Analyzer/Analyzer**

Alternatively, if you are an advanced user, you may want to clone the main branch onto your computer:

```bash
git clone -b main https://github.com/medusabci/medusa-analyzer.git
```

## 2. Download the MEDUSA© Kernel (developers branch)
MEDUSA© Analyzer requires the `developers` branch of the MEDUSA© Kernel. Download it from its [GitHub Repository](https://github.com/medusabci/medusa-kernel/tree/developers_analyzer) using [this link](https://github.com/medusabci/medusa-kernel/archive/refs/heads/developers_analyzer.zip). After downloading it, extract it in an empty folder. 
Suggestion: Extract it into the following folder **C:/Users/Your_Useer/Documents/Medusa_Analyzer/Kernel**

Alternatively, if you are an advanced user, you may want to clone the branch:

```bash
git clone -b developers https://github.com/medusabci/medusa-kernel.git
```

## 3. Download and install Python **3.13**

Download Python **3.13** using [this link](https://www.python.org/downloads/release/python-3130/). Install it in your computer.

## 4. Set up a Python virtual environment
Create a virtual environment. To do so:

- **4.1** Navigate to the folder you have crated in step 1. If you have followed our suggestions, it should be in ```C:/Users/Your_Useer/Documents/Medusa_Analyzer/Analyzer```

- **4.2** Then, click on the address bar at the top (it should show the folder path) and type ```cmd```, then press Enter. This opens a command prompt in the folder. 

- **4.3** In the command window, type: ```python -m venv venv```.
This will create a new folder called venv inside your project folder containing the virtual environment
- **4.3**  Activate the environment: ```venv/Scripts/activate```.

## 5. Install the MEDUSA© Kernel dependencies
Install the MEDUSA© Kernel into your virtual environment. In the CMD window type:

```bash
pip install /path/to/medusa-kernel
```
Replace ```/path/to/medusa-kernel``` with the path to the folder you created in step 2. If you have followed our suggestions it should be e.g. ```C:/Users/Your_Useer/Documents/Medusa_Analyzer/Kernel```).
After activating your virtual environment, install all dependencies with one command:
```bash
pip install -r requirements.txt
```


