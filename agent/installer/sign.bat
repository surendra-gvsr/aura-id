@echo off
REM agent/installer/sign.bat — sign .exe and installer with EV cert
REM Requires: signtool.exe in PATH (Windows SDK), SIGNING_CERT_THUMBPRINT env var set

set EXE=..\dist\AuraAgent.exe
set INSTALLER=..\dist\AuraAgent-Setup-0.1.0.exe

if "%SIGNING_CERT_THUMBPRINT%"=="" (
    echo ERROR: Set SIGNING_CERT_THUMBPRINT to your EV cert thumbprint.
    exit /b 1
)

echo Signing "%EXE%"...
signtool sign /sha1 "%SIGNING_CERT_THUMBPRINT%" ^
    /tr https://timestamp.digicert.com /td sha256 /fd sha256 "%EXE%"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Signing "%INSTALLER%"...
signtool sign /sha1 "%SIGNING_CERT_THUMBPRINT%" ^
    /tr https://timestamp.digicert.com /td sha256 /fd sha256 "%INSTALLER%"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo All artifacts signed.
