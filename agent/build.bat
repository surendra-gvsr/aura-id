@echo off
REM agent/build.bat — full build pipeline

echo [1/3] PyInstaller...
pyinstaller --clean aura_agent.spec
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo [2/3] Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\aura-agent.iss
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo [3/3] Signing...
call installer\sign.bat
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Build complete: dist\AuraAgent-Setup-0.1.0.exe
