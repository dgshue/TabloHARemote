"""Test script for Tablo authentication and device discovery."""
import asyncio
import json
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from tablo_remote.tablo_client import TabloClient
from tablo_remote.logger import get_logger, set_debug

_LOGGER = get_logger("test_auth")

async def test_auth():
    """Test authentication flow."""
    # Enable debug logging
    set_debug(True)
    
    if len(sys.argv) < 3:
        print("Usage: python test_auth.py <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    try:
        print(f"\n{'='*60}")
        print("Testing Tablo Authentication Flow")
        print(f"{'='*60}\n")
        
        print(f"Step 1: Authenticating with email: {username}")
        credentials = await TabloClient.authenticate(username, password)
        
        print(f"\n{'='*60}")
        print("Authentication Successful!")
        print(f"{'='*60}\n")
        
        print("Credentials structure:")
        print(f"  - Lighthouse: {credentials.get('lighthouse', 'N/A')[:20]}...")
        print(f"  - Device URL: {credentials.get('device', {}).get('url', 'N/A')}")
        print(f"  - Device Name: {credentials.get('device', {}).get('name', 'N/A')}")
        print(f"  - Device Server ID: {credentials.get('device', {}).get('serverId', 'N/A')}")
        print(f"  - UUID: {credentials.get('uuid', 'N/A')}")
        print(f"  - Tuners: {credentials.get('tuners', 'N/A')}")
        
        print(f"\n{'='*60}")
        print("Full device object:")
        print(f"{'='*60}")
        device = credentials.get('device', {})
        print(json.dumps(device, indent=2))
        
        print(f"\n{'='*60}")
        print("Testing device connection...")
        print(f"{'='*60}\n")
        
        client = TabloClient(credentials)
        server_info = await client.get_server_info()
        
        print("Server info retrieved successfully:")
        print(json.dumps(server_info, indent=2))
        
    except Exception as e:
        print(f"\n{'='*60}")
        print("ERROR during authentication/connection:")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_auth())

