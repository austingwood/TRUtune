Option Explicit

Dim service, process, commandLine, projectDir
Set service = GetObject("winmgmts:\\.\root\cimv2")
projectDir = LCase(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))

' Stop both the visible GUI supervisor and its worker before restoring Windows audio.
For Each process In service.ExecQuery("Select * from Win32_Process where Name = 'python.exe' or Name = 'pythonw.exe'")
    commandLine = LCase(CStr(process.CommandLine))
    If InStr(commandLine, projectDir) > 0 And InStr(commandLine, "engine.py") > 0 Then
        process.Terminate
    End If
Next

Dim shell, python
Set shell = CreateObject("WScript.Shell")
python = projectDir & "\.venv\Scripts\pythonw.exe"
shell.CurrentDirectory = projectDir
shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & projectDir & "\engine.py" & Chr(34) & " --restore-audio", 0, True
