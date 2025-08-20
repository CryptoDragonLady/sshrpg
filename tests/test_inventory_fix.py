#!/usr/bin/env python3
import asyncio
import sys

async def test_inventory():
    """Test the inventory command fix"""
    writer = None
    try:
        # Connect to game server
        reader, writer = await asyncio.open_connection('localhost', 2223)
        
        # Helper function to read response with timeout
        async def read_response(timeout=2.0):
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
                return data.decode('utf-8')
            except asyncio.TimeoutError:
                return ""
        
        # Helper function to send command
        async def send_command(cmd, wait_time=1.0):
            writer.write((cmd + '\n').encode('utf-8'))
            await writer.drain()
            await asyncio.sleep(wait_time)
            return await read_response()
        
        print("Testing inventory command fix...")
        
        # Read initial welcome
        welcome = await read_response()
        print(f"Connected to server")
        
        # Send login command
        print("Logging in...")
        await send_command('login')
        
        # Send username
        await send_command('admin')
        
        # Send password
        login_result = await send_command('admin123', 2.0)
        
        if "ENTERING THE WORLD" in login_result:
            print("✓ Login successful")
            
            # Test inventory command
            print("Testing inventory command...")
            inv_response = await send_command('inventory', 1.5)
            print(f"Inventory response: {repr(inv_response)}")
            
            if "Error processing input" in inv_response:
                print("✗ Inventory command still broken")
                return False
            elif "Your inventory is empty" in inv_response or "Inventory:" in inv_response:
                print("✓ Inventory command working!")
                return True
            else:
                print(f"? Unexpected inventory response: {inv_response}")
                return False
        else:
            print(f"✗ Login failed: {login_result}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
    finally:
        try:
            if writer:
                writer.close()
                await writer.wait_closed()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_inventory())
    sys.exit(0 if success else 1)