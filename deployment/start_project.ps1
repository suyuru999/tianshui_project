param(
    [switch]$NoBrowser,
    [switch]$NoPause,
    [switch]$SkipElevation
)

$ErrorActionPreference = 'Stop'

$projectRoot = 'D:\tianshui_project'
$backendRoot = Join-Path $projectRoot 'backend'
$frontendIndex = Join-Path $projectRoot 'frontend\dist\index.html'
$runtimeRoot = Join-Path $projectRoot 'runtime'
$pythonExe = 'C:\Program\python.exe'
$nginxRoot = 'D:\nginx-1.30.4\nginx-1.30.4'
$nginxExe = Join-Path $nginxRoot 'nginx.exe'
$projectUrl = 'http://localhost:8081/'

function Write-Step([string]$message) {
    Write-Host "[START] $message" -ForegroundColor Cyan
}

function Write-Ok([string]$message) {
    Write-Host "[ OK  ] $message" -ForegroundColor Green
}

function Write-Warn([string]$message) {
    Write-Host "[WARN ] $message" -ForegroundColor Yellow
}

function Test-ListeningPort([int]$port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $connection.AsyncWaitHandle.WaitOne(800)) {
            return $false
        }
        $client.EndConnect($connection)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForUrl([string]$url, [int]$attempts = 20) {
    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Start-ProjectService([string]$serviceName) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($null -eq $service) {
        Write-Warn "Windows service not found: $serviceName"
        return
    }

    if ($service.Status -ne 'Running') {
        Write-Step "Starting Windows service: $serviceName"
        Start-Service -Name $serviceName
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
    }
    Write-Ok "Windows service is running: $serviceName"
}

# Redis and GeoServer are Windows services and may require administrator rights.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator -and -not $SkipElevation) {
    $elevatedArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($NoBrowser) { $elevatedArguments += ' -NoBrowser' }
    if ($NoPause) { $elevatedArguments += ' -NoPause' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $elevatedArguments
    exit 0
}

try {
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw "Python not found: $pythonExe"
    }
    if (-not (Test-Path -LiteralPath $frontendIndex)) {
        throw "Frontend build not found: $frontendIndex"
    }
    if (-not (Test-Path -LiteralPath $nginxExe)) {
        throw "Nginx not found: $nginxExe"
    }

    # Load the Redis and GeoServer values saved for the current Windows user.
    foreach ($variableName in @(
        'TIANSHUI_CELERY_BROKER_URL',
        'TIANSHUI_CELERY_RESULT_BACKEND',
        'GEOSERVER_URL',
        'GEOSERVER_USERNAME',
        'GEOSERVER_PASSWORD'
    )) {
        $variableValue = [Environment]::GetEnvironmentVariable($variableName, 'User')
        if (-not [string]::IsNullOrWhiteSpace($variableValue)) {
            Set-Item -Path "Env:$variableName" -Value $variableValue
        }
    }

    Start-ProjectService 'RedisService'
    Start-ProjectService 'GeoServer'

    if (Test-ListeningPort 8000) {
        Write-Ok 'Django backend is already listening on port 8000'
    }
    else {
        Write-Step 'Starting Django backend on port 8000'
        Start-Process -FilePath $pythonExe `
            -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') `
            -WorkingDirectory $backendRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runtimeRoot 'django.out.log') `
            -RedirectStandardError (Join-Path $runtimeRoot 'django.err.log')
    }

    $celeryWorker = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq 'python.exe' -and
            $_.CommandLine -match '(?i)celery' -and
            $_.CommandLine -match '(?i)tianshuipy' -and
            $_.CommandLine -match '(?i)worker'
        } |
        Select-Object -First 1

    if ($null -ne $celeryWorker) {
        Write-Ok 'Celery worker is already running'
    }
    else {
        Write-Step 'Starting Celery worker'
        Start-Process -FilePath $pythonExe `
            -ArgumentList @('-m', 'celery', '-A', 'tianshuipy', 'worker', '-l', 'info', '--pool=solo') `
            -WorkingDirectory $backendRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runtimeRoot 'celery.out.log') `
            -RedirectStandardError (Join-Path $runtimeRoot 'celery.err.log')
    }

    if (Test-ListeningPort 8081) {
        Write-Ok 'Nginx is already listening on port 8081'
    }
    else {
        Write-Step 'Starting Nginx on port 8081'
        Start-Process -FilePath $nginxExe -WorkingDirectory $nginxRoot -WindowStyle Hidden
    }

    Write-Step 'Waiting for the backend API'
    if (Wait-ForUrl 'http://127.0.0.1:8000/api/v1/environment/ecological-indices/') {
        Write-Ok 'Django API is ready'
    }
    else {
        Write-Warn "Django API did not become ready. Check: $runtimeRoot\django.err.log"
    }

    Write-Step 'Waiting for the Nginx website'
    if (Wait-ForUrl $projectUrl) {
        Write-Ok "Project is ready: $projectUrl"
        if (-not $NoBrowser) {
            Start-Process $projectUrl
        }
    }
    else {
        Write-Warn "Website did not become ready: $projectUrl"
    }
}
catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if (-not $NoPause) {
        Read-Host 'Press Enter to close'
    }
    exit 1
}

if (-not $NoPause) {
    Write-Host ''
    Read-Host 'Startup finished. Press Enter to close this window'
}
