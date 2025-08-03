#!/usr/bin/env python3
"""
Simple client for testing the SSH RPG server
Can connect via SSH or direct TCP connection
"""

import asyncio
import sys
import socket
import subprocess
import os
from typing import Optional

class RPGClient:
    """Simple client for connecting to the SSH RPG server"""
    
    def __init__(self):
        self.reader = None
        self.writer = None
        self.connected = False
        
    async def connect_tcp(self, host: str = "localhost", port: int = 2223):
        """Connect to server via TCP"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True
            print(f"Connected to {host}:{port} via TCP")
            return True
        except Exception as e:
            print(f"Failed to connect via TCP: {e}")
            return False
    
    def connect_ssh(self, host: str = "localhost", port: int = 2222, username: str = "player"):
        """Connect to server via SSH (using system ssh command)"""
        try:
            cmd = f"ssh -p {port} {username}@{host}"
            print(f"Connecting via SSH: {cmd}")
            print("Note: This will open SSH in a new terminal session")
            
            # Try to open SSH in a new terminal window
            if sys.platform == "darwin":  # macOS
                os.system(f"osascript -e 'tell app \"Terminal\" to do script \"{cmd}\"'")
            elif sys.platform.startswith("linux"):
                os.system(f"gnome-terminal -- {cmd} || xterm -e {cmd} || {cmd}")
            else:  # Windows or fallback
                os.system(cmd)
            
            return True
        except Exception as e:
            print(f"Failed to connect via SSH: {e}")
            return False
    
    async def send_message(self, message: str):
        """Send a message to the server"""
        if not self.connected or not self.writer:
            return False
        
        try:
            self.writer.write(f"{message}\n".encode())
            await self.writer.drain()
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    async def receive_messages(self):
        """Receive messages from the server"""
        if not self.connected or not self.reader:
            return
        
        try:
            while self.connected:
                data = await self.reader.readline()
                if not data:
                    break
                
                message = data.decode().strip()
                if message:
                    print(message)
        except Exception as e:
            print(f"Error receiving messages: {e}")
        finally:
            self.connected = False
    
    async def handle_user_input(self):
        """Handle user input and send to server"""
        try:
            while self.connected:
                try:
                    # Use asyncio to read from stdin
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, ""
                    )
                    
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    
                    await self.send_message(user_input)
                    
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
        except Exception as e:
            print(f"Error handling user input: {e}")
    
    async def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
    
    async def run_tcp_session(self, host: str = "localhost", port: int = 2223):
        """Run a TCP client session"""
        if not await self.connect_tcp(host, port):
            return
        
        print("\n" + "=" * 50)
        print("    SSH RPG - TCP Client")
        print("=" * 50)
        print("Connected! You can now interact with the game.")
        print("Type 'quit' or 'exit' to disconnect.")
        print("For new users: register <username> <password>")
        print("For existing users: login <username> <password>")
        print("=" * 50)
        print()
        
        try:
            # Start receiving messages and handling input concurrently
            await asyncio.gather(
                self.receive_messages(),
                self.handle_user_input()
            )
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            await self.disconnect()
            print("Disconnected from server.")

def print_usage():
    """Print usage information"""
    print("SSH RPG Client")
    print("=" * 30)
    print("Usage:")
    print("  python client.py tcp [host] [port]    - Connect via TCP")
    print("  python client.py ssh [host] [port]    - Connect via SSH")
    print("  python client.py                      - Connect via TCP to localhost:2223")
    print()
    print("Examples:")
    print("  python client.py                      # TCP to localhost:2223")
    print("  python client.py tcp localhost 2223   # TCP to localhost:2223")
    print("  python client.py ssh localhost 2222   # SSH to localhost:2222")
    print()
    print("Default admin account:")
    print("  Username: admin")
    print("  Password: admin123")

async def main():
    """Main client entry point"""
    args = sys.argv[1:]
    
    if not args or args[0] in ['-h', '--help', 'help']:
        print_usage()
        return
    
    client = RPGClient()
    
    connection_type = args[0].lower()
    host = args[1] if len(args) > 1 else "localhost"
    
    if connection_type == "tcp":
        port = int(args[2]) if len(args) > 2 else 2223
        await client.run_tcp_session(host, port)
    
    elif connection_type == "ssh":
        port = int(args[2]) if len(args) > 2 else 2222
        username = args[3] if len(args) > 3 else "player"
        client.connect_ssh(host, port, username)
    
    else:
        # Default to TCP
        port = 2223
        await client.run_tcp_session(host, port)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
    except Exception as e:
        print(f"Client error: {e}")