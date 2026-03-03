# Available NightOwl Commands

Here is the list of commands you can execute on remote agents via the NightOwl dashboard.

## Specific Commands

These commands are natively integrated into the agent to facilitate common operations.

### `whoami`
- **Description**: Displays the name of the current user running the agent.
- **Usage**: `whoami`
- **Arguments**: None.
- **Result**: Returns `domain\user` or `user`.

### `pwd`
- **Description**: Displays the current working directory (Print Working Directory).
- **Usage**: `pwd`
- **Arguments**: None.
- **Result**: Absolute path of the folder where the agent is located.

### `ls`
- **Description**: Lists files and folders.
- **Usage**: `ls` or `ls {"directory": "C:\\Windows"}`
- **Arguments**:
  - `directory` (optional): The path of the folder to list. Defaults to the current folder.
- **Result**: Detailed list of files (equivalent to `dir` on Windows or `ls -la` on Linux).

### `ps`
- **Description**: Lists running processes.
- **Usage**: `ps`
- **Arguments**: None.
- **Result**: Table of processes (equivalent to `tasklist` on Windows or `ps aux` on Linux).

### `ifconfig`
- **Description**: Displays the machine's network configuration.
- **Usage**: `ifconfig`
- **Arguments**: None.
- **Result**: Details of network interfaces, IP addresses, masks, etc. (equivalent to `ipconfig` on Windows).

---

## Data Exfiltration Commands

These commands allow retrieving files from the agent. Data is Base64 encoded for transit.

### `download`
- **Description**: Downloads a specific file from the target machine.
- **Usage**: `download {"path": "C:\\Users\\Admin\\secret.docx"}`
- **Arguments**:
  - `path` (required): The absolute or relative path of the file to download.
- **Result**: File content encoded in Base64.

### `zip`
- **Description**: Compresses a folder or file in memory and downloads it. Useful for exfiltrating multiple files at once.
- **Usage**: `zip {"path": "C:\\Users\\Admin\\Documents"}`
- **Arguments**:
  - `path` (required): The path of the folder or file to compress.
- **Result**: ZIP archive encoded in Base64.

---

## Generic Commands

These commands allow executing any system instruction.

### `shell`
- **Description**: Executes a command in the default system shell interpreter (`cmd.exe` on Windows, `/bin/sh` on Linux).
- **Usage**: `shell {"command": "echo Hello"}`
- **Arguments**:
  - `command` (required): The command line to execute.
- **Examples**:
  - `shell {"command": "mkdir test_folder"}`
  - `shell {"command": "type file.txt"}`

### `powershell`
- **Description**: Executes a PowerShell command or script.
- **Usage**: `powershell {"command": "Get-Process"}`
- **Arguments**:
  - `command` (required): The PowerShell command to execute.
- **Examples**:
  - `powershell {"command": "Get-Service | Where-Object {$_.Status -eq 'Running'}"}`
  - `powershell {"command": "Test-NetConnection 8.8.8.8"}`

---

## "Fallback" Mode (Direct Command)

If you enter a command that does not match any of the keywords above (e.g., `ping 8.8.8.8`), the agent will attempt to execute it directly as a `shell` command.

- **Example**: Simply sending `netstat -an` will execute the corresponding system command.
