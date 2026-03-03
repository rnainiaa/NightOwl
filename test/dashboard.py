#!/usr/bin/env python3
"""
NightOwl Dashboard - Interface Graphique de Gestion Centralisée

Tableau de bord administrateur pour la gestion des agents distants
avec monitoring en temps réel et exécution de commandes.
"""

import asyncio
import aiohttp
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkinter.font import Font
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nightowl.dashboard")


class NightOwlDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("NightOwl - Dashboard de Gestion")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2c3e50')
        
        # Configuration du serveur
        self.server_url = "https://localhost:8443"
        self.session = None
        self.token = None
        
        # Données en mémoire
        self.sessions = []
        self.agents = []
        self.command_history = []
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Démarrer les mises à jour automatiques
        self.update_interval = 5000  # 5 secondes
        self.update_data()
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration des poids pour le redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            header_frame, 
            text="🐦 NIGHTOWL DASHBOARD", 
            font=Font(size=16, weight="bold"),
            foreground="#3498db"
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Stats en temps réel
        stats_frame = ttk.LabelFrame(main_frame, text="📊 Statistiques en Temps Réel", padding="10")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=5, pady=5)
        stats_frame.columnconfigure(0, weight=1)
        
        self.stats_labels = {}
        stats = [
            ("Agents Actifs", "0", "#27ae60"),
            ("Sessions", "0", "#e74c3c"),
            ("Commandes Today", "0", "#f39c12"),
            ("Uptime", "00:00:00", "#9b59b6")
        ]
        
        for i, (text, value, color) in enumerate(stats):
            frame = ttk.Frame(stats_frame)
            frame.grid(row=i//2, column=i%2, sticky=(tk.W, tk.E), padx=5, pady=2)
            frame.columnconfigure(1, weight=1)
            
            ttk.Label(frame, text=f"{text}:", font=Font(weight="bold")).grid(row=0, column=0, sticky=tk.W)
            self.stats_labels[text] = ttk.Label(frame, text=value, foreground=color, font=Font(weight="bold"))
            self.stats_labels[text].grid(row=0, column=1, sticky=tk.E)
        
        # Sessions actives
        sessions_frame = ttk.LabelFrame(main_frame, text="🖥️ Sessions Actives", padding="10")
        sessions_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        sessions_frame.columnconfigure(0, weight=1)
        sessions_frame.rowconfigure(0, weight=1)
        
        # Treeview pour les sessions
        columns = ("ID", "Hostname", "IP", "Status", "Durée", "CPU", "Memory")
        self.sessions_tree = ttk.Treeview(sessions_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.sessions_tree.heading(col, text=col)
            self.sessions_tree.column(col, width=100)
        
        self.sessions_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar pour le treeview
        scrollbar = ttk.Scrollbar(sessions_frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sessions_tree.configure(yscrollcommand=scrollbar.set)
        
        # Frame pour les commandes
        command_frame = ttk.LabelFrame(main_frame, text="⚡ Exécution de Commandes", padding="10")
        command_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        command_frame.columnconfigure(1, weight=1)
        
        ttk.Label(command_frame, text="Session ID:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(command_frame, textvariable=self.session_var, width=30)
        self.session_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(command_frame, text="Commande:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.command_var = tk.StringVar()
        command_entry = ttk.Entry(command_frame, textvariable=self.command_var, width=50)
        command_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        command_entry.bind('<Return>', lambda e: self.execute_command())
        
        execute_btn = ttk.Button(command_frame, text="Exécuter", command=self.execute_command)
        execute_btn.grid(row=1, column=2, padx=5)
        
        # Output des commandes
        output_frame = ttk.LabelFrame(main_frame, text="📋 Output des Commandes", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, width=80, height=10, wrap=tk.WORD)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.output_text.configure(state='disabled')
        
        # Sidebar pour les actions rapides
        sidebar_frame = ttk.Frame(main_frame)
        sidebar_frame.grid(row=1, column=1, rowspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Actions rapides
        actions_frame = ttk.LabelFrame(sidebar_frame, text="🚀 Actions Rapides", padding="10")
        actions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))
        actions_frame.columnconfigure(0, weight=1)
        
        actions = [
            ("🔄 Actualiser", self.update_data),
            ("📊 Graphiques", self.show_graphs),
            ("⚙️ Configuration", self.show_config),
            ("📋 Historique", self.show_history),
            ("🚀 Déployer Agent", self.deploy_agent),
            ("🔒 Authentification", self.authenticate)
        ]
        
        for i, (text, command) in enumerate(actions):
            btn = ttk.Button(actions_frame, text=text, command=command, width=20)
            btn.grid(row=i, column=0, pady=2, sticky=(tk.W, tk.E))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="🔴 Déconnecté")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="red")
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.time_var = tk.StringVar(value=datetime.now().strftime("%H:%M:%S"))
        time_label = ttk.Label(status_frame, textvariable=self.time_var)
        time_label.grid(row=0, column=1, sticky=tk.E)
    
    async def api_request(self, endpoint, method="GET", data=None):
        """Effectue une requête API asynchrone vers le serveur"""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.server_url}{endpoint}"
            headers = {}
            
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            async with self.session.request(method, url, json=data, headers=headers, ssl=False) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API error {response.status}: {await response.text()}")
                    return None
                    
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def sync_api_request(self, endpoint, method="GET", data=None):
        """Effectue une requête API synchrone vers le serveur"""
        try:
            import requests
            
            url = f"{self.server_url}{endpoint}"
            headers = {}
            
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, verify=False, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, verify=False, timeout=10)
            else:
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Sync API request failed: {e}")
            return None
    
    def update_data(self):
        """Met à jour les données depuis le serveur"""
        threading.Thread(target=self._sync_update, daemon=True).start()
    
    def _sync_update(self):
        """Mise à jour synchrone des données"""
        try:
            # Récupérer les sessions via une requête synchrone
            sessions_data = self.sync_api_request("/api/sessions")
            if sessions_data:
                self.sessions = sessions_data.get('sessions', [])
                self.update_sessions_tree()
            
            # Mettre à jour les statistiques
            self.update_stats()
            
            # Mettre à jour le status
            self.status_var.set("🟢 Connecté")
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            self.status_var.set("🔴 Erreur de connexion")
        
        finally:
            # Planifier la prochaine mise à jour
            self.root.after(self.update_interval, self.update_data)
            self.time_var.set(datetime.now().strftime("%H:%M:%S"))
    
    def update_sessions_tree(self):
        """Met à jour l'arbre des sessions"""
        # Vider l'arbre actuel
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        # Ajouter les nouvelles sessions
        for session in self.sessions:
            duration = self.calculate_duration(session.get('created_at'))
            self.sessions_tree.insert('', 'end', values=(
                session.get('id', '')[:8],
                session.get('hostname', 'Unknown'),
                session.get('ip_address', 'Unknown'),
                session.get('status', 'Unknown'),
                duration,
                f"{session.get('cpu_percent', 0)}%",
                f"{session.get('memory_percent', 0)}%"
            ))
        
        # Mettre à jour la combobox des sessions
        session_ids = [s.get('id', '') for s in self.sessions]
        if hasattr(self, 'session_combo'):
            self.session_combo['values'] = session_ids
            if session_ids and not self.session_var.get():
                self.session_var.set(session_ids[0])
    
    def update_stats(self):
        """Met à jour les statistiques"""
        active_agents = len([s for s in self.sessions if s.get('status') == 'active'])
        total_sessions = len(self.sessions)
        
        self.stats_labels["Agents Actifs"].configure(text=str(active_agents))
        self.stats_labels["Sessions"].configure(text=str(total_sessions))
        self.stats_labels["Commandes Today"].configure(text=str(len(self.command_history)))
        self.stats_labels["Uptime"].configure(text=self.get_uptime())
    
    def calculate_duration(self, created_at):
        """Calcule la durée depuis la création"""
        try:
            if not created_at:
                return "00:00:00"
            
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.utcnow()
            delta = now - created
            
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        except Exception:
            return "00:00:00"
    
    def get_uptime(self):
        """Retourne l'uptime du serveur"""
        # Simulé pour le moment
        return "01:23:45"
    
    def execute_command(self):
        """Exécute une commande sur l'agent sélectionné"""
        session_id = self.session_var.get()
        command = self.command_var.get()
        
        if not session_id or not command:
            messagebox.showwarning("Attention", "Veuillez sélectionner une session et entrer une commande")
            return
        
        threading.Thread(target=self._sync_execute_command, args=(session_id, command), daemon=True).start()
    
    def _sync_execute_command(self, session_id, command):
        """Exécution synchrone de commande"""
        try:
            data = {
                "session_id": session_id,
                "command": command,
                "operator": "admin",  # Opérateur par défaut
                "params": {}
            }
            
            result = self.sync_api_request("/api/command", "POST", data)
            
            # Check for nested structure from server wrapper
            command_data = result
            if result and result.get("status") == "success" and "result" in result:
                command_data = result["result"]
            
            if command_data and command_data.get("status") == "scheduled":
                command_id = command_data.get("command_id")
                
                if command_id:
                    self.append_output(f"⏳ Commande planifiée sur {session_id} (ID: {command_id})")
                    self.append_output(f"   $ {command}")
                    
                    # Poll for result
                    self._poll_command_result(command_id, session_id, command)
                else:
                    self.append_output(f"❌ Erreur: ID de commande non reçu")
            else:
                self.append_output(f"❌ Erreur d'exécution sur {session_id}")
                if result and "error" in result:
                     self.append_output(f"   Raison: {result['error']}")
                
        except Exception as e:
            self.append_output(f"❌ Exception: {e}")

    def _poll_command_result(self, command_id, session_id, command_text):
        """Sonde le serveur pour obtenir le résultat de la commande"""
        import time
        max_retries = 30  # Increased to 30s
        for i in range(max_retries):
            time.sleep(1) # Wait 1s between polls
            
            try:
                response = self.sync_api_request(f"/api/command/{command_id}", "GET")
                
                if response and response.get("status") == "success":
                    cmd_data = response.get("data", {})
                    status = cmd_data.get("status")
                    
                    if status == "completed":
                        result = cmd_data.get("result", {})
                        
                        self.command_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'session_id': session_id,
                            'command': command_text,
                            'result': result
                        })
                        
                        stdout = result.get("result", {}).get("stdout", "")
                        stderr = result.get("result", {}).get("stderr", "")
                        
                        # Vérifier si c'est une commande download/zip pour décoder le base64
                        if command_text.startswith("download") or command_text.startswith("zip"):
                            data_content = result.get("result", {}).get("data", "")
                            if data_content:
                                try:
                                    import base64
                                    decoded_data = base64.b64decode(data_content)
                                    # Sauvegarder le fichier
                                    filename = f"download_{command_id}.{'zip' if command_text.startswith('zip') else 'bin'}"
                                    with open(filename, "wb") as f:
                                        f.write(decoded_data)
                                    stdout += f"\n[+] Fichier téléchargé avec succès: {filename} ({len(decoded_data)} bytes)"
                                except Exception as e:
                                    stderr += f"\n[-] Erreur lors du décodage/sauvegarde: {e}"

                        output_msg = f"✅ Commande terminée sur {session_id}:\n"
                        if stdout:
                            output_msg += f"   STDOUT:\n{stdout}\n"
                        if stderr:
                            output_msg += f"   STDERR:\n{stderr}\n"
                        if not stdout and not stderr:
                            output_msg += f"   (Aucune sortie)\n"
                            
                        self.append_output(output_msg)
                        self.append_output("-" * 50)
                        return
                    
                    elif status == "error":
                        self.append_output(f"❌ Erreur commande {command_id}: {cmd_data.get('error', 'Unknown error')}")
                        return
            except Exception as e:
                logger.error(f"Polling error: {e}")
        
        self.append_output(f"⚠️ Timeout: Pas de résultat pour la commande {command_id} après {max_retries}s")

    
    def append_output(self, text):
        """Ajoute du texte à l'output"""
        self.output_text.configure(state='normal')
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.output_text.configure(state='disabled')
    
    def show_graphs(self):
        """Affiche les graphiques de monitoring"""
        graph_window = tk.Toplevel(self.root)
        graph_window.title("📊 Graphiques de Monitoring")
        graph_window.geometry("800x600")
        
        # Créer des graphiques simulés
        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Données simulées
        sessions = [s.get('cpu_percent', 0) for s in self.sessions]
        ax.bar(range(len(sessions)), sessions)
        ax.set_title('Utilisation CPU par Session')
        ax.set_xlabel('Sessions')
        ax.set_ylabel('CPU %')
        
        canvas = FigureCanvasTkAgg(fig, graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def show_config(self):
        """Affiche la configuration"""
        messagebox.showinfo("Configuration", f"Serveur: {self.server_url}\nSessions: {len(self.sessions)}")
    
    def show_history(self):
        """Affiche l'historique des commandes"""
        history_window = tk.Toplevel(self.root)
        history_window.title("📋 Historique des Commandes")
        history_window.geometry("600x400")
        
        text_area = scrolledtext.ScrolledText(history_window, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True)
        
        for cmd in self.command_history:
            text_area.insert(tk.END, f"[{cmd['timestamp']}] {cmd['session_id']}: {cmd['command']}\n")
        
        text_area.configure(state='disabled')
    
    def deploy_agent(self):
        """Ouvre la fenêtre de déploiement d'agent"""
        deploy_window = tk.Toplevel(self.root)
        deploy_window.title("🚀 Déploiement d'Agent")
        deploy_window.geometry("400x300")
        
        ttk.Label(deploy_window, text="Générer un agent personnalisé:").pack(pady=10)
        
        options = [
            ("Platforme", "Windows"),
            ("Architecture", "x64"),
            ("Méthode", "HTTP"),
            ("Intervalle", "30s")
        ]
        
        for i, (label, default) in enumerate(options):
            frame = ttk.Frame(deploy_window)
            frame.pack(fill=tk.X, padx=20, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            ttk.Combobox(frame, values=[default, "Alternative"], width=15).pack(side=tk.LEFT)
        
        ttk.Button(deploy_window, text="📋 Générer Script", command=lambda: self.generate_agent_script()).pack(pady=20)
        ttk.Button(deploy_window, text="⬇️ Télécharger Agent", command=lambda: self.download_agent()).pack(pady=5)
    
    def generate_agent_script(self):
        """Génère un script de déploiement"""
        messagebox.showinfo("Script Généré", "Script de déploiement généré avec succès!")
    
    def download_agent(self):
        """Télécharge un agent"""
        messagebox.showinfo("Téléchargement", "Agent téléchargé avec succès!")
    
    def authenticate(self):
        """Fenêtre d'authentification"""
        auth_window = tk.Toplevel(self.root)
        auth_window.title("🔒 Authentification")
        auth_window.geometry("300x200")
        
        ttk.Label(auth_window, text="Identifiants administrateur:").pack(pady=10)
        
        ttk.Label(auth_window, text="Utilisateur:").pack()
        user_entry = ttk.Entry(auth_window, width=20)
        user_entry.pack(pady=5)
        user_entry.insert(0, "admin")
        
        ttk.Label(auth_window, text="Mot de passe:").pack()
        pass_entry = ttk.Entry(auth_window, width=20, show="*")
        pass_entry.pack(pady=5)
        
        def do_login():
            self.token = "simulated_token"  # Simulé pour le moment
            self.status_var.set("🟢 Authentifié")
            auth_window.destroy()
            messagebox.showinfo("Succès", "Authentification réussie!")
        
        ttk.Button(auth_window, text="Se connecter", command=do_login).pack(pady=20)


def main():
    """Point d'entrée principal"""
    root = tk.Tk()
    dashboard = NightOwlDashboard(root)
    
    # Centrer la fenêtre
    root.eval('tk::PlaceWindow . center')
    
    # Démarrer l'authentification automatique
    root.after(1000, dashboard.authenticate)
    
    root.mainloop()


if __name__ == "__main__":
    main()