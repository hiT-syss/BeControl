BeControl
=========

Control Windows games with hand gestures captured by your webcam. BeControl provides a live preview, a clickable hand selector, game profiles, and custom keyboard and mouse bindings.

**Use the portable application**

Extract the entire `BeControlExe` folder and open `BeControl.exe`. Keep the executable and its `_internal` folder together. The package includes its Python runtime and dependencies, so the recipient does not need to install Python. This release targets 64-bit Windows 10 and Windows 11.
Move that application to C/ProgramFilesX86

**Create your controls**

1. Open **Create game**, enter a project name, and create the profile.
2. Choose the red or green hand. Click the fingers you will keep extended. Click a selected finger again to fold it.
3. Select a keyboard key or mouse button. Add multiple keys to create a combination.
4. Choose **Press**, **Hold**, or **Repeat**, then save the binding.
5. Open **Play**, select the profile and an open game window, turn on the camera, and start control. Switch to the selected game.

For example, select only the ring finger, choose `shift`, and select **Hold**. Shift stays pressed while that gesture remains visible.

The preview is mirrored. The hand on the left of the image is red and the hand on the right is green. The selector supports all 16 combinations of the index, middle, ring, and little fingers. No selected fingers means a fist. All four selected fingers mean an open palm. Keep your hands upright for consistent recognition.

**Press** sends one short press when a gesture begins. **Hold** keeps the keys pressed while the gesture continues. **Repeat** sends repeated presses. Inputs are sent while the selected game window is in the foreground. Returning to BeControl or losing the camera feed releases held keys. Acceptance of simulated input depends on the game.

**Profiles**

The portable application saves profiles in `%LOCALAPPDATA%\BeControl\profiles.json`. It can import a legacy `profiller.json` file from the application directory. Running the source uses `profiller.json` beside `app.py`.

Existing user profiles are retained with the source project. The distributable application includes default bindings only. The default Spider-Man profile includes swing, jump, attack, dodge, web-strike, and optional horizontal wrist steering.

**Run the source**

Install 64-bit Python 3.11, then open `Start.cmd`. The launcher creates a virtual environment when necessary and installs packages from `requirements.txt`. The first dependency installation requires an internet connection.

You can also run these commands from `MainCode`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

**Build the portable package**

Build on 64-bit Windows with Python 3.11. From `MainCode`, install the build dependencies and run PyInstaller using the supplied specification.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath ..\BeControlExe-build --workpath ..\build-work BeControl.spec
```

PyInstaller produces an application folder containing `BeControl.exe` and `_internal`. Distribute the complete folder. Keep the supplied third-party license files with the application.

**Source files**

- `app.py` contains the application window, profiles, and control workflow.
- `kamera_gozlemci.py` processes camera frames and recognizes gestures.
- `oyun_tetikleyici.py` manages keyboard and mouse input for the selected window.
- `hand_picker.py` implements the clickable hand selector.
- `ui_widgets.py` contains the theme and shared interface widgets.
- `chevron.svg` provides the dropdown icon.
- `BeControl.spec` defines the Windows executable bundle.
- `Profiller.txt` You can import your profile with this file / temp file  
Third-party components retain their own licenses and copyright notices, supplied with the release.
