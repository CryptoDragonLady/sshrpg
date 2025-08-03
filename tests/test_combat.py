#!/usr/bin/env python3
"""
Test script to verify combat system by connecting to the server
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ssh_server import SimpleSSHServer

async def test_combat_system():
    """Test the combat system by simulating player actions"""
    print("Testing Combat System")
    print("=" * 50)
    
    writer = None
    try:
        # Connect to the server
        reader, writer = await asyncio.open_connection('localhost', 2222)
        print("Connected to SSH server on localhost:2222")
        
        async def send_command(cmd):
            """Send a command to the server"""
            writer.write(f"{cmd}\n".encode())
            await writer.drain()
            await asyncio.sleep(0.5)  # Give server time to process
        
        async def read_response():
            """Read response from server"""
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                return data.decode().strip()
            except asyncio.TimeoutError:
                return ""
        
        # Login as admin
        print("\n1. Logging in as admin...")
        await send_command("login admin admin123")
        response = await read_response()
        print(f"Login response: {response}")
        
        # Look around
        print("\n2. Looking around...")
        await send_command("look")
        response = await read_response()
        print(f"Look response: {response}")
        
        # Go to a forest area with monsters
        print("\n3. Moving to forest area...")
        await send_command("north")
        await send_command("look")
        response = await read_response()
        print(f"Forest area: {response}")
        
        # Try to attack a monster
        print("\n4. Attempting to attack a monster...")
        await send_command("attack wolf")
        response = await read_response()
        print(f"Attack response: {response}")
        
        # Check health
        await send_command("stats")
        response = await read_response()
        print(f"Stats: {response}")
        
        print("\n" + "=" * 50)
        print("Combat test completed!")
        
    except Exception as e:
        print(f"Error during combat test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(test_combat_system())