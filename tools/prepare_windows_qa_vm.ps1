# Creates only a fresh, owned Hyper-V QA disk. Never formats an existing disk.
# Run elevated, with an official Microsoft evaluation ISO and public inputs.
param([Parameter(Mandatory=$true)][string]$Workspace,
      [Parameter(Mandatory=$true)][string]$Iso,
      [Parameter(Mandatory=$true)][string]$InputRoot,
      [Parameter(Mandatory=$true)][string]$IsoSha256,
      [switch]$DeferBootSetup)
$ErrorActionPreference='Stop'
Import-Module Hyper-V
$Workspace=[IO.Path]::GetFullPath($Workspace)
$Iso=[IO.Path]::GetFullPath($Iso)
$InputRoot=[IO.Path]::GetFullPath($InputRoot)
if(-not (Test-Path -LiteralPath $Workspace -PathType Container)){throw 'Prepared workspace required.'}
$status=Join-Path $Workspace 'vm-progress.json'
function Progress([string]$Stage){@{stage=$Stage;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8}
$diskPath=Join-Path $Workspace 'router-qa.vhdx'
$vmName='CodexRouter-QA-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
$mounted=$false;$mountedIso=$false
try {
 Progress 'verify-media'
 if((Get-FileHash -LiteralPath $Iso -Algorithm SHA256).Hash -ne $IsoSha256){throw 'Official media hash mismatch.'}
 if(Test-Path -LiteralPath $diskPath){throw 'QA disk already exists; do not replace it.'}
 $password='Qa!'+[Guid]::NewGuid().ToString('N')
 @{vmName=$vmName;password=$password} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'guest-credential.private.json') -Encoding UTF8
 Progress 'create-owned-disk'
 New-VHD -Path $diskPath -SizeBytes 64GB -Dynamic | Out-Null
 $vhd=Mount-VHD -Path $diskPath -Passthru;$mounted=$true
 $disk=Get-Disk -Number $vhd.DiskNumber
 $owned=Get-VHD -Path $diskPath
 if($owned.DiskNumber -ne $disk.Number -or $disk.PartitionStyle -ne 'RAW' -or $disk.Size -ne 64GB -or $disk.IsBoot -or $disk.IsSystem){throw 'Owned disk validation failed.'}
 Initialize-Disk -Number $disk.Number -PartitionStyle GPT | Out-Null
 $efi=New-Partition -DiskNumber $disk.Number -Size 260MB -GptType '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}' -AssignDriveLetter
 Format-Volume -Partition $efi -FileSystem FAT32 -NewFileSystemLabel ROUTER-QA-EFI -Confirm:$false | Out-Null
 if(-not (Get-Partition -DiskNumber $disk.Number | Where-Object {$_.GptType -eq '{e3c9e316-0b5c-4db8-817d-f92df00215ae}'})){
  New-Partition -DiskNumber $disk.Number -Size 16MB -GptType '{e3c9e316-0b5c-4db8-817d-f92df00215ae}' | Out-Null
 }
 $windows=New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
 Format-Volume -Partition $windows -FileSystem NTFS -NewFileSystemLabel ROUTER-QA-WINDOWS -Confirm:$false | Out-Null
 $image=Mount-DiskImage -ImagePath $Iso -Passthru;$mountedIso=$true
 $volume=$image | Get-Volume
 $imageFile=$volume.DriveLetter+':\sources\install.wim'
 if(-not (Test-Path -LiteralPath $imageFile)){throw 'Official install.wim unavailable.'}
 $windows=Get-Partition -DiskNumber $disk.Number -PartitionNumber $windows.PartitionNumber
 $efi=Get-Partition -DiskNumber $disk.Number -PartitionNumber $efi.PartitionNumber
 if(-not [char]::IsLetter($windows.DriveLetter) -or -not [char]::IsLetter($efi.DriveLetter)){throw 'Owned QA drive letters unavailable.'}
 $target=$windows.DriveLetter+':\'
 Progress 'apply-official-image'
 & "$env:WINDIR\System32\dism.exe" /Apply-Image ("/ImageFile:"+$imageFile) /Index:1 ("/ApplyDir:"+$target) ("/LogPath:"+(Join-Path $Workspace 'dism.private.log')) | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Windows image application failed.'}
 Progress 'configure-disposable-guest'
 Copy-Item -LiteralPath $InputRoot -Destination (Join-Path $target 'RouterInput') -Recurse
 New-Item -ItemType Directory -Path (Join-Path $target 'RouterOutput') -Force | Out-Null
 $panther=Join-Path $target 'Windows\Panther';New-Item -ItemType Directory -Path $panther -Force | Out-Null
 $unattend=@"
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
 <settings pass="specialize">
  <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><ComputerName>ROUTER-QA</ComputerName><TimeZone>UTC</TimeZone></component>
 </settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><InputLocale>0409:00000409</InputLocale><SystemLocale>en-US</SystemLocale><UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale></component>
  <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
   <OOBE><HideEULAPage>true</HideEULAPage><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><ProtectYourPC>1</ProtectYourPC></OOBE>
   <UserAccounts><LocalAccounts><LocalAccount wcm:action="add"><Name>RouterQA</Name><DisplayName>Router QA</DisplayName><Group>Administrators</Group><Password><Value>$password</Value><PlainText>true</PlainText></Password></LocalAccount></LocalAccounts></UserAccounts>
   <AutoLogon><Username>RouterQA</Username><Enabled>true</Enabled><LogonCount>1</LogonCount><Password><Value>$password</Value><PlainText>true</PlainText></Password></AutoLogon>
   <FirstLogonCommands><SynchronousCommand wcm:action="add"><Order>1</Order><Description>Run isolated router acceptance</Description><CommandLine>powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File C:\RouterInput\windows_clean_guest.ps1</CommandLine></SynchronousCommand></FirstLogonCommands>
  </component>
 </settings>
</unattend>
"@
 $unattend | Set-Content -LiteralPath (Join-Path $panther 'unattend.xml') -Encoding UTF8
 if($DeferBootSetup){
  Dismount-DiskImage -ImagePath $Iso;$mountedIso=$false
  Dismount-VHD -Path $diskPath;$mounted=$false
  Progress 'prepared-offline-guest'
  exit
 }
 # Offline servicing must not select binaries based on the host firmware db.
 # Requires current BCDBoot (26100.8037+) as documented by Microsoft.
 $bootArguments='"'+(Join-Path $target 'Windows')+'" /s '+$efi.DriveLetter+': /f UEFI /offline /c'
 $boot=Start-Process -FilePath "$env:WINDIR\System32\bcdboot.exe" -ArgumentList $bootArguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Workspace 'bcdboot-stdout.private.log') -RedirectStandardError (Join-Path $Workspace 'bcdboot-stderr.private.log')
 $null=$boot.Handle # Cache before exit: Windows PowerShell 5.1 bug #5421.
 if(-not $boot.WaitForExit(180000)){throw 'Owned QA boot setup timed out.'}
 if($boot.ExitCode -ne 0){throw 'Owned QA boot files failed.'}
 Dismount-DiskImage -ImagePath $Iso;$mountedIso=$false
 Dismount-VHD -Path $diskPath;$mounted=$false
 New-VM -Name $vmName -Generation 2 -Path $Workspace -MemoryStartupBytes 4GB -VHDPath $diskPath -SwitchName 'Default Switch' | Out-Null
 Set-VM -Name $vmName -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -AutomaticCheckpointsEnabled $false -CheckpointType Disabled
 Set-VMProcessor -VMName $vmName -Count 2
 Set-VMMemory -VMName $vmName -DynamicMemoryEnabled $true -MinimumBytes 2GB -MaximumBytes 4GB
 Set-VMKeyProtector -VMName $vmName -NewLocalKeyProtector
 Enable-VMTPM -VMName $vmName
 @{created=$true;name=$vmName;memoryStartupGiB=4;cpu=2;network='Default Switch';hostRebootRequested=$false;officialIsoVerified=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'vm-created.json') -Encoding UTF8
 Progress 'booting-clean-guest'
 Start-VM -Name $vmName
} catch {
 @{failed=$true;errorType=$_.Exception.GetType().Name;message=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Workspace 'vm-failure.private.json') -Encoding UTF8
 Progress 'failed'
 throw
} finally {
 if($mountedIso){Dismount-DiskImage -ImagePath $Iso -ErrorAction SilentlyContinue}
 if($mounted){Dismount-VHD -Path $diskPath -ErrorAction SilentlyContinue}
}
