#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
import agent.main
import agent.command_executor

print(f"DEBUG: agent.main file: {agent.main.__file__}")
print(f"DEBUG: agent.command_executor file: {agent.command_executor.__file__}")

from agent.main import NightOwlAgent

# Default configuration
DEFAULT_CONFIG = {
    'server_url': 'https://127.0.0.1:8443',
    'client': {
        'beacon_interval_min': 5,
        'beacon_interval_max': 10,
        'jitter': 0.2
    },
    'security': {
        'encryption_key': "change_this_to_secure_random_key"
    }
}

async def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('agent.log'),
            logging.StreamHandler()
        ]
    )
    
    # Load config (could be expanded to load from file)
    config = DEFAULT_CONFIG.copy()
    
    # Ensure server_url is accessible at root level (as expected by Agent)
    if 'server_url' not in config:
        if 'client' in config and 'server_url' in config['client']:
            config['server_url'] = config['client']['server_url']
        else:
            # Fallback default
            config['server_url'] = 'https://127.0.0.1:8443'
            logging.warning(f"Server URL not found in config, using default: {config['server_url']}")

    
    print(f"[*] Starting NightOwl Agent...")
    print(f"[*] Server URL: {config['server_url']}")
    
    agent = NightOwlAgent(config)
    await agent.run()

if __name__ == '__main__':
    try:
        # On Windows, ProactorEventLoop is required for async subprocesses
        # It's the default since Python 3.8, so let asyncio handle it
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
