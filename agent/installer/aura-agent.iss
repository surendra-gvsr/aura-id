; agent/installer/aura-agent.iss
[Setup]
AppName=Aura ID Agent
AppVersion=0.1.0
AppPublisher=Aura ID, Inc.
DefaultDirName={autopf}\AuraID
DefaultGroupName=Aura ID
OutputDir=dist
OutputBaseFilename=AuraAgent-Setup-0.1.0
SetupIconFile=icons\aura.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Files]
Source: "..\dist\AuraAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Aura ID Agent"; Filename: "{app}\AuraAgent.exe"
Name: "{commonstartup}\Aura ID Agent"; Filename: "{app}\AuraAgent.exe"; Tasks: startup

[Tasks]
Name: "startup"; Description: "Start Aura ID Agent when Windows starts (recommended)"; Flags: checked

[Run]
Filename: "{app}\AuraAgent.exe"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Wipe keyring credential and AppData on uninstall — runascurrentuser ensures
; cleanup targets the installing user's profile, not the elevated admin account.
Filename: "cmd.exe"; Parameters: "/c cmdkey /delete:AuraID-Agent"; Flags: runhidden runascurrentuser
Filename: "cmd.exe"; Parameters: "/c rmdir /s /q ""{userappdata}\AuraID"""; Flags: runhidden runascurrentuser
