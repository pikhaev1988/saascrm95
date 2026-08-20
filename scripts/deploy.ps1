# Deploy analiz_gia to Beget (via git)
# For direct file sync without git use: .\scripts\sync.ps1
# Usage:
#   .\scripts\deploy.ps1              # git push + pull on server + restart
#   .\scripts\deploy.ps1 -SkipPush    # pull on server only (after manual push)
#   .\scripts\deploy.ps1 -TestOnly    # test SSH connection

param(
    [switch]$SkipPush,
    [switch]$TestOnly
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
$branch = if ($cfg["GIT_BRANCH"]) { $cfg["GIT_BRANCH"] } else { "main" }
$pythonBin = if ($cfg["PYTHON_BIN"]) { $cfg["PYTHON_BIN"] } else { "python3" }

Write-Host "Testing SSH ($hostAlias)..." -ForegroundColor Cyan
$test = ssh $hostAlias "echo OK"
if ($LASTEXITCODE -ne 0 -or $test -notmatch "OK") {
    Write-Error "SSH connection failed. Check ~/.ssh/config"
}
Write-Host "SSH: OK" -ForegroundColor Green

if ($TestOnly) {
    $remoteInfo = ssh $hostAlias "cd $deployPath && pwd && git rev-parse --short HEAD 2>/dev/null"
    Write-Host "Remote path: $deployPath"
    Write-Host $remoteInfo
    exit 0
}

if (-not $SkipPush) {
    Write-Host "git push origin $branch..." -ForegroundColor Cyan
    Push-Location $root
    try {
        git push origin $branch
        if ($LASTEXITCODE -ne 0) { throw "git push failed" }
    } finally {
        Pop-Location
    }
    Write-Host "Push: OK" -ForegroundColor Green
}

Write-Host "Updating server..." -ForegroundColor Cyan
$remoteCmd = @"
cd '$deployPath' && \
git fetch origin && \
git checkout '$branch' && \
git pull origin '$branch' && \
$pythonBin -m pip install -r requirements.txt -q && \
$pythonBin manage.py collectstatic --noinput && \
touch '$restartFile' && \
echo DEPLOY_OK
"@

$result = ssh $hostAlias $remoteCmd
$resultText = if ($null -eq $result) { "" } elseif ($result -is [System.Array]) { ($result | Out-String) } else { [string]$result }
if ($LASTEXITCODE -ne 0 -or ($resultText -notmatch "DEPLOY_OK")) {
    Write-Error "Server update failed:`n$resultText"
}

Write-Host "Deploy complete. App restarted." -ForegroundColor Green
$rev = ssh $hostAlias "cd '$deployPath' && git rev-parse --short HEAD"
Write-Host "Server revision: $rev"
