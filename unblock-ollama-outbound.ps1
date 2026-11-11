# Temporarily lets Ollama reach the internet again, to pull or update a model.
# Run from an elevated (Administrator) PowerShell, update, then run block-ollama-outbound.ps1 again:
#   powershell -ExecutionPolicy Bypass -File .\unblock-ollama-outbound.ps1
#   ollama pull qwen3:8b
#   powershell -ExecutionPolicy Bypass -File .\block-ollama-outbound.ps1
#Requires -RunAsAdministrator
$rules = Get-NetFirewallRule -Group 'pii-mask' -ErrorAction SilentlyContinue
if (-not $rules) { Write-Host 'No pii-mask firewall rules found.'; exit 0 }
$rules | Remove-NetFirewallRule
Write-Host "Removed $(@($rules).Count) rule(s). Ollama can reach the internet until you block it again."
