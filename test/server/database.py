#!/usr/bin/env python3
"""
Module de base de données pour NightOwl Server
"""

import sqlite3
import logging
import bcrypt
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class Database:
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.database")
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données et les tables"""
        db_path = Path(self.config.get('path', 'data/nightowl.db'))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Création des tables
        self._create_tables()
        self.logger.info(f"Database initialized: {db_path}")
    
    def _create_tables(self):
        """Crée les tables nécessaires"""
        cursor = self.conn.cursor()
        
        # Table des sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                hostname TEXT,
                ip_address TEXT,
                created_at TEXT,
                last_activity TEXT,
                status TEXT,
                agent_data TEXT
            )
        """)
        
        # Table des commandes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                command TEXT,
                params TEXT,
                status TEXT,
                result TEXT,
                created_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)
        
        # Table des logs d'activité
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                component TEXT,
                message TEXT,
                details TEXT
            )
        """)
        
        # Table des opérateurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                created_at TEXT,
                last_login TEXT,
                password_changed BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("PRAGMA table_info(operators)")
        operator_columns = {row[1] for row in cursor.fetchall()}
        if "password_changed" not in operator_columns:
            cursor.execute("ALTER TABLE operators ADD COLUMN password_changed BOOLEAN DEFAULT 0")
        
        # Insertion des opérateurs par défaut
        self._insert_default_operators()
        
        self.conn.commit()
    
    def _insert_default_operators(self):
        """Insère les opérateurs par défaut"""
        cursor = self.conn.cursor()
        
        # Vérifier si les opérateurs existent déjà
        cursor.execute("SELECT COUNT(*) FROM operators")
        count = cursor.fetchone()[0]
        
        if count == 0:
            timestamp = datetime.utcnow().isoformat()
            
            # Opérateurs par défaut (mots de passe: admin/operator)
            # Hash généré avec bcrypt pour 'admin123'
            salt = bcrypt.gensalt()
            default_admin_hash = bcrypt.hashpw('admin123'.encode('utf-8'), salt).decode('utf-8')
            
            default_operators = [
                ('admin', default_admin_hash, 'admin', timestamp)
            ]
            
            cursor.executemany("""
                INSERT INTO operators (username, password_hash, role, created_at, password_changed)
                VALUES (?, ?, ?, ?, 0)
            """, default_operators)
            
            self.logger.info("Default operators inserted")

    def get_operator_by_username(self, username: str) -> Optional[Dict]:
        """Récupère un opérateur par son nom d'utilisateur"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM operators WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def create_operator(self, username: str, password_hash: str, role: str = 'operator') -> bool:
        """Crée un nouvel opérateur"""
        try:
            from datetime import datetime, timezone
            cursor = self.conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO operators (username, password_hash, role, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, role, now, now)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            self.logger.error(f"Failed to create operator: {e}")
            return False

    def update_operator_login(self, username: str):
        """Met à jour la date de dernière connexion"""
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("UPDATE operators SET last_login = ? WHERE username = ?", (now, username))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update login time: {e}")

    def update_operator_password(self, username: str, password_hash: str) -> bool:
        """Met à jour le mot de passe d'un opérateur et marque comme changé"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE operators SET password_hash = ?, password_changed = 1 WHERE username = ?",
                (password_hash, username)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to update operator password: {e}")
            return False

    def get_operator_password_status(self, username: str) -> bool:
        """Vérifie si l'opérateur a changé son mot de passe"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_changed FROM operators WHERE username = ?", (username,))
        row = cursor.fetchone()
        return bool(row['password_changed']) if row else False
    
    async def log_operator_action(self, operator: str, command: str, target: str, result: Dict):
        """Journalise une action d'opérateur"""
        # Note: Dans une vraie implémentation, utiliser run_in_executor pour ne pas bloquer
        try:
            message = f"Operator {operator} executed {command}"
            if target:
                message += f" on {target}"
            
            self.log_activity(
                level="INFO",
                component="OPERATOR",
                message=message,
                details=str(result)
            )
        except Exception as e:
            self.logger.error(f"Failed to log operator action: {e}")

    def get_commands(self, limit: int = 100, agent_id: str = None) -> List[Dict]:
        """Récupère les dernières commandes exécutées"""
        cursor = self.conn.cursor()
        
        if agent_id:
            cursor.execute("""
                SELECT c.*, s.agent_id, s.hostname 
                FROM commands c 
                JOIN sessions s ON c.session_id = s.id 
                WHERE s.agent_id = ?
                ORDER BY c.created_at DESC 
                LIMIT ?
            """, (agent_id, limit))
        else:
            cursor.execute("""
                SELECT c.*, s.agent_id, s.hostname 
                FROM commands c 
                JOIN sessions s ON c.session_id = s.id 
                ORDER BY c.created_at DESC 
                LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]

    def save_command(self, command_data: Dict):
        """Sauvegarde une nouvelle commande"""
        try:
            cursor = self.conn.cursor()
            import json
            
            # Conversion params en JSON si dict
            params = command_data.get('params', {})
            if isinstance(params, dict):
                params = json.dumps(params)
                
            cursor.execute("""
                INSERT INTO commands (id, session_id, command, params, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                command_data['id'],
                command_data['session_id'],
                command_data['command'],
                params,
                command_data['status'],
                command_data['created_at']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save command: {e}")
            return False

    def update_command_result(self, command_id: str, status: str, result: Any, completed_at: str):
        """Met à jour le résultat d'une commande"""
        try:
            cursor = self.conn.cursor()
            import json
            
            # Conversion result en JSON si dict/list
            if isinstance(result, (dict, list)):
                result = json.dumps(result)
            elif result is None:
                result = ""
            else:
                result = str(result)
                
            cursor.execute("""
                UPDATE commands 
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
            """, (status, result, completed_at, command_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update command result: {e}")
            return False

    def save_session(self, session_data: Dict):
        """Sauvegarde ou met à jour une session"""
        try:
            cursor = self.conn.cursor()
            import json
            
            # Conversion agent_data en JSON si dict
            agent_data = session_data.get('agent_data', {})
            if isinstance(agent_data, dict):
                agent_data = json.dumps(agent_data)
                
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (id, agent_id, hostname, ip_address, created_at, last_activity, status, agent_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data['id'],
                session_data['agent_id'],
                session_data['hostname'],
                session_data['ip_address'],
                session_data['created_at'],
                str(session_data['last_activity']),
                session_data['status'],
                agent_data
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            return False

    def close(self):
        """Ferme la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
    
    def __del__(self):
        self.close()
