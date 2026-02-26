#!/usr/bin/env python3
"""
Client MCP pour Windsurf - Permet d'utiliser le serveur MCP Windsurf
"""

import asyncio
import json
import logging
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

class WindsurMCPClient:
    def __init__(self):
        self.session = None
    
    async def connect(self):
        """Connecte au serveur MCP Windsurf"""
        try:
            self.session = await stdio_client()
            await self.session.initialize()
            logging.info("Connecté au serveur MCP Windsurf")
            return True
        except Exception as e:
            logging.error(f"Erreur de connexion MCP: {e}")
            return False
    
    async def list_tools(self):
        """Liste les outils disponibles"""
        if not self.session:
            await self.connect()
        
        try:
            result = await self.session.list_tools()
            return result.tools
        except Exception as e:
            logging.error(f"Erreur list_tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Appelle un outil MCP"""
        if not self.session:
            await self.connect()
        
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            return result
        except Exception as e:
            logging.error(f"Erreur call_tool {tool_name}: {e}")
            return None
    
    async def get_models(self):
        """Récupère les modèles Windsurf disponibles"""
        result = await self.call_tool("windsurf_models")
        if result and result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def chat(self, prompt: str, model: str = "base"):
        """Chat avec un modèle Windsurf"""
        result = await self.call_tool("windsurf_chat", {
            "prompt": prompt,
            "model": model
        })
        if result and result.content:
            return result.content[0].text
        return "Erreur lors du chat"
    
    async def get_status(self):
        """Vérifie le statut de la connexion"""
        result = await self.call_tool("windsurf_status")
        if result and result.content:
            return json.loads(result.content[0].text)
        return {}

# Test du client MCP
async def test_mcp_client():
    """Test du client MCP Windsurf"""
    client = WindsurMCPClient()
    
    print("🔗 Connexion au serveur MCP Windsurf...")
    if await client.connect():
        print("✅ Connecté!")
        
        print("\n🛠️  Outils disponibles:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        print("\n🤖 Modèles disponibles:")
        models = await client.get_models()
        for model_id, model_info in models.items():
            print(f"  - {model_id}: {model_info['name']} ({model_info['access']})")
        
        print("\n💬 Test de chat:")
        response = await client.chat("Hello, comment ça va ?", "base")
        print(f"  Réponse: {response}")
        
        print("\n📊 Statut:")
        status = await client.get_status()
        for key, value in status.items():
            print(f"  - {key}: {value}")
    else:
        print("❌ Erreur de connexion")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_mcp_client())
