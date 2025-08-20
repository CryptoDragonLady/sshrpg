import asyncio
import json
from typing import Optional, Dict, List, Any
import bcrypt
from input_sanitizer import InputSanitizer

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None
    ASYNCPG_AVAILABLE = False

class Database:
    def __init__(self, db_url: str = "postgresql://localhost/sshrpg"):
        self.db_url = db_url
        self.pool = None

    async def connect(self) -> bool:
        """Connect to the database"""
        if not ASYNCPG_AVAILABLE:
            print("asyncpg not available, using in-memory storage")
            self.pool = None
            self._init_memory_storage()
            return False

        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10
            )
            print("Connected to PostgreSQL database")
            return True
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            print("Using in-memory storage instead")
            self.pool = None
            self._init_memory_storage()
            return False

    def _init_memory_storage(self):
        """Initialize in-memory storage as fallback"""
        self.users = {}
        self.characters = {}
        self.rooms = {}
        self.items = {}
        self.monsters = {}
        self.world_state = {}
        print("Using in-memory storage (no PostgreSQL connection)")

    async def create_tables(self):
        """Create all necessary database tables"""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    access_level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            # Characters table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    name VARCHAR(50) NOT NULL,
                    race VARCHAR(20) NOT NULL,
                    class VARCHAR(20) NOT NULL,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    health INTEGER DEFAULT 100,
                    max_health INTEGER DEFAULT 100,
                    mana INTEGER DEFAULT 50,
                    max_mana INTEGER DEFAULT 50,
                    strength INTEGER DEFAULT 10,
                    dexterity INTEGER DEFAULT 10,
                    constitution INTEGER DEFAULT 10,
                    intelligence INTEGER DEFAULT 10,
                    wisdom INTEGER DEFAULT 10,
                    charisma INTEGER DEFAULT 10,
                    current_room INTEGER DEFAULT 1,
                    inventory JSONB DEFAULT '[]',
                    equipment JSONB DEFAULT '{}',
                    status_line TEXT DEFAULT 'HP: {health}/{max_health} | MP: {mana}/{max_mana} | Room: {room_name}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Rooms table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rooms (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    exits JSONB DEFAULT '{}',
                    items JSONB DEFAULT '[]',
                    monsters JSONB DEFAULT '[]',
                    properties JSONB DEFAULT '{}'
                )
            ''')

            # Items table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    description TEXT,
                    item_type VARCHAR(20) NOT NULL,
                    properties JSONB DEFAULT '{}',
                    stats JSONB DEFAULT '{}'
                )
            ''')

            # Monsters table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS monsters (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    description TEXT,
                    level INTEGER DEFAULT 1,
                    health INTEGER DEFAULT 50,
                    max_health INTEGER DEFAULT 50,
                    attack INTEGER DEFAULT 5,
                    defense INTEGER DEFAULT 2,
                    experience_reward INTEGER DEFAULT 10,
                    loot_table JSONB DEFAULT '[]',
                    properties JSONB DEFAULT '{}'
                )
            ''')

            # Room monsters table (for monster instances in rooms)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS room_monsters (
                    id SERIAL PRIMARY KEY,
                    room_id INTEGER REFERENCES rooms(id),
                    monster_id INTEGER REFERENCES monsters(id),
                    health INTEGER NOT NULL,
                    max_health INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    async def create_user(self, username: str, password: str, access_level: int = 1) -> bool:
        """Create a new user account"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if not self.pool:
            # Memory storage
            if username in self.users:
                return False
            self.users[username] = {
                'id': len(self.users) + 1,
                'username': username,
                'password_hash': password_hash,
                'access_level': access_level
            }
            return True

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    'INSERT INTO users (username, password_hash, access_level) VALUES ($1, $2, $3)',
                    username, password_hash, access_level
                )
                return True
        except asyncpg.UniqueViolationError:
            return False

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user login"""
        if not self.pool:
            # Memory storage
            user = self.users.get(username)
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user
            return None

        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE username = $1', username
            )
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                await conn.execute(
                    'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
                    user['id']
                )
                return dict(user)
            return None

    async def get_user_count(self) -> int:
        """Get total number of users"""
        if not self.pool:
            # Memory storage
            return len(self.users)

        async with self.pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM users')
            return count

    async def create_character(self, user_id: int, name: str, race: str, char_class: str, stats: Dict) -> int:
        """Create a new character"""
        # Sanitize inputs
        sanitized_name = InputSanitizer.sanitize_character_name(name)
        sanitized_race = InputSanitizer.sanitize_string(race)
        sanitized_class = InputSanitizer.sanitize_string(char_class)

        if not self.pool:
            # Memory storage
            char_id = len(self.characters) + 1
            self.characters[char_id] = {
                'id': char_id,
                'user_id': user_id,
                'name': sanitized_name,
                'race': sanitized_race,
                'class': sanitized_class,
                'level': 1,
                'experience': 0,
                'current_room': 1,
                'inventory': [],
                'equipment': {},
                'status_line': 'HP: {health}/{max_health} | MP: {mana}/{max_mana} | Room: {room_name}',
                **stats
            }
            return char_id

        async with self.pool.acquire() as conn:
            char_id = await conn.fetchval('''
                INSERT INTO characters (user_id, name, race, class, strength, dexterity,
                                      constitution, intelligence, wisdom, charisma)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            ''', user_id, sanitized_name, sanitized_race, sanitized_class, stats['strength'], stats['dexterity'],
                stats['constitution'], stats['intelligence'], stats['wisdom'], stats['charisma'])
            return char_id

    async def get_character(self, user_id: int) -> Optional[Dict]:
        """Get character by user ID"""
        if not self.pool:
            # Memory storage
            for char in self.characters.values():
                if char['user_id'] == user_id:
                    return char
            return None

        async with self.pool.acquire() as conn:
            char = await conn.fetchrow(
                'SELECT * FROM characters WHERE user_id = $1', user_id
            )
            if char:
                char_dict = dict(char)
                # Parse JSONB fields from strings to Python objects
                if 'inventory' in char_dict:
                    if isinstance(char_dict['inventory'], str):
                        try:
                            char_dict['inventory'] = json.loads(char_dict['inventory'])
                        except (json.JSONDecodeError, TypeError):
                            char_dict['inventory'] = []
                    elif char_dict['inventory'] is None:
                        char_dict['inventory'] = []
                if 'equipment' in char_dict:
                    if isinstance(char_dict['equipment'], str):
                        try:
                            char_dict['equipment'] = json.loads(char_dict['equipment'])
                        except (json.JSONDecodeError, TypeError):
                            char_dict['equipment'] = {}
                    elif char_dict['equipment'] is None:
                        char_dict['equipment'] = {}
                return char_dict
            return None

    async def update_character(self, char_id: int, updates: Dict):
        """Update character data"""
        if not self.pool:
            # Memory storage
            if char_id in self.characters:
                self.characters[char_id].update(updates)
            return

        # Build dynamic update query
        set_clauses = []
        values = []
        for i, (key, value) in enumerate(updates.items(), 1):
            if key in ['inventory', 'equipment']:
                set_clauses.append(f"{key} = ${i}")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = ${i}")
                values.append(value)

        values.append(char_id)
        query = f"UPDATE characters SET {', '.join(set_clauses)} WHERE id = ${len(values)}"

        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)

    async def get_room(self, room_id: int) -> Optional[Dict]:
        """Get room by ID"""
        if not self.pool:
            return self.rooms.get(room_id)

        async with self.pool.acquire() as conn:
            room = await conn.fetchrow('SELECT * FROM rooms WHERE id = $1', room_id)
            return dict(room) if room else None

    async def create_room(self, name: str, description: str, properties: Dict = None) -> int:
        """Create a new room"""
        if properties is None:
            properties = {}

        try:
            # Sanitize inputs
            sanitized_name = InputSanitizer.sanitize_room_name(name)
            sanitized_description = InputSanitizer.sanitize_description(description)

            if not self.pool:
                room_id = len(self.rooms) + 1
                self.rooms[room_id] = {
                    'id': room_id,
                    'name': sanitized_name,
                    'description': sanitized_description,
                    'exits': {},
                    'items': [],
                    'monsters': [],
                    'properties': properties
                }
                return room_id

            async with self.pool.acquire() as conn:
                room_id = await conn.fetchval('''
                    INSERT INTO rooms (name, description, properties)
                    VALUES ($1, $2, $3) RETURNING id
                ''', sanitized_name, sanitized_description, json.dumps(properties))
                return room_id
        except ValueError as e:
            print(f"Input validation error in create_room: {e}")
            raise

    async def link_rooms(self, room1_id: int, direction: str, room2_id: int):
        """Link two rooms with a directional exit"""
        opposite_dirs = {
            'north': 'south', 'south': 'north',
            'east': 'west', 'west': 'east',
            'up': 'down', 'down': 'up'
        }

        if not self.pool:
            if room1_id in self.rooms:
                self.rooms[room1_id]['exits'][direction] = room2_id
            if room2_id in self.rooms and direction in opposite_dirs:
                self.rooms[room2_id]['exits'][opposite_dirs[direction]] = room1_id
            return

        async with self.pool.acquire() as conn:
            # Update room1 exits
            room1 = await conn.fetchrow('SELECT exits FROM rooms WHERE id = $1', room1_id)
            if room1:
                exits_data = room1['exits'] if room1['exits'] is not None else {}
                exits_data[direction] = room2_id
                await conn.execute('UPDATE rooms SET exits = $1 WHERE id = $2',
                                 json.dumps(exits_data), room1_id)

            # Update room2 exits (bidirectional)
            if direction in opposite_dirs:
                room2 = await conn.fetchrow('SELECT exits FROM rooms WHERE id = $1', room2_id)
                if room2:
                    exits_data = room2['exits'] if room2['exits'] is not None else {}
                    exits_data[opposite_dirs[direction]] = room1_id
                    await conn.execute('UPDATE rooms SET exits = $1 WHERE id = $2',
                                     json.dumps(exits_data), room2_id)

    async def get_item(self, item_id: int) -> Optional[Dict]:
        """Get item by ID"""
        if not self.pool:
            return self.items.get(item_id)

        async with self.pool.acquire() as conn:
            item = await conn.fetchrow('SELECT * FROM items WHERE id = $1', item_id)
            return dict(item) if item else None

    async def create_item(self, name: str, description: str, item_type: str,
                         properties: Dict = None, stats: Dict = None) -> int:
        """Create a new item"""
        if properties is None:
            properties = {}
        if stats is None:
            stats = {}

        if not self.pool:
            item_id = len(self.items) + 1
            self.items[item_id] = {
                'id': item_id,
                'name': name,
                'description': description,
                'item_type': item_type,
                'properties': properties,
                'stats': stats
            }
            return item_id

        async with self.pool.acquire() as conn:
            item_id = await conn.fetchval('''
                INSERT INTO items (name, description, item_type, properties, stats)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
            ''', name, description, item_type, json.dumps(properties), json.dumps(stats))
            return item_id

    async def get_monster(self, monster_id: int) -> Optional[Dict]:
        """Get monster by ID"""
        if not self.pool:
            return self.monsters.get(monster_id)

        async with self.pool.acquire() as conn:
            monster = await conn.fetchrow('SELECT * FROM monsters WHERE id = $1', monster_id)
            return dict(monster) if monster else None

    async def create_monster(self, name: str, description: str, level: int,
                           health: int, attack: int, defense: int,
                           experience_reward: int, loot_table: List = None) -> int:
        """Create a new monster"""
        if loot_table is None:
            loot_table = []

        if not self.pool:
            monster_id = len(self.monsters) + 1
            self.monsters[monster_id] = {
                'id': monster_id,
                'name': name,
                'description': description,
                'level': level,
                'health': health,
                'max_health': health,
                'attack': attack,
                'defense': defense,
                'experience_reward': experience_reward,
                'loot_table': loot_table
            }
            return monster_id

        async with self.pool.acquire() as conn:
            monster_id = await conn.fetchval('''
                INSERT INTO monsters (name, description, level, health, max_health,
                                    attack, defense, experience_reward, loot_table)
                VALUES ($1, $2, $3, $4, $4, $5, $6, $7, $8) RETURNING id
            ''', name, description, level, health, attack, defense,
                experience_reward, json.dumps(loot_table))
            return monster_id

    async def get_room_monsters(self, room_id: int) -> List[Dict]:
        """Get all monster instances in a room"""
        if not self.pool:
            # Memory storage - simplified
            return []

        async with self.pool.acquire() as conn:
            monsters = await conn.fetch('''
                SELECT * FROM room_monsters WHERE room_id = $1
            ''', room_id)
            return [dict(monster) for monster in monsters]

    async def create_room_monster(self, room_id: int, monster_id: int, health: int, max_health: int) -> int:
        """Create a monster instance in a room"""
        if not self.pool:
            # Memory storage - simplified
            return 1

        async with self.pool.acquire() as conn:
            instance_id = await conn.fetchval('''
                INSERT INTO room_monsters (room_id, monster_id, health, max_health)
                VALUES ($1, $2, $3, $4) RETURNING id
            ''', room_id, monster_id, health, max_health)
            return instance_id

    async def update_room_monster_health(self, instance_id: int, health: int):
        """Update a monster instance's health"""
        if not self.pool:
            # Memory storage - simplified
            return

        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE room_monsters SET health = $1 WHERE id = $2
            ''', health, instance_id)

    async def update_room_monster_room(self, instance_id: int, new_room_id: int):
        """Move a monster instance to a different room"""
        if not self.pool:
            # Memory storage - simplified
            return

        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE room_monsters SET room_id = $1 WHERE id = $2
            ''', new_room_id, instance_id)

    async def remove_room_monster(self, instance_id: int):
        """Remove a monster instance from a room"""
        if not self.pool:
            # Memory storage - simplified
            return

        async with self.pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM room_monsters WHERE id = $1
            ''', instance_id)

    async def add_item_to_room(self, room_id: int, item_id: int, hidden: bool = False) -> bool:
        """Add an item to a room's items list"""
        if not self.pool:
            # Memory storage
            if room_id in self.rooms:
                item_data = {'item_id': item_id, 'hidden': hidden}
                if 'items' not in self.rooms[room_id]:
                    self.rooms[room_id]['items'] = []
                self.rooms[room_id]['items'].append(item_data)
                return True
            return False

        async with self.pool.acquire() as conn:
            # Get current items
            room = await conn.fetchrow('SELECT items FROM rooms WHERE id = $1', room_id)
            if not room:
                return False

            items = room['items'] if room['items'] is not None else []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except (json.JSONDecodeError, TypeError):
                    items = []

            # Add new item
            item_data = {'item_id': item_id, 'hidden': hidden}
            items.append(item_data)

            # Update room
            await conn.execute('UPDATE rooms SET items = $1 WHERE id = $2',
                             json.dumps(items), room_id)
            return True

    async def remove_item_from_room(self, room_id: int, item_id: int) -> bool:
        """Remove an item from a room's items list"""
        if not self.pool:
            # Memory storage
            if room_id in self.rooms and 'items' in self.rooms[room_id]:
                items = self.rooms[room_id]['items']
                self.rooms[room_id]['items'] = [item for item in items if item.get('item_id') != item_id]
                return True
            return False

        async with self.pool.acquire() as conn:
            # Get current items
            room = await conn.fetchrow('SELECT items FROM rooms WHERE id = $1', room_id)
            if not room:
                return False

            items = room['items'] if room['items'] is not None else []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except (json.JSONDecodeError, TypeError):
                    items = []

            # Remove item
            items = [item for item in items if item.get('item_id') != item_id]

            # Update room
            await conn.execute('UPDATE rooms SET items = $1 WHERE id = $2',
                             json.dumps(items), room_id)
            return True

    async def get_room_items(self, room_id: int) -> List[Dict]:
        """Get all items in a room with their details"""
        if not self.pool:
            # Memory storage
            if room_id in self.rooms and 'items' in self.rooms[room_id]:
                room_items = []
                for item_data in self.rooms[room_id]['items']:
                    item = self.items.get(item_data['item_id'])
                    if item:
                        item_copy = item.copy()
                        item_copy['hidden'] = item_data.get('hidden', False)
                        room_items.append(item_copy)
                return room_items
            return []

        async with self.pool.acquire() as conn:
            # Get room items
            room = await conn.fetchrow('SELECT items FROM rooms WHERE id = $1', room_id)
            if not room:
                return []

            items = room['items'] if room['items'] is not None else []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except (json.JSONDecodeError, TypeError):
                    items = []

            # Get item details
            room_items = []
            for item_data in items:
                item_id = item_data.get('item_id')
                if item_id:
                    item = await conn.fetchrow('SELECT * FROM items WHERE id = $1', item_id)
                    if item:
                        item_dict = dict(item)
                        item_dict['hidden'] = item_data.get('hidden', False)
                        room_items.append(item_dict)

            return room_items

# Global database instance
db = Database()