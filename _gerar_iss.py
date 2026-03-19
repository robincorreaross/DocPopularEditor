from version import APP_VERSION

# Gera o DocPopularEditor.iss para o Inno Setup (ASCII, sem BOM)
template = """; DocPopularEditor.iss - Script do instalador (Inno Setup 6)

[Setup]
AppId={{9B880DD-1234-4567-89AB-CDEF01234567}}
AppName=DocPopular Editor
AppVersion={{VERSION}}
AppVerName=DocPopular Editor v{{VERSION}}
AppPublisher=DocPopular Team
AppPublisherURL=https://github.com/robincorreaross/DocPopularEditor
AppSupportURL=https://github.com/robincorreaross/DocPopularEditor/issues
AppUpdatesURL=https://github.com/robincorreaross/DocPopularEditor/releases
DefaultDirName={autopf}\\DocPopularEditor
DefaultGroupName=DocPopular Editor
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=DocPopularEditor_Setup_v{{VERSION}}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
AllowNoIcons=yes
UninstallDisplayName=DocPopular Editor
UninstallDisplayIcon={app}\\_internal\\assets\\icon.ico
SetupIconFile=assets\\icon.ico

[Languages]
Name: "english"; MessagesFile: "installer_meta\\Default.isl"
Name: "brazilianportuguese"; MessagesFile: "installer_meta\\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";   Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos:"
Name: "startmenuicon"; Description: "Criar atalho no Menu Iniciar";     GroupDescription: "Atalhos:"

[Files]
Source: "dist\\DocPopularEditor\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\\DocPopular Editor";       Filename: "{app}\\DocPopularEditor.exe"; Tasks: desktopicon
Name: "{group}\\DocPopular Editor";             Filename: "{app}\\DocPopularEditor.exe"; Tasks: startmenuicon
Name: "{group}\\Desinstalar DocPopular Editor"; Filename: "{uninstallexe}";         IconFilename: "{app}\\_internal\\assets\\icon.ico"; Tasks: startmenuicon

[Run]
Filename: "{app}\\DocPopularEditor.exe"; Description: "Abrir DocPopular Editor agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
"""

iss = template.replace("{{VERSION}}", APP_VERSION)

outfile = "DocPopularEditor.iss"
with open(outfile, "w", encoding="ascii") as f:
    f.write(iss)

print(f"Gerado: {outfile} (v{APP_VERSION})")
