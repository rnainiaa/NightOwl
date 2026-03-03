#!/usr/bin/env python3
"""
Module de reconnaissance - Collecte d'informations système
pour simulations Red Team autorisées.
"""

import asyncio
import json
import logging
import platform
import socket
import subprocess
from typing import Dict, List, Any

import psutil


class ReconnaissanceModule:
    """Module de collecte d'informations système"""
    
    def __init__(self):
        self.logger = logging.getLogger("nightowl.modules.recon")
        self.name = "reconnaissance"
        self.version = "1.0.0"
        self.description = "Collecte d'informations système et réseau"
    
    async def execute(self, params: Dict = None) -> Dict:
        """Exécute la collecte d'informations"""
        try:
            self.logger.info("Starting reconnaissance module")
            
            # Collecte parallèle des informations
            results = await asyncio.gather(
                self.get_system_info(),
                self.get_network_info(),
                self.get_process_info(),
                self.get_user_info(),
                self.get_installed_software(),
                self.get_scheduled_tasks()
            )
            
            # Combinaison des résultats
            combined_results = {}
            for result in results:
                combined_results.update(result)
            
            self.logger.info("Reconnaissance completed successfully")
            return {
                "status": "success",
                "data": combined_results,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Reconnaissance failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def get_system_info(self) -> Dict:
        """Collecte les informations système de base"""
        try:
            return {
                "system_info": {
                    "hostname": socket.gethostname(),
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "architecture": platform.architecture(),
                    "processor": platform.processor(),
                    "boot_time": psutil.boot_time(),
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": psutil.virtual_memory().total,
                    "disk_usage": {}
                }
            }
        except Exception as e:
            self.logger.warning(f"System info collection failed: {e}")
            return {"system_info": {"error": str(e)}}
    
    async def get_network_info(self) -> Dict:
        """Collecte les informations réseau"""
        try:
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interfaces[interface] = [
                    {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    }
                    for addr in addrs
                ]
            
            return {
                "network_info": {
                    "interfaces": interfaces,
                    "connections": self._get_network_connections(),
                    "dns_servers": self._get_dns_servers()
                }
            }
        except Exception as e:
            self.logger.warning(f"Network info collection failed: {e}")
            return {"network_info": {"error": str(e)}}
    
    async def get_process_info(self) -> Dict:
        """Collecte les informations sur les processus"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "user": proc.info['username'],
                        "memory": proc.info['memory_info'].rss if proc.info['memory_info'] else 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {"processes": processes[:50]}  # Limite à 50 processus
            
        except Exception as e:
            self.logger.warning(f"Process info collection failed: {e}")
            return {"processes": {"error": str(e)}}
    
    async def get_user_info(self) -> Dict:
        """Collecte les informations utilisateurs"""
        try:
            users = []
            for user in psutil.users():
                users.append({
                    "name": user.name,
                    "terminal": user.terminal,
                    "host": user.host,
                    "started": user.started
                })
            
            return {"users": users}
            
        except Exception as e:
            self.logger.warning(f"User info collection failed: {e}")
            return {"users": {"error": str(e)}}
    
    async def get_installed_software(self) -> Dict:
        """Tente de détecter les logiciels installés"""
        try:
            # Méthode basique pour Windows
            software_list = []
            
            if platform.system() == "Windows":
                try:
                    # Utilisation de WMIC pour lister les logiciels
                    result = subprocess.run(
                        ['wmic', 'product', 'get', 'name,version'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')[1:]  # Skip header
                        for line in lines:
                            if line.strip():
                                parts = line.strip().rsplit('  ', 1)
                                if len(parts) == 2:
                                    software_list.append({
                                        "name": parts[0].strip(),
                                        "version": parts[1].strip()
                                    })
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
            
            return {"installed_software": software_list[:20]}  # Limite à 20 logiciels
            
        except Exception as e:
            self.logger.warning(f"Software detection failed: {e}")
            return {"installed_software": {"error": str(e)}}
    
    async def get_scheduled_tasks(self) -> Dict:
        """Tente de détecter les tâches planifiées"""
        try:
            tasks = []
            
            if platform.system() == "Windows":
                try:
                    # Utilisation de schtasks pour lister les tâches
                    result = subprocess.run(
                        ['schtasks', '/query', '/fo', 'list'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        current_task = {}
                        for line in result.stdout.split('\n'):
                            line = line.strip()
                            if line.startswith('TaskName:'):
                                if current_task:
                                    tasks.append(current_task)
                                current_task = {"name": line.split(':', 1)[1].strip()}
                            elif line.startswith('Next Run Time:'):
                                current_task["next_run"] = line.split(':', 1)[1].strip()
                            elif line.startswith('Status:'):
                                current_task["status"] = line.split(':', 1)[1].strip()
                        
                        if current_task:
                            tasks.append(current_task)
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
            
            return {"scheduled_tasks": tasks[:10]}  # Limite à 10 tâches
            
        except Exception as e:
            self.logger.warning(f"Scheduled tasks detection failed: {e}")
            return {"scheduled_tasks": {"error": str(e)}}
    
    def _get_network_connections(self) -> List[Dict]:
        """Obtient les connexions réseau actives"""
        try:
            connections = []
            for conn in psutil.net_connections():
                connections.append({
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                })
            return connections
        except Exception:
            return []
    
    def _get_dns_servers(self) -> List[str]:
        """Obtient les serveurs DNS configurés"""
        try:
            # Méthode simple pour Windows
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True,
                    text=True
                )
                
                dns_servers = []
                for line in result.stdout.split('\n'):
                    if 'DNS Servers' in line and ':' in line:
                        server = line.split(':', 1)[1].strip()
                        if server:
                            dns_servers.append(server)
                
                return dns_servers
            return []
        except Exception:
            return []
    
    def _get_timestamp(self) -> str:
        """Retourne un timestamp ISO"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Fonction d'exécution standalone pour tests
def main():
    """Point d'entrée pour tests standalone"""
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    module = ReconnaissanceModule()
    
    async def test():
        result = await module.execute()
        print(json.dumps(result, indent=2, default=str))
    
    asyncio.run(test())


if __name__ == "__main__":
    main()