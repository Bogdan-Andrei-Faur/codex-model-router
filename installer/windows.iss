; Per-user setup. Data and Desktop activation are managed by the application.
#ifndef Payload
  #error Payload must point to an isolated package tree
#endif
[Setup]
#ifdef TestDataRoot
AppId=CodexModelRouter.Windows.Fixture
CreateUninstallRegKey=no
#else
AppId=CodexModelRouter.Windows
#endif
AppName=Codex Model Router
AppVersion={#ProductVersion}
AppPublisher=Bogdan Andrei Faur
DefaultDirName={localappdata}\Programs\Codex Model Router
DefaultGroupName=Codex Model Router
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19041
DisableProgramGroupPage=yes
DisableDirPage=yes
UsePreviousAppDir=yes
CloseApplications=no
RestartApplications=no
RestartIfNeededByRun=no
UninstallRestartComputer=no
SetupMutex=Local\CodexModelRouterSetup
WizardStyle=modern dark
SetupIconFile={#Payload}\versions\{#VersionDirectory}\Resources\assets\codex.ico
UninstallDisplayIcon={app}\bin\codex-router.exe
OutputDir={#Output}
OutputBaseFilename=codex-model-router-{#ProductVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
#ifdef PublisherSignTool
SignTool={#PublisherSignTool}
SignedUninstaller=yes
#endif
[Languages]
Name: spanish; MessagesFile: compiler:Languages\Spanish.isl
Name: english; MessagesFile: compiler:Default.isl
[Files]
Source: "{#Payload}\bin\codex-router.exe"; Flags: dontcopy
Source: "{#Bootstrapper}"; DestName: "MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy
Source: "{#Payload}\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "{#Payload}\versions\{#VersionDirectory}\*"; DestDir: "{app}\versions\{#VersionDirectory}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Codex Model Router"; Filename: "{app}\bin\codex-router.exe"; Parameters: "--status"
Name: "{group}\Restaurar versión anterior"; Filename: "{app}\bin\codex-router.exe"; Parameters: "--rollback-ui"
Name: "{group}\Desinstalar Codex Model Router"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\bin\codex-router.exe"; Parameters: "--status"; Description: "Abrir Codex Model Router"; Flags: nowait postinstall skipifsilent
[UninstallDelete]
Type: files; Name: "{app}\active.json"
Type: files; Name: "{app}\active.previous.json"
Type: files; Name: "{app}\active.failed.json"
Type: files; Name: "{app}\activation.lock"
[Code]
function DataArguments: String;
begin
#ifdef TestDataRoot
  Result := '--data-root "{#TestDataRoot}" ';
#else
  Result := '';
#endif
end;
function WebViewPresent: Boolean;
var V: String;
begin
  Result := (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM32, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Release: Cardinal; ExitCode: Integer; Helper, Bootstrap: String;
begin
  Result := '';
  if not RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) or (Release < 528040) then begin
    Result := 'Se necesita .NET Framework 4.8. Instálalo desde Microsoft y vuelve a ejecutar este instalador.'; Exit;
  end;
  ExtractTemporaryFile('codex-router.exe');
  Helper := ExpandConstant('{tmp}\codex-router.exe');
  if not Exec(Helper, '--check-installation "' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) then begin
    Result := 'Hay componentes en uso. Termina las tareas, cierra Codex y el monitor y vuelve a intentarlo. No se ha cerrado ninguna aplicación.'; Exit;
  end;
  if not WebViewPresent then begin
    if WizardSilent or (MsgBox('Falta Microsoft Edge WebView2. Se descargará desde Microsoft y se necesita Internet. ¿Continuar?', mbConfirmation, MB_YESNO) <> IDYES) then begin
      Result := 'Instala Microsoft Edge WebView2 Runtime y vuelve a intentarlo.'; Exit;
    end;
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    Bootstrap := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
    if not Exec(Helper, '--verify-webview2 "' + Bootstrap + '"', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) then begin
      Result := 'No se pudo verificar el instalador de Microsoft. No se ha ejecutado.'; Exit;
    end;
    if not Exec(Bootstrap, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) or not WebViewPresent then
      Result := 'WebView2 no pudo instalarse. Tus datos y la instalación anterior se conservan.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var ExitCode: Integer;
begin
  if CurStep = ssPostInstall then
    if not Exec(ExpandConstant('{app}\bin\codex-router.exe'), DataArguments + '--activate-version {#VersionDirectory}', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) then
      RaiseException('La nueva versión no pudo activarse. La versión anterior y tus datos se conservan.');
end;

function InitializeUninstall: Boolean;
var ExitCode: Integer; Helper: String;
begin
  Helper := ExpandConstant('{app}\bin\codex-router.exe');
  Result := Exec(Helper, '--check-uninstall "' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
  if not Result then begin
    SuppressibleMsgBox('Cierra Codex y el monitor cuando terminen las tareas antes de desinstalar. No se ha cerrado ninguna aplicación.', mbError, MB_OK, IDOK); Exit;
  end;
  Result := Exec(Helper, DataArguments + '--remove-integration-json', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
  if not Result then SuppressibleMsgBox('No se pudo retirar nuestra conexión. Se ha conservado la instalación para permitir su recuperación.', mbError, MB_OK, IDOK);
end;
