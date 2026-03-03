import PyInstaller.__main__
import os
import shutil

if __name__ == '__main__':
    print("Building NightOwl Agent...")
    
    # Nettoyage précédent
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
        
    PyInstaller.__main__.run([
        'run_agent.py',
        '--name=nightowl_agent',
        '--onefile',
        '--clean',
        '--log-level=INFO',
        '--hidden-import=aiohttp',
        '--hidden-import=cryptography',
        '--hidden-import=psutil',
        '--hidden-import=yaml',
        '--paths=.',  # Ajoute le répertoire courant au path pour trouver 'agent'
        # '--noconsole', # Garder la console pour le debug initial
    ])
    
    print("\nBuild complete. Executable is in dist/nightowl_agent.exe")
