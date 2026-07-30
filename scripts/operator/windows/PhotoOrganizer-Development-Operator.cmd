@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "CONTROLLER=%~dp0PhotoOrganizer-Development-Operator.ps1"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%CONTROLLER%" (
    echo ERROR: The PowerShell controller is missing.
    echo Expected: "%CONTROLLER%"
    pause
    exit /b 1
)

if not exist "%POWERSHELL_EXE%" (
    echo ERROR: Windows PowerShell was not found.
    echo Expected: "%POWERSHELL_EXE%"
    pause
    exit /b 1
)

if /I "%~1"=="-SelfTest" (
    if not "%~2"=="" (
        echo ERROR: -SelfTest accepts no additional arguments.
        exit /b 2
    )
    "%POWERSHELL_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" -SelfTest
    exit /b %ERRORLEVEL%
)

if not "%~1"=="" (
    echo ERROR: This launcher accepts no arguments.
    echo Run it by double-clicking, or use -SelfTest for non-mutating validation.
    pause
    exit /b 2
)

"%POWERSHELL_EXE%" -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%CONTROLLER%" -LaunchDetached
if errorlevel 1 (
    echo ERROR: The Photo Organizer Development Operator could not be launched.
    pause
    exit /b 1
)

exit /b 0
