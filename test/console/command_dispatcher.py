#!/usr/bin/env python3
"""
Dispatcher de commandes pour la console NightOwl
"""

import logging
from typing import Dict, List, Optional


class CommandDispatcher:
    """Dispatch les commandes vers les handlers appropriés"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.console.command_dispatcher")
        self.command_handlers = {
            "help": self.handle_help,
            "sessions": self.handle_sessions,
            "exec": self.handle_exec,
            "quit": self.handle_quit,
            "exit": self.handle_quit,
            "clear": self.handle_clear,
        }
    
    async def dispatch(self, command: str, args: List[str], session_manager) -> str:
        """Dispatch une commande vers le handler approprié"""
        if not command:
            return ""
        
        if command in self.command_handlers:
            return await self.command_handlers[command](args, session_manager)
        else:
            return f"Commande inconnue: {command}. Tapez 'help' pour la liste des commandes."
    
    async def handle_help(self, args: List[str], session_manager) -> str:
        """Affiche l'aide"""
        help_text = """
📋 **NightOwl Console - Commandes Disponibles**

🔍 **Sessions**
  sessions list      - Lister toutes les sessions actives
  sessions info <id> - Afficher les détails d'une session

⚡ **Exécution**
  exec <command>    - Exécuter une commande système
  exec whoami       - Afficher l'utilisateur courant
  exec pwd          - Afficher le répertoire courant
  exec ls <dir>     - Lister les fichiers d'un répertoire

🔧 **Utilitaires**
  help              - Afficher cette aide
  clear             - Effacer l'écran
  quit / exit       - Quitter la console

💡 **Exemples**:
  sessions list
  exec whoami
  exec ls C:\\Users
"""
        return help_text
    
    async def handle_sessions(self, args: List[str], session_manager) -> str:
        """Gère les commandes de sessions"""
        if not args:
            return "Usage: sessions [list|info <id>]"
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            sessions = await session_manager.list_sessions()
            if not sessions:
                return "❌ Aucune session active"
            
            result = "📊 **Sessions Actives**\n\n"
            for session in sessions:
                result += f"🔹 {session['id']} - {session.get('hostname', 'Unknown')} ({session.get('ip_address', 'N/A')})\n"
                result += f"   Status: {session.get('status', 'unknown')} | Last: {session.get('last_activity', 'N/A')}\n\n"
            return result
            
        elif subcommand == "info" and len(args) > 1:
            session_id = args[1]
            session_info = session_manager.get_session_info(session_id)
            if session_info:
                return f"📋 **Session {session_id}**\n{self._format_session_info(session_info)}"
            else:
                return f"❌ Session non trouvée: {session_id}"
        
        return "Usage: sessions [list|info <id>]"
    
    async def handle_exec(self, args: List[str], session_manager) -> str:
        """Exécute une commande sur une session"""
        if not args:
            return "Usage: exec <command> [args...]"
        
        # Pour l'instant, retourne un message d'information
        # L'implémentation réelle nécessitera de sélectionner une session active
        command = " ".join(args)
        return f"⚠️  Fonctionnalité en développement\nCommande: {command}\nSélectionnez d'abord une session avec 'sessions list'"
    
    async def handle_quit(self, args: List[str], session_manager) -> str:
        """Gère la commande quit"""
        return "quit"
    
    async def handle_clear(self, args: List[str], session_manager) -> str:
        """Efface l'écran"""
        return "clear"
    
    def _format_session_info(self, session_info: Dict) -> str:
        """Formate les informations d'une session"""
        info = f"Hostname: {session_info.get('hostname', 'N/A')}\n"
        info += f"IP: {session_info.get('ip_address', 'N/A')}\n"
        info += f"OS: {session_info.get('os', 'N/A')}\n"
        info += f"User: {session_info.get('user', 'N/A')}\n"
        info += f"Status: {session_info.get('status', 'unknown')}\n"
        info += f"Last Activity: {session_info.get('last_activity', 'N/A')}\n"
        return info