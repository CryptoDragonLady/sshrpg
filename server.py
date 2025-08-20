#!/usr/bin/env python3
"""
SSH RPG - Text-Based MMORPG Server
Copyright (c) 2024

This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 
International License. To view a copy of this license, visit:
http://creativecommons.org/licenses/by-nc-sa/4.0/

For commercial licensing, please contact the project maintainer.
"""

import asyncio
import sys
import traceback
from typing import Dict, Optional, Any
import signal

from database import db
from game_engine import GameEngine, game_engine
from character_creation import CharacterCreation, CharacterCreationSession
from admin_system import AdminSystem
from ssh_server import start_ssh_server, SimpleSSHServer, DirectConnection
from input_sanitizer import InputSanitizer

class GameServer:
    """Main game server that coordinates all components"""
    
    def __init__(self):
        self.db = db
        self.game_engine: Optional[GameEngine] = None
        self.admin_system: Optional[AdminSystem] = None
        self.ssh_server = None
        self.tcp_server = None
        self.running = False
        
        # Connection management
        self.connections = {}  # connection_id -> connection object
        self.user_sessions = {}  # user_id -> connection_id
        self.character_creation_sessions = {}  # connection_id -> CharacterCreationSession
        
        # Server configuration
        self.max_players = 24
        self.ssh_port = 2222
        self.tcp_port = 2223
        
    async def start(self, enable_ssh=True):
        """Start the game server"""
        try:
            print("Starting SSH RPG Server...")
            
            # Initialize database
            await self.db.connect()
            await self.db.create_tables()
            
            # Create default admin user if it doesn't exist
            await self._create_default_admin()
            
            # Initialize game engine
            self.game_engine = GameEngine(self.db)
            await self.game_engine.start()
            
            # Initialize admin system
            self.admin_system = AdminSystem(self.game_engine)
            
            # Start servers based on configuration
            if enable_ssh:
                # Start SSH server
                try:
                    await start_ssh_server(self, port=self.ssh_port)
                except Exception as e:
                    print(f"SSH server failed to start: {e}")
            
            # Always start TCP server for testing and fallback
            print("Starting TCP server...")
            self.tcp_server = SimpleSSHServer(self)
            await self.tcp_server.start(port=self.tcp_port)
            
            self.running = True
            print(f"Game server started successfully!")
            print(f"Maximum players: {self.max_players}")
            print(f"SSH Port: {self.ssh_port}")
            print(f"TCP Port: {self.tcp_port}")
            print("Server is ready for connections.")
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            traceback.print_exc()
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the game server"""
        print("Stopping game server...")
        self.running = False
        
        # Disconnect all players
        for connection in list(self.connections.values()):
            try:
                await connection.send_message("Server is shutting down. Goodbye!", "red")
            except:
                pass
        
        # Stop game engine
        if self.game_engine:
            await self.game_engine.stop()
        
        # Stop servers
        if self.tcp_server:
            await self.tcp_server.stop()
        
        print("Game server stopped.")
    
    async def _create_default_admin(self):
        """Create default admin account if it doesn't exist"""
        try:
            # Try to create default admin account
            success = await self.db.create_user("admin", "admin123", access_level=3)
            if success:
                print("Created default admin account (username: admin, password: admin123)")
            else:
                print("Admin account already exists")
        except Exception as e:
            print(f"Error creating admin account: {e}")
    
    async def handle_client_input(self, connection, input_text: str):
        """Handle input from a client connection"""
        try:
            input_text = input_text.strip()
            if not input_text:
                return
            
            connection_id = id(connection)
            
            # Store connection if new
            if connection_id not in self.connections:
                self.connections[connection_id] = connection
            
            # Handle different states
            if not connection.is_authenticated:
                await self._handle_authentication(connection, input_text)
            elif connection.is_in_character_creation:
                await self._handle_character_creation(connection, input_text)
            else:
                await self._handle_game_command(connection, input_text)
                
        except Exception as e:
            await connection.send_message(f"Error processing input: {e}", "red")
            print(f"Error handling client input: {e}")
            traceback.print_exc()
    
    async def _handle_authentication(self, connection, input_text: str):
        """Handle user authentication with multi-step process"""
        input_text = input_text.strip()
        
        # Handle different authentication states
        if connection.auth_state == "waiting_for_command":
            # Check if user typed 'register' command
            if input_text.lower() == "register":
                connection.auth_state = "waiting_for_username"
                connection.auth_command = "register"
                await connection.send_message("Username: ", "white")
                return
            # Otherwise treat input as username for login
            else:
                try:
                    connection.username_buffer = InputSanitizer.sanitize_username(input_text)
                    connection.auth_state = "waiting_for_password"
                    connection.auth_command = "login"
                    connection.password_masking = True
                    await connection.send_message("Password: ", "white")
                    return
                except ValueError as e:
                    await connection.send_message(f"Invalid username: {e}", "red")
                    await connection.send_message("Please enter username to login, otherwise type 'register' to create a new character", "yellow")
                    return
        
        elif connection.auth_state == "waiting_for_username":
            # Store username and ask for password
            try:
                connection.username_buffer = InputSanitizer.sanitize_username(input_text)
                connection.auth_state = "waiting_for_password"
                connection.password_masking = True
                await connection.send_message("Password: ", "white")
                return
            except ValueError as e:
                await connection.send_message(f"Invalid username: {e}", "red")
                connection.auth_state = "waiting_for_command"
                await connection.send_message("Please enter username to login, otherwise type 'register' to create a new character", "yellow")
                return
        
        elif connection.auth_state == "waiting_for_password":
            # Process authentication with stored username and entered password
            try:
                username = connection.username_buffer
                password = InputSanitizer.sanitize_string(input_text, max_length=100)
                command = connection.auth_command
                
                # Reset authentication state
                connection.auth_state = "waiting_for_command"
                connection.username_buffer = None
                connection.auth_command = None
                connection.password_masking = False
            except ValueError as e:
                await connection.send_message(f"Invalid password: {e}", "red")
                connection.auth_state = "waiting_for_command"
                await connection.send_message("Please type 'login' or 'register'", "yellow")
                return
        
        else:
            # Fallback to command state
            connection.auth_state = "waiting_for_command"
            await connection.send_message("Please type 'login' or 'register'", "yellow")
            return
        
        # Process the authentication command
        if command == "login":
            try:
                user = await self.db.authenticate_user(username, password)
                if user:
                    connection.user_id = user['id']
                    connection.is_authenticated = True
                    
                    # Check if user has a character
                    character = await self.db.get_character(user['id'])
                    if character:
                        # User has a character, enter game
                        connection.character = character
                        await self._enter_game(connection)
                    else:
                        # User needs to create a character
                        await self._start_character_creation(connection)
                else:
                    await connection.send_message("Invalid username or password.", "red")
                    await connection.send_message("Please type 'login' or 'register'", "yellow")
            except Exception as e:
                await connection.send_message(f"Authentication error: {e}", "red")
                await connection.send_message("Please type 'login' or 'register'", "yellow")
        
        elif command == "register":
            try:
                if len(username) < 3 or len(password) < 6:
                    await connection.send_message("Username must be at least 3 characters, password at least 6 characters.", "red")
                    await connection.send_message("Please type 'login' or 'register'", "yellow")
                    return
                
                # Check if this is the first user (excluding the default admin)
                user_count = await self.db.get_user_count()
                is_first_user = user_count <= 1  # 1 or less because default admin might exist
                
                # Create user with admin privileges if first user
                access_level = 3 if is_first_user else 1  # 3 = admin, 1 = regular user
                success = await self.db.create_user(username, password, access_level=access_level)
                
                if success:
                    if is_first_user:
                        await connection.send_message("Account created successfully with ADMIN privileges!", "gold")
                        await connection.send_message("You are the first player and have been granted administrator access.", "gold")
                    else:
                        await connection.send_message("Account created successfully!", "green")
                    await connection.send_message("Please type 'login' to sign in with your new account.", "white")
                else:
                    await connection.send_message("Username already exists. Please choose a different username.", "red")
                    await connection.send_message("Please type 'login' or 'register'", "yellow")
            except Exception as e:
                await connection.send_message(f"Registration error: {e}", "red")
                await connection.send_message("Please type 'login' or 'register'", "yellow")
        
        else:
            await connection.send_message("Unknown authentication command.", "red")
            await connection.send_message("Please type 'login' or 'register'", "yellow")
    
    async def _start_character_creation(self, connection):
        """Start character creation process"""
        connection.is_in_character_creation = True
        connection_id = id(connection)
        
        session = CharacterCreationSession()
        self.character_creation_sessions[connection_id] = session
        
        await connection.send_message("\n" + "=" * 50, "cyan")
        await connection.send_message("    CHARACTER CREATION", "gold")
        await connection.send_message("=" * 50, "cyan")
        await connection.send_message("")
        await connection.send_message("Let's create your character!", "white")
        await connection.send_message("Please enter your character's name:", "white")
    
    async def _handle_character_creation(self, connection, input_text: str):
        """Handle character creation input"""
        connection_id = id(connection)
        session = self.character_creation_sessions.get(connection_id)
        
        if not session:
            await connection.send_message("Character creation session not found. Please reconnect.", "red")
            return
        
        is_complete, response = await session.process_input(input_text, connection)
        await connection.send_message(response, "white")
        
        if is_complete:
            # Character creation finished
            character_data = session.get_character_data()
            
            if character_data:
                # Save character to database
                char_id = await self.db.create_character(
                    connection.user_id,
                    character_data['name'],
                    character_data['race'],
                    character_data['class'],
                    {
                        'strength': character_data['strength'],
                        'dexterity': character_data['dexterity'],
                        'constitution': character_data['constitution'],
                        'intelligence': character_data['intelligence'],
                        'wisdom': character_data['wisdom'],
                        'charisma': character_data['charisma']
                    }
                )
                
                # Update character data with ID and derived stats
                character_data['id'] = char_id
                connection.character = character_data
                
                # Update character in database with derived stats
                await self.db.update_character(char_id, {
                    'health': character_data['health'],
                    'max_health': character_data['max_health'],
                    'mana': character_data['mana'],
                    'max_mana': character_data['max_mana'],
                    'inventory': character_data['inventory']
                })
                
                # Clean up character creation session
                connection.is_in_character_creation = False
                del self.character_creation_sessions[connection_id]
                
                # Enter the game
                await self._enter_game(connection)
            else:
                await connection.send_message("Error creating character. Please try again.", "red")
                connection.is_in_character_creation = False
                del self.character_creation_sessions[connection_id]
    
    async def _enter_game(self, connection):
        """Enter the player into the game world"""
        if not self.game_engine:
            await connection.send_message("Game engine not available.", "red")
            return
            
        # Check server capacity
        if len(self.game_engine.players) >= self.max_players:
            await connection.send_message("Server is full. Please try again later.", "red")
            return
        
        # Add player to game engine
        player = await self.game_engine.add_player(connection.user_id, connection.character, connection)
        
        # Store session mapping
        self.user_sessions[connection.user_id] = id(connection)
        
        await connection.send_message("\n" + "=" * 50, "cyan")
        await connection.send_message("    ENTERING THE WORLD", "gold")
        await connection.send_message("=" * 50, "cyan")
        await connection.send_message("")
        await connection.send_message("Type 'help' for available commands.", "white")
        await connection.send_message("Type 'quit' to exit the game.", "white")
        await connection.send_message("")
    
    async def _handle_game_command(self, connection, input_text: str):
        """Handle game commands from authenticated players"""
        if input_text.lower() in ['quit', 'exit']:
            await self._disconnect_player(connection)
            return
        
        # Check for admin commands first
        if self.admin_system and self.admin_system.is_admin_command(input_text):
            if self.game_engine:
                player = self.game_engine.players.get(connection.user_id)
                if player:
                    handled = await self.admin_system.process_command(player, input_text)
                    if handled:
                        return
        
        # Process regular game command
        if self.game_engine:
            success = await self.game_engine.process_command(connection.user_id, input_text)
        else:
            success = False
        
        if not success:
            await connection.send_message("Unable to process command. Type 'help' for available commands.", "yellow")
    
    async def _disconnect_player(self, connection):
        """Disconnect a player from the game"""
        try:
            await connection.send_message("Goodbye! Thanks for playing SSH RPG!", "cyan")
            
            # Signal that the connection should be closed
            connection.should_disconnect = True
            
            if connection.user_id:
                # Remove from game engine
                if self.game_engine:
                    await self.game_engine.remove_player(connection.user_id)
                
                # Clean up session mappings
                if connection.user_id in self.user_sessions:
                    del self.user_sessions[connection.user_id]
            
            # Clean up connection
            connection_id = id(connection)
            if connection_id in self.connections:
                del self.connections[connection_id]
            
            if connection_id in self.character_creation_sessions:
                del self.character_creation_sessions[connection_id]
                
        except Exception as e:
            print(f"Error disconnecting player: {e}")
    
    async def disconnect_player(self, user_id: int):
        """Disconnect a player by user ID (called from SSH server)"""
        connection_id = self.user_sessions.get(user_id)
        if connection_id and connection_id in self.connections:
            connection = self.connections[connection_id]
            await self._disconnect_player(connection)
    
    def get_server_stats(self) -> Dict:
        """Get server statistics"""
        return {
            'online_players': len(self.game_engine.players) if self.game_engine else 0,
            'max_players': self.max_players,
            'current_tick': self.game_engine.current_tick if self.game_engine else 0,
            'tick_rate': self.game_engine.tick_rate if self.game_engine else 0,
            'running': self.running
        }

# Global game server instance
game_server = GameServer()

async def main():
    """Main server entry point"""
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(game_server.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        await game_server.start()
        
        # Keep the server running
        while game_server.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Server error: {e}")
        traceback.print_exc()
    finally:
        await game_server.stop()

if __name__ == "__main__":
    print("SSH RPG - Text-Based MMORPG Server")
    print("=" * 40)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)