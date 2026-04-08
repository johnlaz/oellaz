@echo off
:: Odoo Email Link - Start
:: Double-click to launch. Runs as administrator automatically.

:: ── Reliable UAC self-elevation ──────────────────────────────────────────────
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrator privileges...
    goto UACPrompt
) else ( goto GotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /b

:GotAdmin
    pushd "%~dp0"

:: ── Python check ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://python.org
    pause
    exit /b 1
)

:: ── Auto-startup registration (runs once, silently) ──────────────────────────
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP_DIR%\OdooEmailLink.lnk
if not exist "%SHORTCUT%" (
    powershell -WindowStyle Hidden -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath='%~dpnx0'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Description='OdooEmailLink background servers'; $s.Save()" >nul 2>&1
)

:: ── Stop any existing instances ──────────────────────────────────────────────
powershell -WindowStyle Hidden -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 7843 -ErrorAction SilentlyContinue).OwningProcess -ErrorAction SilentlyContinue" >nul 2>&1
powershell -WindowStyle Hidden -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 7842 -ErrorAction SilentlyContinue).OwningProcess -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 1 /nobreak >nul

:: ── Start servers ─────────────────────────────────────────────────────────────
powershell -WindowStyle Hidden -Command "Start-Process pythonw -ArgumentList 'imap_server.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden -ErrorAction SilentlyContinue"
if errorlevel 1 (
    powershell -WindowStyle Hidden -Command "Start-Process python -ArgumentList 'imap_server.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden"
)

:: ── Wait then open app ───────────────────────────────────────────────────────
timeout /t 3 /nobreak >nul
set "FILE_URL=file:///%~dp0index.html"
set "FILE_URL=%FILE_URL:\=/%"
start "" "chrome.exe" --disk-cache-size=1 "%FILE_URL%" 2>nul
if errorlevel 1 ( start "" "index.html" )
exit /b 0
