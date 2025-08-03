#!/usr/bin/env python3
"""
Test script to verify monster system is working
"""

import socket
import time
import sys

def test_monster_system():
    """Test the monster system by connecting and exploring"""
    print("=== Testing Monster System ===")
    
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 2222))
        
        def send_command(cmd):
            sock.send((cmd + '\n').encode())
            time.sleep(0.5)
            
        def receive_data():
            try:
                data = sock.recv(4096).decode()
                return data
            except:
                return ""
        
        # Initial connection
        print("Connected to server")
        initial_data = receive_data()
        print("Server response:", initial_data[:200] + "..." if len(initial_data) > 200 else initial_data)
        
        # Login as admin
        print("\n--- Logging in as admin ---")
        send_command("admin")
        time.sleep(0.5)
        send_command("admin123")
        
        login_response = receive_data()
        print("Login response:", login_response[:300] + "..." if len(login_response) > 300 else login_response)
        
        # Look around starting area
        print("\n--- Looking around starting area ---")
        send_command("look")
        look_response = receive_data()
        print("Look response:", look_response)
        
        # Navigate to forest (north, then east twice)
        print("\n--- Moving to forest ---")
        send_command("north")
        time.sleep(0.5)
        north_response = receive_data()
        print("North response:", north_response)
        
        send_command("east")
        time.sleep(0.5)
        east1_response = receive_data()
        print("East 1 response:", east1_response)
        
        send_command("east")
        time.sleep(0.5)
        east2_response = receive_data()
        print("East 2 response:", east2_response)
        
        # Look for monsters
        print("\n--- Looking for monsters in forest ---")
        send_command("look")
        forest_look = receive_data()
        print("Forest look response:", forest_look)
        
        # Try to attack a monster if present
        if "Forest Wolf" in forest_look:
            print("\n--- Attacking Forest Wolf ---")
            send_command("attack wolf")
            attack_response = receive_data()
            print("Attack response:", attack_response)
        elif "Giant Spider" in forest_look:
            print("\n--- Attacking Giant Spider ---")
            send_command("attack spider")
            attack_response = receive_data()
            print("Attack response:", attack_response)
        else:
            print("No monsters found in this forest room, trying another room...")
            send_command("north")
            time.sleep(0.5)
            receive_data()
            send_command("look")
            another_look = receive_data()
            print("Another room look:", another_look)
        
        # Quit
        print("\n--- Quitting ---")
        send_command("quit")
        quit_response = receive_data()
        print("Quit response:", quit_response)
        
        sock.close()
        print("\n=== Monster System Test Complete ===")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_monster_system()