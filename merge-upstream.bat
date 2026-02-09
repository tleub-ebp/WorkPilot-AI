@echo off
REM Merge upstream changes from Auto-Claude into your fork
REM This is a wrapper script that calls the PowerShell version
REM 
REM Usage:
REM   merge-upstream.bat
REM   merge-upstream.bat develop
REM   merge-upstream.bat main --skip-push

setlocal enabledelayedexpansion

REM Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: PowerShell is not available in PATH
    exit /b 1
)

REM Parse arguments
set "BRANCH=main"
set "SKIP_PUSH="

if not "%~1"=="" (
    if "%~1"=="--skip-push" (
        set "SKIP_PUSH=-SkipPush"
    ) else (
        set "BRANCH=%~1"
        if not "%~2"=="" (
            if "%~2"=="--skip-push" (
                set "SKIP_PUSH=-SkipPush"
            )
        )
    )
)

REM Get the script directory
set "SCRIPT_DIR=%~dp0"

REM Execute PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%merge-upstream.ps1" -Branch %BRANCH% %SKIP_PUSH%
if %ERRORLEVEL% neq 0 (
    exit /b %ERRORLEVEL%
)

exit /b 0
