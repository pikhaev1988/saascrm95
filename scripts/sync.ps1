# Прямая синхронизация файлов на Beget (без git)
# Usage:
#   .\scripts\sync.ps1              # sync all + restart app
#   .\scripts\sync.ps1 -TestOnly      # test SSH connection
#   .\scripts\sync.ps1 -NoRestart     # sync without restart
#   .\scripts\sync.ps1 -Paths users,exams  # sync selected folders only

param(
    [switch]$TestOnly,
    [switch]$NoRestart,
    [string[]]$Paths
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root ".env.deploy"

if (-not (Test-Path $envFile)) {
    Write-Error ".env.deploy not found. Copy .env.deploy.example to .env.deploy"
}

$cfg = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Count -eq 2) { $cfg[$parts[0].Trim()] = $parts[1].Trim() }
}

$hostAlias = $cfg["DEPLOY_HOST"]
$deployPath = $cfg["DEPLOY_PATH"]
$restartFile = $cfg["RESTART_FILE"]
$pythonBin = if ($cfg["PYTHON_BIN"]) { $cfg["PYTHON_BIN"] } else { "python3" }

$excludes = @(
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".env",
    ".env.deploy",
    ".env.server.tmp",
    "db.sqlite3",
    ".idea",
    "staticfiles",
    "media",
    "tmp",
    "*.pyc"
)

Write-Host "Testing SSH ($hostAlias)..." -ForegroundColor Cyan
$test = ssh $hostAlias "echo OK"
if ($LASTEXITCODE -ne 0 -or $test -notmatch "OK") {
    Write-Error "SSH connection failed. Check ~/.ssh/config"
}
Write-Host "SSH: OK" -ForegroundColor Green

if ($TestOnly) {
    $remoteInfo = ssh $hostAlias "ls -la '$deployPath/manage.py' && du -sh '$deployPath'"
    Write-Host "Remote path: $deployPath"
    Write-Host $remoteInfo
    exit 0
}

# PowerShell corrupts binary pipes (tar | ssh), so write archive to a temp file and scp it.
$archive = Join-Path $env:TEMP "analiz_gia_sync.tar"
$tarArgs = @("-cf", $archive, "--format=ustar")
foreach ($ex in $excludes) {
    $tarArgs += "--exclude=$ex"
}

if ($Paths -and $Paths.Count -gt 0) {
    Write-Host "Syncing paths: $($Paths -join ', ')" -ForegroundColor Cyan
    $tarArgs += "-C"
    $tarArgs += $root
    $tarArgs += $Paths
} else {
    Write-Host "Syncing project to $deployPath ..." -ForegroundColor Cyan
    $tarArgs += "-C"
    $tarArgs += $root
    $tarArgs += "."
}

try {
    & tar @tarArgs
    if ($LASTEXITCODE -ne 0) {
        throw "tar create failed"
    }
    scp $archive "${hostAlias}:/tmp/analiz_gia_sync.tar"
    if ($LASTEXITCODE -ne 0) {
        throw "scp upload failed"
    }
    ssh $hostAlias "cd '$deployPath' && tar -xf /tmp/analiz_gia_sync.tar && rm -f /tmp/analiz_gia_sync.tar"
    if ($LASTEXITCODE -ne 0) {
        throw "File sync failed"
    }
} finally {
    if (Test-Path $archive) { Remove-Item $archive -Force }
}

Write-Host "Sync: OK" -ForegroundColor Green

ssh $hostAlias "cd '$deployPath' && $pythonBin -m pip install -r requirements.txt -q && $pythonBin manage.py collectstatic --noinput"
if ($LASTEXITCODE -ne 0) {
    Write-Error "collectstatic failed on server"
}

if (-not $NoRestart) {
    ssh $hostAlias "touch '$restartFile'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to restart app (touch restart.txt)"
    }
    Write-Host "App restarted." -ForegroundColor Green
}

Write-Host "Done." -ForegroundColor Green
