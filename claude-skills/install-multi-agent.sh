#!/bin/bash
# Script d'installation multi-agents pour Skills EBP
# Basé sur l'approche de Aaronontheweb/dotnet-skills

set -e

echo "🚀 Installation des Skills EBP Multi-Agents..."
echo "=================================="

# Vérifier si nous sommes dans le bon répertoire
if [ ! -d "claude-skills" ]; then
    echo "❌ Erreur: Exécutez ce script depuis le répertoire racine d'Auto-Claude_EBP"
    exit 1
fi

# Fonction pour créer les répertoires si nécessaire
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo "✅ Créé: $1"
    fi
}

# Fonction pour copier les skills
copy_skills() {
    local target_dir="$1"
    echo "📋 Copie des skills vers: $target_dir"
    
    # Copier tous les skills
    if [ -d "claude-skills/skills" ]; then
        cp -r claude-skills/skills/* "$target_dir/"
        echo "✅ Skills copiés avec succès"
    fi
    
    # Copier les agents
    if [ -d "claude-skills/agents" ]; then
        cp -r claude-skills/agents/* "$target_dir/"
        echo "✅ Agents copiés avec succès"
    fi
}

# Installation Claude Code
install_claude_code() {
    echo "🔧 Configuration Claude Code..."
    
    create_dir "$HOME/.claude/skills"
    create_dir "$HOME/.claude/agents"
    
    copy_skills "$HOME/.claude/skills"
    
    # Créer le fichier de configuration Claude Code
    cat > "$HOME/.claude/config.yaml" << EOF
# Claude Code Configuration EBP
skills:
  - net-developer
  - akka-net-patterns
  - aspire-orchestration
  - benchmark-dotnet
  - testcontainers-integration
  - mcp-builder
  - webapp-testing
  - brand-guidelines
  - business-comms

agents:
  - net-architect
  - bmad-net-architect
  - performance-analyst

auto_invoke: true
context_awareness: true
business_focus: ebp
net_version: 10
performance_optimization: true
modern_patterns: true
EOF
    
    echo "✅ Claude Code configuré"
}

# Installation GitHub Copilot (projet)
install_github_copilot_project() {
    echo "🔧 Configuration GitHub Copilot (niveau projet)..."
    
    create_dir ".github/skills"
    create_dir ".github/agents"
    
    copy_skills ".github/skills"
    
    # Créer le fichier de configuration Copilot
    cat > ".github/copilot.yml" << EOF
# GitHub Copilot Configuration EBP
skills:
  enabled: true
  paths:
    - .github/skills/*
    - claude-skills/skills/*

agents:
  auto_invoke: true
  personalities:
    - net-architect
    - bmad-net-architect
    - performance-analyst
    - net-developer
    - akka-net-specialist
    - benchmark-designer
    - testcontainers-expert

business_context: ebp
architecture_focus: clean_architecture
performance_optimization: true
net_version: 10
modern_patterns: immutability,type_safety,performance
distributed_systems: akka_net,aspire,testcontainers
EOF
    
    echo "✅ GitHub Copilot (projet) configuré"
}

# Installation GitHub Copilot (global)
install_github_copilot_global() {
    echo "🔧 Configuration GitHub Copilot (global)..."
    
    create_dir "$HOME/.copilot/skills"
    create_dir "$HOME/.copilot/agents"
    
    copy_skills "$HOME/.copilot/skills"
    
    echo "✅ GitHub Copilot (global) configuré"
}

# Installation OpenCode
install_opencode() {
    echo "🔧 Configuration OpenCode..."
    
    create_dir "$HOME/.config/opencode/skills"
    create_dir "$HOME/.config/opencode/agents"
    
    # Copier les skills avec la structure correcte pour OpenCode
    echo "📋 Traitement des skills pour OpenCode..."
    
    for skill_file in claude-skills/skills/*/SKILL.md; do
        if [ -f "$skill_file" ]; then
            skill_name=$(grep -m1 "^name:" "$skill_file" | sed 's/name: *//' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
            if [ ! -z "$skill_name" ]; then
                skill_dir="$HOME/.config/opencode/skills/$skill_name"
                create_dir "$skill_dir"
                cp "$skill_file" "$skill_dir/SKILL.md"
                echo "  ✅ Skill: $skill_name"
            fi
        fi
    done
    
    # Copier les agents
    cp claude-skills/agents/* "$HOME/.config/opencode/agents/"
    
    # Créer la configuration OpenCode
    cat > "$HOME/.config/opencode/config.yaml" << EOF
# OpenCode Configuration EBP
skills_directory: ~/.config/opencode/skills
agents_directory: ~/.config/opencode/agents
auto_load: true
business_focus: ebp
architecture_patterns: clean_architecture, ddd, microservices
performance_monitoring: true
net_version: 10
modern_patterns: immutability,type_safety,performance
distributed_systems: akka_net,aspire,testcontainers
EOF
    
    echo "✅ OpenCode configuré"
}

# Installation Cursor IDE
install_cursor() {
    echo "🔧 Configuration Cursor IDE..."
    
    create_dir "$HOME/.cursor/skills"
    create_dir "$HOME/.cursor/agents"
    
    copy_skills "$HOME/.cursor/skills"
    
    # Créer la configuration Cursor
    cat > "$HOME/.cursor/config.json" << EOF
{
  "skills": {
    "enabled": true,
    "directory": "~/.cursor/skills",
    "auto_load": true,
    "ebp_focus": true,
    "net_version": 10,
    "modern_patterns": true
  },
  "agents": {
    "enabled": true,
    "directory": "~/.cursor/agents",
    "auto_invoke": true
  },
  "business_context": {
    "domain": "ebp",
    "architecture": "clean_architecture",
    "performance": "optimized",
    "net_version": 10,
    "modern_patterns": "immutability,type_safety,performance"
  }
}
EOF
    
    echo "✅ Cursor IDE configuré"
}

# Validation des installations
validate_installation() {
    echo "🔍 Validation des installations..."
    
    local platforms=()
    
    # Vérifier Claude Code
    if [ -d "$HOME/.claude/skills" ]; then
        platforms+=("Claude Code ✅")
    fi
    
    # Vérifier GitHub Copilot
    if [ -d ".github/skills" ] || [ -d "$HOME/.copilot/skills" ]; then
        platforms+=("GitHub Copilot ✅")
    fi
    
    # Vérifier OpenCode
    if [ -d "$HOME/.config/opencode/skills" ]; then
        platforms+=("OpenCode ✅")
    fi
    
    # Vérifier Cursor
    if [ -d "$HOME/.cursor/skills" ]; then
        platforms+=("Cursor IDE ✅")
    fi
    
    echo "📊 Plateformes configurées:"
    for platform in "${platforms[@]}"; do
        echo "  $platform"
    done
    
    # Compter les skills installés
    local skill_count=0
    local agent_count=0
    
    if [ -d "claude-skills/skills" ]; then
        skill_count=$(find claude-skills/skills -name "SKILL.md" | wc -l)
    fi
    
    if [ -d "claude-skills/agents" ]; then
        agent_count=$(find claude-skills/agents -name "*.md" | wc -l)
    fi
    
    echo "📈 Skills installés: $skill_count"
    echo "🤖 Agents installés: $agent_count"
}

# Menu d'installation
show_menu() {
    echo "🎯 Sélectionnez les plateformes à installer:"
    echo "1) Claude Code"
    echo "2) GitHub Copilot (projet)"
    echo "3) GitHub Copilot (global)"
    echo "4) OpenCode"
    echo "5) Cursor IDE"
    echo "6) Toutes les plateformes"
    echo "7) Personnalisé"
    echo "0) Quitter"
    echo
    read -p "Votre choix (0-7): " choice
    
    case $choice in
        1)
            install_claude_code
            ;;
        2)
            install_github_copilot_project
            ;;
        3)
            install_github_copilot_global
            ;;
        4)
            install_opencode
            ;;
        5)
            install_cursor
            ;;
        6)
            install_claude_code
            install_github_copilot_project
            install_opencode
            install_cursor
            ;;
        7)
            echo "Installation personnalisée:"
            read -p "Claude Code? (y/n): " claude
            read -p "GitHub Copilot (projet)? (y/n): " copilot_proj
            read -p "GitHub Copilot (global)? (y/n): " copilot_global
            read -p "OpenCode? (y/n): " opencode
            read -p "Cursor IDE? (y/n): " cursor
            
            [[ $claude == "y" ]] && install_claude_code
            [[ $copilot_proj == "y" ]] && install_github_copilot_project
            [[ $copilot_global == "y" ]] && install_github_copilot_global
            [[ $opencode == "y" ]] && install_opencode
            [[ $cursor == "y" ]] && install_cursor
            ;;
        0)
            echo "Au revoir!"
            exit 0
            ;;
        *)
            echo "Choix invalide"
            show_menu
            ;;
    esac
}

# Installation automatique (toutes les plateformes)
install_all() {
    echo "🚀 Installation automatique de toutes les plateformes..."
    
    install_claude_code
    install_github_copilot_project
    install_opencode
    install_cursor
    
    validate_installation
}

# Détecter automatiquement les plateformes disponibles
detect_platforms() {
    echo "🔍 Détection des plateformes disponibles..."
    
    local available=()
    
    # Détecter Claude Code
    if command -v claude &> /dev/null; then
        available+=("claude-code")
    fi
    
    # Détecter GitHub Copilot (si dans un repo git)
    if [ -d ".git" ]; then
        available+=("github-copilot")
    fi
    
    # Détecter OpenCode
    if command -v opencode &> /dev/null; then
        available+=("opencode")
    fi
    
    # Détecter Cursor
    if command -v cursor &> /dev/null; then
        available+=("cursor")
    fi
    
    if [ ${#available[@]} -eq 0 ]; then
        echo "⚠️  Aucune plateforme détectée, installation de toutes les options..."
        install_all
    else
        echo "✅ Plateformes détectées: ${available[*]}"
        echo "Installation automatique des plateformes détectées..."
        
        for platform in "${available[@]}"; do
            case $platform in
                "claude-code")
                    install_claude_code
                    ;;
                "github-copilot")
                    install_github_copilot_project
                    ;;
                "opencode")
                    install_opencode
                    ;;
                "cursor")
                    install_cursor
                    ;;
            esac
        done
    fi
}

# Point d'entrée principal
main() {
    echo "🎯 Skills EBP Multi-Agents Installation"
    echo "======================================="
    echo
    
    # Vérifier les arguments
    if [ "$1" = "--all" ]; then
        install_all
    elif [ "$1" = "--detect" ]; then
        detect_platforms
    elif [ "$1" = "--menu" ]; then
        show_menu
    elif [ "$1" = "--claude" ]; then
        install_claude_code
    elif [ "$1" = "--copilot" ]; then
        install_github_copilot_project
    elif [ "$1" = "--opencode" ]; then
        install_opencode
    elif [ "$1" = "--cursor" ]; then
        install_cursor
    else
        echo "Usage: $0 [OPTION]"
        echo "Options:"
        echo "  --all      Installer toutes les plateformes"
        echo "  --detect   Détecter et installer les plateformes disponibles"
        echo "  --menu     Menu interactif"
        echo "  --claude   Installer Claude Code uniquement"
        echo "  --copilot  Installer GitHub Copilot uniquement"
        echo "  --opencode Installer OpenCode uniquement"
        echo "  --cursor   Installer Cursor IDE uniquement"
        echo
        echo "Aucune option fournie, détection automatique..."
        detect_platforms
    fi
    
    validate_installation
    
    echo
    echo "🎉 Installation terminée!"
    echo "📚 Consultez claude-skills/MULTI_AGENT_GUIDE.md pour plus d'informations"
    echo "🔄 Pour mettre à jour: ./claude-skills/update-multi-agent.sh"
}

# Exécuter le script
main "$@"
