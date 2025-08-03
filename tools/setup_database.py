#!/usr/bin/env python3
"""
Database setup script for SSH RPG
Creates PostgreSQL database and user if they don't exist
"""

import asyncio
import sys
import getpass
from pathlib import Path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from input_sanitizer import InputSanitizer

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

async def create_database_and_user():
    """Create PostgreSQL database and user for SSH RPG"""
    print("SSH RPG Database Setup")
    print("=" * 30)
    
    if not ASYNCPG_AVAILABLE:
        print("asyncpg not available. Please install it first:")
        print("pip install asyncpg")
        return False
    
    # Get PostgreSQL admin credentials
    print("Enter PostgreSQL admin credentials:")
    try:
        admin_user_input = input("Admin username (default: postgres): ").strip() or "postgres"
        admin_user = InputSanitizer.sanitize_username(admin_user_input)
        
        admin_password = getpass.getpass("Admin password: ")
        # Don't sanitize password as it might contain special characters intentionally
        
        host_input = input("Host (default: localhost): ").strip() or "localhost"
        host = InputSanitizer.sanitize_string(host_input)
        
        port_input = input("Port (default: 5432): ").strip() or "5432"
        port = InputSanitizer.sanitize_integer(port_input, min_val=1, max_val=65535)
        
    except ValueError as e:
        print(f"Invalid input: {e}")
        return False
    
    # Database and user to create
    db_name = "sshrpg"
    db_user = "sshrpg_user"
    try:
        db_password_input = input("Password for sshrpg_user (default: sshrpg_password): ").strip() or "sshrpg_password"
        # Don't sanitize password as it might contain special characters intentionally
        db_password = db_password_input
    except ValueError as e:
        print(f"Invalid password input: {e}")
        return False
    
    try:
        # Connect to PostgreSQL as admin
        print(f"\nConnecting to PostgreSQL at {host}:{port}...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            database="postgres"
        )
        
        # Check if database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        
        if not db_exists:
            print(f"Creating database '{db_name}'...")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")
        
        # Check if user exists
        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_user WHERE usename = $1", db_user
        )
        
        if not user_exists:
            print(f"Creating user '{db_user}'...")
            await conn.execute(f"CREATE USER {db_user} WITH PASSWORD '{db_password}'")
            print(f"User '{db_user}' created successfully!")
        else:
            print(f"User '{db_user}' already exists.")
        
        # Grant privileges
        print(f"Granting privileges to '{db_user}'...")
        await conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO {db_user}')
        
        await conn.close()
        
        # Test connection with new user
        print(f"\nTesting connection with new user...")
        test_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        await test_conn.close()
        print("Connection test successful!")
        
        # Update config file
        await update_config_file(host, port, db_name, db_user, db_password)
        
        print("\nDatabase setup completed successfully!")
        print(f"Database: {db_name}")
        print(f"User: {db_user}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

async def update_config_file(host, port, database, username, password):
    """Update config.yaml with database settings"""
    config_file = Path("config.yaml")
    
    if not config_file.exists():
        print("config.yaml not found, skipping config update")
        return
    
    try:
        # Read current config
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Simple replacement (not perfect YAML parsing, but works for our structure)
        lines = content.split('\n')
        updated_lines = []
        in_postgresql_section = False
        
        for line in lines:
            if 'postgresql:' in line:
                in_postgresql_section = True
                updated_lines.append(line)
            elif in_postgresql_section and line.strip().startswith('host:'):
                updated_lines.append(f'    host: "{host}"')
            elif in_postgresql_section and line.strip().startswith('port:'):
                updated_lines.append(f'    port: {port}')
            elif in_postgresql_section and line.strip().startswith('database:'):
                updated_lines.append(f'    database: "{database}"')
            elif in_postgresql_section and line.strip().startswith('username:'):
                updated_lines.append(f'    username: "{username}"')
            elif in_postgresql_section and line.strip().startswith('password:'):
                updated_lines.append(f'    password: "{password}"')
            else:
                if in_postgresql_section and line.strip() and not line.startswith('  '):
                    in_postgresql_section = False
                updated_lines.append(line)
        
        # Write updated config
        with open(config_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print("Updated config.yaml with database settings")
        
    except Exception as e:
        print(f"Error updating config file: {e}")

async def test_connection():
    """Test database connection with current config"""
    print("Testing database connection...")
    
    try:
        # Try to import and use our database module
        from database import db
        
        success = await db.connect()
        if success:
            print("Database connection successful!")
            await db.create_tables()
            print("Database tables created/verified!")
            return True
        else:
            print("Database connection failed!")
            return False
            
    except Exception as e:
        print(f"Error testing connection: {e}")
        return False

def print_usage():
    """Print usage information"""
    print("SSH RPG Database Setup")
    print("=" * 30)
    print("Usage:")
    print("  python setup_database.py setup    - Set up PostgreSQL database")
    print("  python setup_database.py test     - Test database connection")
    print("  python setup_database.py          - Interactive setup")
    print()
    print("This script will:")
    print("  1. Create a PostgreSQL database named 'sshrpg'")
    print("  2. Create a user 'sshrpg_user' with appropriate permissions")
    print("  3. Update config.yaml with the database settings")
    print("  4. Test the connection")

async def main():
    """Main setup function"""
    args = sys.argv[1:]
    
    if args and args[0] in ['-h', '--help', 'help']:
        print_usage()
        return
    
    if args and args[0] == 'test':
        success = await test_connection()
        sys.exit(0 if success else 1)
    
    if args and args[0] == 'setup':
        success = await create_database_and_user()
        if success:
            await test_connection()
        sys.exit(0 if success else 1)
    
    # Interactive mode
    print("SSH RPG Database Setup")
    print("=" * 30)
    print("This will set up a PostgreSQL database for SSH RPG.")
    print("Make sure PostgreSQL is installed and running.")
    print()
    
    choice = input("Continue? (y/n): ").strip().lower()
    if choice not in ['y', 'yes']:
        print("Setup cancelled.")
        return
    
    success = await create_database_and_user()
    if success:
        await test_connection()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
    except Exception as e:
        print(f"Setup error: {e}")
        sys.exit(1)