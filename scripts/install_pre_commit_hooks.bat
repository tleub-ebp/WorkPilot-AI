@echo off
REM Install pre-commit hooks for Windows
echo 🚀 Setting up pre-commit hooks for automatic code formatting...

REM Check if .pre-commit-config.yaml exists
if not exist ".pre-commit-config.yaml" (
    echo ❌ Error: .pre-commit-config.yaml not found in current directory
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Install pre-commit
echo 📦 Installing pre-commit...
python -m pip install pre-commit
if errorlevel 1 (
    echo ❌ Failed to install pre-commit
    pause
    exit /b 1
)

REM Install the hooks
echo 🔧 Installing pre-commit hooks...
pre-commit install
if errorlevel 1 (
    echo ❌ Failed to install pre-commit hooks
    pause
    exit /b 1
)

echo.
echo 🎉 Pre-commit hooks installed successfully!
echo.
echo 📋 What's been set up:
echo    • Automatic ruff linting and fixing for backend code
echo    • Automatic ruff formatting for backend code
echo    • Hooks will run automatically before each commit
echo.
echo 💡 To run hooks manually on all files:
echo    pre-commit run --all-files
echo.
echo 💡 To skip hooks (not recommended):
echo    git commit --no-verify
echo.
pause
