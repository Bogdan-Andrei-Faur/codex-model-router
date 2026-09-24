param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$routerRoot = $PSScriptRoot
$routerOutput = Join-Path $routerRoot 'dist'
New-Item -ItemType Directory -Path $routerOutput -Force | Out-Null
$routerCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$routerFramework = 'C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.6.1'
$routerIcon = Join-Path $routerRoot 'assets\codex.ico'
$routerPng = [IO.File]::ReadAllBytes((Join-Path $routerRoot 'assets\codex-official.png'))
$routerWriter = [IO.BinaryWriter]::new([IO.File]::Create($routerIcon))
try {
    $routerWriter.Write([UInt16]0); $routerWriter.Write([UInt16]1); $routerWriter.Write([UInt16]1)
    1..4 | ForEach-Object { $routerWriter.Write([Byte]0) }
    $routerWriter.Write([UInt16]1); $routerWriter.Write([UInt16]32)
    $routerWriter.Write([UInt32]$routerPng.Length); $routerWriter.Write([UInt32]22)
    $routerWriter.Write($routerPng)
} finally { $routerWriter.Dispose() }
& $routerCompiler /nologo /target:winexe /optimize+ /r:System.Windows.Forms.dll /r:System.Web.Extensions.dll "/win32icon:$routerIcon" "/out:$routerOutput\codex-router-v19.exe" "$routerRoot\Launcher.cs"
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
& $routerCompiler /nologo /target:winexe /optimize+ /main:RouterMonitorProgram /r:System.Core.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll /r:System.Security.dll "/r:$routerFramework\System.Xaml.dll" "/r:$routerFramework\WindowsBase.dll" "/r:$routerFramework\PresentationCore.dll" "/r:$routerFramework\PresentationFramework.dll" "/win32icon:$routerIcon" "/out:$routerOutput\codex-monitor-v24.exe" "$routerRoot\MonitorWpf.cs" "$routerRoot\MonitorAgents.cs" "$routerRoot\MonitorAnalytics.cs" "$routerRoot\MonitorPhases.cs" "$routerRoot\MonitorReviewTests.cs"
if ($LASTEXITCODE -ne 0) { throw 'Monitor compilation failed' }
if ($BuildOnly) { Write-Output 'Compilación preparada sin cambiar los accesos.'; return }
$routerStable = Join-Path $routerOutput 'codex-router.exe'
Copy-Item -LiteralPath (Join-Path $routerOutput 'codex-router-v19.exe') -Destination ($routerStable + '.new') -Force
try { Move-Item -LiteralPath ($routerStable + '.new') -Destination $routerStable -Force }
catch { throw 'El lanzador estable está en uso. Conservado sin cambios: publica cuando hayan terminado las tareas.' }
$routerShell = New-Object -ComObject WScript.Shell
$routerLinks = @{
    'Abrir Codex automatico' = '--open'
    'Estado del selector' = '--status'
    'Pausar selector' = '--pause'
    'Activar selector' = '--resume'
    'Diagnostico de conexion' = '--doctor'
    'Desconectar integracion' = '--remove-integration'
}
foreach ($routerName in $routerLinks.Keys) {
    $routerShortcut = $routerShell.CreateShortcut((Join-Path $routerRoot "$routerName.lnk"))
    $routerShortcut.TargetPath = $routerStable
    $routerShortcut.Arguments = $routerLinks[$routerName]
    $routerShortcut.WorkingDirectory = $routerRoot
    $routerShortcut.IconLocation = "$routerIcon,0"
    $routerShortcut.Save()
}
$routerDesktop = [Environment]::GetFolderPath('Desktop')
foreach ($routerEntry in @(@('Codex automático', '--open'), @('Estado de Codex automático', '--status'))) {
    $routerShortcut = $routerShell.CreateShortcut((Join-Path $routerDesktop ($routerEntry[0] + '.lnk')))
    $routerShortcut.TargetPath = $routerStable
    $routerShortcut.Arguments = $routerEntry[1]
    $routerShortcut.WorkingDirectory = $routerRoot
    $routerShortcut.IconLocation = "$routerIcon,0"
    $routerShortcut.Save()
}
Write-Output 'Selector compilado. Accesos creados en la carpeta del proyecto.'
