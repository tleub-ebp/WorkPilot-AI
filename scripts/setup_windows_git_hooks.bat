@echo off
REM Setup Git hooks for Windows development

echo 🚀 Setting up Git hooks for Windows...

REM Check if we're in the right directory
if not exist ".husky" (
    echo ❌ Error: .husky directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Configure Git to use Windows hooks
echo 🔧 Configuring Git hooks for Windows...
git config core.hooksPath .husky
if errorlevel 1 (
    echo ❌ Failed to configure Git hooks path
    pause
    exit /b 1
)

REM Make the pre-commit hook executable (copy Windows version)
echo 🔧 Setting up pre-commit hook...
copy .husky\pre-commit-windows.bat .husky\pre-commit.bat > nul
if errorlevel 1 (
    echo ❌ Failed to copy pre-commit hook
    pause
    exit /b 1
)

echo.
echo 🎉 Git hooks setup completed!
echo.
echo 📋 What's been set up:
echo    • Git hooks path configured to .husky
echo    • Pre-commit hook will run automatically before each commit
echo    • Automatic ruff formatting for backend code
echo    • Automatic ruff linting for backend code
echo    • Frontend lint and typecheck
echo.
echo 💡 To test the hook:
echo    git add .
echo    git commit -m "test: trigger pre-commit hooks"
echo.
echo 💡 To skip hooks (not recommended):
echo    git commit --no-verify
echo.
pause
