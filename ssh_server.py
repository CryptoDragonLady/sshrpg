import asyncio
import sys
import os
from typing import Dict, Optional, Union, Any

try:
    import asyncssh
    SSH_AVAILABLE = True
except ImportError:
    asyncssh = None
    SSH_AVAILABLE = False
from colorama import Fore, Back, Style, init
import traceback

# Initialize colorama
init(autoreset=True)

class GameConnection:
    """Represents a connection to the game (SSH or direct)"""
    
    def __init__(self, connection_type: str = "direct"):
        self.connection_type = connection_type
        self.user_id: Optional[str] = None
        self.character = None
        self.is_authenticated = False
        self.is_in_character_creation = False
        self.character_creation_session = None
        self.ssh_process: Optional[Any] = None
        self.reader: Optional[Any] = None  # For TCP connections
        self.writer: Optional[Any] = None  # For TCP connections
        self.should_disconnect = False  # Flag to signal connection should be closed
        self.has_entered_game = False  # Flag to track if player has entered the game
        self._just_entered_game = False
        
        # Authentication state tracking
        self.auth_state = "waiting_for_command"  # waiting_for_command, waiting_for_username, waiting_for_password
        self.auth_command: Optional[str] = None  # "login" or "register"
        self.username_buffer: Optional[str] = None
        self.password_masking = False
        
    async def send_message(self, message: str, color: str = "white"):
        """Send a message to the client with optional color"""
        # Color mapping with black background
        color_map = {
            'red': Fore.RED + Back.BLACK,
            'green': Fore.GREEN + Back.BLACK,
            'blue': Fore.BLUE + Back.BLACK,
            'yellow': Fore.YELLOW + Back.BLACK,
            'cyan': Fore.CYAN + Back.BLACK,
            'magenta': Fore.MAGENTA + Back.BLACK,
            'white': Fore.WHITE + Back.BLACK,
            'gold': Fore.YELLOW + Style.BRIGHT + Back.BLACK,
            'bright_green': Fore.GREEN + Style.BRIGHT + Back.BLACK,
            'bright_red': Fore.RED + Style.BRIGHT + Back.BLACK,
            'dark_yellow': Fore.YELLOW + Style.DIM + Back.BLACK,
            'light_green': Fore.GREEN + Style.BRIGHT + Back.BLACK
        }
        
        colored_message = color_map.get(color, Fore.WHITE) + message + Style.RESET_ALL
        
        if self.connection_type == "ssh" and self.ssh_process:
            self.ssh_process.stdout.write(colored_message + '\n')
        else:
            print(colored_message)
    
    async def send_prompt(self, prompt: str):
        """Send a prompt without newline (placeholder)"""
        pass
    
    async def get_input(self, prompt: str = "") -> str:
        """Get input from the client"""
        if self.connection_type == "ssh" and self.ssh_process:
            if prompt:
                self.ssh_process.stdout.write(prompt)
            return await self.ssh_process.stdin.readline()
        else:
            return input(prompt)

class SSHGameSession:
    """SSH session handler for game connections"""
    
    def __init__(self, game_server):
        self.game_server = game_server
        self.connection: Optional[GameConnection] = None
        self.chan: Optional[Any] = None
        
    def connection_made(self, chan):
        """Called when SSH connection is established"""
        self.connection = GameConnection("ssh")
        self.connection.ssh_process = self
        self.chan = chan
        print(f"SSH connection established from {chan.get_extra_info('peername')}")
        
        # Start the game session
        asyncio.create_task(self._start_game_session())
        
    def data_received(self, data, datatype):
        """Handle incoming data from SSH client"""
        if asyncssh and datatype == asyncssh.EXTENDED_DATA_STDERR:
            return
            
        # Check if connection should be disconnected
        if self.connection and self.connection.should_disconnect:
            if self.chan:
                self.chan.close()
            return
            
        try:
            text = data.decode('utf-8').strip()
            if text:
                asyncio.create_task(self._handle_input_and_check_disconnect(text))
        except Exception as e:
            print(f"Error processing SSH data: {e}")
    
    async def _handle_input_and_check_disconnect(self, text):
        """Handle input and check for disconnect flag"""
        try:
            await self.game_server.handle_client_input(self.connection, text)
            
            # Check if connection should be disconnected after processing input
            if self.connection and self.connection.should_disconnect:
                if self.chan:
                    self.chan.close()
        except Exception as e:
            print(f"Error handling SSH input: {e}")
    
    def connection_lost(self, exc):
        """Called when SSH connection is lost"""
        if self.connection and self.connection.user_id:
            try:
                asyncio.create_task(self.game_server.disconnect_player(self.connection.user_id))
            except:
                pass
        print("SSH connection lost")
    
    async def _start_game_session(self):
        """Start the game session for this SSH connection"""
        try:
            if self.connection:
                await self.connection.send_message("=" * 60, "cyan")
                await self.connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG", "gold")
                await self.connection.send_message("=" * 60, "cyan")
                await self.connection.send_message("")
                
                # Start authentication process
                await self._handle_authentication()
            
        except Exception as e:
            if self.connection:
                await self.connection.send_message(f"Error starting game session: {e}", "red")
            print(f"Error in SSH game session: {e}")
            traceback.print_exc()
    
    async def _handle_authentication(self):
        """Handle user authentication"""
        if self.connection:
            await self.connection.send_message("Please login or create a new account.", "white")
            await self.connection.send_message("Please enter username to login, otherwise type 'register' to create a new character", "yellow")
    
    # SSH session interface methods
    def pty_requested(self, term_type, term_size, term_modes):
        """Handle PTY request"""
        return True
    
    def shell_requested(self):
        """Handle shell request"""
        return True
    
    def exec_requested(self, command):
        """Handle exec request"""
        return False
    
    def subsystem_requested(self, subsystem):
        """Handle subsystem request"""
        return False
    
    def break_received(self, msec) -> bool:
        """Handle break signal"""
        return True
    
    def signal_received(self, signal):
        """Handle signal"""
        if signal == 'INT':
            if self.chan:
                self.chan.close()
    
    def terminal_size_changed(self, width, height, pixwidth, pixheight):
        """Handle terminal size change"""
        pass
    
    # Output methods for the game
    def write(self, data):
        """Write data to SSH client"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        if self.chan:
            self.chan.write(data)
    
    def writelines(self, lines):
        """Write multiple lines to SSH client"""
        for line in lines:
            self.write(line + '\n')
    
    def flush(self):
        """Flush output"""
        pass
    
    @property
    def stdout(self):
        """Provide stdout-like interface"""
        return self
    
    @property
    def stdin(self):
        """Provide stdin-like interface"""
        return SSHInputStream(self.chan)

class SSHInputStream:
    """Provides stdin-like interface for SSH"""
    
    def __init__(self, chan):
        self.chan = chan
        self._buffer = ""
        self._lines = []
    
    async def readline(self):
        """Read a line from SSH input"""
        # This is a simplified implementation
        # In a real implementation, you'd need to handle the SSH input stream properly
        return ""

class SSHGameServer:
    """SSH server for the game"""
    
    def __init__(self, game_server):
        self.game_server = game_server
        
    def session_requested(self):
        """Create new session for incoming SSH connection"""
        return SSHGameSession(self.game_server)
    
    def password_auth_supported(self):
        """Allow password authentication"""
        return True
    
    def validate_password(self, username, password):
        """Accept any username/password for game access"""
        return True
    
    def connection_requested(self, dest_host, dest_port, orig_host, orig_port):
        """Handle connection requests - reject all"""
        return False
    
    def server_requested(self, listen_host, listen_port):
        """Handle server requests - reject all"""
        return False

def handle_ssh_client_with_server(game_server):
    """Create SSH client handler with game_server instance"""
    async def handle_ssh_client(process):
        """Handle SSH client connections using process factory"""
        connection = None
        try:
            # Get connection info
            username = process.get_extra_info('username')
            peername = process.get_extra_info('peername')
            
            # Create a game connection wrapper for SSH
            connection = SSHProcessConnection(process)
            
            # Use the passed game_server instance instead of importing
            
            # Send welcome messages
            await connection.send_message("=" * 60)
            await connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG")
            await connection.send_message("=" * 60)
            await connection.send_message("")
            await connection.send_message("Please login or create a new account.")
            await connection.send_message("Please enter username to login, otherwise type 'register' to create a new character")
            
            # Handle client input loop
            while True:
                try:
                    # Check if connection should be disconnected
                    if connection.should_disconnect:
                        break
                        
                    # Read input from SSH process
                    line = await process.stdin.readline()
                    if not line:
                        break
                        
                    command = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
                    
                    if command:

                        await game_server.handle_client_input(connection, command)
                        # Display prompt after command processing
                        prompt = await game_server.get_player_prompt(connection)
                        if prompt:
                            await connection.send_prompt(prompt)
                    else:
                        # For empty input, still show prompt if authenticated
                        prompt = await game_server.get_player_prompt(connection)
                        if prompt:
                            await connection.send_prompt(prompt)
                        
                    # Check again after processing command
                    if connection.should_disconnect:
                        break
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error handling SSH client input: {e}")
                    break
            
        except Exception as e:
            print(f"Error in SSH client handler: {e}")
        finally:
            try:
                if connection and connection.user_id:
                    await game_server.disconnect_player(int(connection.user_id))
            except:
                pass
            try:
                if connection:
                    await connection.send_message("Connection closed.", "yellow")
            except:
                pass
            try:
                process.exit(0)
            except:
                pass
    
    return handle_ssh_client

async def handle_ssh_client(process):
    """Handle SSH client connections using process factory (fallback)"""
    connection = None
    try:
        # Get connection info
        username = process.get_extra_info('username')
        peername = process.get_extra_info('peername')
        
        # Create a game connection wrapper for SSH
        connection = SSHProcessConnection(process)
        
        # Import here to avoid circular imports
        from server import game_server
        
        # Send welcome messages
        await connection.send_message("=" * 60)
        await connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG")
        await connection.send_message("=" * 60)
        await connection.send_message("")
        await connection.send_message("Please login or create a new account.")
        await connection.send_message("Please enter username to login, otherwise type 'register' to create a new character")
        
        # Handle client input loop
        while True:
            try:
                # Check if connection should be disconnected
                if connection.should_disconnect:
                    break
                    
                # Read input from SSH process
                line = await process.stdin.readline()
                if not line:
                    break
                    
                command = line.decode('utf-8').strip() if isinstance(line, bytes) else line.strip()
                
                if command:
                    await game_server.handle_client_input(connection, command)
                    # Display prompt after command processing
                    prompt = await game_server.get_player_prompt(connection)
                    if prompt:
                        await connection.send_prompt(prompt)
                else:
                    # For empty input, still show prompt if authenticated
                    prompt = await game_server.get_player_prompt(connection)
                    if prompt:
                        await connection.send_prompt(prompt)
                    
                # Check again after processing command
                if connection.should_disconnect:
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error handling SSH client input: {e}")
                break
        
    except Exception as e:
        print(f"SSH client error: {e}")
        traceback.print_exc()
    finally:
        try:
            if connection and connection.user_id:
                from server import game_server
                await game_server.disconnect_player(int(connection.user_id))
        except:
            pass
        try:
            process.exit(0)
        except:
            pass

class SSHProcessConnection(GameConnection):
    """Game connection wrapper for SSH process"""
    
    def __init__(self, process):
        super().__init__("ssh")
        self.process = process
        self.ssh_process = process  # Set this for base class compatibility
        self._input_buffer = ""
    
    async def send_message(self, message: str, color: str = "white"):
        """Send message to SSH client"""
        try:
            # Apply color formatting
            colors = {
                "red": Fore.RED,
                "green": Fore.GREEN,
                "blue": Fore.BLUE,
                "yellow": Fore.YELLOW,
                "magenta": Fore.MAGENTA,
                "cyan": Fore.CYAN,
                "white": Fore.WHITE,
                "bright_red": Fore.LIGHTRED_EX,
                "bright_green": Fore.LIGHTGREEN_EX,
                "bright_blue": Fore.LIGHTBLUE_EX,
                "bright_yellow": Fore.LIGHTYELLOW_EX,
                "bright_magenta": Fore.LIGHTMAGENTA_EX,
                "bright_cyan": Fore.LIGHTCYAN_EX,
                "bright_white": Fore.LIGHTWHITE_EX
            }
            
            color_code = colors.get(color, Fore.WHITE)
            formatted_message = f"{color_code}{message}{Style.RESET_ALL}\n"
            
            self.process.stdout.write(formatted_message)
            
        except Exception as e:
            print(f"Error sending SSH message: {e}")
    
    async def send_prompt(self, prompt: str):
        """Send a prompt without newline for bash-like behavior"""
        try:
            # Send prompt without newline to create proper prompt behavior
            self.process.stdout.write(prompt)
        except Exception as e:
            print(f"Error sending SSH prompt: {e}")
    
    async def get_input(self, prompt: str = "") -> str:
        """Get input from SSH client"""
        try:
            if prompt:
                self.process.stdout.write(prompt)
            
            # Read line from stdin
            line = await self.process.stdin.readline()
            return line.strip() if line else ""
            
        except Exception as e:
            print(f"Error getting SSH input: {e}")
            return ""

# Create SSH server class with proper inheritance
class SSHGameServerAuth:
    """SSH server with authentication"""
    
    def __new__(cls):
        if SSH_AVAILABLE and asyncssh is not None:
            # Create a dynamic class that inherits from asyncssh.SSHServer
            class _SSHGameServerAuth(asyncssh.SSHServer):
                def password_auth_supported(self):
                    """Allow password authentication"""
                    return True
                
                def validate_password(self, username, password):
                    """Accept any username/password for game access"""
                    return True
                
                def connection_made(self, conn):
                    """Called when a connection is made"""
                    pass
            return _SSHGameServerAuth()
        else:
            # Return a basic object when asyncssh is not available
            return super().__new__(cls)
    
    def password_auth_supported(self):
        """Allow password authentication"""
        return True
    
    def validate_password(self, username, password):
        """Accept any username/password for game access"""
        return True
    
    def connection_made(self, conn):
        """Called when a connection is made"""
        pass

async def start_ssh_server(game_server, host='localhost', port=2222):
    """Start the SSH server"""
    if not SSH_AVAILABLE or asyncssh is None:
        print("SSH support not available. Install asyncssh to enable SSH connections.")
        return None
    
    try:
        # Generate or load persistent host key
        host_key_file = "server_host_key"
        
        if os.path.exists(host_key_file):
            # Load existing host key
            try:
                with open(host_key_file, 'r') as f:
                    host_key_data = f.read()
                host_key = asyncssh.import_private_key(host_key_data)
                print(f"Loaded existing SSH host key from {host_key_file}")
            except Exception as e:
                print(f"Failed to load existing host key: {e}")
                print("Generating new host key...")
                host_key = asyncssh.generate_private_key('ssh-rsa')
                # Save the new key
                with open(host_key_file, 'w') as f:
                    f.write(host_key.export_private_key().decode())
                print(f"New SSH host key saved to {host_key_file}")
        else:
            # Generate new host key and save it
            host_key = asyncssh.generate_private_key('ssh-rsa')
            with open(host_key_file, 'w') as f:
                f.write(host_key.export_private_key().decode())
            print(f"Generated and saved new SSH host key to {host_key_file}")
        
        # Create and start SSH server using process factory
        server = await asyncssh.create_server(
            SSHGameServerAuth,
            host=host,
            port=port,
            server_host_keys=[host_key],
            process_factory=handle_ssh_client_with_server(game_server)
        )
        
        print(f"SSH server started on {host}:{port}")
        return server
        
    except Exception as e:
        print(f"Failed to start SSH server: {e}")
        traceback.print_exc()
        return None

# Alternative simple SSH server using asyncio
class SimpleSSHServer:
    """Simple SSH-like server using raw TCP sockets"""
    
    def __init__(self, game_server):
        self.game_server = game_server
        self.server = None
        
    async def start(self, host='localhost', port=2223):
        """Start the simple TCP server"""
        try:
            self.server = await asyncio.start_server(
                self._handle_client, host, port
            )
            print(f"Simple TCP server started on {host}:{port}")
            print(f"Players can connect with: telnet {host} {port}")
            
        except Exception as e:
            print(f"Failed to start TCP server: {e}")
            traceback.print_exc()
    
    async def _handle_client(self, reader, writer):
        """Handle a new TCP client connection"""
        connection = None
        try:
            connection = GameConnection("tcp")
            connection.reader = reader
            connection.writer = writer
            
            # Override send_message for TCP with color support
            async def tcp_send_message(message: str, color: str = "white"):
                try:
                    # Color mapping with black background
                    color_map = {
                        'red': Fore.RED + Back.BLACK,
                        'green': Fore.GREEN + Back.BLACK,
                        'blue': Fore.BLUE + Back.BLACK,
                        'yellow': Fore.YELLOW + Back.BLACK,
                        'cyan': Fore.CYAN + Back.BLACK,
                        'magenta': Fore.MAGENTA + Back.BLACK,
                        'white': Fore.WHITE + Back.BLACK,
                        'gold': Fore.YELLOW + Style.BRIGHT + Back.BLACK,
                        'bright_green': Fore.GREEN + Style.BRIGHT + Back.BLACK,
                        'bright_red': Fore.RED + Style.BRIGHT + Back.BLACK,
                        'dark_yellow': Fore.YELLOW + Style.DIM + Back.BLACK,
                        'light_green': Fore.GREEN + Style.BRIGHT + Back.BLACK
                    }
                    
                    colored_message = color_map.get(color, Fore.WHITE + Back.BLACK) + message + Style.RESET_ALL
                    writer.write((colored_message + '\n').encode('utf-8'))
                    await writer.drain()
                except:
                    pass
            
            # Override send_prompt for TCP
            async def tcp_send_prompt(prompt: str):
                try:
                    # Send prompt without newline for bash-like behavior
                    writer.write(prompt.encode('utf-8'))
                    await writer.drain()
                except:
                    pass
            
            connection.send_message = tcp_send_message
            connection.send_prompt = tcp_send_prompt
            
            # Send welcome message
            await connection.send_message("=" * 60)
            await connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG")
            await connection.send_message("=" * 60)
            await connection.send_message("")
            await connection.send_message("Please login or create a new account.")
            await connection.send_message("Please enter username to login, otherwise type 'register' to create a new character")
            
            # Handle client input with password masking support
            while True:
                try:
                    # Check if connection should be disconnected
                    if connection.should_disconnect:
                        break
                        
                    if connection.password_masking:
                        # Handle password input with masking
                        command = await self._read_password_input(reader, writer)
                        connection.password_masking = False  # Reset after reading
                    else:
                        # Normal input handling
                        data = await reader.readline()
                        if not data:
                            break
                        command = data.decode('utf-8').strip()
                    
                    if command:
                        await self.game_server.handle_client_input(connection, command)
                        # Send prompt after command processing, but not immediately after entering game
                        if (not connection.password_masking and 
                            not (hasattr(connection, 'has_entered_game') and connection.has_entered_game and 
                                 getattr(connection, '_just_entered_game', False))):
                            prompt = await self.game_server.get_player_prompt(connection)
                            if prompt:
                                await connection.send_prompt(prompt)
                    else:
                        # For empty input, only show prompt if authenticated and not just entering game
                        if (not connection.password_masking and 
                            connection.is_authenticated and 
                            not connection.is_in_character_creation and
                            hasattr(connection, 'has_entered_game') and connection.has_entered_game):
                            # Clear the just entered flag after first empty input
                            if getattr(connection, '_just_entered_game', False):
                                connection._just_entered_game = False
                            prompt = await self.game_server.get_player_prompt(connection)
                            if prompt:
                                await connection.send_prompt(prompt)
                        
                    # Check again after processing command
                    if connection.should_disconnect:
                        break
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error handling TCP client: {e}")
                    break
            
        except Exception as e:
            print(f"Error in TCP client handler: {e}")
            traceback.print_exc()
        finally:
            try:
                if connection and connection.user_id:
                    await self.game_server.disconnect_player(int(connection.user_id))
            except:
                pass
            try:
                if writer:
                    writer.close()
                    await writer.wait_closed()
            except:
                pass
    
    async def _read_password_input(self, reader, writer):
        """Read password input with asterisk masking"""
        password = ""
        while True:
            try:
                # Read one character at a time
                data = await reader.read(1)
                if not data:
                    break
                
                char = data.decode('utf-8')
                
                # Handle different input characters
                if char == '\r' or char == '\n':
                    # Enter pressed, finish input
                    writer.write(b'\n')
                    await writer.drain()
                    break
                elif char == '\x7f' or char == '\x08':  # Backspace or DEL
                    if password:
                        password = password[:-1]
                        # Move cursor back, write space, move back again
                        writer.write(b'\x08 \x08')
                        await writer.drain()
                elif char.isprintable():
                    password += char
                    # Show asterisk instead of actual character
                    writer.write(b'*')
                    await writer.drain()
                    
            except Exception as e:
                print(f"Error reading password input: {e}")
                break
                
        return password
    
    async def stop(self):
        """Stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

# For testing without SSH dependencies
class DirectConnection(GameConnection):
    """Direct connection for testing without SSH"""
    
    def __init__(self):
        super().__init__("direct")
        
    async def send_message(self, message: str, color: str = "white"):
        """Send message to console"""
        color_map = {
            'red': Fore.RED + Back.BLACK,
            'green': Fore.GREEN + Back.BLACK,
            'blue': Fore.BLUE + Back.BLACK,
            'yellow': Fore.YELLOW + Back.BLACK,
            'cyan': Fore.CYAN + Back.BLACK,
            'magenta': Fore.MAGENTA + Back.BLACK,
            'white': Fore.WHITE + Back.BLACK,
            'gold': Fore.YELLOW + Style.BRIGHT + Back.BLACK,
            'bright_green': Fore.GREEN + Style.BRIGHT + Back.BLACK,
            'bright_red': Fore.RED + Style.BRIGHT + Back.BLACK,
            'dark_yellow': Fore.YELLOW + Style.DIM + Back.BLACK,
            'light_green': Fore.GREEN + Style.BRIGHT + Back.BLACK
        }
        
        colored_message = color_map.get(color, Fore.WHITE) + message + Style.RESET_ALL
        print(colored_message)
    
    async def get_input(self, prompt: str = "") -> str:
        """Get input from console"""
        if prompt:
            print(prompt, end='')
        return input()

async def test_direct_connection():
    """Test the game with a direct console connection"""
    try:
        from server import GameServer
        
        # Create game server
        game_server = GameServer()
        await game_server.start()
        
        # Create direct connection
        connection = DirectConnection()
        
        print("=" * 60)
        print("    SSH RPG - Text-Based MMORPG (Direct Mode)")
        print("=" * 60)
        print()
        print("Please login or create a new account.")
        print("Type 'login <username> <password>' or 'register <username> <password>'")
        print("Type 'quit' to exit.")
        
        # Main input loop
        while True:
            try:
                command = await connection.get_input("> ")
                if command.lower() in ['quit', 'exit']:
                    break
                
                await game_server.handle_client_input(connection, command)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        # Cleanup
        if connection.user_id:
            await game_server.disconnect_player(int(connection.user_id))
        await game_server.stop()
        
    except Exception as e:
        print(f"Error in direct connection test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Run direct connection test
    asyncio.run(test_direct_connection())