# How to Set Up Medusa Analyzer

To get **Medusa Analyzer** up and running, follow these steps:

## 1. Clone the Medusa Analyzer repository
First, download the main branch of Medusa-Analyzer from our [GitHub repository](https://github.com/medusabci/medusa-analyzer) using [this link](https://github.com/medusabci/medusa-analyzer/archive/refs/heads/main.zip). After downloading it, extract it in an empty folder.

Alternatively, if you are an advanced user, you may want to clone the main branch onto your computer:

```bash
git clone -b main https://github.com/medusabci/medusa-analyzer.git
```

## 2. Download the Medusa Kernel (Analyzer branch)
Medusa Analyzer requires the `developers_analyzer` branch of the Medusa Kernel. Download it from its [GitHub Repository](https://github.com/medusabci/medusa-kernel/tree/developers_analyzer) using [this link](https://github.com/medusabci/medusa-kernel/archive/refs/heads/developers_analyzer.zip). After downloading it, extract it in an empty folder. 

Alternatively, if you are an advanced user, you may want to clone the branch:

```bash
git clone -b developers_analyzer https://github.com/medusabci/medusa-kernel.git
```

## 3. Download and install Python **3.13**

Download Python **3.13** using [this link](https://www.python.org/downloads/release/python-3130/). Install it in your computer.

## 4. Set up a Python virtual environment
Create a virtual environment: To do so:
- First, create a new empty folder and open it. 
- Then, click on the address bar at the top (it should show the folder path) and type cmd, then press Enter. This opens a command prompt in the folder.
- In the command window, type (this will create a new folder called venv inside your project folder containing the virtual environment): 
```bash
python -m venv venv
```
-Activate the environment:
 - On **Linux/Mac**:
    ```bash
    source venv/bin/activate # activate virtual environment
    ```
  - On **Windows**:
    ```bash
    source venv\Scripts\activate # activate virtual environment
      ```

## 4. Install the Medusa Kernel
Install the Medusa Kernel into your virtual environment by pointing `pip` to the kernel folder you just downloaded. For example:

```bash
pip install /path/to/medusa-kernel
```
Replace */path/to/medusa-kernel* with the actual path on your computer, e.g. /Users/john/projects/medusa-kernel/.)
