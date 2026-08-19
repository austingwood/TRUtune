Option Explicit

Dim service, process, commandLine
Set service = GetObject("winmgmts:\\.\root\cimv2")

For Each process In service.ExecQuery("Select * from Win32_Process where Name = 'pythonw.exe'")
    commandLine = LCase(CStr(process.CommandLine))
    If InStr(commandLine, "engine.py") > 0 And InStr(commandLine, "--background") > 0 Then
        process.Terminate
    End If
Next
