import asyncio
import sys
from typing import Dict, Optional

try:
    import asyncssh
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
from colorama import Fore, Back, Style, init
import traceback

# Initialize colorama
init(autoreset=True)

class GameConnection:
    """Represents a connection to the game (SSH or direct)"""
    
    def __init__(self, connection_type: str = "direct"):
        self.connection_type = connection_type
        self.user_id = None
        self.character = None
        self.is_authenticated = False
        self.is_in_character_creation = False
        self.character_creation_session = None
        self.ssh_process = None
        
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
    
    async def get_input(self, prompt: str = "") -> str:
        """Get input from the client"""
        if self.connection_type == "ssh" and self.ssh_process:
            if prompt:
                self.ssh_process.stdout.write(prompt)
            return await self.ssh_process.stdin.readline()
        else:
            return input(prompt)

class SSHGameSession(asyncssh.SSHServerSession):
    """SSH session handler for game connections"""
    
    def __init__(self, game_server):
        self.game_server = game_server
        self.connection = None
        
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
        if datatype == asyncssh.EXTENDED_DATA_STDERR:
            return
            
        try:
            text = data.decode('utf-8').strip()
            if text:
                asyncio.create_task(self.game_server.handle_client_input(self.connection, text))
        except Exception as e:
            print(f"Error processing SSH data: {e}")
    
    def connection_lost(self, exc):
        """Called when SSH connection is lost"""
        if self.connection and self.connection.user_id:
            asyncio.create_task(self.game_server.disconnect_player(self.connection.user_id))
        print("SSH connection lost")
    
    async def _start_game_session(self):
        """Start the game session for this SSH connection"""
        try:
            await self.connection.send_message("=" * 60, "cyan")
            await self.connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG", "gold")
            await self.connection.send_message("=" * 60, "cyan")
            await self.connection.send_message("")
            
            # Start authentication process
            await self._handle_authentication()
            
        except Exception as e:
            await self.connection.send_message(f"Error starting game session: {e}", "red")
            print(f"Error in SSH game session: {e}")
            traceback.print_exc()
    
    async def _handle_authentication(self):
        """Handle user authentication"""
        await self.connection.send_message("Please login or create a new account.", "white")
        await self.connection.send_message("Type 'login <username> <password>' or 'register <username> <password>'", "yellow")
    
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
    
    def break_received(self, msec):
        """Handle break signal"""
        pass
    
    def signal_received(self, signal):
        """Handle signal"""
        if signal == 'INT':
            self.chan.close()
    
    def terminal_size_changed(self, width, height, pixwidth, pixheight):
        """Handle terminal size change"""
        pass
    
    # Output methods for the game
    def write(self, data):
        """Write data to SSH client"""
        if isinstance(data, str):
            data = data.encode('utf-8')
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

class SSHGameServer(asyncssh.SSHServer):
    """SSH server for the game"""
    
    def __init__(self, game_server):
        self.game_server = game_server
        
    def session_requested(self):
        """Create new session for incoming SSH connection"""
        return SSHGameSession(self.game_server)

async def start_ssh_server(game_server, host='localhost', port=2222):
    """Start the SSH server"""
    if not SSH_AVAILABLE:
        print("SSH support not available. Install asyncssh to enable SSH connections.")
        return None
    
    try:
        # Generate or load host key
        host_key = asyncssh.generate_private_key('ssh-rsa')
        
        # Create and start SSH server
        def ssh_server_factory():
            return SSHGameServer(game_server)
        
        server = await asyncssh.create_server(
            ssh_server_factory,
            host=host,
            port=port,
            server_host_keys=[host_key]
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
            
            connection.send_message = tcp_send_message
            
            # Send welcome message
            await connection.send_message("=" * 60)
            await connection.send_message("    Welcome to SSH RPG - Text-Based MMORPG")
            await connection.send_message("=" * 60)
            await connection.send_message("")
            await connection.send_message("Please login or create a new account.")
            await connection.send_message("Type 'login <username> <password>' or 'register <username> <password>'")
            
            # Handle client input
            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break
                    
                    command = data.decode('utf-8').strip()
                    if command:
                        await self.game_server.handle_client_input(connection, command)
                        
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
                if connection.user_id:
                    await self.game_server.disconnect_player(connection.user_id)
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
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
            await game_server.disconnect_player(connection.user_id)
        await game_server.stop()
        
    except Exception as e:
        print(f"Error in direct connection test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Run direct connection test
    asyncio.run(test_direct_connection())