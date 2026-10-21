<#
.SYNOPSIS
  Starts MovieShare with one double-click or one command.

.EXAMPLE
  .\Start-MovieShare.ps1
  .\Start-MovieShare.ps1 -Folder "E:\Videos" -Port 8080
  .\Start-MovieShare.ps1 -AllowNetwork   # lets other devices on your Wi-Fi/Tailscale connect
#>
param(
    [string]$Folder = "D:\Movies",
    [int]$Port = 6789,
    [switch]$AllowNetwork
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
    Write-Host "Folder not found: $Folder" -ForegroundColor Red
    Write-Host "Edit the -Folder value, or run: .\Start-MovieShare.ps1 -Folder `"C:\Your\Folder`"" -ForegroundColor Yellow
    exit 1
}

$bindAddress = if ($AllowNetwork) { "0.0.0.0" } else { "127.0.0.1" }

python "$PSScriptRoot\server.py" --directory $Folder --host $bindAddress --port $Port
