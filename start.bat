@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title KeenScreen Studio — Auto-Syncing & Launching...

:: ============================================================================
:: KeenScreen Studio — Injected PowerShell Auto-Sync from Public GitHub Repo
:: Repo: https://github.com/Ganeshmakad/KeenScreen
:: Checks GitHub on every launch, pulls any code updates automatically
:: (even on PCs without Git installed!), and then launches the GUI silently.
:: ============================================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop'; " ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
  "$repoOwner = 'Ganeshmakad'; " ^
  "$repoName  = 'KeenScreen'; " ^
  "$branch    = 'main'; " ^
  "$workDir   = '%~dp0'.TrimEnd('\'); " ^
  "$syncFile  = Join-Path $workDir '.sync_commit'; " ^
  "$reqHashFile = Join-Path $workDir '.sync_req_hash'; " ^
  "Write-Host '[KeenScreen Auto-Sync] Checking https://github.com/' + $repoOwner + '/' + $repoName + ' for updates...' -ForegroundColor Cyan; " ^
  "try { " ^
  "  $headers = @{ 'User-Agent' = 'KeenScreen-AutoSync/1.2'; 'Cache-Control' = 'no-cache' }; " ^
  "  $apiUrl  = \"https://api.github.com/repos/$repoOwner/$repoName/commits/$branch\"; " ^
  "  $commitResp = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 6; " ^
  "  $remoteSha  = $commitResp.sha; " ^
  "  $localSha   = if (Test-Path $syncFile) { (Get-Content $syncFile -Raw).Trim() } else { '' }; " ^
  "  $coreExists = (Test-Path (Join-Path $workDir 'keyer_engine.py')) -and (Test-Path (Join-Path $workDir 'app_gui.py')); " ^
  "  if (($remoteSha -ne $localSha) -or (-not $coreExists)) { " ^
  "    Write-Host ('[KeenScreen Auto-Sync] Update detected (' + $remoteSha.Substring(0,7) + '). Syncing latest files...') -ForegroundColor Yellow; " ^
  "    $files = @('keyer_engine.py','app_gui.py','cli.py','requirements.txt','Launch_GUI.bat','Launch_GUI_Silent.vbs','setup.bat','version.json'); " ^
  "    try { " ^
  "      $verUrl = \"https://raw.githubusercontent.com/$repoOwner/$repoName/$branch/version.json?cb=\" + [Guid]::NewGuid().ToString('N'); " ^
  "      $verObj = Invoke-RestMethod -Uri $verUrl -Headers $headers -TimeoutSec 5; " ^
  "      if ($verObj.tracked_files) { $files = $verObj.tracked_files } " ^
  "    } catch {} " ^
  "    foreach ($f in $files) { " ^
  "      $rawUrl = \"https://raw.githubusercontent.com/$repoOwner/$repoName/$branch/$f?cb=\" + [Guid]::NewGuid().ToString('N'); " ^
  "      $tmpDst = Join-Path $workDir ($f + '.tmp_sync'); " ^
  "      $finalDst = Join-Path $workDir $f; " ^
  "      Invoke-WebRequest -Uri $rawUrl -Headers $headers -OutFile $tmpDst -UseBasicParsing -TimeoutSec 10; " ^
  "      if ((Test-Path $tmpDst) -and ((Get-Item $tmpDst).Length -gt 0)) { " ^
  "        Move-Item -Path $tmpDst -Destination $finalDst -Force; " ^
  "        Write-Host ('  -> Updated ' + $f) -ForegroundColor Green; " ^
  "      } " ^
  "    } " ^
  "    $reqPath = Join-Path $workDir 'requirements.txt'; " ^
  "    if (Test-Path $reqPath) { " ^
  "      $newHash = (Get-FileHash $reqPath -Algorithm SHA256).Hash; " ^
  "      $oldHash = if (Test-Path $reqHashFile) { (Get-Content $reqHashFile -Raw).Trim() } else { '' }; " ^
  "      if ($newHash -ne $oldHash) { " ^
  "        Write-Host '[KeenScreen Auto-Sync] Updating Python packages...' -ForegroundColor Yellow; " ^
  "        & python -m pip install -r $reqPath --quiet; " ^
  "        Set-Content -Path $reqHashFile -Value $newHash -NoNewline; " ^
  "      } " ^
  "    } " ^
  "    Set-Content -Path $syncFile -Value $remoteSha -NoNewline; " ^
  "    Write-Host ('[KeenScreen Auto-Sync] Synced to latest commit ' + $remoteSha.Substring(0,7) + ' successfully!') -ForegroundColor Green; " ^
  "  } else { " ^
  "    Write-Host ('[KeenScreen Auto-Sync] Up to date (' + $remoteSha.Substring(0,7) + ').') -ForegroundColor Green; " ^
  "  } " ^
  "} catch { " ^
  "  Write-Host ('[KeenScreen Auto-Sync] Offline or repo not yet populated (' + $_.Exception.Message + '). Using local version.') -ForegroundColor DarkYellow; " ^
  "}"

:: Launch the GUI completely silently in the background (zero console window open during work)
if exist "%~dp0Launch_GUI_Silent.vbs" (
    wscript.exe "%~dp0Launch_GUI_Silent.vbs"
) else (
    start "" pythonw.exe "%~dp0app_gui.py"
)
exit /b 0
