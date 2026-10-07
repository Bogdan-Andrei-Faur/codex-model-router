# Read only sanitized output from an owned VM using its synthetic local account.
# Run elevated; never use an owner account or operate on a pre-existing VM.
param([Parameter(Mandatory=$true)][string]$Workspace,[int]$TimeoutMinutes=30)
$ErrorActionPreference='Stop'
Import-Module Hyper-V
$Workspace=[IO.Path]::GetFullPath($Workspace)
$private=Get-Content -LiteralPath (Join-Path $Workspace 'guest-credential.private.json') -Raw | ConvertFrom-Json
$vmName=[string]$private.vmName
if($vmName -notmatch '^CodexRouter-QA-[0-9a-f]{8}$'){throw 'Owned QA VM required.'}
$expectedDisk=[IO.Path]::GetFullPath((Join-Path $Workspace 'router-qa.vhdx'))
$disks=@(Get-VMHardDiskDrive -VMName $vmName)
if($disks.Count -ne 1 -or [IO.Path]::GetFullPath($disks[0].Path) -ne $expectedDisk){throw 'QA disk ownership mismatch.'}
$password=ConvertTo-SecureString ([string]$private.password) -AsPlainText -Force
$credential=New-Object Management.Automation.PSCredential('RouterQA',$password)
$private=$null
$deadline=[DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
$status=Join-Path $Workspace 'collection-progress.json'
$session=$null
try {
 while([DateTime]::UtcNow -lt $deadline){
  try {
   if(-not $session){$session=New-PSSession -VMName $vmName -Credential $credential -ErrorAction Stop}
   $probe=Invoke-Command -Session $session -ScriptBlock {
    $result='C:\RouterOutput\clean-windows-result.json'
    $progress='C:\RouterOutput\guest-progress.json'
    if(Test-Path -LiteralPath $result){return @{complete=$true;result=(Get-Content -LiteralPath $result -Raw)}}
    if(Test-Path -LiteralPath $progress){return @{complete=$false;progress=(Get-Content -LiteralPath $progress -Raw)}}
    return @{complete=$false;progress=$null}
   }
   if($probe.complete){
    $result=$probe.result | ConvertFrom-Json
    if($result.ownerDataUsed -ne $false -or $result.liveInference -ne $false){throw 'Unexpected guest output scope.'}
    [IO.File]::WriteAllText((Join-Path $Workspace 'clean-windows-result.json'),($result | ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))
    if(-not $result.passed){
     # Guest-generated logs contain synthetic QA paths only. Keep them private
     # for diagnosis; never mix owner data or raw output into a Git receipt.
     $diagnostic=Invoke-Command -Session $session -ScriptBlock {
      $files=@(Get-ChildItem -LiteralPath 'C:\RouterQA' -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -match '^(?:(stdout|stderr)-[0-9]+\.txt|uninstall-[0-9]+\.log)$'} | Sort-Object LastWriteTime | Select-Object -Last 8)
      return @($files | ForEach-Object {@{file=$_.Name;content=[string](Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue)}})
     }
     [IO.File]::WriteAllText((Join-Path $Workspace 'guest-diagnostic.private.json'),($diagnostic | ConvertTo-Json -Depth 5),(New-Object Text.UTF8Encoding($false)))
    }
    @{complete=$true;passed=[bool]$result.passed;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8
    if($result.passed){Stop-VM -Name $vmName}
    exit
   }
   $stage=if($probe.progress){($probe.progress | ConvertFrom-Json).stage}else{'waiting-for-guest-test'}
   @{stage=$stage;vmState=[string](Get-VM -Name $vmName).State;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8
  } catch {
   if($session){Remove-PSSession -Session $session -ErrorAction SilentlyContinue;$session=$null}
   @{stage='waiting-for-powerShell-direct';vmState=[string](Get-VM -Name $vmName).State;errorType=$_.Exception.GetType().Name;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8
  }
  Start-Sleep -Seconds 10
 }
 @{complete=$false;stage='timed-out';utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $status -Encoding UTF8
} finally {if($session){Remove-PSSession -Session $session -ErrorAction SilentlyContinue}}
