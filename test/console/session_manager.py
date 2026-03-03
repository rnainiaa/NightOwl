#!/usr/bin/env python3
"""
Gestionnaire de sessions pour la console NightOwl
"""

import aiohttp
import logging
from typing import Dict, List, Optional


class SessionManager:
    """Gère les sessions d'agents connectés"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.console.session_manager")
        self.sessions: Dict[str, Dict] = {}
        self.base_url = f"https://{config['server']['host']}:{config['server']['port']}"
    
    async def authenticate(self, username: str, password: str) -> bool:
        """Authentifie l'opérateur auprès du serveur"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/operator/auth",
                    json={"username": username, "password": password},
                    ssl=False  # Ignorer la vérification SSL pour les certificats auto-signés
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.token = data.get('token')
                        return True
                    return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    async def list_sessions(self) -> List[Dict]:
        """Récupère la liste des sessions actives"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/sessions",
                    headers={"Authorization": f"Bearer {self.token}"},
                    ssl=False
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return []
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def execute_command(self, session_id: str, command: str, params: Dict = None) -> Dict:
        """Exécute une commande sur une session"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/command",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "session_id": session_id,
                        "command": command,
                        "params": params or {}
                    },
                    ssl=False
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Récupère les informations d'une session spécifique"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, data: Dict):
        """Met à jour les informations d'une session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(data)
        else:
            self.sessions[session_id] = data
    
    def remove_session(self, session_id: str):
        """Supprime une session"""
        if session_id in self.sessions:
            del self.sessions[session_id]