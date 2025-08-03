# Tools Directory

This directory contains utility scripts and tools for managing the SSH RPG game.

## Scripts

### Database Management
- **`setup_database.py`** - Sets up PostgreSQL database and user for the game
  ```bash
  python tools/setup_database.py
  ```

### Game Content Management
- **`create_world.py`** - Creates the initial game world with rooms and connections
  ```bash
  python tools/create_world.py
  ```

- **`populate_monsters.py`** - Populates the game world with monsters
  ```bash
  python tools/populate_monsters.py
  ```

### Administration
- **`create_admin_character.py`** - Creates an admin character for game management
  ```bash
  python tools/create_admin_character.py
  ```

### Debugging
- **`debug_exits.py`** - Debug utility for checking room exits and connections
  ```bash
  python tools/debug_exits.py
  ```

## Usage Notes

- Run these scripts from the project root directory
- Ensure the virtual environment is activated before running any scripts
- Some scripts may require database configuration to be set up first
- Admin tools should be used carefully in production environments

## Dependencies

All tools use the same dependencies as the main game. Make sure to install requirements:
```bash
pip install -r requirements.txt
```