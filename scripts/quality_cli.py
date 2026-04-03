#!/usr/bin/env python
"""
Quality CLI - Script standalone pour tester le Quality Scorer
=============================================================

Usage:
    python quality_cli.py score --files file1.py file2.py
    python quality_cli.py score --files file.py --format json
    python quality_cli.py score --files file.py --format markdown --output report.md
    python quality_cli.py trends --project-dir .
    python quality_cli.py history --limit 10
    python quality_cli.py autofix --files file.py --dry-run
    python quality_cli.py autofix --files file.py --apply
    python quality_cli.py clones --project-dir . --min-lines 6
    python quality_cli.py performance --project-dir .
    python quality_cli.py rules --generate-template
    python quality_cli.py grepai --query "votre requête"
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from cli.quality_commands import handle_quality_score_command


def ensure_grepai():
    """Automatise le lancement et la vérification de grepai."""
    subprocess.run([
        'python', 'src/connectors/grepai/grepai_launcher.py'
    ], check=True)


def handle_quality_score_command(args):
    """Gère la commande de score qualité."""
    from review.quality_scorer import QualityScorer

    from src.connectors.base import GrepaiConnector
    
    project_dir = Path(args.project_dir or '.')
    
    # Initialiser le Grepai Connector
    grepai = GrepaiConnector()
    
    # Lancer l'analyse de qualité
    scorer = QualityScorer(project_dir)
    score = scorer.score_files(args.files)
    
    # Afficher les résultats
    print("\n✅ Quality Analysis Results")
    print("=" * 50)
    print(f"Files analyzed: {len(args.files)}")
    print(f"Total issues found: {score.total_issues}")
    
    # Rechercher des informations supplémentaires avec Grepai
    for file in args.files:
        result = grepai.search_code(f"score file:{file}")
        if result and 'error' not in result:
            print(f"[Grepai] Résultats pour {file} : {result}")
    
    return 0


def handle_autofix_command(args):
    """Applique des fixes automatiques."""
    from review.quality_autofix import AutoFixEngine
    from review.quality_extended import ExtendedQualityScorer

    from src.connectors.base import GrepaiConnector
    
    project_dir = Path(args.project_dir or '.')
    
    # Score les fichiers
    scorer = ExtendedQualityScorer(project_dir)
    score = scorer.score_pr("", args.files, "Auto-fix analysis")
    
    print("\n🔧 Auto-Fix Analysis")
    print("=" * 50)
    print(f"Total issues found: {score.total_issues}")
    
    # Générer les fixes
    engine = AutoFixEngine(project_dir)
    fixes = engine.generate_fixes(score.issues)
    
    print(f"Fixes available: {len(fixes)}")
    
    if not fixes:
        print("\n✅ No automatic fixes available.")
        return 0
    
    # Preview ou apply
    if args.preview:
        preview = engine.preview_fixes(score.issues)
        print(f"\n{preview}")
        return 0
    
    if args.dry_run:
        print("\n📋 Dry Run - No files will be modified:")
        result = engine.apply_fixes(fixes, min_confidence=args.confidence, dry_run=True)
    elif args.apply:
        print(f"\n✅ Applying fixes (min confidence: {args.confidence * 100:.0f}%)...")
        result = engine.apply_fixes(fixes, min_confidence=args.confidence, dry_run=False)
    else:
        print("\n⚠️  Use --dry-run to preview or --apply to apply fixes")
        return 1
    
    print("\nResults:")
    print(f"  Total fixes: {result['total_fixes']}")
    print(f"  Applied: {result['applied']}")
    print(f"  Skipped: {result['skipped']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Files modified: {result['files_modified']}")
    
    # Recherche Grepai pour des suggestions supplémentaires
    grepai = GrepaiConnector()
    for file in args.files:
        result = grepai.search_code(f"autofix file:{file}")
        if result and 'error' not in result:
            print(f"[Grepai] Suggestions autofix pour {file} : {result}")
    
    return 0


def handle_clones_command(args):
    """Détecte les clones de code."""
    from review.quality_similarity import (
        CodeSimilarityDetector,
        detect_clones_in_project,
    )

    from src.connectors.base import GrepaiConnector
    
    project_dir = Path(args.project_dir or '.')
    
    print("\n🔍 Code Clone Detection")
    print("=" * 50)
    print(f"Project: {project_dir}")
    print(f"Min lines: {args.min_lines}")
    print(f"Min similarity: {args.min_similarity * 100:.0f}%")
    print()
    
    clones, issues = detect_clones_in_project(
        project_dir,
        min_lines=args.min_lines,
        min_similarity=args.min_similarity,
    )
    
    print(f"Clones found: {len(clones)}")
    print(f"Issues generated: {len(issues)}")
    
    # Recherche Grepai pour des informations sur les clones
    grepai = GrepaiConnector()
    for file in args.files:
        result = grepai.search_code(f"clones file:{file}")
        if result and 'error' not in result:
            print(f"[Grepai] Recherche de clones pour {file} : {result}")
    
    if args.format == 'markdown':
        detector = CodeSimilarityDetector()
        report = detector.generate_report(clones)
        
        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f"\n✅ Report saved: {args.output}")
        else:
            print(f"\n{report}")
    else:
        # Terminal output
        for clone in clones[:10]:
            print(f"\n📄 Clone: {clone.lines_count} lines ({clone.similarity*100:.0f}% similar)")
            print(f"   {clone.file1}:{clone.line1_start}-{clone.line1_end}")
            print(f"   {clone.file2}:{clone.line2_start}-{clone.line2_end}")
        
        if len(clones) > 10:
            print(f"\n... and {len(clones) - 10} more clones")
    
    return 0


def handle_performance_command(args):
    """Analyse les problèmes de performance."""
    from review.quality_performance import analyze_project_performance

    from src.connectors.base import GrepaiConnector
    
    project_dir = Path(args.project_dir or '.')
    
    print("\n⚡ Performance Analysis")
    print("=" * 50)
    print(f"Project: {project_dir}")
    print()
    
    issues = analyze_project_performance(project_dir)
    
    print(f"Performance issues found: {len(issues)}")
    
    if issues:
        # Grouper par sévérité
        by_severity = {}
        for issue in issues:
            sev = issue.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(issue)
        
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                print(f"\n{severity.upper()}: {len(by_severity[severity])}")
                for issue in by_severity[severity][:5]:
                    print(f"  - {issue.title}")
                    print(f"    {issue.file}:{issue.line}")
                    if issue.suggestion:
                        print(f"    💡 {issue.suggestion}")
    else:
        print("\n✅ No performance issues detected!")
    
    # Recherche Grepai pour des analyses de performance
    grepai = GrepaiConnector()
    for file in args.files:
        result = grepai.search_code(f"performance file:{file}")
        if result and 'error' not in result:
            print(f"[Grepai] Analyse performance pour {file} : {result}")
    
    return 0


def handle_rules_command(args):
    """Gère les règles personnalisées."""
    from review.quality_custom_rules import CustomRuleEngine
    
    project_dir = Path(args.project_dir or '.')
    
    if args.generate_template:
        output = project_dir / '.quality-rules.yml'
        engine = CustomRuleEngine()
        engine.generate_template(output)
        print(f"✅ Template generated: {output}")
        return 0
    
    if args.list:
        from review.quality_custom_rules import load_project_rules
        engine = load_project_rules(project_dir)
        
        print(f"\n📋 Custom Rules ({len(engine.rules)} rules)")
        print("=" * 50)
        
        if not engine.rules:
            print("No custom rules found.")
            print("Run with --generate-template to create a template.")
        else:
            for rule in engine.rules:
                status = "✅" if rule.enabled else "❌"
                print(f"{status} {rule.id}: {rule.name}")
                print(f"   {rule.severity.value} | {rule.category.value}")
                print()
        
        return 0
    
    return 0


def handle_ml_command(args):
    """Gère le ML pattern detection."""
    from review.quality_ml import MLPatternDetector
    
    project_dir = Path(args.project_dir or '.')
    
    print("\n🧠 ML Pattern Detection")
    print("=" * 50)
    
    detector = MLPatternDetector(project_dir)
    
    if args.learn:
        print("Learning patterns from codebase...")
        stats = detector.learn_from_codebase()
        
        print("\n✅ Learning complete!")
        print(f"  Files analyzed: {stats['files_analyzed']}")
        print(f"  Patterns learned: {stats['patterns_learned']}")
        print(f"  Naming conventions: {stats['naming_conventions']}")
        print(f"  Import patterns: {stats['import_patterns']}")
        
        return 0
    
    if args.report:
        detector._load_learned_data()
        report = detector.get_report()
        
        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f"✅ Report saved: {args.output}")
        else:
            print(f"\n{report}")
        
        return 0
    
    return 0


def handle_coverage_command(args):
    """Analyse la couverture de tests."""
    from review.quality_coverage import analyze_project_coverage
    
    project_dir = Path(args.project_dir or '.')
    
    print("\n🧪 Test Coverage Analysis")
    print("=" * 50)
    
    stats, issues = analyze_project_coverage(project_dir)
    
    coverage_pct = stats['coverage_percentage']
    
    print(f"Coverage: {coverage_pct:.1f}%")
    print(f"Tested: {stats['tested_entities']}/{stats['total_public']} entities")
    print(f"Untested: {len(stats['untested_entities'])} entities")
    
    if args.format == 'markdown':
        from review.quality_coverage import TestCoverageAnalyzer
        analyzer = TestCoverageAnalyzer(project_dir)
        report = analyzer.generate_report(stats)
        
        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f"\n✅ Report saved: {args.output}")
        else:
            print(f"\n{report}")
    else:
        if stats['untested_entities']:
            print("\n⚠️ Untested entities (showing first 10):")
            for entity in stats['untested_entities'][:10]:
                print(f"  - {entity['type']}: {entity['name']}")
                print(f"    {Path(entity['file']).name}:{entity['line']}")
        else:
            print("\n🎉 All public entities have tests!")
    
    return 0


def handle_trends_command(args):
    """Affiche les tendances de qualité."""
    from review.quality_integration import QualityReviewIntegration
    
    project_dir = Path(args.project_dir or '.')
    integration = QualityReviewIntegration(project_dir)
    trends = integration.get_quality_trends()
    
    print("\n📈 Quality Trends")
    print("=" * 50)
    print(f"Total PRs Analyzed: {trends['total_prs']}")
    print(f"Average Score: {trends['average_score']:.1f}/100")
    print(f"Median Score: {trends['median_score']:.1f}/100")
    print(f"Best Score: {trends['best_score']:.1f}/100")
    print(f"Worst Score: {trends['worst_score']:.1f}/100")
    print(f"Trend: {trends['trend']}")
    
    if trends['grade_distribution']:
        print("\nGrade Distribution:")
        for grade, count in sorted(trends['grade_distribution'].items()):
            print(f"  {grade}: {count}")
    
    print()
    return 0


def handle_history_command(args):
    """Affiche l'historique des scores."""
    from review.quality_integration import QualityReviewIntegration
    
    project_dir = Path(args.project_dir or '.')
    integration = QualityReviewIntegration(project_dir)
    history = integration.get_historical_scores(limit=args.limit)
    
    print(f"\n📚 Quality History (last {args.limit})")
    print("=" * 50)
    
    for entry in history:
        timestamp = entry.get('timestamp', 'Unknown')
        score = entry.get('score', 0)
        grade = entry.get('grade', '?')
        pr_id = entry.get('pr_id', 'N/A')
        passing = '✅' if entry.get('passing') else '❌'
        
        print(f"{passing} {timestamp[:19]} | PR {pr_id} | Score: {score:.0f} ({grade})")
    
    print()
    return 0


def handle_grepai_search_command(args):
    """Effectue une recherche via Grepai et affiche les résultats."""
    from src.connectors.grepai.client import GrepaiClient
    client = GrepaiClient()
    query = args.query
    print(f"Recherche Grepai pour : {query}")
    result = client.search(query=query)
    if 'error' in result:
        print("Erreur Grepai :", result['error'])
    else:
        print("Résultats Grepai :", result)


def main():
    ensure_grepai()  # Vérifie et lance grepai automatiquement
    parser = argparse.ArgumentParser(
        description="🧠 AI Code Review Quality Scorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s score --files apps/backend/review/quality_scorer.py
  %(prog)s score --files test1.py test2.py --format json
  %(prog)s score --files src/*.py --format markdown --output report.md
  %(prog)s trends
  %(prog)s history --limit 20
  %(prog)s autofix --files file.py --preview
  %(prog)s autofix --files file.py --apply --confidence 0.8
  %(prog)s clones --project-dir . --min-lines 10
  %(prog)s performance --project-dir .
  %(prog)s rules --generate-template
  %(prog)s grepai --query "votre requête"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande: score
    score_parser = subparsers.add_parser(
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
        help='Fichier de sortie'
    )
    
    # Commande: trends
    trends_parser = subparsers.add_parser(
        'trends',
        help='Afficher les tendances de qualité'
    )
    trends_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    
    # Commande: history
    history_parser = subparsers.add_parser(
        'history',
        help='Afficher l\'historique des scores'
    )
    history_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    history_parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Nombre d\'entrées à afficher (défaut: 10)'
    )
    
    # Commande: autofix
    autofix_parser = subparsers.add_parser(
        'autofix',
        help='Appliquer des fixes automatiques'
    )
    autofix_parser.add_argument(
        '--files',
        nargs='+',
        required=True,
        help='Fichiers à fixer'
    )
    autofix_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    autofix_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview sans appliquer les fixes'
    )
    autofix_parser.add_argument(
        '--apply',
        action='store_true',
        help='Appliquer les fixes'
    )
    autofix_parser.add_argument(
        '--preview',
        action='store_true',
        help='Afficher un preview détaillé'
    )
    autofix_parser.add_argument(
        '--confidence',
        type=float,
        default=0.8,
        help='Confidence minimum (0.0-1.0, défaut: 0.8)'
    )
    
    # Commande: clones (NOUVEAU)
    clones_parser = subparsers.add_parser(
        'clones',
        help='Détecter les clones de code'
    )
    clones_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    clones_parser.add_argument(
        '--min-lines',
        type=int,
        default=6,
        help='Nombre minimum de lignes (défaut: 6)'
    )
    clones_parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.85,
        help='Similarité minimum (0.0-1.0, défaut: 0.85)'
    )
    clones_parser.add_argument(
        '--format',
        choices=['terminal', 'markdown'],
        default='terminal',
        help='Format de sortie (défaut: terminal)'
    )
    clones_parser.add_argument(
        '--output',
        help='Fichier de sortie pour markdown'
    )
    
    # Commande: performance (NOUVEAU)
    performance_parser = subparsers.add_parser(
        'performance',
        help='Analyser les problèmes de performance'
    )
    performance_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    
    # Commande: rules (NOUVEAU)
    rules_parser = subparsers.add_parser(
        'rules',
        help='Gérer les règles personnalisées'
    )
    rules_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    rules_parser.add_argument(
        '--generate-template',
        action='store_true',
        help='Générer un template de configuration'
    )
    rules_parser.add_argument(
        '--list',
        action='store_true',
        help='Lister les règles existantes'
    )
    
    # Commande: ml (NOUVEAU)
    ml_parser = subparsers.add_parser(
        'ml',
        help='ML pattern detection'
    )
    ml_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    ml_parser.add_argument(
        '--learn',
        action='store_true',
        help='Apprendre les patterns du projet'
    )
    ml_parser.add_argument(
        '--report',
        action='store_true',
        help='Générer un rapport des patterns appris'
    )
    ml_parser.add_argument(
        '--output',
        help='Fichier de sortie pour le rapport'
    )
    
    # Commande: coverage (NOUVEAU)
    coverage_parser = subparsers.add_parser(
        'coverage',
        help='Analyser la couverture de tests'
    )
    coverage_parser.add_argument(
        '--project-dir',
        default='.',
        help='Répertoire du projet (défaut: .)'
    )
    coverage_parser.add_argument(
        '--format',
        choices=['terminal', 'markdown'],
        default='terminal',
        help='Format de sortie (défaut: terminal)'
    )
    coverage_parser.add_argument(
        '--output',
        help='Fichier de sortie pour markdown'
    )
    
    # Commande: grepai (NOUVEAU)
    grepai_parser = subparsers.add_parser(
        'grepai',
        help='Effectuer une recherche via Grepai'
    )
    grepai_parser.add_argument(
        '--query',
        required=True,
        help='La requête de recherche'
    )
    
    # Commande: grepai-search (NOUVEAU)
    grepai_parser = subparsers.add_parser("grepai-search", help="Recherche avancée via Grepai")
    grepai_parser.add_argument("--query", required=True, help="Texte à rechercher avec Grepai")
    grepai_parser.set_defaults(func=handle_grepai_search_command)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    ensure_grepai()
    sys.exit(main())
