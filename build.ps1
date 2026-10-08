param(
    [switch]$BuildOnly,
    [string]$FrameworkReferencePath = 'C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8'
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'tools\packaging\build_windows.ps1') @PSBoundParameters
