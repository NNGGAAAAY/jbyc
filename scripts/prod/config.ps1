$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$MappedDrive = 'X:'
$Domain = 'ojxdxcx.xyz'
$AltDomains = @('www.ojxdxcx.xyz')
$BackendPort = 8000
$PythonExe = 'D:\anaconda3\envs\pytorch\python.exe'
$DatabaseUrl = 'mysql+pymysql://root:46939@127.0.0.1:3306/anesthesia_ml?charset=utf8mb4'
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$NginxProjectRoot = Join-Path $ProjectRoot 'nginx-1.30.0'
$WinAcmeRoot = Join-Path $ProjectRoot 'scripts\tools\win-acme'
$BackendLogsDir = Join-Path $ProjectRoot 'artifacts\logs'

function Ensure-MappedDrive {
  $current = (Get-PSDrive -Name $MappedDrive.TrimEnd(':') -ErrorAction SilentlyContinue)
  if (-not $current -or $current.Root -ne "$ProjectRoot\") {
    cmd /c "subst $MappedDrive `"$ProjectRoot`""
  }
}

function Get-MappedPath([string]$relativePath) {
  $normalized = $relativePath -replace '^[\\/]+', ''
  return "$MappedDrive\$normalized"
}

function Get-NginxRoot {
  return Get-MappedPath 'nginx-1.30.0'
}

function Get-NginxExe {
  return Join-Path (Get-NginxRoot) 'nginx.exe'
}

function Get-FrontendDist {
  return Get-MappedPath 'frontend\dist'
}

function Get-SslCertDir {
  return Get-MappedPath 'nginx-1.30.0\conf\certs'
}

function Get-SslConfigDir {
  return Join-Path $NginxProjectRoot 'conf\ssl-enabled'
}

function Get-SslConfigPath {
  return Join-Path (Get-SslConfigDir) "$Domain.conf"
}

function Get-SslChainPath {
  return Join-Path (Get-SslCertDir) "$Domain-chain.pem"
}

function Get-SslKeyPath {
  return Join-Path (Get-SslCertDir) "$Domain-key.pem"
}

function Get-WinAcmeExe {
  return Join-Path $WinAcmeRoot 'wacs.exe'
}

function Ensure-Directory([string]$path) {
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}

function Ensure-MySqlService {
  $service = Get-Service -Name 'MySQL97Trae' -ErrorAction Stop
  if ($service.Status -ne 'Running') {
    Start-Service -Name 'MySQL97Trae'
  }
}

function Get-ListeningProcessId([int]$port) {
  $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($connection) {
    return $connection.OwningProcess
  }
  return $null
}

function Test-PortListening([int]$port) {
  return [bool](Get-ListeningProcessId $port)
}

function Test-SslFilesPresent {
  return (Test-Path (Get-SslChainPath)) -and (Test-Path (Get-SslKeyPath))
}

function Test-NginxReady {
  return (Test-Path (Get-NginxExe)) -and (Test-Path (Join-Path (Get-NginxRoot) 'conf\nginx.conf'))
}

function Get-PublicIp {
  try {
    return (Invoke-RestMethod -Uri 'https://api.ipify.org?format=json' -TimeoutSec 15).ip
  } catch {
    return $null
  }
}

function Get-DomainDnsAddress {
  try {
    $result = Resolve-DnsName -Name $Domain -Type A -ErrorAction Stop | Where-Object { $_.Type -eq 'A' } | Select-Object -First 1 -ExpandProperty IPAddress
    return $result
  } catch {
    return $null
  }
}

function Write-SslServerConfig {
  Ensure-Directory (Get-SslConfigDir)
  $config = @"
server {
    listen       443 ssl;
    server_name  $Domain $($AltDomains -join ' ');

    ssl_certificate      $(Get-SslChainPath -replace '\\','/');
    ssl_certificate_key  $(Get-SslKeyPath -replace '\\','/');
    ssl_protocols        TLSv1.2 TLSv1.3;
    ssl_session_timeout  1d;
    ssl_session_cache    shared:SSL:10m;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 20m;

    location /api/ {
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_pass http://anesthesia_backend/;
    }

    location /docs {
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_pass http://anesthesia_backend/docs;
    }

    location /openapi.json {
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_pass http://anesthesia_backend/openapi.json;
    }

    location / {
        root   $(Get-FrontendDist -replace '\\','/');
        index  index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
"@
  Set-Content -Path (Get-SslConfigPath) -Value $config -Encoding ascii
}
