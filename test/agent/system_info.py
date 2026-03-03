#!/usr/bin/env python3
"""
Collecte d'informations système pour l'agent NightOwl
"""

import logging
import platform
import socket
from pathlib import Path
from typing import Dict, List


class SystemInfo:
    """Collecteur d'informations système"""
    
    def __init__(self):
        self.logger = logging.getLogger("nightowl.agent.system_info")
    
    def get_all_info(self) -> Dict:
        """Récupère toutes les informations système"""
        return {
            "system": self.get_system_info(),
            "network": self.get_network_info(),
            "users": self.get_user_info(),
            "processes": self.get_process_info(),
            "hardware": self.get_hardware_info(),
            "timestamp": self._get_timestamp()
        }
    
    def get_system_info(self) -> Dict:
        """Informations du système d'exploitation"""
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "machine": platform.machine()
        }
    
    def get_network_info(self) -> Dict:
        """Informations réseau"""
        try:
            import netifaces
            interfaces = {}
            for interface in netifaces.interfaces(): 
                addrs = netifaces.ifaddresses(interface)
                interfaces[interface] = addrs
            return {"interfaces": interfaces}
        except ImportError:
            return {"interfaces": "netifaces module not available"}
    
    def get_user_info(self) -> Dict:
        """Informations utilisateur"""
        import getpass
        return {
            "current_user": getpass.getuser(),
            "home_directory": str(Path.home()),
            "user_domain": socket.getfqdn()
        }
    
    def get_process_info(self) -> List[Dict]:
        """Liste des processus"""
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes[:50]  # Limiter à 50 processus
    
    def get_hardware_info(self) -> Dict:
        """Informations matérielles"""
        import psutil
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": {}
        }
    
    def _get_timestamp(self) -> str:
        """Retourne un timestamp formaté"""
        from datetime import datetime
        return datetime.utcnow().isoformat()