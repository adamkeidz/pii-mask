# Blocks all outbound network traffic from Ollama, so the local model can never send data out.
# Loopback (127.0.0.1) is not affected, so pii-mask can still talk to Ollama.
# Run ONCE from an elevated (Administrator) PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\block-ollama-outbound.ps1
# Pull or update models BEFORE running this, or run unblock-ollama-outbound.ps1 first.
#Requires -RunAsAdministrator
param([string]$OllamaDir = (Join-Path $env:LOCALAPPDATA 'Programs\Ollama'))

$programs = @(
  (Join-Path $OllamaDir 'ollama.exe'),
  (Join-Path $OllamaDir 'ollama app.exe')
) + @(Get-ChildItem -Path (Join-Path $OllamaDir 'lib') -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue |
      ForEach-Object { $_.FullName })

$n = 0
foreach ($p in $programs | Select-Object -Unique) {
  if (-not (Test-Path $p)) { continue }
  $name = 'pii-mask: block Ollama outbound (' + (Split-Path $p -Leaf) + ')'
  Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  New-NetFirewallRule -DisplayName $name -Group 'pii-mask' -Direction Outbound -Program $p `
    -Action Block -Profile Any | Out-Null
  $n++
}
Write-Host "Added $n outbound block rule(s) in firewall group 'pii-mask'."
Get-NetFirewallRule -Group 'pii-mask' | Format-Table DisplayName, Enabled, Direction, Action -AutoSize
