"""
CLI Commands for Quality Scoring
=================================

Commandes CLI pour le système de scoring de qualité.
"""

import json
import sys
from pathlib import Path

# Ajouter le backend au path si nécessaire
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from review.quality_scorer import QualityScorer

def handle_quality_score_command(args):
    """
    Commande: auto-claude quality score
    
    Analyse la qualité du code et génère un score.
    """
    from argparse import Namespace
    
    # Récupérer les arguments
    if isinstance(args, Namespace):
        files = args.files if hasattr(args, 'files') else []
        project_dir = Path(args.project_dir if hasattr(args, 'project_dir') else ".")
        output_format = args.format if hasattr(args, 'format') else "terminal"
        output_file = args.output if hasattr(args, 'output') else None
    else:
        files = args.get('files', [])
        project_dir = Path(args.get('project_dir', '.'))
        output_format = args.get('format', 'terminal')
        output_file = args.get('output')
    
    # Créer le scorer
    scorer = QualityScorer(project_dir)
    
    # Analyser les fichiers
    if not files:
        print("❌ Erreur: Aucun fichier spécifié")
        print("Usage: auto-claude quality score --files file1.py file2.py")
        return 1
    
    print(f"📊 Analyse de {len(files)} fichier(s)...\n")
    
    score = scorer.score_pr("", files, "CLI analysis")
    
    # Formatter la sortie
    if output_format == "json":
        output = json.dumps(score.to_dict(), indent=2)
        if output_file:
            Path(output_file).write_text(output, encoding='utf-8')
            print(f"✅ Rapport JSON sauvegardé: {output_file}")
        else:
            print(output)
    
    elif output_format == "markdown":
        from review.quality_badge import QualityBadgeFormatter
        formatter = QualityBadgeFormatter()
        output = formatter.generate_markdown_summary(score)
        if output_file:
            Path(output_file).write_text(output, encoding='utf-8')
            print(f"✅ Rapport Markdown sauvegardé: {output_file}")
            print(f"🔗 Badge URL: {formatter.generate_shields_badge_url(score)}")
        else:
            print(output)
    
    elif output_format == "terminal":
        # Output formaté pour terminal
        print("=" * 70)
        print("  🧠 AI CODE REVIEW - SCORE DE QUALITÉ")
        print("=" * 70)
        print()
        print(f"  Score Global: {score.overall_score:.1f}/100 (Grade: {score.grade})")
        print()
        
        if score.is_passing:
            print("  ✅ PASSED - Le code respecte les standards de qualité.")
        else:
            print("  ❌ FAILED - Problèmes détectés.")
        
        print()
        print("  Issues Détectées:")
        print(f"    🚨 Critical: {score.critical_issues}")
        print(f"    ⚠️  Total: {score.total_issues}")
        print()
        
        if score.issues:
            print("  Détails des Issues:")
            for issue in score.issues[:10]:  # Limiter à 10
                print(f"    - [{issue.severity.value}] {issue.title}")
                print(f"      {issue.file}:{issue.line}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")
            
            if len(score.issues) > 10:
                print(f"    ... et {len(score.issues) - 10} autres issues")
        
        print()
        print("=" * 70)
    
    # Exit code selon le résultat
    return 0 if score.is_passing else 1


def add_quality_commands(subparsers):
    """
    Ajoute les commandes quality au parser CLI.
    
    Usage:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        add_quality_commands(subparsers)
    """
    # Commande principale: quality
    quality_parser = subparsers.add_parser(
        'quality',
        help='Commandes de scoring de qualité de code'
    )
    quality_subparsers = quality_parser.add_subparsers(dest='quality_command')
    
    # Sous-commande: quality score
    score_parser = quality_subparsers.add_parser(
        'score',
        help='Analyser la qualité du code'
    )
    score_parser.add_argument(
        '--files',
        nargs='+',
        required=True,
        help='Fichiers à analyser'
    )
    score_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    score_parser.add_argument(
        '--format',
        choices=['terminal', 'json', 'markdown'],
        default='terminal',
        help='Format de sortie (défaut: terminal)'
    )
    score_parser.add_argument(
        '--output',
        help='Fichier de sortie pour JSON'
    )
    score_parser.set_defaults(func=handle_quality_score_command)
    
    return quality_parser

