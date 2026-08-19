Option Explicit

Dim shell, projectDir, python, script
Set shell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
python = projectDir & "\.venv\Scripts\pythonw.exe"
script = projectDir & "\engine.py"

shell.CurrentDirectory = projectDir
shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & script & Chr(34), 1, False