# Compatibility alias for the complete Day 5 Live build.
param([int]$BackendPort = 8000, [int]$FrontendPort = 3000)
& (Join-Path $PSScriptRoot 'start-day5.ps1') -Mode live -BackendPort $BackendPort -FrontendPort $FrontendPort
