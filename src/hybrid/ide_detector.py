"""
IDE-Agnostic Detection System
Détecte l'IDE actuel et adapte le comportement en conséquence
Compatible avec Claude Code, GitHub Copilot, Cursor, Windsurf, etc.
"""

import json
import os
import re
from pathlib import Path


class IDEDetector:
    """Détecte l'IDE actuel et fournit des adaptations spécifiques"""
    
    def __init__(self):
        self.ide_patterns = {
            'claude-code': {
                'indicators': [
                    r'claude-code',
                    r'anthropic',
                    r'claude.*code',
                    r'.claude'
                ],
                'features': {
                    'markdown_support': True,
                    'code_generation': True,
                    'file_operations': True,
                    'context_aware': True
                },
                'communication_style': 'collaborative',
                'output_format': 'markdown'
            },
            'github-copilot': {
                'indicators': [
                    r'github.*copilot',
                    r'copilot',
                    r'vscode.*copilot'
                ],
                'features': {
                    'inline_suggestions': True,
                    'code_completion': True,
                    'chat_interface': True,
                    'context_files': True
                },
                'communication_style': 'technical',
                'output_format': 'code_blocks'
            },
            'cursor': {
                'indicators': [
                    r'cursor',
                    r'cursor.*ai',
                    r'cursor.*editor'
                ],
                'features': {
                    'multi_file_editing': True,
                    'context_aware': True,
                    'command_palette': True,
                    'ai_chat': True
                },
                'communication_style': 'efficient',
                'output_format': 'structured'
            },
            'windsurf': {
                'indicators': [
                    r'windsurf',
                    r'windsurf.*ai',
                    r'codeium.*windsurf'
                ],
                'features': {
                    'workflow_integration': True,
                    'context_management': True,
                    'multi_agent': True,
                    'slash_commands': True
                },
                'communication_style': 'structured',
                'output_format': 'workflow'
            },
            'generic': {
                'indicators': [],
                'features': {
                    'basic_text': True,
                    'file_operations': True,
                    'context_limited': True
                },
                'communication_style': 'neutral',
                'output_format': 'plain'
            }
        }
    
    def detect_ide(self, project_path: str = None) -> dict[str, any]:
        """
        Détecte l'IDE actuel basé sur plusieurs indicateurs
        
        Returns:
            Dict avec informations sur l'IDE détecté
        """
        if project_path is None:
            project_path = os.getcwd()
        
        # Indicateurs à vérifier
        indicators = []
        
        # 1. Variables d'environnement
        env_indicators = self._check_environment()
        indicators.extend(env_indicators)
        
        # 2. Fichiers de configuration
        config_indicators = self._check_config_files(project_path)
        indicators.extend(config_indicators)
        
        # 3. Processus en cours
        process_indicators = self._check_running_processes()
        indicators.extend(process_indicators)
        
        # 4. Structure du projet
        structure_indicators = self._check_project_structure(project_path)
        indicators.extend(structure_indicators)
        
        # 5. Fichiers récents/temporaires
        temp_indicators = self._check_temp_files(project_path)
        indicators.extend(temp_indicators)
        
        # Analyser les indicateurs
        detected_ide = self._analyze_indicators(indicators)
        
        # Récupérer la configuration IDE
        ide_config = self.ide_patterns.get(detected_ide, self.ide_patterns['generic'])
        
        return {
            'ide_name': detected_ide,
            'confidence': self._calculate_confidence(indicators, detected_ide),
            'indicators_found': indicators,
            'features': ide_config['features'],
            'communication_style': ide_config['communication_style'],
            'output_format': ide_config['output_format'],
            'recommendations': self._get_recommendations(detected_ide)
        }
    
    def _check_environment(self) -> list[str]:
        """Vérifie les variables d'environnement"""
        indicators = []
        
        env_vars = [
            'VSCODE_PID', 'VSCODE_IPC_HOOK',
            'CLAUDE_CODE_SESSION', 'ANTHROPIC_API_KEY',
            'CURSOR_WORKSPACE', 'CURSOR_SESSION',
            'WINDSURF_SESSION', 'CODEIUM_SESSION',
            'GITHUB_COPILOT_TOKEN'
        ]
        
        for var in env_vars:
            if os.environ.get(var):
                indicators.append(var.lower())
        
        return indicators
    
    def _check_config_files(self, project_path: str) -> list[str]:
        """Vérifie les fichiers de configuration"""
        indicators = []
        
        config_patterns = {
            '.vscode/': 'vscode',
            '.cursor/': 'cursor',
            '.windsurf/': 'windsurf',
            '.claude/': 'claude-code',
            'claude_settings.json': 'claude-code',
            'copilot.json': 'github-copilot',
            'cursor.json': 'cursor',
            'windsurf.json': 'windsurf'
        }
        
        project_path = Path(project_path)
        
        for pattern, ide in config_patterns.items():
            if pattern.endswith('/'):
                # Directory
                if (project_path / pattern).exists():
                    indicators.append(ide)
            else:
                # File
                if (project_path / pattern).exists():
                    indicators.append(ide)
        
        return indicators
    
    def _check_running_processes(self) -> list[str]:
        """Vérifie les processus en cours"""
        indicators = []
        
        try:
            # Sur Windows, utiliser tasklist
            if os.name == 'nt':
                import subprocess
                result = subprocess.run(['tasklist'], capture_output=True, text=True)
                processes = result.stdout.lower()
                
                process_names = [
                    'code.exe',  # VS Code
                    'cursor.exe',  # Cursor
                    'claude.exe',  # Claude Code (si applicable)
                    'windsurf.exe'
                ]
                
                for process in process_names:
                    if process in processes:
                        indicators.append(process.replace('.exe', ''))
            
        except Exception:
            pass
        
        return indicators
    
    def _check_project_structure(self, project_path: str) -> list[str]:
        """Vérifie la structure du projet pour des indices"""
        indicators = []
        
        project_path = Path(project_path)
        
        # Patterns spécifiques à chaque IDE
        structure_patterns = {
            '.windsurf/workflows/': 'windsurf',
            '.claude-skills/': 'claude-code',
            'claude-skills/': 'claude-code',
            'node_modules/.bin/claude': 'claude-code',
            '.github/copilot/': 'github-copilot'
        }
        
        for pattern, ide in structure_patterns.items():
            if (project_path / pattern).exists():
                indicators.append(ide)
        
        return indicators
    
    def _check_temp_files(self, project_path: str) -> list[str]:
        """Vérifie les fichiers temporaires"""
        indicators = []
        
        project_path = Path(project_path)
        
        # Fichiers temporaires communs
        temp_patterns = {
            '.vscode/settings.json': 'vscode',
            '.cursor/logs/': 'cursor',
            '.windsurf/cache/': 'windsurf'
        }
        
        for pattern, ide in temp_patterns.items():
            if (project_path / pattern).exists():
                indicators.append(ide)
        
        return indicators
    
    def _analyze_indicators(self, indicators: list[str]) -> str:
        """Analyse les indicateurs pour déterminer l'IDE"""
        
        scores = {}
        
        for ide_name, config in self.ide_patterns.items():
            if ide_name == 'generic':
                continue
                
            score = 0
            for indicator in indicators:
                for pattern in config['indicators']:
                    if re.search(pattern, indicator, re.IGNORECASE):
                        score += 1
                        break
            
            scores[ide_name] = score
        
        # Retourner l'IDE avec le plus haut score
        if scores:
            return max(scores, key=scores.get)
        
        return 'generic'
    
    def _calculate_confidence(self, indicators: list[str], detected_ide: str) -> float:
        """Calcule la confiance dans la détection"""
        
        if detected_ide == 'generic':
            return 0.0
        
        config = self.ide_patterns.get(detected_ide, {})
        patterns = config.get('indicators', [])
        
        if not patterns:
            return 0.0
        
        matching_indicators = 0
        for indicator in indicators:
            for pattern in patterns:
                if re.search(pattern, indicator, re.IGNORECASE):
                    matching_indicators += 1
                    break
        
        # Normaliser le score
        confidence = min(matching_indicators / len(patterns), 1.0)
        
        # Ajuster basé sur le nombre total d'indicateurs
        if len(indicators) >= 3:
            confidence = min(confidence * 1.2, 1.0)
        
        return confidence
    
    def _get_recommendations(self, ide_name: str) -> list[str]:
        """Retourne des recommandations spécifiques à l'IDE"""
        
        recommendations = {
            'claude-code': [
                'Utiliser le format markdown pour une meilleure compatibilité',
                'Exploiter les capacités de génération de code contextuelles',
                'Profiter de la collaboration en temps réel',
                'Utiliser les slash commands pour les workflows'
            ],
            'github-copilot': [
                'Fournir du code dans des blocs pour les suggestions',
                'Utiliser des commentaires explicatifs pour de meilleures suggestions',
                'Exploiter les capacités de chat pour les questions complexes',
                'Structurer les sorties pour faciliter le copier-coller'
            ],
            'cursor': [
                'Utiliser des instructions claires et structurées',
                'Profiter des capacités d\'édition multi-fichiers',
                'Utiliser la palette de commandes pour l\'efficacité',
                'Structurer les réponses pour les workflows automatisés'
            ],
            'windsurf': [
                'Intégrer parfaitement avec les workflows existants',
                'Utiliser les commandes slash pour les workflows BMAD',
                'Exploiter les capacités multi-agents',
                'Maintenir la cohérence avec la structure .windsurf/workflows'
            ],
            'generic': [
                'Utiliser un format standard (markdown)',
                'Fournir des instructions claires et détaillées',
                'Éviter les fonctionnalités spécifiques à un IDE',
                'Maintenir la compatibilité multi-plateforme'
            ]
        }
        
        return recommendations.get(ide_name, recommendations['generic'])
    
    def adapt_communication_style(self, ide_info: dict[str, any], content: str) -> str:
        """Adapte le style de communication selon l'IDE détecté"""
        
        style = ide_info.get('communication_style', 'neutral')
        
        if style == 'collaborative':
            # Style conversationnel et collaboratif
            return self._make_collaborative(content)
        elif style == 'technical':
            # Style technique et direct
            return self._make_technical(content)
        elif style == 'efficient':
            # Style efficace et concis
            return self._make_efficient(content)
        elif style == 'structured':
            # Style structuré et formel
            return self._make_structured(content)
        else:
            # Style neutre par défaut
            return content
    
    def _make_collaborative(self, content: str) -> str:
        """Rend le contenu plus collaboratif"""
        collaborative_phrases = [
            "Que pensez-vous de cette approche ?",
            "Ensemble, nous pouvons",
            "Je vous suggère de considérer",
            "Voici une option que nous pourrions explorer",
            "N'hésitez pas à partager vos réflexions"
        ]
        
        # Ajouter des éléments collaboratifs
        lines = content.split('\n')
        enhanced_lines = []
        
        for i, line in enumerate(lines):
            enhanced_lines.append(line)
            
            # Ajouter des invitations à la collaboration
            if i % 10 == 8 and len(lines) > i + 1:
                phrase = collaborative_phrases[i % len(collaborative_phrases)]
                enhanced_lines.append(f"\n*{phrase}*\n")
        
        return '\n'.join(enhanced_lines)
    
    def _make_technical(self, content: str) -> str:
        """Rend le contenu plus technique"""
        # Ajouter des détails techniques et des précisions
        return content
    
    def _make_efficient(self, content: str) -> str:
        """Rend le contenu plus efficace et concis"""
        lines = content.split('\n')
        efficient_lines = []
        
        for line in lines:
            # Supprimer les lignes vides multiples
            if line.strip() or (efficient_lines and efficient_lines[-1].strip()):
                efficient_lines.append(line)
        
        return '\n'.join(efficient_lines)
    
    def _make_structured(self, content: str) -> str:
        """Rend le contenu plus structuré"""
        # Ajouter plus de structure avec des sections claires
        if not content.startswith('#'):
            content = "# Résultat\n\n" + content
        
        return content


# Point d'entrée principal
if __name__ == "__main__":
    detector = IDEDetector()
    ide_info = detector.detect_ide()
    
    print("Détection IDE:")
    print(json.dumps(ide_info, indent=2, default=str))
