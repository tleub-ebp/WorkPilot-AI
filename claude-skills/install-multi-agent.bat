@echo off
REM Script d'installation multi-agents pour Skills EBP (Windows)
REM Basé sur l'approche de Aaronontheweb/dotnet-skills

echo 🚀 Installation des Skills EBP Multi-Agents...
echo ==================================

REM Vérifier si nous sommes dans le bon répertoire
if not exist "claude-skills" (
    echo ❌ Erreur: Exécutez ce script depuis le répertoire racine d'Auto-Claude_EBP
    pause
    exit /b 1
)

REM Fonction pour créer les répertoires si nécessaire
:CREATE_DIR
if not exist "%~1" (
    mkdir "%~1"
    echo ✅ Créé: %~1
)
goto :EOF

REM Installation Claude Code
:INSTALL_CLAUDE_CODE
echo 🔧 Configuration Claude Code...

call :CREATE_DIR "%USERPROFILE%\.claude\skills"
call :CREATE_DIR "%USERPROFILE%\.claude\agents"

REM Copier les skills
if exist "claude-skills\skills" (
    xcopy /E /I /Y "claude-skills\skills\*" "%USERPROFILE%\.claude\skills\"
    echo ✅ Skills copiés avec succès
)

REM Copier les agents
if exist "claude-skills\agents" (
    xcopy /E /I /Y "claude-skills\agents\*" "%USERPROFILE%\.claude\agents\"
    echo ✅ Agents copiés avec succès
)

REM Créer le fichier de configuration Claude Code
echo # Claude Code Configuration EBP > "%USERPROFILE%\.claude\config.yaml"
echo skills: >> "%USERPROFILE%\.claude\config.yaml"
echo   - net-developer >> "%USERPROFILE%\.claude\config.yaml"
echo   - akka-net-patterns >> "%USERPROFILE%\.claude\config.yaml"
echo   - aspire-orchestration >> "%USERPROFILE%\.claude\config.yaml"
echo   - benchmark-dotnet >> "%USERPROFILE%\.claude\config.yaml"
echo   - testcontainers-integration >> "%USERPROFILE%\.claude\config.yaml"
echo   - mcp-builder >> "%USERPROFILE%\.claude\config.yaml"
echo   - webapp-testing >> "%USERPROFILE%\.claude\config.yaml"
echo   - brand-guidelines >> "%USERPROFILE%\.claude\config.yaml"
echo   - business-comms >> "%USERPROFILE%\.claude\config.yaml"
echo. >> "%USERPROFILE%\.claude\config.yaml"
echo agents: >> "%USERPROFILE%\.claude\config.yaml"
echo   - net-architect >> "%USERPROFILE%\.claude\config.yaml"
echo   - bmad-net-architect >> "%USERPROFILE%\.claude\config.yaml"
echo   - performance-analyst >> "%USERPROFILE%\.claude\config.yaml"
echo. >> "%USERPROFILE%\.claude\config.yaml"
echo auto_invoke: true >> "%USERPROFILE%\.claude\config.yaml"
echo context_awareness: true >> "%USERPROFILE%\.claude\config.yaml"
echo business_focus: ebp >> "%USERPROFILE%\.claude\config.yaml"
echo net_version: 10 >> "%USERPROFILE%\.claude\config.yaml"
echo performance_optimization: true >> "%USERPROFILE%\.claude\config.yaml"
echo modern_patterns: true >> "%USERPROFILE%\.claude\config.yaml"

echo ✅ Claude Code configuré
goto :EOF

REM Installation GitHub Copilot (projet)
:INSTALL_GITHUB_COPILOT_PROJECT
echo 🔧 Configuration GitHub Copilot (niveau projet)...

call :CREATE_DIR ".github\skills"
call :CREATE_DIR ".github\agents"

REM Copier les skills
if exist "claude-skills\skills" (
    xcopy /E /I /Y "claude-skills\skills\*" ".github\skills\"
    echo ✅ Skills copiés avec succès
)

REM Copier les agents
if exist "claude-skills\agents" (
    xcopy /E /I /Y "claude-skills\agents\*" ".github\agents\"
    echo ✅ Agents copiés avec succès
)

REM Créer le fichier de configuration Copilot
echo # GitHub Copilot Configuration EBP > ".github\copilot.yml"
echo skills: >> ".github\copilot.yml"
echo   enabled: true >> ".github\copilot.yml"
echo   paths: >> ".github\copilot.yml"
echo     - .github\skills\* >> ".github\copilot.yml"
echo     - claude-skills\skills\* >> ".github\copilot.yml"
echo. >> ".github\copilot.yml"
echo agents: >> ".github\copilot.yml"
echo   auto_invoke: true >> ".github\copilot.yml"
echo   personalities: >> ".github\copilot.yml"
echo     - net-architect >> ".github\copilot.yml"
echo     - bmad-net-architect >> ".github\copilot.yml"
echo     - performance-analyst >> ".github\copilot.yml"
echo     - net-developer >> ".github\copilot.yml"
echo     - akka-net-specialist >> ".github\copilot.yml"
echo     - benchmark-designer >> ".github\copilot.yml"
echo     - testcontainers-expert >> ".github\copilot.yml"
echo. >> ".github\copilot.yml"
echo business_context: ebp >> ".github\copilot.yml"
echo architecture_focus: clean_architecture >> ".github\copilot.yml"
echo performance_optimization: true >> ".github\copilot.yml"
echo net_version: 10 >> ".github\copilot.yml"
echo modern_patterns: immutability,type_safety,performance >> ".github\copilot.yml"
echo distributed_systems: akka_net,aspire,testcontainers >> ".github\copilot.yml"

echo ✅ GitHub Copilot (projet) configuré
goto :EOF

REM Installation GitHub Copilot (global)
:INSTALL_GITHUB_COPILOT_GLOBAL
echo 🔧 Configuration GitHub Copilot (global)...

call :CREATE_DIR "%USERPROFILE%\.copilot\skills"
call :CREATE_DIR "%USERPROFILE%\.copilot\agents"

REM Copier les skills
if exist "claude-skills\skills" (
    xcopy /E /I /Y "claude-skills\skills\*" "%USERPROFILE%\.copilot\skills\"
    echo ✅ Skills copiés avec succès
)

REM Copier les agents
if exist "claude-skills\agents" (
    xcopy /E /I /Y "claude-skills\agents\*" "%USERPROFILE%\.copilot\agents\"
    echo ✅ Agents copiés avec succès
)

echo ✅ GitHub Copilot (global) configuré
goto :EOF

REM Installation OpenCode
:INSTALL_OPENCODE
echo 🔧 Configuration OpenCode...

call :CREATE_DIR "%USERPROFILE%\.config\opencode\skills"
call :CREATE_DIR "%USERPROFILE%\.config\opencode\agents"

REM Copier les skills avec la structure correcte pour OpenCode
echo 📋 Traitement des skills pour OpenCode...

REM Traiter chaque skill
for /d %%D in ("claude-skills\skills\*") do (
    if exist "%%D\SKILL.md" (
        REM Extraire le nom du skill depuis le fichier SKILL.md
        for /f "tokens=2 delims=: " %%A in ('findstr /R "^name:" "%%D\SKILL.md"') do (
            set "skill_name=%%A"
        )
        
        if defined skill_name (
            REM Nettoyer le nom du skill
            set "skill_name=!skill_name: =!"
            set "skill_name=!skill_name: =!"
            
            REM Créer le répertoire et copier le fichier
            call :CREATE_DIR "%USERPROFILE%\.config\opencode\skills\!skill_name!"
            copy "%%D\SKILL.md" "%USERPROFILE%\.config\opencode\skills\!skill_name!\SKILL.md" >nul
            echo   ✅ Skill: !skill_name!
        )
    )
)

REM Copier les agents
if exist "claude-skills\agents" (
    xcopy /E /I /Y "claude-skills\agents\*" "%USERPROFILE%\.config\opencode\agents\"
    echo ✅ Agents copiés avec succès
)

REM Créer la configuration OpenCode
echo # OpenCode Configuration EBP > "%USERPROFILE%\.config\opencode\config.yaml"
echo skills_directory: ~/.config/opencode/skills >> "%USERPROFILE%\.config\opencode\config.yaml"
echo agents_directory: ~/.config/opencode/agents >> "%USERPROFILE%\.config\opencode\config.yaml"
echo auto_load: true >> "%USERPROFILE%\.config\opencode\config.yaml"
echo business_focus: ebp >> "%USERPROFILE%\.config\opencode\config.yaml"
echo architecture_patterns: clean_architecture, ddd, microservices >> "%USERPROFILE%\.config\opencode\config.yaml"
echo performance_monitoring: true >> "%USERPROFILE%\.config\opencode\config.yaml"

echo ✅ OpenCode configuré
goto :EOF

REM Installation Cursor IDE
:INSTALL_CURSOR
echo 🔧 Configuration Cursor IDE...

call :CREATE_DIR "%USERPROFILE%\.cursor\skills"
call :CREATE_DIR "%USERPROFILE%\.cursor\agents"

REM Copier les skills
if exist "claude-skills\skills" (
    xcopy /E /I /Y "claude-skills\skills\*" "%USERPROFILE%\.cursor\skills\"
    echo ✅ Skills copiés avec succès
)

REM Copier les agents
if exist "claude-skills\agents" (
    xcopy /E /I /Y "claude-skills\agents\*" "%USERPROFILE%\.cursor\agents\"
    echo ✅ Agents copiés avec succès
)

REM Créer la configuration Cursor
echo { > "%USERPROFILE%\.cursor\config.json"
echo   "skills": { >> "%USERPROFILE%\.cursor\config.json"
echo     "enabled": true, >> "%USERPROFILE%\.cursor\config.json"
echo     "directory": "~/.cursor/skills", >> "%USERPROFILE%\.cursor\config.json"
echo     "auto_load": true, >> "%USERPROFILE%\.cursor\config.json"
echo     "ebp_focus": true >> "%USERPROFILE%\.cursor\config.json"
echo   }, >> "%USERPROFILE%\.cursor\config.json"
echo   "agents": { >> "%USERPROFILE%\.cursor\config.json"
echo     "enabled": true, >> "%USERPROFILE%\.cursor\config.json"
echo     "directory": "~/.cursor/agents", >> "%USERPROFILE%\.cursor\config.json"
echo     "auto_invoke": true >> "%USERPROFILE%\.cursor\config.json"
echo   }, >> "%USERPROFILE%\.cursor\config.json"
echo   "business_context": { >> "%USERPROFILE%\.cursor\config.json"
echo     "domain": "ebp", >> "%USERPROFILE%\.cursor\config.json"
echo     "architecture": "clean_architecture", >> "%USERPROFILE%\.cursor\config.json"
echo     "performance": "optimized" >> "%USERPROFILE%\.cursor\config.json"
echo   } >> "%USERPROFILE%\.cursor\config.json"
echo } >> "%USERPROFILE%\.cursor\config.json"

echo ✅ Cursor IDE configuré
goto :EOF

REM Validation des installations
:VALIDATE_INSTALLATION
echo 🔍 Validation des installations...

set platforms=0

REM Vérifier Claude Code
if exist "%USERPROFILE%\.claude\skills" (
    echo 📊 Claude Code ✅
    set /a platforms+=1
)

REM Vérifier GitHub Copilot
if exist ".github\skills" (
    echo 📊 GitHub Copilot (projet) ✅
    set /a platforms+=1
) else if exist "%USERPROFILE%\.copilot\skills" (
    echo 📊 GitHub Copilot (global) ✅
    set /a platforms+=1
)

REM Vérifier OpenCode
if exist "%USERPROFILE%\.config\opencode\skills" (
    echo 📊 OpenCode ✅
    set /a platforms+=1
)

REM Vérifier Cursor
if exist "%USERPROFILE%\.cursor\skills" (
    echo 📊 Cursor IDE ✅
    set /a platforms+=1
)

REM Compter les skills installés
set skill_count=0
if exist "claude-skills\skills" (
    for /d %%D in ("claude-skills\skills\*") do (
        if exist "%%D\SKILL.md" set /a skill_count+=1
    )
)

REM Compter les agents installés
set agent_count=0
if exist "claude-skills\agents" (
    for %%F in ("claude-skills\agents\*.md") do set /a agent_count+=1
)

echo 📈 Skills installés: %skill_count%
echo 🤖 Agents installés: %agent_count%
goto :EOF

REM Menu d'installation
:SHOW_MENU
echo 🎯 Sélectionnez les plateformes à installer:
echo 1) Claude Code
echo 2) GitHub Copilot (projet)
echo 3) GitHub Copilot (global)
echo 4) OpenCode
echo 5) Cursor IDE
echo 6) Toutes les plateformes
echo 7) Personnalisé
echo 0) Quitter
echo.
set /p choice="Votre choix (0-7): "

if "%choice%"=="1" (
    call :INSTALL_CLAUDE_CODE
) else if "%choice%"=="2" (
    call :INSTALL_GITHUB_COPILOT_PROJECT
) else if "%choice%"=="3" (
    call :INSTALL_GITHUB_COPILOT_GLOBAL
) else if "%choice%"=="4" (
    call :INSTALL_OPENCODE
) else if "%choice%"=="5" (
    call :INSTALL_CURSOR
) else if "%choice%"=="6" (
    call :INSTALL_CLAUDE_CODE
    call :INSTALL_GITHUB_COPILOT_PROJECT
    call :INSTALL_OPENCODE
    call :INSTALL_CURSOR
) else if "%choice%"=="7" (
    echo Installation personnalisée:
    set /p claude="Claude Code? (y/n): "
    set /p copilot_proj="GitHub Copilot (projet)? (y/n): "
    set /p copilot_global="GitHub Copilot (global)? (y/n): "
    set /p opencode="OpenCode? (y/n): "
    set /p cursor="Cursor IDE? (y/n): "
    
    if /i "%claude%"=="y" call :INSTALL_CLAUDE_CODE
    if /i "%copilot_proj%"=="y" call :INSTALL_GITHUB_COPILOT_PROJECT
    if /i "%copilot_global%"=="y" call :INSTALL_GITHUB_COPILOT_GLOBAL
    if /i "%opencode%"=="y" call :INSTALL_OPENCODE
    if /i "%cursor%"=="y" call :INSTALL_CURSOR
) else if "%choice%"=="0" (
    echo Au revoir!
    pause
    exit /b 0
) else (
    echo Choix invalide
    goto :SHOW_MENU
)

goto :EOF

REM Installation automatique (toutes les plateformes)
:INSTALL_ALL
echo 🚀 Installation automatique de toutes les plateformes...

call :INSTALL_CLAUDE_CODE
call :INSTALL_GITHUB_COPILOT_PROJECT
call :INSTALL_OPENCODE
call :INSTALL_CURSOR

call :VALIDATE_INSTALLATION
goto :EOF

REM Point d'entrée principal
:MAIN
echo 🎯 Skills EBP Multi-Agents Installation
echo =======================================
echo.

REM Activer l'expansion des variables locales
setlocal enabledelayedexpansion

REM Vérifier les arguments
if "%1"=="--all" (
    call :INSTALL_ALL
) else if "%1"=="--claude" (
    call :INSTALL_CLAUDE_CODE
) else if "%1"=="--copilot" (
    call :INSTALL_GITHUB_COPILOT_PROJECT
) else if "%1"=="--opencode" (
    call :INSTALL_OPENCODE
) else if "%1"=="--cursor" (
    call :INSTALL_CURSOR
) else if "%1"=="--menu" (
    call :SHOW_MENU
) else (
    echo Usage: %~nx0 [OPTION]
    echo Options:
    echo   --all      Installer toutes les plateformes
    echo   --menu     Menu interactif
    echo   --claude   Installer Claude Code uniquement
    echo   --copilot  Installer GitHub Copilot uniquement
    echo   --opencode Installer OpenCode uniquement
    echo   --cursor   Installer Cursor IDE uniquement
    echo.
    echo Aucune option fournie, installation de toutes les plateformes...
    call :INSTALL_ALL
)

call :VALIDATE_INSTALLATION

echo.
echo 🎉 Installation terminée!
echo 📚 Consultez claude-skills\MULTI_AGENT_GUIDE.md pour plus d'informations
echo 🔄 Pour mettre à jour: claude-skills\update-multi-agent.bat
pause
