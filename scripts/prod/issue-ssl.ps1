param(
  [Parameter(Mandatory = $true)]
  [string]$EmailAddress
)

. (Join-Path $PSScriptRoot 'config.ps1')

function Ensure-WinAcme {
  $wacsExe = Get-WinAcmeExe
  if (Test-Path $wacsExe) {
    return $wacsExe
  }

  Ensure-Directory $WinAcmeRoot
  $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/win-acme/win-acme/releases/latest' -TimeoutSec 30
  $asset = $release.assets | Where-Object { $_.name -match 'x64.*(pluggable|trimmed)\.zip$' } | Select-Object -First 1
  if (-not $asset) {
    throw 'No usable win-acme release package found'
  }

  $zipPath = Join-Path $WinAcmeRoot $asset.name
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -TimeoutSec 120
  Expand-Archive -Path $zipPath -DestinationPath $WinAcmeRoot -Force

  if (-not (Test-Path $wacsExe)) {
    throw 'wacs.exe not found after extracting win-acme'
  }

  return $wacsExe
}

function Normalize-CertificateFiles {
  Ensure-Directory (Get-SslCertDir)
  $chainFile = Get-ChildItem -Path (Get-SslCertDir) -Filter '*-chain.pem' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $keyFile = Get-ChildItem -Path (Get-SslCertDir) -Filter '*-key.pem' | Sort-Object LastWriteTime -Descending | Select-Object -First 1

  if (-not $chainFile -or -not $keyFile) {
    throw 'PEM files not found after certificate issuance'
  }

  Copy-Item -Path $chainFile.FullName -Destination (Get-SslChainPath) -Force
  Copy-Item -Path $keyFile.FullName -Destination (Get-SslKeyPath) -Force
}

Ensure-MappedDrive
Ensure-Directory (Get-SslCertDir)
Ensure-Directory (Get-SslConfigDir)

$dnsAddress = Get-DomainDnsAddress
$publicIp = Get-PublicIp
if (-not $dnsAddress) {
  throw "DNS lookup failed for $Domain. Make sure the A record is active."
}
if ($publicIp -and $dnsAddress -ne $publicIp) {
  throw "Domain $Domain resolves to $dnsAddress, but current public IP is $publicIp. Point the A record to this server first."
}

Push-Location $FrontendDir
try {
  npm run build
  if ($LASTEXITCODE -ne 0) {
    throw 'Frontend build failed, cannot continue certificate issuance'
  }
} finally {
  Pop-Location
}

& (Join-Path $PSScriptRoot 'start-backend.ps1')
if ($LASTEXITCODE -ne 0) {
  throw 'Backend startup failed'
}

& (Join-Path $PSScriptRoot 'start-nginx.ps1')
if ($LASTEXITCODE -ne 0) {
  throw 'Nginx startup failed'
}

$wacsExe = Ensure-WinAcme
$hostNames = @($Domain) + $AltDomains
$hostArg = ($hostNames -join ',')
$webroot = Get-FrontendDist
$pemDir = Get-SslCertDir

& $wacsExe `
  --source manual `
  --host $hostArg `
  --validation filesystem `
  --webroot $webroot `
  --store pemfiles `
  --pemfilespath $pemDir `
  --installation none `
  --accepttos `
  --emailaddress $EmailAddress `
  --closeonfinish

if ($LASTEXITCODE -ne 0) {
  throw 'win-acme certificate issuance failed. Check DNS, port 80 and command output.'
}

Normalize-CertificateFiles
Write-SslServerConfig
& (Join-Path $PSScriptRoot 'start-nginx.ps1') -ReloadOnly

Write-Host "HTTPS certificate deployed: https://$Domain"
