# Run only in an explicitly disposable Windows Sandbox or owned QA VM.
# Input contains public installers only; output contains sanitized assertions.
param([string]$InputRoot='C:\RouterInput',[string]$OutputRoot='C:\RouterOutput')
$ErrorActionPreference='Stop'
$work='C:\RouterQA'
if($env:USERNAME -notin @('WDAGUtilityAccount','RouterQA')){throw 'Disposable QA account required.'}
if($env:USERNAME -eq 'RouterQA' -and $env:COMPUTERNAME -ne 'ROUTER-QA'){throw 'Owned QA guest required.'}
New-Item -ItemType Directory -Path $work -Force | Out-Null
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$checks=[ordered]@{}
$sequence=0
function Check([string]$Name,[bool]$Condition){
 $script:checks[$Name]=$Condition
 @{stage=$Name;passed=$Condition;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputRoot 'guest-progress.json') -Encoding UTF8
 if(-not $Condition){throw ('Check failed: '+$Name)}
}
function Run([string]$File,[string]$Arguments,[bool]$AllowFailure=$false){
 $script:sequence++
 $stdout=Join-Path $work ('stdout-'+$script:sequence+'.txt')
 $stderr=Join-Path $work ('stderr-'+$script:sequence+'.txt')
 $uninstallLog=$null
 if([IO.Path]::GetFileName($File) -eq 'unins000.exe'){
  $uninstallLog=Join-Path $work ('uninstall-'+$script:sequence+'.log')
  $Arguments+=' /LOG="'+$uninstallLog+'"'
 }
 $process=Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 $null=$process.Handle # PowerShell 5.1 otherwise loses redirected exit codes.
 if(-not $process.WaitForExit(180000)){Stop-Process -Id $process.Id -Force;throw 'QA process timeout.'}
 $result=[pscustomobject]@{code=$process.ExitCode;output=(Get-Content -LiteralPath $stdout -Raw -ErrorAction SilentlyContinue)}
 if($uninstallLog){
  $deadline=[DateTime]::UtcNow.AddSeconds(10)
  while(Test-Path -LiteralPath $uninstallLog){
   try {$stream=[IO.File]::Open($uninstallLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None);$stream.Dispose();break}
   catch {if([DateTime]::UtcNow -ge $deadline){throw 'Owned uninstall finalizer timeout.'};Start-Sleep -Milliseconds 100}
  }
 }
 if(-not $AllowFailure -and $result.code -ne 0){throw ('QA process failed: '+[IO.Path]::GetFileName($File)+' exit '+$result.code)}
 return $result
}
function WebViewPresent {
 foreach($base in @('HKCU:\Software\Microsoft\EdgeUpdate\Clients','HKLM:\Software\WOW6432Node\Microsoft\EdgeUpdate\Clients')){
  $record=Get-ItemProperty -LiteralPath (Join-Path $base '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}') -ErrorAction SilentlyContinue
  if($record.pv -and $record.pv -ne '0.0.0.0'){return $true}
 }
 return $false
}
function RunStandard([string]$File,[string]$Arguments,[Management.Automation.PSCredential]$Credential){
 $process=Start-Process -FilePath $File -ArgumentList $Arguments -Credential $Credential -LoadUserProfile -WindowStyle Hidden -PassThru
 $null=$process.Handle
 if(-not $process.WaitForExit(180000)){Stop-Process -Id $process.Id -Force;throw 'Standard-user QA timeout.'}
 if($process.ExitCode -ne 0){throw 'Standard-user QA process failed.'}
}
try {
 $expected=Get-Content -LiteralPath (Join-Path $InputRoot 'expected.json') -Raw | ConvertFrom-Json
 $latest=Join-Path $InputRoot 'latest.exe';$previous=Join-Path $InputRoot 'previous.exe'
 Check 'latestInstallerIntegrity' ((Get-FileHash -LiteralPath $latest -Algorithm SHA256).Hash -eq $expected.latest.sha256)
 Check 'previousInstallerIntegrity' ((Get-FileHash -LiteralPath $previous -Algorithm SHA256).Hash -eq $expected.previous.sha256)
 $app=Join-Path $env:LOCALAPPDATA 'Programs\Codex Model Router'
 $data=Join-Path $env:LOCALAPPDATA 'codex-model-router'
 Check 'initiallyClean' (-not (Test-Path -LiteralPath $app) -and -not (Test-Path -LiteralPath $data))
 $pythonCommand=Get-Command python.exe -ErrorAction SilentlyContinue
 $checks.developerPythonPresent=[bool]($pythonCommand -and $pythonCommand.Source -notmatch '\\WindowsApps\\')
 $checks.sourceCheckoutPresent=$false
 $checks.initialWebViewPresent=WebViewPresent
 $net=Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
 Check 'framework48Present' ($net.Release -ge 528040)
 if(-not $checks.initialWebViewPresent){
  $blocked=Run $latest '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $true
  Check 'silentMissingPrerequisiteBlocked' ($blocked.code -ne 0 -and -not (Test-Path -LiteralPath (Join-Path $app 'active.json')))
  $bootstrap=Join-Path $InputRoot 'MicrosoftEdgeWebview2Setup.exe'
  $signature=Get-AuthenticodeSignature -LiteralPath $bootstrap
  Check 'webViewMicrosoftSignature' ($signature.Status -eq 'Valid' -and $signature.SignerCertificate.Subject -match 'Microsoft Corporation')
  Run $bootstrap '/silent /install' | Out-Null
  Check 'webViewInstalled' (WebViewPresent)
 }
 Run $previous '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' | Out-Null
 $wrapper=Join-Path $app 'bin\codex-router.exe'
 $uninstallKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CodexModelRouter.Windows_is1'
 Check 'realUninstallRegistration' (Test-Path -LiteralPath $uninstallKey)
 $programs=[Environment]::GetFolderPath('Programs')
 $shortcuts=Join-Path $programs 'Codex Model Router'
 $shell=New-Object -ComObject WScript.Shell
 $link=$shell.CreateShortcut((Join-Path $shortcuts 'Codex Model Router.lnk'))
 Check 'startMenuMonitorShortcut' ($link.TargetPath -eq $wrapper -and $link.Arguments -eq '--status')
 $recovery=$shell.CreateShortcut((Join-Path $shortcuts ('Restaurar versi'+[char]0xf3+'n anterior.lnk')))
 Check 'startMenuRecoveryShortcut' ($recovery.TargetPath -eq $wrapper -and $recovery.Arguments -eq '--rollback-ui')
 Run $wrapper '--bootstrap' | Out-Null
 $config=Join-Path $data 'config.local.json';$original=[IO.File]::ReadAllBytes($config)
 $history=Join-Path $data 'state\history.jsonl';[IO.File]::WriteAllText($history,'{"event":"synthetic"}'+[Environment]::NewLine)
 Add-Type -AssemblyName System.Security
 $secret=Join-Path $data 'state\jev-vercel.secret'
 [IO.File]::WriteAllBytes($secret,[Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes('SYNTHETIC_QA_KEY'),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))
 Run $latest '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' | Out-Null
 $identity=(Run $wrapper '--identity').output | ConvertFrom-Json
 Check 'latestActiveIdentity' ($identity.version -eq $expected.latest.version -and $identity.build -eq $expected.latest.build)
 Check 'configPreservedOnUpgrade' ([Convert]::ToBase64String([IO.File]::ReadAllBytes($config)) -eq [Convert]::ToBase64String($original))
 # Real per-user setup under a disposable non-administrator account.
 $standardPassword=ConvertTo-SecureString ('Qa!'+[Guid]::NewGuid().ToString('N')) -AsPlainText -Force
 $standardUser=New-LocalUser -Name RouterQAUser -Password $standardPassword -AccountNeverExpires -PasswordNeverExpires
 Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $standardUser
 $administrators=@(Get-LocalGroupMember -SID 'S-1-5-32-544')
 Check 'standardAccountIsNotAdministrator' (-not ($administrators | Where-Object {$_.SID -eq $standardUser.SID}))
 $standardCredential=New-Object Management.Automation.PSCredential('ROUTER-QA\RouterQAUser',$standardPassword)
 try {
  RunStandard $latest '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $standardCredential
  $profile=Get-CimInstance Win32_UserProfile | Where-Object {$_.SID -eq [string]$standardUser.SID}
  $standardApp=Join-Path $profile.LocalPath 'AppData\Local\Programs\Codex Model Router'
  $standardActive=Get-Content -LiteralPath (Join-Path $standardApp 'active.json') -Raw | ConvertFrom-Json
  Check 'standardUserInstallWithoutElevation' ($standardActive.versionDirectory -eq ($expected.latest.version+'-'+$expected.latest.build))
  RunStandard (Join-Path $standardApp 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $standardCredential
  Check 'standardUserUninstallWithoutElevation' (-not (Test-Path -LiteralPath (Join-Path $standardApp 'bin\codex-router.exe')))
 } finally {$standardPassword.Dispose();Remove-LocalUser -SID $standardUser.SID}
 # Permission failure uses an owned guest-only directory and restores its ACL.
 $denied=Join-Path $work 'denied-install';New-Item -ItemType Directory -Path $denied | Out-Null
 $acl=Get-Acl -LiteralPath $denied
 $blockedAcl=Get-Acl -LiteralPath $denied
 $rule=New-Object Security.AccessControl.FileSystemAccessRule('Everyone','Write','ContainerInherit,ObjectInherit','None','Deny')
 $blockedAcl.AddAccessRule($rule);Set-Acl -LiteralPath $denied -AclObject $blockedAcl
 try {
  $blocked=Run $latest ('/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="'+$denied+'"') $true
  Check 'permissionFailurePreservesExistingInstall' ($blocked.code -ne 0 -and (Test-Path -LiteralPath $wrapper) -and -not (Test-Path -LiteralPath (Join-Path $denied 'active.json')))
 } finally {Set-Acl -LiteralPath $denied -AclObject $acl}
 # A small, fresh guest-only VHD exercises the setup disk-space guard.
 $smallDisk=Join-Path $work 'small-qa.vhd'
 $letter=@('R','S','T','U','V','W','X','Y','Z') | Where-Object {-not (Test-Path ($_+':\'))} | Select-Object -First 1
 if(-not $letter){throw 'No free QA drive letter.'}
 $diskScript=Join-Path $work 'diskpart-create.txt'
 @("create vdisk file=`"$smallDisk`" maximum=32 type=fixed","select vdisk file=`"$smallDisk`"",'attach vdisk','create partition primary','format fs=ntfs quick label=ROUTER-QA-SMALL',"assign letter=$letter") | Set-Content -LiteralPath $diskScript -Encoding ASCII
 Run "$env:WINDIR\System32\diskpart.exe" ('/s "'+$diskScript+'"') | Out-Null
 try {
  Check 'ownedSmallDiskMounted' (Test-Path ($letter+':\'))
  $blocked=Run $latest ('/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="'+$letter+':\CodexRouterQA"') $true
  Check 'diskFullPreservesExistingInstall' ($blocked.code -ne 0 -and (Test-Path -LiteralPath $wrapper) -and -not (Test-Path ($letter+':\CodexRouterQA\active.json')))
 } finally {
  @("select vdisk file=`"$smallDisk`"",'detach vdisk') | Set-Content -LiteralPath $diskScript -Encoding ASCII
  Run "$env:WINDIR\System32\diskpart.exe" ('/s "'+$diskScript+'"') | Out-Null
 }
 Run $wrapper '--rollback' | Out-Null
 $identity=(Run $wrapper '--identity').output | ConvertFrom-Json
 Check 'rollbackIdentity' ($identity.build -eq $expected.previous.build)
 Run $wrapper ('--activate-version '+$expected.latest.version+'-'+$expected.latest.build) | Out-Null
 $monitor=Join-Path $app ('versions\'+$expected.latest.version+'-'+$expected.latest.build+'\bin\codex-monitor.exe')
 Run $monitor ('--self-test --root "'+(Join-Path $work 'native-probe')+'"') | Out-Null
 $nativeReceipts=@(Get-ChildItem -LiteralPath (Join-Path $work 'native-probe') -Filter ui-review-checks.txt -Recurse)
 Check 'nativeWebViewAndCapsuleRegion' ($nativeReceipts.Count -eq 1 -and (Get-Content -LiteralPath $nativeReceipts[0].FullName -Raw).StartsWith('PASS:'))
 Start-Sleep -Seconds 1
 # Exercise native uninstaller against actual guest-only per-user registration.
 $environment=[Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Environment')
 $before='%SystemRoot%\synthetic-router.exe'
 $environment.SetValue('CODEX_CLI_PATH',$wrapper,[Microsoft.Win32.RegistryValueKind]::String)
 $receipt=[ordered]@{schema=1;platform='win32';status='registered';wrapper=$wrapper;previous=@{value=$before;kind=2}}
 [IO.File]::WriteAllText((Join-Path $data 'state\desktop-integration.json'),($receipt | ConvertTo-Json -Depth 3),(New-Object Text.UTF8Encoding($false)))
 $environment.SetValue('CODEX_CLI_PATH','synthetic-foreign.exe',[Microsoft.Win32.RegistryValueKind]::String)
 $blocked=Run (Join-Path $app 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $true
 Check 'foreignConnectionBlocksUninstall' ($blocked.code -ne 0 -and (Test-Path -LiteralPath $wrapper) -and $environment.GetValue('CODEX_CLI_PATH') -eq 'synthetic-foreign.exe')
 $environment.SetValue('CODEX_CLI_PATH',$wrapper,[Microsoft.Win32.RegistryValueKind]::String)
 Run (Join-Path $app 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' | Out-Null
 Check 'priorEnvironmentRestored' ($environment.GetValue('CODEX_CLI_PATH',$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) -eq $before -and $environment.GetValueKind('CODEX_CLI_PATH') -eq [Microsoft.Win32.RegistryValueKind]::ExpandString)
 $environment.Close()
 Check 'uninstallRegistryRemoved' (-not (Test-Path -LiteralPath $uninstallKey))
 Check 'startMenuRemoved' (-not (Test-Path -LiteralPath (Join-Path $shortcuts 'Codex Model Router.lnk')))
 Check 'historyRetained' ((Get-Content -LiteralPath $history -Raw).Contains('synthetic'))
 Check 'keyRetainedAndDecryptable' ([Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($secret),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)) -eq 'SYNTHETIC_QA_KEY')
 Run $latest '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' | Out-Null
 Check 'reinstallPreservesConfig' ([Convert]::ToBase64String([IO.File]::ReadAllBytes($config)) -eq [Convert]::ToBase64String($original))
 Run (Join-Path $app 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' | Out-Null
 $result=[ordered]@{passed=$true;checks=$checks;version=$expected.latest.version;build=$expected.latest.build;osVersion=[Environment]::OSVersion.Version.ToString();liveInference=$false;ownerDataUsed=$false}
} catch {
 $result=[ordered]@{passed=$false;checks=$checks;errorType=$_.Exception.GetType().Name;failedCheck=[string]$_.Exception.Message;liveInference=$false;ownerDataUsed=$false}
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot 'clean-windows-result.json') -Encoding UTF8
