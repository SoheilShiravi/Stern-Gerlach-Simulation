# Stern-Gerlach Simulation

An interactive simulation of sequential Stern-Gerlach experiments. You connect magnets along any axis, block output beams, and watch the final spin distribution change.

## How to run
You can Simply Run portable exe file for windows in Windows_exe
You need Python 3.11 or newer. In the project folder, create a virtual environment and install the dependencies (NumPy, Matplotlib and pytest):

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Start the application:

```powershell
.venv\Scripts\python main.py
```

A window opens with a z → x → z experiment loaded. Pick another setup from **Configuration**, click a magnet to change its direction, or click a colored port to block a beam or add a magnet.




