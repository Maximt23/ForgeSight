Set WshShell = WScript.CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
strScriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

Set oShellLink = WshShell.CreateShortcut(strDesktop & "\CadOwl.lnk")
oShellLink.TargetPath = strScriptDir & "\CadOwl.bat"
oShellLink.WorkingDirectory = strScriptDir
oShellLink.Description = "CadOwl - CAD to SiteOwl Converter"
oShellLink.WindowStyle = 7
oShellLink.Save

WScript.Echo "Desktop shortcut created!"
