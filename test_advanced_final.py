
import requests
import json
import time
import urllib3
import base64
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVER_URL = "https://127.0.0.1:8443"
USERNAME = "admin"
PASSWORD = "password123"

def login():
    try:
        resp = requests.post(f"{SERVER_URL}/api/auth/login", json={"username": USERNAME, "password": PASSWORD}, verify=False)
        if resp.status_code == 200:
            return resp.json().get("token")
        print(f"Login failed: {resp.text}")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def get_active_session(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{SERVER_URL}/api/sessions", headers=headers, verify=False)
    if resp.status_code == 200:
        sessions = resp.json().get("sessions", [])
        if sessions:
            return sessions[0]["id"]
    return None

def send_command(token, session_id, command, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "session_id": session_id,
        "command": command,
        "params": params or {},
        "operator": "test_script"
    }
    resp = requests.post(f"{SERVER_URL}/api/command", json=payload, headers=headers, verify=False)
    if resp.status_code == 200:
        return resp.json()
    print(f"Command send failed: {resp.text}")
    return None

def get_command_result(token, command_id):
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(20):
        resp = requests.get(f"{SERVER_URL}/api/command/{command_id}", headers=headers, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] == "completed":
                return data["result"]
        time.sleep(1)
    return None

def main():
    print("[-] Logging in...")
    token = login()
    if not token:
        return

    print("[-] Waiting for agent...")
    session_id = None
    for _ in range(10):
        session_id = get_active_session(token)
        if session_id:
            break
        time.sleep(2)
    
    if not session_id:
        print("[!] No active session found.")
        return

    print(f"[+] Found session: {session_id}")

    # Test Screenshot
    print("[-] Sending 'screenshot' command...")
    cmd_resp = send_command(token, session_id, "screenshot")
    if cmd_resp and (cmd_id := cmd_resp.get("command_id")):
        print(f"[-] Waiting for result (ID: {cmd_id})...")
        result = get_command_result(token, cmd_id)
        if result:
            print("[+] Result received!")
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass
            
            if isinstance(result, dict) and result.get("status") == "success":
                print("[+] Screenshot success!")
                if "b64" in result:
                    print(f"[+] Base64 length: {len(result['b64'])}")
                    # Save for verification
                    try:
                        with open("test_screenshot.png", "wb") as f:
                            f.write(base64.b64decode(result['b64']))
                        print("[+] Saved to test_screenshot.png")
                    except Exception as e:
                        print(f"[!] Failed to save image: {e}")
            else:
                print(f"[!] Screenshot failed or unexpected result: {result}")
        else:
            print("[!] Timeout waiting for result")
    else:
        print("[!] Failed to send command")

if __name__ == "__main__":
    main()
