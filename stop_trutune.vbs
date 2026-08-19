Option Explicit

Dim service, process, commandLine
Set service = GetObject("winmgmts:\\.\root\cimv2")

Dim shell, projectDir, python
Set shell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
python = projectDir & "\.venv\Scripts\pythonw.exe"
shell.CurrentDirectory = projectDir
shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & projectDir & "\engine.py" & Chr(34) & " --restore-audio", 0, True

For Each process In service.ExecQuery("Select * from Win32_Process where Name = 'pythonw.exe'")
    commandLine = LCase(CStr(process.CommandLine))
    If InStr(commandLine, "engine.py") > 0 And InStr(commandLine, "--background") > 0 Then
        process.Terminate
    End If
Next
