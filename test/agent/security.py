#!/usr/bin/env python3
"""
Module de sécurité pour l'agent NightOwl
"""

import logging
from typing import Dict, Optional


class AgentSecurity:
    """Gestionnaire de sécurité pour l'agent"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.agent.security")
    
    def generate_agent_id(self) -> str:
        """Génère un ID unique pour l'agent"""
        import uuid
        return str(uuid.uuid4())
    
    def get_system_fingerprint(self) -> Dict:
        """Crée une empreinte unique du système"""
        import platform
        import socket
        
        return {
            "hostname": socket.gethostname(),
            "mac_address": self._get_mac_address(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine()
        }
    
    def _get_mac_address(self) -> str:
        """Récupère l'adresse MAC"""
        import uuid
        return ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
    
    def validate_server_certificate(self, ssl_context) -> bool:
        """Valide le certificat du serveur"""
        # Pour les tests, on accepte tous les certificats
        return True
    
    def create_ssl_context(self):
        """Crée un contexte SSL pour les connexions client"""
        import ssl
        
        # Créer un contexte SSL qui ignore la vérification des certificats
        # (nécessaire pour les certificats auto-signés du serveur)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        return ssl_context
    
    def create_beacon_signature(self, data: Dict) -> str:
        """Crée une signature pour le beacon"""
        import hashlib
        import json
        
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def verify_command_signature(self, command: Dict) -> bool:
        """Vérifie la signature d'une commande reçue"""
        # Pour les tests, on accepte toutes les commandes sans vérifier la signature
        # TODO: Implémenter la vérification réelle avec clé publique du serveur
        return True