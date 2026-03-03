import os
import sys
import logging
from server.builder import AgentBuilder

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def test_build():
    base_path = os.getcwd()
    builder = AgentBuilder(base_path)
    
    config = {
        'server_url': 'http://localhost:8443',
        'beacon_interval_min': 5,
        'beacon_interval_max': 10,
        'jitter': 0.3
    }
    
    print("[-] Testing EXE generation...")
    try:
        exe_bytes, filename = builder.generate_agent(config, 'exe', 'none')
        print(f"[+] EXE generated successfully: {len(exe_bytes)} bytes")
        with open('test_agent.exe', 'wb') as f:
            f.write(exe_bytes)
    except Exception as e:
        print(f"[!] EXE generation failed: {e}")

    print("\n[-] Testing PowerShell generation...")
    try:
        ps_bytes, filename = builder.generate_agent(config, 'powershell', 'none')
        print(f"[+] PS1 generated successfully: {len(ps_bytes)} bytes")
        with open('test_agent.ps1', 'wb') as f:
            f.write(ps_bytes)
    except Exception as e:
        print(f"[!] PS1 generation failed: {e}")

if __name__ == "__main__":
    test_build()
