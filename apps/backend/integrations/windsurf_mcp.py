"""
Intégration MCP Windsurf dans le backend WorkPilot AI
"""

import asyncio
import json
import logging
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


class WindsurMCPIntegration:
    """Intégration MCP pour Windsurf dans le backend"""

    def __init__(self):
        self.session: ClientSession | None = None
        self.connected = False
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialise la connexion MCP"""
        try:
            self.session = await stdio_client()
            await self.session.initialize()
            self.connected = True
            self.logger.info("MCP Windsurf connecté")
            return True
        except Exception as e:
            self.logger.error(f"Erreur connexion MCP Windsurf: {e}")
            self.connected = False
            return False

    async def get_available_models(self) -> dict[str, Any]:
        """Récupère les modèles Windsurf disponibles"""
        if not self.connected:
            await self.initialize()

        try:
            result = await self.session.call_tool("windsurf_models", {})
            if result and result.content:
                return json.loads(result.content[0].text)
        except Exception as e:
            self.logger.error(f"Erreur récupération modèles: {e}")

        return {
            "base": {"name": "Windsurf Base", "access": "free"},
            "premier": {"name": "Windsurf Premier", "access": "paid"},
        }

    async def generate_response(self, prompt: str, model: str = "base") -> str:
        """Génère une réponse via MCP Windsurf"""
        if not self.connected:
            await self.initialize()

        try:
            result = await self.session.call_tool(
                "windsurf_chat", {"prompt": prompt, "model": model}
            )

            if result and result.content:
                return result.content[0].text
        except Exception as e:
            self.logger.error(f"Erreur génération réponse: {e}")

        return "[Windsurf MCP Error] Impossible de générer une réponse"

    async def check_status(self) -> dict[str, Any]:
        """Vérifie le statut de l'intégration"""
        if not self.connected:
            await self.initialize()

        try:
            result = await self.session.call_tool("windsurf_status", {})
            if result and result.content:
                return json.loads(result.content[0].text)
        except Exception as e:
            self.logger.error(f"Erreur statut: {e}")

        return {"connected": False, "error": str(e)}


# Instance globale de l'intégration MCP
_windsurf_mcp_instance = None


async def get_windsurf_mcp() -> WindsurMCPIntegration:
    """Récupère l'instance MCP Windsurf (singleton)"""
    global _windsurf_mcp_instance
    if _windsurf_mcp_instance is None:
        _windsurf_mcp_instance = WindsurMCPIntegration()
        await _windsurf_mcp_instance.initialize()
    return _windsurf_mcp_instance


# Test d'intégration
async def test_windsurf_mcp_integration():
    """Test de l'intégration MCP Windsurf"""
    print("🧪 Test de l'intégration MCP Windsurf...")

    mcp = await get_windsurf_mcp()

    print("\n📊 Statut:")
    status = await mcp.check_status()
    for key, value in status.items():
        print(f"  - {key}: {value}")

    print("\n🤖 Modèles disponibles:")
    models = await mcp.get_available_models()
    for model_id, model_info in models.items():
        print(f"  - {model_id}: {model_info['name']} ({model_info['access']})")

    print("\n💬 Test de génération:")
    response = await mcp.generate_response("Test simple", "base")
    print(f"  Réponse: {response}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_windsurf_mcp_integration())
