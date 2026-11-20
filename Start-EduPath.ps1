Set-Location -LiteralPath $PSScriptRoot
$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $cmd = 'py -3 server.py' }
else { $cmd = 'python server.py' }
Write-Host 'Starting local SQLite demo at http://127.0.0.1:8765' -ForegroundColor Green
Start-Process 'http://127.0.0.1:8765'
cmd /c $cmd
