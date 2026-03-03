# NightOwl Red Team Framework

## 🦉 Overview

**NightOwl** is a modern and modular Command & Control (C2) framework, designed for **Red Teaming** operations and authorized adversary simulations. It allows operators to remotely manage deployed agents, execute commands, transfer files, and monitor targets via an intuitive and secure web interface.

This project aims to provide an educational and professional tool for testing infrastructure resilience and training defense teams (Blue Teams).

### ✨ Key Features

*   **Robust C2 Server**: High-performance asynchronous architecture based on Python (aiohttp).
*   **Modern Web Interface**: Reactive Vue.js dashboard for real-time agent monitoring (status, logs, alerts).
*   **Stealth Agent**:
    *   Shell command execution.
    *   Bidirectional file transfer.
    *   Surveillance modules (Screenshot, Webcam, Microphone).
    *   Persistence and evasion (configurable).
*   **Secure Communication**: End-to-end encryption (TLS + Application Layer Encryption).
*   **Integrated Builder**: Automatic generation of executable agents (.exe) or source scripts.
*   **Multi-Operator Management**: JWT authentication and roles (Admin/Operator).

---

## ⚠️ Legal Disclaimer

**THE USE OF THIS SOFTWARE IS STRICTLY RESERVED FOR LEGAL AND ETHICAL PURPOSES.**

NightOwl is an offensive security tool. It must only be used on systems for which you have **explicit written authorization** (mandate).

*   Any illegal use (unauthorized access, data exfiltration without consent, spying) is strictly prohibited.
*   The authors decline all responsibility for damages caused by misuse of this tool.
*   By using this software, you agree to assume full responsibility for your actions.

---

## 🛠️ Prerequisites and Installation

### Technical Prerequisites
*   **Operating System**: Windows, Linux, or macOS.
*   **Language**: Python 3.8 or higher.
*   **Browser**: Modern browser (Chrome, Firefox, Edge) for the dashboard.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/nightowl.git
    cd nightowl
    ```

2.  **Create a virtual environment (recommended)**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Generate SSL certificates** (for HTTPS):
    ```bash
    python generate_certs.py
    ```
    *This will create `server.crt` and `server.key` in the `certs/` folder.*

---

## 🚀 Usage

### 1. Start the C2 Server
Launch the main server that will host the API and web interface:

```bash
python run_server.py
```
The server will start by default on `https://0.0.0.0:8443`.

### 2. Access the Dashboard
Open your browser and navigate to:
**`https://localhost:8443`**

*(Note: Accept the security warning if you are using a self-signed certificate).*

**Default Credentials:**
*   **User**: `admin`
*   **Password**: `password123`
*   *(Please change these credentials in `config.yaml` for any real use)*

### 3. Deploy an Agent
From the dashboard, go to the **Builder** tab:
1.  Configure your server's IP address (e.g., your attacking machine's IP).
2.  Choose the format (Python Source or Windows Executable).
3.  Click on **Generate**.
4.  Transfer and execute the agent on the target machine (authorized).

Alternatively, to test locally:
```bash
python run_agent.py
```

---

## ⚙️ Configuration

The `config.yaml` file at the root allows customizing the framework's behavior.

### Important Settings

```yaml
server:
  port: 8443             # Server listening port
  ssl_enabled: true      # Enable HTTPS (recommended)

security:
  encryption_key: "..."  # Encryption key (must be changed)
  operators:             # User account management
    - username: "admin"
      password_hash: "..." # bcrypt password hash

client:                  # Default agent configuration
  beacon_interval_min: 5 # Minimum communication interval (seconds)
  beacon_interval_max: 10
```

---

## 🛡️ Security and Best Practices

To ensure responsible and secure usage:

1.  **Key Rotation**: Immediately modify `encryption_key` and `jwt_secret` in `config.yaml`.
2.  **Passwords**: Change default passwords. Use a utility to generate new bcrypt hashes.
3.  **Certificates**: For production use, use certificates signed by a valid Certificate Authority (CA) instead of self-signed ones.
4.  **Isolation**: Run the C2 server in an isolated environment (VM, dedicated VPS) to avoid exposing your personal machine.
5.  **Logs**: Regularly monitor log files (`logs/`) to detect any anomalies.

---

## 📂 Project Structure

*   `server/`: Server source code (API, Database, Session Management).
*   `agent/`: Agent source code (Command Execution, Surveillance).
*   `web/`: User Interface (HTML, CSS, Vue.js).
*   `certs/`: SSL certificate storage.
*   `uploads/`: Directory for received exfiltrated files.
*   `run_server.py`: Server launch script.
*   `run_agent.py`: Agent launch script (test).

---

*NightOwl Red Team Framework - Developed for cybersecurity research and education.*
