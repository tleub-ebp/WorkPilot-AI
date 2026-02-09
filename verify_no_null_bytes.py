#!/usr/bin/env python3
"""Vérifier l'absence de null bytes dans quality_scorer.py"""

from pathlib import Path

scorer_file = Path("apps/backend/review/quality_scorer.py")

if not scorer_file.exists():
    print(f"❌ Fichier non trouvé: {scorer_file}")
    exit(1)

# Lire le fichier en binaire
content_bytes = scorer_file.read_bytes()

# Vérifier les null bytes
if b'\x00' in content_bytes:
    print("❌ Le fichier contient des null bytes!")
    # Trouver où
    positions = [i for i, byte in enumerate(content_bytes) if byte == 0]
    print(f"   Positions: {positions[:10]}...")  # Afficher les 10 premiers
    exit(1)
else:
    print("✅ Pas de null bytes détectés!")

# Vérifier que c'est du UTF-8 valide
try:
    content = scorer_file.read_text(encoding='utf-8')
    print(f"✅ Fichier UTF-8 valide ({len(content)} caractères)")
    
    # Vérifier les imports essentiels
    if "from dataclasses import dataclass" in content:
        print("✅ Import dataclass trouvé")
    if "class QualityScorer:" in content:
        print("✅ Classe QualityScorer trouvée")
    if "def score_pr" in content:
        print("✅ Méthode score_pr trouvée")
    
    print("\n✅ Le fichier est correct et prêt à être utilisé!")
    
except UnicodeDecodeError as e:
    print(f"❌ Erreur d'encodage: {e}")
    exit(1)
