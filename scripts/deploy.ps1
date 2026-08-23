# Deploy analiz_gia to Beget (via git) — safe mode: DB backup before migrate
# For direct file sync without git use: .\scripts\sync.ps1
# Usage:
#   .\scripts\deploy.ps1              # git push + pull on server + backup + migrate + restart
#   .\scripts\deploy.ps1 -SkipPush    # pull on server only (after manual push)
#   .\scripts\deploy.ps1 -TestOnly    # test SSH connection
#   .\scripts\deploy.ps1 -SkipMigrate # update code without migrate

param(
    [switch]$SkipPush,
    [switch]$TestOnly,
    [switch]$SkipMigrate
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
$backupDir = if ($cfg["BACKUP_DIR"]) { $cfg["BACKUP_DIR"] } else { "/home/p/pikhae0x/backups/analiz_gia" }

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

if ($SkipMigrate) {
    $migratePart = "echo SKIP_MIGRATE"
} else {
    $migratePart = @"
echo '--- DB backup ---' && \
mkdir -p '$backupDir' && \
STAMP=`$(date +%Y%m%d_%H%M%S) && \
if [ -f db.sqlite3 ]; then \
  cp -a db.sqlite3 '$backupDir/pre_deploy_`$STAMP.sqlite3' && \
  SIZE=`$(wc -c < '$backupDir/pre_deploy_`$STAMP.sqlite3') && \
  echo "SQLite backup: `$SIZE bytes -> pre_deploy_`$STAMP.sqlite3" && \
  test "`$SIZE" -gt 1024; \
elif [ -f .env ]; then \
  set -a && . ./.env && set +a && \
  if [ "`${USE_SQLITE:-True}" != "True" ] && [ -n "`$DB_NAME" ] && command -v pg_dump >/dev/null 2>&1; then \
    pg_dump -h "`${DB_HOST:-localhost}" -p "`${DB_PORT:-5432}" -U "`$DB_USER" -Fc "`$DB_NAME" -f '$backupDir/pre_deploy_`$STAMP.dump' && \
    SIZE=`$(wc -c < '$backupDir/pre_deploy_`$STAMP.dump') && \
    echo "PostgreSQL backup: `$SIZE bytes -> pre_deploy_`$STAMP.dump" && \
    test "`$SIZE" -gt 102400; \
  else \
    echo 'WARNING: no db.sqlite3 / pg_dump target — aborting for safety' && exit 1; \
  fi; \
else \
  echo 'WARNING: cannot locate DB for backup — aborting for safety' && exit 1; \
fi && \
ls -lt '$backupDir' | head -n 6 && \
echo '--- migrate ---' && \
$pythonBin manage.py migrate --noinput
"@
}

Write-Host "Updating server (backup + update)..." -ForegroundColor Cyan
$remoteCmd = @"
set -e
cd '$deployPath'
echo '--- pre-deploy revision ---'
git rev-parse --short HEAD
git fetch origin
git checkout '$branch'
git pull origin '$branch'
echo '--- post-pull revision ---'
git rev-parse --short HEAD
$pythonBin -m pip install -r requirements.txt -q
$migratePart
$pythonBin manage.py collectstatic --noinput
touch '$restartFile'
echo DEPLOY_OK
"@

$result = ssh $hostAlias $remoteCmd
$resultText = if ($null -eq $result) { "" } elseif ($result -is [System.Array]) { ($result | Out-String) } else { [string]$result }
Write-Host $resultText
if ($LASTEXITCODE -ne 0 -or ($resultText -notmatch "DEPLOY_OK")) {
    Write-Error "Server update failed:`n$resultText"
}

Write-Host "Deploy complete. App restarted." -ForegroundColor Green
$rev = ssh $hostAlias "cd '$deployPath' && git rev-parse --short HEAD"
Write-Host "Server revision: $rev"
