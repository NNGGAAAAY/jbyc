param(
  [switch]$SkipBuild
)

. (Join-Path $PSScriptRoot 'config.ps1')

Write-Host '== Start production stack =='
Ensure-MappedDrive
Ensure-MySqlService

if (-not $SkipBuild) {
  Write-Host 'Building frontend...'
  Push-Location $FrontendDir
  try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
      throw 'Frontend build failed'
    }
  } finally {
    Pop-Location
  }
}

Write-Host 'Starting backend...'
& (Join-Path $PSScriptRoot 'start-backend.ps1')
if ($LASTEXITCODE -ne 0) {
  throw 'Backend startup failed'
}

Write-Host 'Starting Nginx...'
& (Join-Path $PSScriptRoot 'start-nginx.ps1')
if ($LASTEXITCODE -ne 0) {
  throw 'Nginx startup failed'
}

Write-Host ''
Write-Host '== Production stack ready =='
Write-Host "HTTP:  http://$Domain"
if (Test-PortListening 443 -and (Test-SslFilesPresent)) {
  Write-Host "HTTPS: https://$Domain"
} else {
  Write-Host 'HTTPS: not enabled yet, run issue-ssl.ps1 first'
}
