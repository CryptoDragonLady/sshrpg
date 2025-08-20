#!/usr/bin/env python3
"""
Test script for room items and search functionality
"""

import socket
import time
import json

def test_room_items():
    """Test room items display and search functionality"""
    sock = None
    try:
        # Connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 2223))
        
        # Read welcome message
        welcome = sock.recv(1024).decode('utf-8')
        print(f"Welcome: {welcome}")
        
        # Login as admin
        sock.send(b"admin\n")
        time.sleep(0.5)
        sock.send(b"admin123\n")
        time.sleep(1)
        
        # Read login response
        response = sock.recv(4096).decode('utf-8')
        print(f"Login response: {response}")
        
        # Create a test item first
        print("\n=== Creating test item ===")
        sock.send(b"/create_item \"test sword\" weapon '{\"damage\": 10}'\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Create item response: {response}")
        
        # Spawn visible item in current room
        print("\n=== Spawning visible item ===")
        sock.send(b"/spawn_item 1\n")  # item_id=1
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Spawn visible item response: {response}")
        
        # Look at room to see visible item
        print("\n=== Looking at room (should show visible item) ===")
        sock.send(b"look\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Look response: {response}")
        
        # Create another test item
        print("\n=== Creating hidden test item ===")
        sock.send(b"/create_item \"hidden gem\" treasure '{\"value\": 100}'\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Create hidden item response: {response}")
        
        # Spawn hidden item in current room
        print("\n=== Spawning hidden item ===")
        sock.send(b"/spawn_item 27 hidden\n")  # item_id=27, hidden=true
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Spawn hidden item response: {response}")
        
        # Look at room again (should not show hidden item)
        print("\n=== Looking at room (should not show hidden item) ===")
        sock.send(b"look\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Look response: {response}")
        
        # Try searching for hidden items
        print("\n=== Searching for hidden items ===")
        sock.send(b"search\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Search response: {response}")
        
        # Look at room again (might show found item)
        print("\n=== Looking at room after search ===")
        sock.send(b"look\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Look response after search: {response}")
        
        # Try searching again
        print("\n=== Searching again ===")
        sock.send(b"search\n")
        time.sleep(0.5)
        response = sock.recv(4096).decode('utf-8')
        print(f"Second search response: {response}")
        
        print("\n=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        if sock:
            sock.close()

if __name__ == "__main__":
    test_room_items()