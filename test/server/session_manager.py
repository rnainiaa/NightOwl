#!/usr/bin/env python3
"""
Gestionnaire de sessions pour le serveur NightOwl
"""

import uuid
import time
from typing import Dict, List, Optional
from datetime import datetime


class SessionManager:
    """Gère les sessions des agents connectés"""
    
    def __init__(self, database=None):
        self.sessions: Dict[str, Dict] = {}
        self.db = database
        self.logger = None
    
    def set_logger(self, logger):
        """Définit le logger"""
        self.logger = logger
    
    def create_session(self, agent_id: str, agent_data: Dict, ip_address: str = None) -> str:
        """Crée une nouvelle session pour un agent"""
        session_id = str(uuid.uuid4())
        
        # Tenter de récupérer l'IP depuis les données système si non fournie
        if not ip_address or ip_address == '127.0.0.1':
            # Essayer de trouver une IP non locale dans les interfaces
            try:
                interfaces = agent_data.get('system_info', {}).get('network', {}).get('interfaces', {})
                if isinstance(interfaces, dict):
                    for iface, addrs in interfaces.items():
                        # Logique simplifiée : prendre la première IP IPv4
                        if 2 in addrs: # AF_INET
                            for addr in addrs[2]:
                                ip = addr.get('addr')
                                if ip and not ip.startswith('127.'):
                                    ip_address = ip
                                    break
            except Exception:
                pass

        self.sessions[session_id] = {
            'id': session_id,
            'agent_id': agent_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': time.time(),
            'agent_data': agent_data,
            'status': 'active',
            'hostname': agent_data.get('hostname') or agent_data.get('system_info', {}).get('hostname', 'unknown'),
            'ip_address': ip_address or 'unknown'
        }
        
        if self.logger:
            self.logger.info(f"New session created: {session_id} for agent: {agent_id} (IP: {ip_address})")
        
        # Save to DB
        if self.db:
            self.db.save_session(self.sessions[session_id])
            
        return session_id

    def update_session_stats(self, session_id: str, stats: Dict):
        """Met à jour les statistiques de la session"""
        if session_id in self.sessions:
            # Mettre à jour les stats dans agent_data
            if 'agent_data' not in self.sessions[session_id]:
                self.sessions[session_id]['agent_data'] = {}
            
            self.sessions[session_id]['agent_data']['system_stats'] = stats
    
    def validate_session(self, session_id: str) -> bool:
        """Vérifie si une session est valide"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Vérifie si la session a expiré (10 minutes d'inactivité)
        if time.time() - session['last_activity'] > 600:
            # Au lieu de terminer la session, on la marque comme inactive
            session['status'] = 'inactive'
            if self.logger:
                self.logger.info(f"Session marked as inactive: {session_id} (last activity: {time.time() - session['last_activity']:.0f}s ago)")
            return False
        
        return True
    
    def update_activity(self, session_id: str):
        """Met à jour le timestamp de dernière activité"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = time.time()
    
    def terminate_session(self, session_id: str):
        """Termine une session"""
        if session_id in self.sessions:
            if self.logger:
                self.logger.info(f"Session terminated: {session_id}")
            del self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Récupère les informations d'une session"""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict]:
        """Retourne toutes les sessions (actives et inactives)"""
        sessions_list = []
        for session_id, session_data in self.sessions.items():
            # Vérifier si la session est toujours active
            is_active = self.validate_session(session_id)
            
            sessions_list.append({
                'id': session_id,
                'agent_id': session_data['agent_id'],
                'hostname': session_data['hostname'],
                'ip_address': session_data['ip_address'],
                'status': session_data['status'],
                'created_at': session_data['created_at'],
                'last_activity': session_data['last_activity'],
                'last_seen': datetime.fromtimestamp(session_data['last_activity']).isoformat(),
                'is_online': is_active
            })
        
        return sessions_list
    
    def get_next_beacon_time(self) -> int:
        """Retourne le temps avant le prochain beacon"""
        import random
        return random.randint(30, 120)  # Entre 30 et 120 secondes