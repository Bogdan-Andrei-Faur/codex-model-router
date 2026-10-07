# Recover only the QA disk prepared by prepare_windows_qa_vm.ps1.
# BCDBoot runs inside the disposable VM, never against the host's live BCD store.
param([Parameter(Mandatory=$true)][string]$Workspace,
      [Parameter(Mandatory=$true)][string]$Iso,
      [Parameter(Mandatory=$true)][string]$IsoSha256,
      [switch]$ResumePreparedMedia,[switch]$ResumeExistingVm,
      [ValidateRange(2,4)][int]$StartupMemoryGiB=4)
$ErrorActionPreference='Stop'
Import-Module Hyper-V
$Workspace=[IO.Path]::GetFullPath($Workspace);$Iso=[IO.Path]::GetFullPath($Iso)
$main=Join-Path $Workspace 'router-qa.vhdx'
$pe=Join-Path $Workspace 'router-qa-winpe.vhdx'
$mount=Join-Path $Workspace 'pe-mount'
$status=Join-Path $Workspace 'vm-progress.json'
function Progress([string]$Stage){@{stage=$Stage;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8}
function Dism([string]$Arguments,[string]$Label){
 # DISM's mount servicing child can outlive the command. -Wait waits the whole
 # process tree and deadlocks until a later unmount; wait on the parent only.
 $process=Start-Process -FilePath "$env:WINDIR\System32\dism.exe" -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Workspace ($Label+'-stdout.private.log')) -RedirectStandardError (Join-Path $Workspace ($Label+'-stderr.private.log'))
 $null=$process.Handle # Cache before exit: Windows PowerShell 5.1 bug #5421.
 if(-not $process.WaitForExit(300000)){throw ('Owned image operation timed out: '+$Label)}
 if($process.ExitCode -ne 0){throw ('Owned WinPE image operation failed: '+$Label)}
}
$mountedMain=$false;$mountedPe=$false;$mountedIso=$false;$mountedWim=$false
try {
 Progress 'verify-winpe-recovery-inputs'
 if((Get-FileHash -LiteralPath $Iso -Algorithm SHA256).Hash -ne $IsoSha256){throw 'Official media integrity mismatch.'}
 $credential=Get-Content -LiteralPath (Join-Path $Workspace 'guest-credential.private.json') -Raw | ConvertFrom-Json
 $vmName=[string]$credential.vmName;$credential=$null
 if($vmName -notmatch '^CodexRouter-QA-[0-9a-f]{8}$'){throw 'Owned QA VM name required.'}
 $existingVm=Get-VM -Name $vmName -ErrorAction SilentlyContinue
 if($existingVm){
  $drives=@(Get-VMHardDiskDrive -VMName $vmName)
  if(-not $ResumeExistingVm -or $existingVm.State -ne 'Off' -or $drives.Count -ne 2 -or @($drives | Where-Object {$_.Path -in @($main,$pe)}).Count -ne 2){throw 'Stopped owned two-disk QA VM required.'}
 }
 $existing=Test-Path -LiteralPath $pe
 if($existing -and -not $ResumePreparedMedia){throw 'Recovery disk already exists; never replace it.'}
 $mainVhd=Mount-VHD -Path $main -Passthru;$mountedMain=$true
 $mainDisk=Get-Disk -Number $mainVhd.DiskNumber
 if((Get-VHD -Path $main).DiskNumber -ne $mainDisk.Number -or $mainDisk.Size -ne 64GB -or $mainDisk.IsBoot -or $mainDisk.IsSystem){throw 'Main QA disk ownership mismatch.'}
 $mainWindows=@(Get-Partition -DiskNumber $mainDisk.Number | Where-Object {$_.GptType -eq '{ebd0a0a2-b9e5-4433-87c0-68b6b72699c7}'})
 $mainEfi=@(Get-Partition -DiskNumber $mainDisk.Number | Where-Object {$_.GptType -eq '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}'})
 if($mainWindows.Count -ne 1 -or $mainEfi.Count -ne 1){throw 'Owned main partitions required.'}
 $mainRoot=$mainWindows[0].DriveLetter+':\'
 if(-not (Test-Path -LiteralPath (Join-Path $mainRoot 'RouterInput\expected.json'))){throw 'Prepared QA inputs required.'}
 [IO.File]::WriteAllText((Join-Path $mainRoot 'RouterInput\qa-owned.marker'),'codex-router-owned-qa')
 $guestTest=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests\windows_clean_guest.ps1'
 Copy-Item -LiteralPath $guestTest -Destination (Join-Path $mainRoot 'RouterInput\windows_clean_guest.ps1') -Force
 Dismount-VHD -Path $main;$mountedMain=$false
 Progress 'create-owned-winpe-media'
 if(-not $existing){New-VHD -Path $pe -SizeBytes 2GB -Dynamic | Out-Null}
 $peVhd=Mount-VHD -Path $pe -Passthru;$mountedPe=$true
 $peDisk=Get-Disk -Number $peVhd.DiskNumber
 if((Get-VHD -Path $pe).DiskNumber -ne $peDisk.Number -or $peDisk.Size -ne 2GB -or $peDisk.IsBoot -or $peDisk.IsSystem){throw 'Owned recovery disk mismatch.'}
 if(-not $existing){
  if($peDisk.PartitionStyle -ne 'RAW'){throw 'Fresh RAW recovery disk required.'}
  Initialize-Disk -Number $peDisk.Number -PartitionStyle GPT | Out-Null
  $partition=New-Partition -DiskNumber $peDisk.Number -UseMaximumSize -GptType '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}' -AssignDriveLetter
  Format-Volume -Partition $partition -FileSystem FAT32 -Confirm:$false | Out-Null
 }else{
  $partitions=@(Get-Partition -DiskNumber $peDisk.Number | Where-Object {$_.GptType -eq '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}'})
  if($partitions.Count -ne 1){throw 'Existing owned recovery partition required.'}
  $partition=$partitions[0]
 }
 $partition=Get-Partition -DiskNumber $peDisk.Number -PartitionNumber $partition.PartitionNumber
 if(-not [char]::IsLetter($partition.DriveLetter)){
  Add-PartitionAccessPath -DiskNumber $peDisk.Number -PartitionNumber $partition.PartitionNumber -AssignDriveLetter
  $partition=Get-Partition -DiskNumber $peDisk.Number -PartitionNumber $partition.PartitionNumber
 }
 if(-not [char]::IsLetter($partition.DriveLetter)){throw 'Owned recovery drive unavailable.'}
 $peRoot=$partition.DriveLetter+':\'
 $image=Mount-DiskImage -ImagePath $Iso -Passthru;$mountedIso=$true
 $source=($image | Get-Volume).DriveLetter+':\'
 if(-not $existing){
  foreach($name in @('boot','efi','bootmgr','bootmgr.efi')){Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $peRoot $name) -Recurse}
  New-Item -ItemType Directory -Path (Join-Path $peRoot 'sources') | Out-Null
  Copy-Item -LiteralPath (Join-Path $source 'sources\boot.wim') -Destination (Join-Path $peRoot 'sources\boot.wim')
 }
 New-Item -ItemType Directory -Path $mount -Force | Out-Null
 if(@(Get-ChildItem -LiteralPath $mount -Force).Count){throw 'Empty owned WinPE mount directory required.'}
 $wim=Join-Path $peRoot 'sources\boot.wim'
 if($existingVm){
  (Get-Item -LiteralPath $wim).IsReadOnly=$false
  Copy-Item -LiteralPath (Join-Path $source 'sources\boot.wim') -Destination $wim -Force
 }
 if((Get-FileHash -LiteralPath $wim).Hash -ne (Get-FileHash -LiteralPath (Join-Path $source 'sources\boot.wim')).Hash){throw 'Unmodified Microsoft WinPE image required.'}
 (Get-Item -LiteralPath $wim).IsReadOnly=$false
 Progress 'configure-owned-winpe-startup'
 Dism ('/Mount-Image /ImageFile:"'+$wim+'" /Index:2 /MountDir:"'+$mount+'"') 'pe-mount';$mountedWim=$true
 $system=Join-Path $mount 'Windows\System32'
 @('[LaunchApps]','%SYSTEMROOT%\System32\cmd.exe, /c X:\Windows\System32\router-qa-boot.cmd') | Set-Content -LiteralPath (Join-Path $system 'winpeshl.ini') -Encoding ASCII
 $command=@'
@echo off
wpeinit
set QAOS=
for %%L in (C D E F G H I J K L M N O P Q R T U V W Y Z) do if exist %%L:\RouterInput\qa-owned.marker set QAOS=%%L:
if not defined QAOS goto shutdown
echo {"passed":false,"stage":"preparing"}>%QAOS%\RouterOutput\pe-boot-result.json
rem Selecting the basic Windows volume also selects its disk. No localized
rem DiskPart table parsing or assumed disk number is needed.
rem Redirect first: a trailing partition number must not become a file handle.
>X:\qa-letters.txt echo select volume %QAOS:~0,1%
>>X:\qa-letters.txt echo select partition QA_EFI_PARTITION
>>X:\qa-letters.txt echo assign letter=S
diskpart /s X:\qa-letters.txt >%QAOS%\RouterOutput\pe-diskpart.private.log 2>&1
if errorlevel 1 goto failed
if not exist S:\ goto failed
rem Evaluation media may contain an older WinPE BCDBoot without /offline.
rem Standard /s /f UEFI deployment runs wholly inside this disposable VM.
bcdboot %QAOS%\Windows /s S: /f UEFI /c >%QAOS%\RouterOutput\pe-boot.private.log 2>&1
if errorlevel 1 goto failed
echo {"passed":true}>%QAOS%\RouterOutput\pe-boot-result.json
goto shutdown
:failed
echo {"passed":false}>%QAOS%\RouterOutput\pe-boot-result.json
:shutdown
wpeutil shutdown
'@
 $command=$command.Replace('QA_EFI_PARTITION',[string]$mainEfi[0].PartitionNumber)
 $command | Set-Content -LiteralPath (Join-Path $system 'router-qa-boot.cmd') -Encoding ASCII
 Dism ('/Unmount-Image /MountDir:"'+$mount+'" /Commit') 'pe-commit';$mountedWim=$false
 Dismount-DiskImage -ImagePath $Iso;$mountedIso=$false
 Dismount-VHD -Path $pe;$mountedPe=$false
 if(-not $existingVm){New-VM -Name $vmName -Generation 2 -Path $Workspace -MemoryStartupBytes ($StartupMemoryGiB*1GB) -VHDPath $main -SwitchName 'Default Switch' | Out-Null}
 Set-VM -Name $vmName -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -AutomaticCheckpointsEnabled $false -CheckpointType Disabled
 Set-VMProcessor -VMName $vmName -Count 2
 Set-VMMemory -VMName $vmName -DynamicMemoryEnabled $true -StartupBytes ($StartupMemoryGiB*1GB) -MinimumBytes 2GB -MaximumBytes 4GB
 if(-not $existingVm){
  Set-VMKeyProtector -VMName $vmName -NewLocalKeyProtector
  Enable-VMTPM -VMName $vmName
 }
 if(-not $existingVm){Add-VMHardDiskDrive -VMName $vmName -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 1 -Path $pe}
 $recovery=Get-VMHardDiskDrive -VMName $vmName | Where-Object {$_.Path -eq $pe}
 Set-VMFirmware -VMName $vmName -FirstBootDevice $recovery
 Progress 'booting-winpe-in-owned-vm'
 Start-VM -Name $vmName
 $deadline=[DateTime]::UtcNow.AddMinutes(15)
 do {Start-Sleep -Seconds 5;$state=[string](Get-VM -Name $vmName).State} while($state -ne 'Off' -and [DateTime]::UtcNow -lt $deadline)
 if($state -ne 'Off'){throw 'Owned WinPE recovery timeout; VM retained for inspection.'}
 $mainVhd=Mount-VHD -Path $main -ReadOnly -Passthru;$mountedMain=$true
 $windows=Get-Partition -DiskNumber $mainVhd.DiskNumber -PartitionNumber $mainWindows[0].PartitionNumber
 $resultPath=$windows.DriveLetter+':\RouterOutput\pe-boot-result.json'
 $result=Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
 if($result.passed -ne $true){throw 'In-guest boot setup failed.'}
 @{passed=$true;insideDisposableGuest=$true;hostBcdChanged=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'winpe-boot-result.json') -Encoding UTF8
 Dismount-VHD -Path $main;$mountedMain=$false
 Remove-VMHardDiskDrive -VMHardDiskDrive $recovery
 $primary=Get-VMHardDiskDrive -VMName $vmName | Where-Object {$_.Path -eq $main}
 Set-VMFirmware -VMName $vmName -FirstBootDevice $primary
 @{created=$true;name=$vmName;memoryStartupGiB=$StartupMemoryGiB;cpu=2;network='Default Switch';hostRebootRequested=$false;officialIsoVerified=$true;winpeRecovery=$true;automaticCheckpoints=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'vm-created.json') -Encoding UTF8
 Progress 'booting-clean-guest'
 Start-VM -Name $vmName
} catch {
 @{failed=$true;errorType=$_.Exception.GetType().Name;message=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'winpe-failure.private.json') -Encoding UTF8
 Progress 'winpe-failed'
 throw
} finally {
 if($mountedWim){Dism ('/Unmount-Image /MountDir:"'+$mount+'" /Discard') 'pe-discard'}
 if($mountedIso){Dismount-DiskImage -ImagePath $Iso -ErrorAction SilentlyContinue}
 if($mountedPe){Dismount-VHD -Path $pe -ErrorAction SilentlyContinue}
 if($mountedMain){Dismount-VHD -Path $main -ErrorAction SilentlyContinue}
}
