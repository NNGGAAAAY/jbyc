param(
  [switch]$ReloadOnly
)

. (Join-Path $PSScriptRoot 'config.ps1')

Ensure-MappedDrive

if (-not (Test-NginxReady)) {
  throw 'Nginx executable or config file not found'
}

Ensure-Directory (Get-SslConfigDir)
Ensure-Directory (Get-SslCertDir)

if (Test-SslFilesPresent) {
  Write-SslServerConfig
} elseif (Test-Path (Get-SslConfigPath)) {
  Remove-Item -Force (Get-SslConfigPath)
}

$nginxExe = Get-NginxExe
$nginxRoot = Get-NginxRoot

& $nginxExe -t -p $nginxRoot -c 'conf/nginx.conf'
if ($LASTEXITCODE -ne 0) {
  throw 'Nginx config test failed'
}

$nginxPid = Get-ListeningProcessId 80
if (-not $nginxPid) {
  $nginxPid = Get-ListeningProcessId 443
}

if ($ReloadOnly -or $nginxPid) {
  & $nginxExe -s reload -p $nginxRoot -c 'conf/nginx.conf'
  if ($LASTEXITCODE -ne 0) {
    throw 'Nginx reload failed'
  }
  Write-Host 'Nginx reloaded'
  exit 0
}

Start-Process -FilePath $nginxExe -ArgumentList '-p', $nginxRoot, '-c', 'conf/nginx.conf' -WorkingDirectory $nginxRoot -WindowStyle Hidden | Out-Null
Start-Sleep -Seconds 2

if (-not (Test-PortListening 80)) {
  throw 'Nginx failed to start, port 80 is not listening'
}

Write-Host 'Nginx started'
if (Test-PortListening 443) {
  Write-Host "HTTPS enabled: https://$Domain"
} else {
  Write-Host "HTTP only: http://$Domain"
}
