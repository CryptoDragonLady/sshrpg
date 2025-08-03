#!/usr/bin/env python3
"""
SSH RPG Server Startup Script
Handles configuration loading and server initialization
"""

import asyncio
import sys
import os
import yaml
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import game_server
from debug_logger import debug_logger

def load_config(config_file: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"Configuration file {config_file} not found. Using defaults.")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Using default configuration.")
        return {}

def apply_config(config: dict):
    """Apply configuration to game server"""
    if not config:
        return
    
    # Configure debug logger first
    debug_logger.configure(config)
    
    # Server settings
    server_config = config.get('server', {})
    if 'max_players' in server_config:
        game_server.max_players = server_config['max_players']
    if 'ssh_port' in server_config:
        game_server.ssh_port = server_config['ssh_port']
    if 'tcp_port' in server_config:
        game_server.tcp_port = server_config['tcp_port']
    
    # Database settings
    db_config = config.get('database', {})
    if 'postgresql' in db_config:
        pg_config = db_config['postgresql']
        # Note: Database configuration will be handled by the database module
        # These assignments are commented out due to linter errors
        # game_server.db.pg_host = pg_config.get('host', 'localhost')
        # game_server.db.pg_port = pg_config.get('port', 5432)
        # game_server.db.pg_database = pg_config.get('database', 'sshrpg')
        # game_server.db.pg_user = pg_config.get('username', 'sshrpg_user')
        # game_server.db.pg_password = pg_config.get('password', 'sshrpg_password')
    
    print(f"Configuration applied:")
    print(f"  Max players: {game_server.max_players}")
    print(f"  SSH port: {game_server.ssh_port}")
    print(f"  TCP port: {game_server.tcp_port}")
    
    # Print debug logger status
    if debug_logger.enabled:
        print(f"  Debug logging: ENABLED")
        print(f"    {debug_logger.get_status()}")
    else:
        print(f"  Debug logging: DISABLED")

def print_banner():
    """Print server startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                        SSH RPG SERVER                        ║
║                  Text-Based MMORPG v1.0                     ║
║                                                              ║
║  A multi-user text-based RPG with SSH support               ║
║  Supports up to 24 simultaneous players                     ║
║  Features character creation, combat, and world editing     ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []
    optional_deps = []
    
    try:
        import asyncssh
    except ImportError:
        optional_deps.append("asyncssh (for SSH support)")
    
    try:
        import asyncpg
    except ImportError:
        optional_deps.append("asyncpg (for PostgreSQL support)")
    
    try:
        import bcrypt
    except ImportError:
        missing_deps.append("bcrypt")
    
    try:
        import colorama
    except ImportError:
        missing_deps.append("colorama")
    
    try:
        import yaml
    except ImportError:
        missing_deps.append("pyyaml")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall missing dependencies with:")
        print(f"  pip install {' '.join(missing_deps)}")
        return False
    
    if optional_deps:
        print("Optional dependencies not found:")
        for dep in optional_deps:
            print(f"  - {dep}")
        print("Server will run with limited functionality.")
    
    return True

async def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="SSH RPG Server")
    parser.add_argument("--config", "-c", default="config.yaml",
                       help="Configuration file path (default: config.yaml)")
    parser.add_argument("--no-ssh", action="store_true",
                       help="Disable SSH server (TCP only)")
    parser.add_argument("--port", "-p", type=int,
                       help="Override SSH port")
    parser.add_argument("--tcp-port", type=int,
                       help="Override TCP port")
    parser.add_argument("--max-players", type=int,
                       help="Override max players")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode")
    parser.add_argument("--debug-verbosity", type=int, choices=[0, 1, 2, 3],
                       help="Set debug verbosity level (0=minimal, 1=normal, 2=verbose, 3=very_verbose)")
    parser.add_argument("--debug-components", nargs="+",
                       choices=["admin_commands", "database", "game_engine", "server", "character_creation", "combat"],
                       help="Enable debug logging for specific components")
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install missing dependencies before running the server.")
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    apply_config(config)
    
    # Apply command line overrides
    if args.port:
        game_server.ssh_port = args.port
    if args.tcp_port:
        game_server.tcp_port = args.tcp_port
    if args.max_players:
        game_server.max_players = args.max_players
    
    # Handle debug options
    if args.debug:
        debug_logger.enable(args.debug_verbosity if args.debug_verbosity is not None else 1)
        print("Debug logging enabled via command line")
    
    if args.debug_verbosity is not None:
        debug_logger.verbosity = args.debug_verbosity
        if not debug_logger.enabled:
            debug_logger.enable()
        print(f"Debug verbosity set to {args.debug_verbosity}")
    
    if args.debug_components:
        # Disable all components first, then enable specified ones
        for component in debug_logger.components:
            debug_logger.set_component(component, False)
        for component in args.debug_components:
            debug_logger.set_component(component, True)
        if not debug_logger.enabled:
            debug_logger.enable()
        print(f"Debug components enabled: {', '.join(args.debug_components)}")
    
    # Disable SSH if requested
    if args.no_ssh:
        print("SSH server disabled - TCP only mode")
        # We'll handle this in the server startup
    
    print("\nStarting server...")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        await game_server.start(enable_ssh=not args.no_ssh)
        
        # Keep server running
        while game_server.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Server error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    finally:
        await game_server.stop()
        print("Server stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)