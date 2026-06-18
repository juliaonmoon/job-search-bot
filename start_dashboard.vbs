Set WshShell = CreateObject("WScript.Shell")
Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
Set procs = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%dashboard.py%'")

If procs.Count = 0 Then
    cmd = "C:\Users\jules\AppData\Local\Programs\Python\Python312\python.exe " & _
          "C:\Users\jules\job-search-bot\dashboard.py"
    WshShell.Run cmd, 0, False
End If
