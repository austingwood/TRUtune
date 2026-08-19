# TRUtune

MIT licensed. See [LICENSE](LICENSE).

TRUtune is a small Windows-friendly pyo application that shifts live stereo
system audio down by 0.3176665363 semitones, the equal-temperament difference
between 440 Hz and 432 Hz. With VB-CABLE installed, routing is automatic.

## Setup

The easiest installation is to double-click `install.bat`. It finds or installs
Python 3.11, creates the local virtual environment, installs pyo and WxPython,
validates the audio stack, and creates TRUtune shortcuts. The installer does not
need administrator access unless Windows Package Manager requires it for Python.

For a PowerShell installation without shortcuts, run:

```powershell
.\install.ps1 -SkipShortcuts
```

The equivalent manual setup is:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Select `.venv\Scripts\python.exe` as the VS Code Python interpreter. The
`.venv` folder is machine-specific and should not be copied to another computer.

## Use

List audio devices first:

```powershell
.\.venv\Scripts\python.exe .\engine.py --list-devices
```

Start with automatic device selection:

```powershell
.\.venv\Scripts\python.exe .\engine.py
```

TRUtune follows the Windows DirectSound default input and output devices. It
checks every two seconds and restarts its audio worker when Windows switches
from headphones to speakers, HDMI, or another default endpoint. The pyo GUI
is reopened for the new audio worker after these changes.

Keep Windows' desired playback device selected as the system default. TRUtune
will follow that default automatically; explicit device IDs are only needed
when you want to override the automatic behavior.

When VB-CABLE is installed, TRUtune automatically routes Windows playback into
VB-CABLE, processes `CABLE Output`, and restores the previous Windows playback
device when stopped.

Choose devices from the list when needed:

```powershell
.\.venv\Scripts\python.exe .\engine.py --input-device 1 --output-device 3
```

Device numbers are machine-specific. The explicit-device form disables
automatic selection for the sides you specify; use numbers from your own
`--list-devices` output.

The pyo control window opens by default and uses WxPython when installed. For
a terminal-only session, use `--no-gui` and stop with Ctrl+C. The pitch shift,
harmonizer window, and device polling interval are configurable with
`--shift`, `--window-size`, and `--poll-interval`; run `--help` to see all
options.

For a completely silent background run, double-click `start_trutune.vbs`. It
uses `pythonw.exe`, hides the console and pyo window, and continues following
Windows default-device changes. To see status while testing, run the normal
PowerShell command instead.

To open the normal visible pyo/WxPython control window, double-click
`start_trutune_gui.vbs`. The visible launcher is also added as `TRUtune GUI` in
the Start Menu during installation. Close the pyo window or use
`stop_trutune.vbs` when finished.

The background mode is transparent rather than concealed: the project files,
Python process, launchers, and `trutune.log` remain visible. The log records
startup, device changes, shutdown, and runtime errors.

To stop the hidden background process, double-click `stop_trutune.vbs`.

## USB use

Windows intentionally blocks programs from launching automatically just because
a USB drive was plugged in. This prevents removable drives from silently
executing software. Put the project folder on the USB drive and double-click
`USB_START_HERE.bat`; it installs or repairs the local `.venv`, validates the
dependencies, and starts TRUtune silently. On a new computer, Python 3.11 may
be installed through Windows Package Manager during this step.

Use `stop_trutune.vbs` from the same USB drive to stop the background process.

## Audio safety

Use headphones to avoid feedback. Begin with a low monitoring volume.
