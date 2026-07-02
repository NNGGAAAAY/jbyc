. (Join-Path $PSScriptRoot 'config.ps1')

Ensure-Directory $BackendLogsDir
Ensure-MySqlService

if (Test-PortListening $BackendPort) {
  Write-Host "Backend already running at 127.0.0.1:$BackendPort"
  exit 0
}

$stdoutLog = Join-Path $BackendLogsDir 'backend.stdout.log'
$stderrLog = Join-Path $BackendLogsDir 'backend.stderr.log'
$command = "`$env:DATABASE_URL='$DatabaseUrl'; Set-Location '$ProjectRoot'; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort"

Start-Process `
  -FilePath 'powershell.exe' `
  -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $command `
  -WorkingDirectory $ProjectRoot `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog `
  -WindowStyle Hidden | Out-Null

Start-Sleep -Seconds 3

if (-not (Test-PortListening $BackendPort)) {
  throw "Backend failed to start. Check logs: $stdoutLog / $stderrLog"
}

Write-Host "Backend started: http://127.0.0.1:$BackendPort"
