"""
Anthropic Usage Metrics - Récupération des données d'usage pour Claude
"""

import os
import subprocess
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


def get_anthropic_usage_metrics() -> Dict[str, Any]:
    """
    Récupère les données d'usage Anthropic en temps réel via la CLI Claude
    
    Returns:
        Dict: Données d'usage formatées pour le frontend
    """
    try:
        # D'abord vérifier l'authentification
        auth_result = subprocess.run(
            ["claude", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if auth_result.returncode != 0:
            return {
                "provider": "anthropic",
                "available": False,
                "error": "NOT_AUTHENTICATED",
                "message": "Please sign in to Claude CLI with 'claude login'",
                "providerName": "anthropic"
            }
        
        auth_data = json.loads(auth_result.stdout)
        
        if not auth_data.get("loggedIn", False):
            return {
                "provider": "anthropic",
                "available": False,
                "error": "NOT_AUTHENTICATED",
                "message": "Please sign in to Claude CLI with 'claude login'",
                "providerName": "anthropic"
            }
        
        # Maintenant récupérer les données d'usage en temps réel
        usage_result = subprocess.run(
            ["claude", "usage"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if usage_result.returncode == 0:
            # Parser la sortie de la commande usage
            parsed_usage = parse_claude_usage_output(usage_result.stdout)
            
            if parsed_usage:
                # Convertir les données au format attendu par le frontend
                return {
                    "provider": "anthropic",
                    "available": True,
                    "usage": {
                        "sessionPercent": parsed_usage.get("session_percent", 0),
                        "weeklyPercent": parsed_usage.get("weekly_percent", 0),
                        "sessionResetTime": parsed_usage.get("session_reset_time", "N/A"),
                        "weeklyResetTime": parsed_usage.get("weekly_reset_time", "N/A"),
                        "sessionUsageValue": parsed_usage.get("session_usage_value", 0),
                        "weeklyUsageValue": parsed_usage.get("weekly_usage_value", 0),
                        "needsReauthentication": parsed_usage.get("needs_reauthentication", False),
                        "profile_info": {
                            "email": auth_data.get("email", ""),
                            "subscription": auth_data.get("subscriptionType", "unknown"),
                            "org_id": auth_data.get("orgId")
                        }
                    },
                    "fetched_at": datetime.now().isoformat(),
                    "providerName": "anthropic",
                    "message": "Real-time usage data from Claude CLI"
                }
            else:
                # Erreur de parsing, retourner les infos d'auth basiques
                return {
                    "provider": "anthropic",
                    "available": True,
                    "usage": {
                        "sessionPercent": 0,
                        "weeklyPercent": 0,
                        "sessionResetTime": "N/A",
                        "weeklyResetTime": "N/A",
                        "sessionUsageValue": 0,
                        "weeklyUsageValue": 0,
                        "needsReauthentication": False,
                        "profile_info": {
                            "email": auth_data.get("email", ""),
                            "subscription": auth_data.get("subscriptionType", "unknown"),
                            "org_id": auth_data.get("orgId")
                        }
                    },
                    "fetched_at": datetime.now().isoformat(),
                    "providerName": "anthropic",
                    "message": "Usage data parsing failed - authenticated but no usage data available"
                }
        else:
            # La commande usage a échoué, vérifier si c'est une erreur de ré-authentification
            error_output = usage_result.stderr.lower()
            if "re-authenticate" in error_output or "sign in" in error_output:
                return {
                    "provider": "anthropic",
                    "available": False,
                    "error": "REAUTH_REQUIRED",
                    "message": "Please re-authenticate with 'claude login'",
                    "providerName": "anthropic"
                }
            else:
                return {
                    "provider": "anthropic",
                    "available": False,
                    "error": "USAGE_COMMAND_ERROR",
                    "message": f"Claude usage command error: {usage_result.stderr.strip()}",
                    "providerName": "anthropic"
                }
                
    except subprocess.TimeoutExpired:
        return {
            "provider": "anthropic",
            "available": False,
            "error": "TIMEOUT",
            "message": "Claude CLI request timed out",
            "providerName": "anthropic"
        }
    except FileNotFoundError:
        return {
            "provider": "anthropic",
            "available": False,
            "error": "CLI_NOT_FOUND",
            "message": "Claude CLI not found. Please install it with 'npm install -g @anthropic-ai/claude-cli'",
            "providerName": "anthropic"
        }
    except json.JSONDecodeError as e:
        return {
            "provider": "anthropic",
            "available": False,
            "error": "JSON_PARSE_ERROR",
            "message": f"Failed to parse Claude CLI response: {str(e)}",
            "providerName": "anthropic"
        }
    except Exception as e:
        return {
            "error": "UNKNOWN_ERROR",
            "message": f"Unexpected error: {str(e)}",
            "provider": "anthropic"
        }


def parse_claude_usage_output(output: str) -> Optional[Dict[str, Any]]:
    """
    Parse la sortie de la commande 'claude usage'
    
    Format attendu:
    Session usage: 45% (resets in 2h 15m)
    Weekly usage: 23% (resets in 4d 12h)
    """
    usage_data = {}
    
    try:
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Parser session usage
            session_match = re.search(r'Session usage:\s*(\d+)%\s*\(resets in\s*([^)]+)\)', line, re.IGNORECASE)
            if session_match:
                usage_data["session_percent"] = int(session_match.group(1))
                usage_data["session_reset_time"] = f"resets in {session_match.group(2).strip()}"
                continue
            
            # Parser weekly usage  
            weekly_match = re.search(r'Weekly usage:\s*(\d+)%\s*\(resets in\s*([^)]+)\)', line, re.IGNORECASE)
            if weekly_match:
                usage_data["weekly_percent"] = int(weekly_match.group(1))
                usage_data["weekly_reset_time"] = f"resets in {weekly_match.group(2).strip()}"
                continue
            
            # Parser les messages d'erreur ou re-authentification
            if "re-authenticate" in line.lower() or "sign in" in line.lower():
                usage_data["needs_reauthentication"] = True
            
            # Parser les valeurs brutes si disponibles (tokens, etc.)
            tokens_match = re.search(r'(\d+(?:,\d+)*)\s*tokens?', line, re.IGNORECASE)
            if tokens_match:
                # Enlever les virgules et convertir en entier
                token_value = int(tokens_match.group(1).replace(',', ''))
                usage_data["session_usage_value"] = token_value
            
            # Parser les limites si disponibles
            limit_match = re.search(r'limit:\s*(\d+(?:,\d+)*)', line, re.IGNORECASE)
            if limit_match:
                limit_value = int(limit_match.group(1).replace(',', ''))
                usage_data["weekly_usage_value"] = limit_value
        
        # Si nous avons au moins les pourcentages, considérer que c'est un succès
        if "session_percent" in usage_data or "weekly_percent" in usage_data:
            # S'assurer que les valeurs par défaut sont présentes
            if "needs_reauthentication" not in usage_data:
                usage_data["needs_reauthentication"] = False
            if "session_usage_value" not in usage_data:
                # Estimer basé sur le pourcentage (approximation)
                session_pct = usage_data.get("session_percent", 0)
                usage_data["session_usage_value"] = session_pct * 1000  # ~1000 tokens par %
            if "weekly_usage_value" not in usage_data:
                # Estimer basé sur le pourcentage (approximation)
                weekly_pct = usage_data.get("weekly_percent", 0)
                usage_data["weekly_usage_value"] = weekly_pct * 10000  # ~10000 tokens par %
            
            return usage_data
            
    except Exception as e:
        print(f"Error parsing Claude usage output: {e}")
    
    return None


def get_anthropic_oauth_usage() -> Dict[str, Any]:
    """
    Alternative: Tenter de récupérer les données via l'API Anthropic si possible
    """
    # Pour l'instant, cette fonction n'est pas implémentée
    # L'API Anthropic n'expose pas publiquement les données d'usage
    return get_anthropic_usage_metrics()
