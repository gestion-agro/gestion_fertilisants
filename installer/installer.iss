[Setup]
AppName=Gestion Fertilisant
AppVersion=1.0.0
DefaultDirName={pf}\GestionFertilisant
DefaultGroupName=Gestion Fertilisant
OutputBaseFilename=GestionFertilisant_Setup
OutputDir=Output
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\Gestion_Fertilisant_windows.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Gestion Fertilisant"; Filename: "{app}\Gestion_Fertilisant_windows.exe"
Name: "{commondesktop}\Gestion Fertilisant"; Filename: "{app}\Gestion_Fertilisant_windows.exe"

[Run]
Filename: "{app}\Gestion_Fertilisant_windows.exe"; Flags: nowait postinstall skipifsilent
