#!/usr/bin/env python3

import socket
import time
import sys

def test_inventory_command():
    """Test inventory command by manually connecting to the TCP server"""
    
    print("Testing inventory command with manual TCP connection...")
    
    sock = None
    try:
        # Connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 2223))
        sock.settimeout(5.0)  # 5 second timeout
        
        print("Connected to server")
        
        # Read initial welcome message
        data = sock.recv(4096).decode('utf-8')
        print(f"Initial response: {repr(data[:100])}...")
        
        # Send username (admin)
        print("Sending username: admin")
        sock.send(b"admin\n")
        time.sleep(0.5)
        
        # Read password prompt
        data = sock.recv(4096).decode('utf-8')
        print(f"Password prompt: {repr(data[:50])}...")
        
        # Send password
        print("Sending password: admin123")
        sock.send(b"admin123\n")
        time.sleep(1.0)  # Give more time for login
        
        # Read game entry and initial prompt (should skip character creation)
        data = sock.recv(4096).decode('utf-8')
        print(f"Game entry: {repr(data[:100])}...")
        
        # Check if we successfully entered the game
        if "ENTERING THE WORLD" in data:
            print("✓ Successfully entered the game")
        else:
            print("✗ Failed to enter the game")
            return False
        
        # Now test inventory command
        print("\n=== Testing inventory command ===")
        
        # Send inventory command
        print("Sending 'inventory' command...")
        sock.send(b"inventory\n")
        time.sleep(1.0)
        
        # Read inventory response
        data = sock.recv(4096).decode('utf-8')
        print(f"Inventory response: {repr(data)}")
        
        # Check for error
        if "Error processing input" in data:
            print("✗ Inventory command failed with error")
            return False
        elif "invalid input for query argument" in data:
            print("✗ Inventory command failed with database error")
            return False
        elif "Your inventory is empty" in data or "Inventory:" in data:
            print("✓ Inventory command working correctly!")
            
            # Test the 'inv' alias too
            print("\nTesting 'inv' alias...")
            sock.send(b"inv\n")
            time.sleep(1.0)
            
            data = sock.recv(4096).decode('utf-8')
            print(f"Inv alias response: {repr(data)}")
            
            if "Error processing input" in data:
                print("✗ Inv alias failed with error")
                return False
            elif "Your inventory is empty" in data or "Inventory:" in data:
                print("✓ Inv alias also working correctly!")
                return True
            else:
                print("? Unexpected inv alias response")
                return False
        else:
            print(f"? Unexpected inventory response: {data}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        return False
    finally:
        try:
            if sock:
                sock.close()
        except:
            pass

if __name__ == "__main__":
    success = test_inventory_command()
    if success:
        print("\n🎉 Inventory command test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Inventory command test FAILED!")
        sys.exit(1)