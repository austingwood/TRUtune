Option Explicit

Dim shell, projectDir, pythonw, script
Set shell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonw = projectDir & "\.venv\Scripts\pythonw.exe"
script = projectDir & "\engine.py"

shell.CurrentDirectory = projectDir
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & script & Chr(34) & " --background", 0, False
