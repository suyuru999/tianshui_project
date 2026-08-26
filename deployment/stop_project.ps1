param(
    [switch]$NoPause,
    [switch]$SkipElevation
)

$ErrorActionPreference = 'Stop'
$nginxRoot = 'D:\nginx-1.30.4\nginx-1.30.4'
$nginxExe = Join-Path $nginxRoot 'nginx.exe'

function Write-Ok([string]$message) {
    Write-Host "[ OK  ] $message" -ForegroundColor Green
}

function Write-Warn([string]$message) {
    Write-Host "[WARN ] $message" -ForegroundColor Yellow
}

function Stop-ProjectProcess([int]$processId, [string]$description) {
    try {
        Stop-Process -Id $processId -ErrorAction Stop
        Write-Ok "Stopped: $description"
    }
    catch {
        Write-Warn "Could not stop $description : $($_.Exception.Message)"
    }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator -and -not $SkipElevation) {
    $elevatedArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($NoPause) { $elevatedArguments += ' -NoPause' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $elevatedArguments
    exit 0
}

try {
    # Stop only the Celery workers that belong to this project.
    $celeryWorkers = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq 'python.exe' -and
            $_.CommandLine -match '(?i)celery' -and
            $_.CommandLine -match '(?i)tianshuipy' -and
            $_.CommandLine -match '(?i)worker'
        }
    if ($celeryWorkers) {
        foreach ($worker in $celeryWorkers) {
            Stop-ProjectProcess $worker.ProcessId 'Tianshui Celery worker'
        }
    }
    else {
        Write-Ok 'Tianshui Celery worker is not running'
    }

    # Stop only a Django development server that explicitly listens on this project's port.
    $backendListeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $backendStopped = $false
    foreach ($listener in $backendListeners) {
        $backendProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if ($backendProcess -and $backendProcess.Name -eq 'python.exe' -and $backendProcess.CommandLine -match 'manage\.py\s+runserver\s+127\.0\.0\.1:8000') {
            Stop-ProjectProcess $backendProcess.ProcessId 'Tianshui Django backend'
            $backendStopped = $true
        }
    }
    if (-not $backendStopped) {
        Write-Ok 'Tianshui Django backend is not running'
    }

    # This controls only the Nginx installation dedicated to port 8081.
    if (Test-Path -LiteralPath $nginxExe) {
        $nginxResult = Start-Process -FilePath $nginxExe `
            -ArgumentList @('-s', 'quit', '-p', $nginxRoot, '-c', 'conf/nginx.conf') `
            -WorkingDirectory $nginxRoot `
            -Wait `
            -PassThru `
            -WindowStyle Hidden
        if ($nginxResult.ExitCode -eq 0) {
            Write-Ok 'Stopped Tianshui Nginx on port 8081'
        }
        else {
            Write-Ok 'Tianshui Nginx is not running'
        }
    }
    else {
        Write-Warn "Nginx was not found: $nginxExe"
    }

    Write-Host ''
    Write-Host 'Redis and GeoServer were left running because they may be used by other projects.' -ForegroundColor Cyan
}
catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if (-not $NoPause) {
        Read-Host 'Press Enter to close'
    }
    exit 1
}

if (-not $NoPause) {
    Read-Host 'Project shutdown finished. Press Enter to close this window'
}

