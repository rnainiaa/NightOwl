#!/usr/bin/env python3
"""
Module de sécurité pour NightOwl Server
"""

import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional


class SecurityManager:
    """Gestionnaire de sécurité et d'authentification"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.security")
        self.jwt_secret = config.get('jwt_secret', 'change_this_to_secure_jwt_secret')
        self.jwt_expiry_hours = config.get('jwt_expiry_hours', 24)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe contre son hash bcrypt"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Password verification failed: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def create_jwt_token(self, payload: Dict) -> str:
        """Crée un token JWT"""
        from datetime import datetime, timezone
        payload = payload.copy()
        payload['exp'] = datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiry_hours)
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Vérifie et décode un token JWT"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def validate_operator_credentials(self, username: str, password: str, db) -> Dict:
        """Valide les credentials d'un opérateur et retourne le statut du mot de passe"""
        operator = db.get_operator_by_username(username)
        if not operator:
            self.logger.warning(f"Operator not found: {username}")
            return {"authenticated": False, "password_changed": False}
        
        self.logger.info(f"Checking auth for {username}")
        if self.verify_password(password, operator['password_hash']):
            db.update_operator_login(username)
            self.logger.info(f"Operator authenticated: {username}")
            
            # Vérifier si le mot de passe a été changé
            password_changed = bool(operator.get('password_changed', 0))
            return {
                "authenticated": True, 
                "password_changed": password_changed,
                "operator": operator
            }
        
        self.logger.warning(f"Invalid password for operator: {username}")
        return {"authenticated": False, "password_changed": False}

    def validate_password_complexity(self, password: str) -> Dict:
        """Valide la complexité d'un mot de passe"""
        errors = []
        
        # Longueur minimale
        if len(password) < 12:
            errors.append("Le mot de passe doit contenir au moins 12 caractères")
        
        # Lettres majuscules
        if not any(c.isupper() for c in password):
            errors.append("Le mot de passe doit contenir au moins une lettre majuscule")
        
        # Lettres minuscules
        if not any(c.islower() for c in password):
            errors.append("Le mot de passe doit contenir au moins une lettre minuscule")
        
        # Chiffres
        if not any(c.isdigit() for c in password):
            errors.append("Le mot de passe doit contenir au moins un chiffre")
        
        # Caractères spéciaux
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("Le mot de passe doit contenir au moins un caractère spécial")
        
        # Vérifier que ce n'est pas le mot de passe par défaut
        default_passwords = ["password123", "admin123", "changeme"]
        if password.lower() in default_passwords:
            errors.append("Le mot de passe ne peut pas être un mot de passe par défaut")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def generate_agent_token(self, agent_id: str) -> str:
        """Génère un token pour un agent"""
        from datetime import datetime, timezone
        payload = {
            'agent_id': agent_id,
            'type': 'agent',
            'iat': datetime.now(timezone.utc)
        }
        
        return self.create_jwt_token(payload)
    
    def verify_agent_token(self, token: str) -> Optional[str]:
        """Vérifie un token d'agent"""
        payload = self.verify_jwt_token(token)
        if payload and payload.get('type') == 'agent':
            return payload.get('agent_id')
        return None
    
    def validate_session_access(self, session_id: str, operator_role: str) -> bool:
        """Valide l'accès à une session basé sur le rôle"""
        # Les admins ont accès à tout
        if operator_role == 'admin':
            return True
        
        # Les utilisateurs normaux peuvent avoir des restrictions
        # (à implémenter selon les besoins)
        return True

    async def authenticate_operator(self, request) -> bool:
        """Authentifie une requête d'opérateur via header Authorization"""
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return False
            
        try:
            scheme, token = auth_header.strip().split()
            if scheme.lower() != 'bearer':
                return False
                
            payload = self.verify_jwt_token(token)
            if not payload or payload.get('type') != 'operator':
                return False
                
            # On pourrait ajouter une vérification supplémentaire en base ici
            # mais le token valide suffit pour l'instant
            return True
            
        except ValueError:
            return False

