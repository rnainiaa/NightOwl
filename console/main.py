#!/usr/bin/env python3
"""
NightOwl Console - Interface opérateur pour tests Red Team

Console interactive de type Metasploit pour la gestion
des sessions et l'exécution de commandes sur les agents.
"""

import asyncio
import cmd
import json
import logging
try:
    import pyreadline3 as readline  # Alternative pour Windows
except ImportError:
    import readline  # Pour Linux/Mac
from typing import Dict, List, Optional
from datetime import datetime

import aiohttp
import rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from session_manager import SessionManager
from command_dispatcher import CommandDispatcher


class NightOwlConsole(cmd.Cmd):
    """Console interactive NightOwl"""
    
    def __init__(self, config: Dict):
        super().__init__()
        
        self.config = config
        self.logger = logging.getLogger("nightowl.console")
        
        # Composants
        self.console = Console()
        self.session_manager = SessionManager(config)
        self.command_dispatcher = CommandDispatcher(config)
        
        # État
        self.authenticated = False
        self.current_session: Optional[str] = None
        self.prompt = "nightowl> "
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
    
    def preloop(self):
        """Initialisation avant démarrage console"""
        self.console.print(Panel.fit(
            "[bold red]⚠️  NIGHTOWL RED TEAM CONSOLE[/bold red]\n"
            "[yellow]Usage restreint aux tests autorisés[/yellow]\n\n"
            "[green]Tapez 'help' pour la liste des commandes[/green]",
            title="NightOwl Framework",
            border_style="red"
        ))
    
    async def initialize(self):
        """Initialisation de la console"""
        try:
            # Création session HTTP
            self.session = aiohttp.ClientSession(
                base_url=self.config['server_url'],
                headers={
                    'User-Agent': 'NightOwl-Console/1.0.0',
                    'Content-Type': 'application/json'
                }
            )
            
            # Authentification
            if not await self.authenticate():
                self.console.print("[red]Authentication failed![/red]")
                return False
            
            self.authenticated = True
            self.console.print("[green]Authentication successful![/green]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]Initialization failed: {e}[/red]")
            return False
    
    async def authenticate(self) -> bool:
        """Authentification auprès du serveur"""
        try:
            # Demande credentials
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            
            auth_data = {
                "username": username,
                "password": password
            }
            
            async with self.session.post(
                "/api/operator/auth",
                json=auth_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.session.headers.update({
                        'Authorization': f"Bearer {result['token']}"
                    })
                    return True
                else:
                    return False
                    
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def do_sessions(self, arg: str):
        """Affiche les sessions actives : sessions [list|info|interact]"""
        asyncio.run(self._handle_sessions(arg))
    
    async def _handle_sessions(self, arg: str):
        """Gestion des sessions"""
        try:
            if arg == "list" or not arg:
                # Liste des sessions
                async with self.session.get("/api/sessions") as response:
                    if response.status == 200:
                        sessions = await response.json()
                        self._display_sessions(sessions)
                    else:
                        self.console.print("[red]Failed to get sessions[/red]")
            
            elif arg.startswith("interact "):
                # Interaction avec session
                session_id = arg.split(" ", 1)[1]
                self.current_session = session_id
                self.prompt = f"nightowl({session_id[:8]})> "
                self.console.print(f"[green]Interacting with session {session_id}[/green]")
            
            elif arg == "back":
                # Retour au prompt principal
                self.current_session = None
                self.prompt = "nightowl> "
                self.console.print("[yellow]Returned to main prompt[/yellow]")
            
            else:
                self.console.print("[yellow]Usage: sessions [list|interact ID|back][/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]Sessions error: {e}[/red]")
    
    def _display_sessions(self, sessions: List[Dict]):
        """Affichage des sessions dans un tableau"""
        table = Table(title="Active Sessions")
        
        table.add_column("ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Hostname", style="white")
        table.add_column("IP", style="blue")
        table.add_column("Last Seen", style="yellow")
        table.add_column("Status", style="magenta")
        
        for session in sessions:
            table.add_row(
                session['id'][:8],
                session['agent_id'][:8],
                session['hostname'],
                session['ip'],
                session['last_seen'],
                session['status']
            )
        
        self.console.print(table)
    
    def do_exec(self, arg: str):
        """Exécute une commande : exec <command>"""
        if not self.current_session:
            self.console.print("[red]No active session. Use 'sessions interact ID' first[/red]")
            return
        
        asyncio.run(self._handle_exec(arg))
    
    async def _handle_exec(self, arg: str):
        """Exécution de commande"""
        try:
            command_data = {
                "operator": "console_user",
                "session_id": self.current_session,
                "command": {
                    "type": "shell",
                    "payload": arg,
                    "timeout": 30
                }
            }
            
            async with self.session.post(
                "/api/command",
                json=command_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.console.print(f"[green]Result:[/green]\n{result['result']}")
                else:
                    self.console.print("[red]Command execution failed[/red]")
                    
        except Exception as e:
            self.console.print(f"[red]Exec error: {e}[/red]")
    
    def do_sysinfo(self, arg: str):
        """Récupère les informations système : sysinfo [session_id]"""
        asyncio.run(self._handle_sysinfo(arg))
    
    async def _handle_sysinfo(self, arg: str):
        """Récupération informations système"""
        try:
            target_session = arg if arg else self.current_session
            if not target_session:
                self.console.print("[red]No session specified[/red]")
                return
            
            command_data = {
                "operator": "console_user",
                "session_id": target_session,
                "command": {
                    "type": "system_info",
                    "timeout": 10
                }
            }
            
            async with self.session.post(
                "/api/command",
                json=command_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Affichage formaté
                    info = result['result']
                    table = Table(title=f"System Info - {target_session[:8]}")
                    
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")
                    
                    for key, value in info.items():
                        if isinstance(value, dict):
                            for k, v in value.items():
                                table.add_row(f"{key}.{k}", str(v))
                        else:
                            table.add_row(key, str(value))
                    
                    self.console.print(table)
                else:
                    self.console.print("[red]System info failed[/red]")
                    
        except Exception as e:
            self.console.print(f"[red]Sysinfo error: {e}[/red]")
    
    def do_modules(self, arg: str):
        """Gère les modules : modules [list|load|run]"""
        self.console.print("[yellow]Modules functionality coming soon...[/yellow]")
    
    def do_logs(self, arg: str):
        """Affiche les logs : logs [system|forensic|clear]"""
        asyncio.run(self._handle_logs(arg))
    
    async def _handle_logs(self, arg: str):
        """Gestion des logs"""
        try:
            if arg == "system":
                async with self.session.get("/api/logs?type=system") as response:
                    if response.status == 200:
                        logs = await response.json()
                        self._display_logs(logs, "System Logs")
            
            elif arg == "forensic":
                async with self.session.get("/api/logs?type=forensic") as response:
                    if response.status == 200:
                        logs = await response.json()
                        self._display_logs(logs, "Forensic Logs")
            
            else:
                self.console.print("[yellow]Usage: logs [system|forensic][/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]Logs error: {e}[/red]")
    
    def _display_logs(self, logs: List[Dict], title: str):
        """Affichage des logs"""
        table = Table(title=title)
        
        table.add_column("Timestamp", style="cyan")
        table.add_column("Level", style="yellow")
        table.add_column("Message", style="white")
        
        for log in logs[-20:]:  # Last 20 entries
            level_style = {
                "INFO": "green",
                "WARNING": "yellow", 
                "ERROR": "red",
                "DEBUG": "blue"
            }.get(log['level'], "white")
            
            table.add_row(
                log['timestamp'],
                f"[{level_style}]{log['level']}[/{level_style}]",
                log['message'][:100] + "..." if len(log['message']) > 100 else log['message']
            )
        
        self.console.print(table)
    
    def do_exit(self, arg: str):
        """Quitte la console : exit"""
        asyncio.run(self._cleanup())
        self.console.print("[green]Goodbye![/green]")
        return True
    
    def do_quit(self, arg: str):
        """Quitte la console : quit"""
        return self.do_exit(arg)
    
    async def _cleanup(self):
        """Nettoyage des ressources"""
        if self.session:
            await self.session.close()
    
    def help(self):
        """Affiche l'aide"""
        help_text = """
[bold]Commandes disponibles:[/bold]

[cyan]sessions[/cyan] list          - Liste les sessions actives
[cyan]sessions[/cyan] interact ID   - Interagit avec une session
[cyan]sessions[/cyan] back         - Retour au prompt principal

[cyan]exec[/cyan] <commande>      - Exécute une commande shell
[cyan]sysinfo[/cyan] [ID]         - Informations système de la session

[cyan]modules[/cyan] list         - Liste les modules disponibles
[cyan]logs[/cyan] system         - Affiche les logs système
[cyan]logs[/cyan] forensic       - Affiche les logs forensiques

[cyan]exit[/cyan]               - Quitte la console
[cyan]quit[/cyan]               - Quitte la console
[cyan]help[/cyan]               - Affiche cette aide
"""
        self.console.print(help_text)


def main():
    """Point d'entrée principal de la console"""
    import argparse
    import yaml
    
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='NightOwl Red Team Console')
    parser.add_argument('--config', '-c', default='config.yaml', help='Configuration file')
    parser.add_argument('--server', '-s', help='C2 Server URL')
    args = parser.parse_args()
    
    # Chargement configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Configuration file not found")
        return
    
    # Override server URL if provided
    if args.server:
        config['server_url'] = args.server
    
    # Vérification URL serveur
    if 'server_url' not in config:
        print("Server URL not configured")
        return
    
    # Création console
    console = NightOwlConsole(config)
    
    # Initialisation asynchrone
    async def run_console():
        if await console.initialize():
            console.cmdloop()
        else:
            print("Console initialization failed")
    
    try:
        asyncio.run(run_console())
    except KeyboardInterrupt:
        print("\nConsole interrupted")
    except Exception as e:
        print(f"Console error: {e}")


if __name__ == "__main__":
    main()