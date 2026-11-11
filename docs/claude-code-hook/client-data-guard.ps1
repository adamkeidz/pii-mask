# Keeps Claude out of the private client-data folders (ClientData\raw, \keys, \restored).
# Only ClientData\masked may be touched. One exception: a Bash/PowerShell call that runs exactly the
# mask or unmask wrapper (they print counts and output paths, never values).
# Install: copy to ~/.claude/hooks/ and merge settings.example.json into ~/.claude/settings.json.
# Rename ClientData below if your data root has another folder name.
# Pipe-test: Get-Content sample.json | powershell -NoProfile -File client-data-guard.ps1
$stream = [Console]::OpenStandardInput()
$reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
$raw = $reader.ReadToEnd()
try { $j = $raw | ConvertFrom-Json } catch { exit 0 }
$tool = [string]$j.tool_name
$ti = $j.tool_input
if (-not $ti) { exit 0 }

function Deny($why) {
  $msg = "Blocked by client-data-guard.ps1: $why Real client data lives in ClientData\raw, \keys and \restored and must never reach Claude. Work only on ClientData\masked, and run 'mask <file>' or 'unmask <file>' on their own (no pipes, redirects or chained commands)."
  $out = @{ hookSpecificOutput = @{ hookEventName = "PreToolUse"; permissionDecision = "deny"; permissionDecisionReason = $msg } } | ConvertTo-Json -Compress
  Write-Output $out
  exit 0
}

# Which text to scan. Write/Edit content may quote these paths in docs; only their target matters.
if ($tool -in @('Write', 'Edit', 'MultiEdit', 'NotebookEdit')) {
  $text = @($ti.file_path, $ti.notebook_path) -join "`n"
} else {
  $text = ($ti | ConvertTo-Json -Depth 50 -Compress)
  $text = $text -replace '\\\\', '\'          # JSON-escaped backslashes
  $text = $text -replace '\\u005c', '\'
}
$cwd = [string]$j.cwd

# Any mention of ClientData that is not ClientData\masked (raw, keys, restored, the bare parent, wildcards).
$private = '(?i)ClientData(?![\\/]+masked(?![\w.-]))'
$hit = ($text -match $private) -or ($cwd -match $private)

if ($hit) {
  if ($tool -in @('Bash', 'PowerShell')) {
    $cmd = ([string]$ti.command).Trim()
    $wrapper = '(?i)^(?:&\s*)?["'']?(?:(?:[A-Za-z]:|/[A-Za-z])[\\/]Users[\\/][^\\/\s]+[\\/]tools[\\/]pii-mask[\\/])?(?:mask|unmask)(?:\.cmd)?["'']?'
    $arg = '(?:"[^"`$;&|<>\r\n]*"|''[^''`$;&|<>\r\n]*''|[^\s"''`$;&|<>]+)'
    if ($cmd -match ($wrapper + '(?:[ \t]+' + $arg + ')*[ \t]*$') -and $cmd -notmatch '[\r\n]') { exit 0 }
  }
  Deny "this call references a private ClientData folder."
}

# Broad searches from a parent folder (C:\, C:\Users, home) would sweep ClientData\raw too.
$ancestor = '(?i)^(?:[A-Za-z]:[\\/]?|/[A-Za-z]/?|[A-Za-z]:[\\/]Users[\\/]?|/[A-Za-z]/Users/?|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]?|/[A-Za-z]/Users/[^/\s]+/?|~[\\/]?|\$HOME[\\/]?|\$env:USERPROFILE[\\/]?|%USERPROFILE%[\\/]?)$'
if ($tool -in @('Grep', 'Glob')) {
  $base = [string]$ti.path
  if (-not $base) { $base = $cwd }
  $pat = [string]$ti.pattern
  if ($base -match $ancestor) { Deny "searching a parent of ClientData would include the private folders. Search a narrower folder." }
  if ($tool -eq 'Glob' -and $pat -match '(?i)^(?:[A-Za-z]:|/[A-Za-z]|~)(?:[\\/]Users(?:[\\/][^\\/\s]+)?)?[\\/]+\*\*') { Deny "this glob sweeps a parent of ClientData." }
}
if ($tool -in @('Bash', 'PowerShell')) {
  $cmd = [string]$ti.command
  $recursive = '(?i)(\bgrep\b[^|;&]*\s-[a-zA-Z]*[rR]|\brg\b|\bfind\b|\bls\b[^|;&]*\s-[a-zA-Z]*R|\bGet-ChildItem\b[^|;&]*-r|\bgci\b[^|;&]*-r|\bdir\b[^|;&]*(/s|-r)|\bSelect-String\b|\btree\b|\brobocopy\b|\bxcopy\b|\btar\b|\bzip\b|Compress-Archive|\bcp\b[^|;&]*\s-[a-zA-Z]*r|\bdu\b)'
  $parentTok = '(?i)(?<![\w/\\.-])(?:"|'')?(?:[A-Za-z]:[\\/]?|/[A-Za-z]/?|[A-Za-z]:[\\/]Users[\\/]?|/[A-Za-z]/Users/?|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]?|/[A-Za-z]/Users/[^/\s]+/?|~[\\/]?|\$HOME[\\/]?|\$env:USERPROFILE[\\/]?|%USERPROFILE%[\\/]?)(?:"|'')?(?=\s|$|;|\||&|\))'
  if (($cmd -match $recursive) -and ($cmd -match $parentTok)) { Deny "a recursive command over a parent of ClientData would include the private folders. Point it at a narrower folder." }
}
exit 0
