#!/usr/bin/env python3

import socket
import time
import sys

def test_prompt_placement():
    """Test prompt placement by manually connecting to the TCP server"""
    
    print("Testing prompt placement with manual TCP connection...")
    
    try:
        # Connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 2223))
        sock.settimeout(5.0)  # 5 second timeout
        
        print("Connected to server")
        
        # Read initial welcome message
        data = sock.recv(4096).decode('utf-8')
        print(f"Initial response: {repr(data)}")
        
        # Send username (admin)
        print("Sending username: admin")
        sock.send(b"admin\n")
        time.sleep(0.5)
        
        # Read password prompt
        data = sock.recv(4096).decode('utf-8')
        print(f"Password prompt: {repr(data)}")
        
        # Send password
        print("Sending password: admin123")
        sock.send(b"admin123\n")
        time.sleep(1.0)  # Give more time for login
        
        # Read game entry and initial prompt (should skip character creation)
        data = sock.recv(4096).decode('utf-8')
        print(f"Game entry and initial prompt: {repr(data)}")
        
        # Check if we see a prompt (HP: indicator)
        if "HP:" in data:
            print("✓ Initial prompt detected after game entry")
        else:
            print("✗ No initial prompt detected")
        
        # Now test command flow
        print("\n=== Testing command flow ===")
        
        # Send first command
        print("Sending command: east")
        sock.send(b"east\n")
        time.sleep(0.5)
        
        # Read response
        data = sock.recv(4096).decode('utf-8')
        print(f"Response to 'east': {repr(data)}")
        
        # Check for prompt after command
        if "HP:" in data:
            print("✓ Prompt detected after 'east' command")
        else:
            print("✗ No prompt after 'east' command")
        
        # Send second command
        print("Sending command: west")
        sock.send(b"west\n")
        time.sleep(0.5)
        
        # Read response
        data = sock.recv(4096).decode('utf-8')
        print(f"Response to 'west': {repr(data)}")
        
        # Check for prompt after command
        if "HP:" in data:
            print("✓ Prompt detected after 'west' command")
        else:
            print("✗ No prompt after 'west' command")
        
        # Exit gracefully
        print("Sending quit command")
        sock.send(b"quit\n")
        time.sleep(0.5)
        
        # Read final response
        try:
            data = sock.recv(4096).decode('utf-8')
            print(f"Final response: {repr(data)}")
        except:
            print("Connection closed after quit")
        
        sock.close()
        print("\nTest completed successfully")
        
    except Exception as e:
        print(f"Error during test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_prompt_placement()