@echo off
REM Windows pre-commit hook for automatic code formatting

echo 🔧 Running ruff format on backend...
python -m ruff format apps/backend/
if errorlevel 1 (
    echo ❌ Ruff format failed
    exit /b 1
)

echo 🔧 Running ruff check on backend...
ruff check --fix .
if errorlevel 1 (
    echo ❌ Ruff check failed
    exit /b 1
)

echo 🔧 Running frontend lint and typecheck...
cd apps/frontend
call pnpm lint
if errorlevel 1 (
    echo ❌ Frontend lint failed
    exit /b 1
)

call pnpm typecheck
if errorlevel 1 (
    echo ❌ Frontend typecheck failed
    exit /b 1
)

echo ✅ All pre-commit checks passed!
