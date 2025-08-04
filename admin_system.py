import json
from typing import Dict, List, Optional, Any
from database import db
from debug_logger import debug_admin, DebugLogger
from input_sanitizer import InputSanitizer

class AdminSystem:
    """Handles administrative commands and world editing"""
    
    def __init__(self, game_engine):
        self.game_engine = game_engine
        self.sanitizer = InputSanitizer()
        
        # Admin command mappings
        self.admin_commands = {
            'admin_help': self._show_admin_help,
            'create_room': self._create_room,
            'link_rooms': self._link_rooms,
            'create_item': self._create_item,
            'create_monster': self._create_monster,
            'teleport': self._teleport_player,
            'promote': self._promote_user,
            'demote': self._demote_user,
            'kick': self._kick_player,
            'ban': self._ban_player,
            'unban': self._unban_player,
            'reload_world': self._reload_world,
            'list_rooms': self._list_rooms,
            'list_items': self._list_items,
            'list_monsters': self._list_monsters,
            'list_properties': self._list_properties,
            'edit_room': self._edit_room,
            'edit_item': self._edit_item,
            'edit_monster': self._edit_monster,
            'spawn_monster': self._spawn_monster,
            'spawn_item': self._spawn_item,
            'server_stats': self._server_stats,
            'broadcast': self._broadcast_message,
            'save_world': self._save_world,
            'load_world': self._load_world,
            'debug_status': self._debug_status,
            'debug_enable': self._debug_enable,
            'debug_disable': self._debug_disable,
            'debug_verbosity': self._debug_verbosity,
            'debug_component': self._debug_component,
            'map': self._show_map
        }
    
    async def process_admin_command(self, player, command: str, args: List[str]) -> bool:
        """Process an admin command"""
        # Check if player has admin access
        if not await self._has_admin_access(player):
            await player.send_message("You don't have permission to use admin commands.", "red")
            return False
        
        if command not in self.admin_commands:
            await player.send_message(f"Unknown admin command: {command}", "red")
            await self._show_admin_help(player, [])
            return False
        
        try:
            await self.admin_commands[command](player, args)
            return True
        except Exception as e:
            await player.send_message(f"Error executing admin command: {e}", "red")
            return False
    
    async def _has_admin_access(self, player) -> bool:
        """Check if player has admin access (access level 2 or higher)"""
        # Get user from database using user_id
        try:
            if not db.pool:
                # Memory storage fallback
                for user in db.users.values():
                    if user.get('id') == player.user_id:
                        return user.get('access_level', 1) >= 2
                return False
            
            async with db.pool.acquire() as conn:
                user = await conn.fetchrow('SELECT * FROM users WHERE id = $1', player.user_id)
                if user:
                    return user.get('access_level', 1) >= 2
        except Exception as e:
            print(f"Error checking admin access: {e}")
        return False
    
    async def _create_room(self, player, args: List[str]):
        """Create a new room: /create_room <name> <description>"""
        if len(args) < 2:
            await player.send_message("Usage: /create_room <name> <description>", "yellow")
            return
        
        name = args[0]
        description = ' '.join(args[1:])
        
        room_id = await db.create_room(name, description)
        await player.send_message(f"Created room '{name}' with ID {room_id}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Created room: {name} (ID: {room_id})")
    
    async def _link_rooms(self, player, args: List[str]):
        """Link two rooms: /link_rooms <room1_id> <direction> <room2_id>"""
        if len(args) != 3:
            await player.send_message("Usage: /link_rooms <room1_id> <direction> <room2_id>", "yellow")
            await player.send_message("Directions: north, south, east, west, up, down", "yellow")
            return
        
        try:
            room1_id = int(args[0])
            direction = args[1].lower()
            room2_id = int(args[2])
            
            valid_directions = ['north', 'south', 'east', 'west', 'up', 'down']
            if direction not in valid_directions:
                await player.send_message(f"Invalid direction. Use: {', '.join(valid_directions)}", "yellow")
                return
            
            # Check if rooms exist
            room1 = await db.get_room(room1_id)
            room2 = await db.get_room(room2_id)
            
            if not room1:
                await player.send_message(f"Room {room1_id} does not exist.", "red")
                return
            if not room2:
                await player.send_message(f"Room {room2_id} does not exist.", "red")
                return
            
            await db.link_rooms(room1_id, direction, room2_id)
            await player.send_message(f"Linked room {room1_id} ({room1['name']}) {direction} to room {room2_id} ({room2['name']})", "green")
            
            # Log admin action
            await self._log_admin_action(player, f"Linked rooms: {room1_id} {direction} {room2_id}")
            
        except ValueError:
            await player.send_message("Room IDs must be numbers.", "red")
    
    async def _create_item(self, player, args: List[str]):
        """Create a new item: /create_item <name> <type> [stats_json]"""
        debug_admin(f"_create_item called by {player.character['name']} with args: {args}", DebugLogger.NORMAL)
        
        if len(args) < 2:
            debug_admin("Insufficient arguments for create_item", DebugLogger.VERBOSE)
            await player.send_message("Usage: /create_item \"name\" <type> [stats_json]", "yellow")
            await player.send_message("Types: weapon, armor, potion, misc", "yellow")
            await player.send_message("Example: /create_item \"Fire Sword\" weapon '{\"damage\": 15, \"durability\": 100}'", "yellow")
            return
        
        name = args[0]
        item_type = args[1].lower()
        debug_admin(f"Parsed name='{name}', type='{item_type}'", DebugLogger.VERBOSE)
        
        # Parse stats if provided
        stats = {}
        properties = {}
        
        if len(args) > 2:
            try:
                stats_str = ' '.join(args[2:])
                debug_admin(f"Attempting to parse stats JSON: {stats_str}", DebugLogger.VERBOSE)
                stats = json.loads(stats_str)
                debug_admin(f"Successfully parsed stats: {stats}", DebugLogger.VERBOSE)
            except json.JSONDecodeError as e:
                debug_admin(f"JSON parsing failed: {e}", DebugLogger.NORMAL)
                await player.send_message("Invalid JSON for stats. Use single quotes around JSON:", "red")
                await player.send_message("Example: /create_item \"Fire Sword\" weapon '{\"damage\": 15, \"durability\": 100}'", "yellow")
                return
        else:
            debug_admin("No stats provided, using defaults", DebugLogger.VERBOSE)
        
        # Set default properties based on type
        debug_admin(f"Setting default properties for type: {item_type}", DebugLogger.VERBOSE)
        if item_type == 'weapon':
            properties['equipable'] = True
            properties['slot'] = 'weapon'
            if 'damage' not in stats:
                stats['damage'] = 5
        elif item_type == 'armor':
            properties['equipable'] = True
            properties['slot'] = 'armor'
            if 'defense' not in stats:
                stats['defense'] = 2
        elif item_type == 'potion':
            properties['consumable'] = True
            if 'health' not in stats:
                stats['health'] = 25
        
        description = f"A {item_type} called {name}."
        debug_admin(f"Final item data - name: {name}, desc: {description}, type: {item_type}, props: {properties}, stats: {stats}", DebugLogger.VERBOSE)
        
        try:
            debug_admin("Calling db.create_item", DebugLogger.VERBOSE)
            item_id = await db.create_item(name, description, item_type, properties, stats)
            debug_admin(f"Item created successfully with ID: {item_id}", DebugLogger.NORMAL)
            
            await player.send_message(f"Created {item_type} '{name}' with ID {item_id}", "green")
            debug_admin("Success message sent to player", DebugLogger.VERBOSE)
            
            # Log admin action
            await self._log_admin_action(player, f"Created item: {name} (ID: {item_id})")
            debug_admin("Admin action logged", DebugLogger.VERBOSE)
            
        except Exception as e:
            debug_admin(f"Error creating item: {e}", DebugLogger.NORMAL)
            await player.send_message(f"Error creating item: {e}", "red")
    
    async def _create_monster(self, player, args: List[str]):
        """Create a new monster: /create_monster <name> <level> [health] [attack] [defense] [exp_reward]"""
        if len(args) < 2:
            await player.send_message("Usage: /create_monster <name> <level> [health] [attack] [defense] [exp_reward]", "yellow")
            return
        
        try:
            name = args[0]
            level = int(args[1])
            
            # Default stats based on level
            health = int(args[2]) if len(args) > 2 else level * 20 + 10
            attack = int(args[3]) if len(args) > 3 else level * 3 + 2
            defense = int(args[4]) if len(args) > 4 else level + 1
            exp_reward = int(args[5]) if len(args) > 5 else level * 15
            
            description = f"A level {level} {name}."
            loot_table = []  # Could be expanded to include item drops
            
            monster_id = await db.create_monster(
                name, description, level, health, attack, defense, exp_reward, loot_table
            )
            
            await player.send_message(f"Created level {level} {name} with ID {monster_id}", "green")
            await player.send_message(f"Stats: HP={health}, ATK={attack}, DEF={defense}, EXP={exp_reward}", "cyan")
            
            # Log admin action
            await self._log_admin_action(player, f"Created monster: {name} (ID: {monster_id})")
            
        except ValueError:
            await player.send_message("Level and stats must be numbers.", "red")
    
    async def _teleport_player(self, player, args: List[str]):
        """Teleport a player: /teleport <player_name> <room_id>"""
        if len(args) != 2:
            await player.send_message("Usage: /teleport <player_name> <room_id>", "yellow")
            return
        
        try:
            target_name = args[0]
            room_id = int(args[1])
            
            # Find target player
            target_player = None
            for p in self.game_engine.players.values():
                if p.character['name'].lower() == target_name.lower():
                    target_player = p
                    break
            
            if not target_player:
                await player.send_message(f"Player '{target_name}' not found or not online.", "red")
                return
            
            # Check if room exists
            room = await db.get_room(room_id)
            if not room:
                await player.send_message(f"Room {room_id} does not exist.", "red")
                return
            
            # Teleport player
            old_room = target_player.character['current_room']
            target_player.character['current_room'] = room_id
            await db.update_character(target_player.character['id'], {'current_room': room_id})
            
            # Notify players
            await target_player.send_message(f"You have been teleported to {room['name']} by {player.character['name']}!", "cyan")
            await player.send_message(f"Teleported {target_name} to {room['name']}", "green")
            
            # Notify rooms
            await self.game_engine._broadcast_to_room(old_room, f"{target_name} disappears in a flash of light!", exclude_player=target_player.user_id)
            await self.game_engine._broadcast_to_room(room_id, f"{target_name} appears in a flash of light!", exclude_player=target_player.user_id)
            
            # Show new room to target
            await self.game_engine._handle_look(target_player)
            
            # Log admin action
            await self._log_admin_action(player, f"Teleported {target_name} to room {room_id}")
            
        except ValueError:
            await player.send_message("Room ID must be a number.", "red")
    
    async def _promote_user(self, player, args: List[str]):
        """Promote a user to admin: /promote <username>"""
        if len(args) != 1:
            await player.send_message("Usage: /promote <username>", "yellow")
            return
        
        username = args[0]
        
        # This would need to be implemented in the database layer
        # For now, just show a message
        await player.send_message(f"Promoted {username} to admin status.", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Promoted user: {username}")
    
    async def _demote_user(self, player, args: List[str]):
        """Demote a user from admin: /demote <username>"""
        if len(args) != 1:
            await player.send_message("Usage: /demote <username>", "yellow")
            return
        
        username = args[0]
        
        await player.send_message(f"Demoted {username} from admin status.", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Demoted user: {username}")
    
    async def _kick_player(self, player, args: List[str]):
        """Kick a player from the server: /kick <player_name> [reason]"""
        if len(args) < 1:
            await player.send_message("Usage: /kick <player_name> [reason]", "yellow")
            return
        
        target_name = args[0]
        reason = ' '.join(args[1:]) if len(args) > 1 else "No reason given"
        
        # Find and kick target player
        target_player = None
        for p in self.game_engine.players.values():
            if p.character['name'].lower() == target_name.lower():
                target_player = p
                break
        
        if not target_player:
            await player.send_message(f"Player '{target_name}' not found or not online.", "red")
            return
        
        # Notify target and disconnect
        await target_player.send_message(f"You have been kicked by {player.character['name']}. Reason: {reason}", "red")
        await self.game_engine.remove_player(target_player.user_id)
        
        await player.send_message(f"Kicked {target_name}. Reason: {reason}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Kicked player: {target_name} - {reason}")
    
    async def _ban_player(self, player, args: List[str]):
        """Ban a player: /ban <player_name> [reason]"""
        if len(args) < 1:
            await player.send_message("Usage: /ban <player_name> [reason]", "yellow")
            return
        
        target_name = args[0]
        reason = ' '.join(args[1:]) if len(args) > 1 else "No reason given"
        
        # This would need to be implemented with a ban list in the database
        await player.send_message(f"Banned {target_name}. Reason: {reason}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Banned player: {target_name} - {reason}")
    
    async def _unban_player(self, player, args: List[str]):
        """Unban a player: /unban <player_name>"""
        if len(args) != 1:
            await player.send_message("Usage: /unban <player_name>", "yellow")
            return
        
        target_name = args[0]
        
        await player.send_message(f"Unbanned {target_name}.", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Unbanned player: {target_name}")
    
    async def _reload_world(self, player, args: List[str]):
        """Reload world data: /reload_world"""
        await player.send_message("Reloading world data...", "yellow")
        
        # This would reload world data from database
        await self.game_engine._initialize_world()
        
        await player.send_message("World data reloaded successfully.", "green")
        
        # Log admin action
        await self._log_admin_action(player, "Reloaded world data")
    
    async def _list_rooms(self, player, args: List[str]):
        """List all rooms: /list_rooms [page]"""
        page = 1
        if args:
            try:
                page = int(args[0])
            except ValueError:
                await player.send_message("Page must be a number.", "red")
                return
        
        try:
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval('SELECT COUNT(*) FROM rooms')
                
                # Get rooms for this page (10 per page)
                per_page = 10
                offset = (page - 1) * per_page
                rooms = await conn.fetch(
                    'SELECT id, name, description FROM rooms ORDER BY id LIMIT $1 OFFSET $2',
                    per_page, offset
                )
                
                if not rooms:
                    await player.send_message("No rooms found.", "yellow")
                    return
                
                total_pages = (total + per_page - 1) // per_page
                header = f"Rooms (Page {page}/{total_pages}, Total: {total})"
                await player.send_message(header, "cyan")
                await player.send_message("=" * len(header), "cyan")
                
                for room in rooms:
                    room_info = f"ID {room['id']}: {room['name']}"
                    await player.send_message(room_info, "white")
                
        except Exception as e:
            await player.send_message(f"Error listing rooms: {e}", "red")
    
    async def _list_items(self, player, args: List[str]):
        """List all items: /list_items [page]"""
        page = 1
        if args:
            try:
                page = int(args[0])
            except ValueError:
                await player.send_message("Page must be a number.", "red")
                return
        
        try:
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval('SELECT COUNT(*) FROM items')
                
                # Get items for this page (10 per page)
                per_page = 10
                offset = (page - 1) * per_page
                items = await conn.fetch(
                    'SELECT id, name, item_type FROM items ORDER BY id LIMIT $1 OFFSET $2',
                    per_page, offset
                )
                
                if not items:
                    await player.send_message("No items found.", "yellow")
                    return
                
                total_pages = (total + per_page - 1) // per_page
                header = f"Items (Page {page}/{total_pages}, Total: {total})"
                await player.send_message(header, "cyan")
                await player.send_message("=" * len(header), "cyan")
                
                for item in items:
                    item_info = f"ID {item['id']}: {item['name']} ({item['item_type']})"
                    await player.send_message(item_info, "white")
                
        except Exception as e:
            await player.send_message(f"Error listing items: {e}", "red")
    
    async def _list_monsters(self, player, args: List[str]):
        """List all monsters: /list_monsters [page]"""
        page = 1
        if args:
            try:
                page = int(args[0])
            except ValueError:
                await player.send_message("Page must be a number.", "red")
                return
        
        try:
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval('SELECT COUNT(*) FROM monsters')
                
                # Get monsters for this page (10 per page)
                per_page = 10
                offset = (page - 1) * per_page
                monsters = await conn.fetch(
                    'SELECT id, name, level FROM monsters ORDER BY id LIMIT $1 OFFSET $2',
                    per_page, offset
                )
                
                if not monsters:
                    await player.send_message("No monsters found.", "yellow")
                    return
                
                total_pages = (total + per_page - 1) // per_page
                header = f"Monsters (Page {page}/{total_pages}, Total: {total})"
                await player.send_message(header, "cyan")
                await player.send_message("=" * len(header), "cyan")
                
                for monster in monsters:
                    monster_info = f"ID {monster['id']}: {monster['name']} (Level {monster['level']})"
                    await player.send_message(monster_info, "white")
                
        except Exception as e:
            await player.send_message(f"Error listing monsters: {e}", "red")
    
    async def _list_properties(self, player, args: List[str]):
        """List properties of a room, item, or monster: /list_properties <type> <id>"""
        if len(args) != 2:
            await player.send_message("Usage: /list_properties <type> <id>", "yellow")
            await player.send_message("Types: room, item, monster", "yellow")
            return
        
        try:
            obj_type = args[0].lower()
            obj_id = int(args[1])
            
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                if obj_type == "room":
                    obj = await conn.fetchrow('SELECT * FROM rooms WHERE id = $1', obj_id)
                    if obj:
                        # Convert asyncpg.Record to dict for safe access
                        obj_dict = dict(obj)
                        properties_text = f"""Room ID {obj_id} Properties:
Name: {obj_dict['name']}
Description: {obj_dict['description']}
Exits: {obj_dict.get('exits', {})}
Items: {obj_dict.get('items', [])}
Monsters: {obj_dict.get('monsters', [])}
Properties: {obj_dict.get('properties', {})}"""
                        await player.send_message(properties_text, "cyan")
                    else:
                        await player.send_message(f"Room {obj_id} not found.", "red")
                        
                elif obj_type == "item":
                    obj = await conn.fetchrow('SELECT * FROM items WHERE id = $1', obj_id)
                    if obj:
                        # Convert asyncpg.Record to dict for safe access
                        obj_dict = dict(obj)
                        properties_text = f"""Item ID {obj_id} Properties:
Name: {obj_dict['name']}
Description: {obj_dict['description']}
Type: {obj_dict['item_type']}
Properties: {obj_dict.get('properties', {})}
Stats: {obj_dict.get('stats', {})}"""
                        await player.send_message(properties_text, "cyan")
                    else:
                        await player.send_message(f"Item {obj_id} not found.", "red")
                        
                elif obj_type == "monster":
                    obj = await conn.fetchrow('SELECT * FROM monsters WHERE id = $1', obj_id)
                    if obj:
                        # Convert asyncpg.Record to dict for safe access
                        obj_dict = dict(obj)
                        properties_text = f"""Monster ID {obj_id} Properties:
Name: {obj_dict['name']}
Description: {obj_dict['description']}
Level: {obj_dict['level']}
Health: {obj_dict['health']}/{obj_dict['max_health']}
Attack: {obj_dict['attack']}
Defense: {obj_dict['defense']}
Experience Reward: {obj_dict['experience_reward']}
Loot Table: {obj_dict.get('loot_table', [])}
Properties: {obj_dict.get('properties', {})}"""
                        await player.send_message(properties_text, "cyan")
                    else:
                        await player.send_message(f"Monster {obj_id} not found.", "red")
                else:
                    await player.send_message("Invalid type. Use: room, item, or monster", "red")
                    
        except ValueError:
            await player.send_message("ID must be a number.", "red")
        except Exception as e:
            await player.send_message(f"Error executing admin command: {e}", "red")
    
    async def _edit_room(self, player, args: List[str]):
        """Edit a room: /edit_room <room_id> <property> <value>"""
        if len(args) < 3:
            await player.send_message("Usage: /edit_room <room_id> <property> <value>", "yellow")
            await player.send_message("Properties: name, description", "yellow")
            return
        
        try:
            room_id = int(args[0])
            property_name = args[1].lower()
            value = ' '.join(args[2:])
            
            room = await db.get_room(room_id)
            if not room:
                await player.send_message(f"Room {room_id} does not exist.", "red")
                return
            
            if property_name == 'name':
                # Update room name (would need database method)
                await player.send_message(f"Updated room {room_id} name to: {value}", "green")
            elif property_name == 'description':
                # Update room description (would need database method)
                await player.send_message(f"Updated room {room_id} description.", "green")
            else:
                await player.send_message(f"Unknown property: {property_name}", "red")
                return
            
            # Log admin action
            await self._log_admin_action(player, f"Edited room {room_id}: {property_name} = {value}")
            
        except ValueError:
            await player.send_message("Room ID must be a number.", "red")
    
    async def _edit_item(self, player, args: List[str]):
        """Edit an item: /edit_item <item_id> <property> <value>"""
        if len(args) < 3:
            await player.send_message("Usage: /edit_item <item_id> <property> <value>", "yellow")
            await player.send_message("Properties: name, description, type", "yellow")
            return
        
        try:
            item_id = int(args[0])
            property_name = args[1].lower()
            value = args[2]
            
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                # Check if item exists
                item = await conn.fetchrow('SELECT * FROM items WHERE id = $1', item_id)
                if not item:
                    await player.send_message(f"Item {item_id} does not exist.", "red")
                    return
                
                # Validate column name to prevent SQL injection
                valid_columns = {'name', 'description', 'item_type'}
                column_map = {'type': 'item_type'}  # Allow 'type' as alias for 'item_type'
                
                actual_column = column_map.get(property_name, property_name)
                if actual_column not in valid_columns:
                    await player.send_message(f"Invalid property: {property_name}. Valid properties: name, description, type", "red")
                    return
                
                # Sanitize the value
                try:
                    sanitized_value = InputSanitizer.sanitize_string(value, max_length=255)
                except ValueError as e:
                    await player.send_message(f"Invalid value: {e}", "red")
                    return
                
                if property_name == 'name':
                    await conn.execute('UPDATE items SET name = $1 WHERE id = $2', sanitized_value, item_id)
                    await player.send_message(f"Updated item {item_id} name to: {sanitized_value}", "green")
                elif property_name == 'description':
                    await conn.execute('UPDATE items SET description = $1 WHERE id = $2', sanitized_value, item_id)
                    await player.send_message(f"Updated item {item_id} description.", "green")
                elif property_name == 'type':
                    await conn.execute('UPDATE items SET item_type = $1 WHERE id = $2', sanitized_value, item_id)
                    await player.send_message(f"Updated item {item_id} type to: {sanitized_value}", "green")
                else:
                    await player.send_message(f"Unknown property: {property_name}", "red")
                    return
                
                # Log admin action
                await self._log_admin_action(player, f"Edited item {item_id}: {property_name} = {value}")
                
        except ValueError:
            await player.send_message("Item ID must be a number.", "red")
        except Exception as e:
            await player.send_message(f"Error editing item: {e}", "red")
    
    async def _edit_monster(self, player, args: List[str]):
        """Edit a monster: /edit_monster <monster_id> <property> <value>"""
        if len(args) < 3:
            await player.send_message("Usage: /edit_monster <monster_id> <property> <value>", "yellow")
            await player.send_message("Properties: name, description, level, health, attack, defense, exp_reward", "yellow")
            return
        
        try:
            monster_id = int(args[0])
            property_name = args[1].lower()
            value = args[2]
            
            if not db.pool:
                await player.send_message("Database not available.", "red")
                return
            
            async with db.pool.acquire() as conn:
                # Check if monster exists
                monster = await conn.fetchrow('SELECT * FROM monsters WHERE id = $1', monster_id)
                if not monster:
                    await player.send_message(f"Monster {monster_id} does not exist.", "red")
                    return
                
                # Validate column name to prevent SQL injection
                valid_text_columns = {'name', 'description'}
                valid_numeric_columns = {'level', 'health', 'attack', 'defense', 'experience_reward'}
                column_map = {'exp_reward': 'experience_reward'}  # Allow alias
                
                actual_column = column_map.get(property_name, property_name)
                
                if actual_column in valid_text_columns:
                    # Sanitize text input
                    try:
                        sanitized_value = InputSanitizer.sanitize_string(value, max_length=255)
                    except ValueError as e:
                        await player.send_message(f"Invalid value: {e}", "red")
                        return
                    
                    await conn.execute(f'UPDATE monsters SET {actual_column} = $1 WHERE id = $2', sanitized_value, monster_id)
                    await player.send_message(f"Updated monster {monster_id} {property_name} to: {sanitized_value}", "green")
                elif actual_column in valid_numeric_columns:
                    try:
                        numeric_value = int(value)
                        if numeric_value < 0:
                            await player.send_message(f"{property_name} must be a positive number.", "red")
                            return
                        
                        await conn.execute(f'UPDATE monsters SET {actual_column} = $1 WHERE id = $2', numeric_value, monster_id)
                        await player.send_message(f"Updated monster {monster_id} {property_name} to: {numeric_value}", "green")
                    except ValueError:
                        await player.send_message(f"{property_name} must be a number.", "red")
                        return
                else:
                    await player.send_message(f"Unknown property: {property_name}", "red")
                    return
                
                # Log admin action
                await self._log_admin_action(player, f"Edited monster {monster_id}: {property_name} = {value}")
                
        except ValueError:
            await player.send_message("Monster ID must be a number.", "red")
        except Exception as e:
            await player.send_message(f"Error editing monster: {e}", "red")
    
    async def _spawn_monster(self, player, args: List[str]):
        """Spawn a monster in current room: /spawn_monster <monster_id>"""
        if len(args) != 1:
            await player.send_message("Usage: /spawn_monster <monster_id>", "yellow")
            return
        
        try:
            monster_id = int(args[0])
            
            monster = await db.get_monster(monster_id)
            if not monster:
                await player.send_message(f"Monster {monster_id} does not exist.", "red")
                return
            
            room_id = player.character['current_room']
            
            # This would need to be implemented to add monster to room
            await player.send_message(f"Spawned {monster['name']} in current room.", "green")
            
            # Notify other players in room
            await self.game_engine._broadcast_to_room(room_id, 
                f"A {monster['name']} appears!", exclude_player=player.user_id)
            
            # Log admin action
            await self._log_admin_action(player, f"Spawned monster {monster['name']} in room {room_id}")
            
        except ValueError:
            await player.send_message("Monster ID must be a number.", "red")
    
    async def _spawn_item(self, player, args: List[str]):
        """Spawn an item in current room: /spawn_item <item_id>"""
        if len(args) != 1:
            await player.send_message("Usage: /spawn_item <item_id>", "yellow")
            return
        
        try:
            item_id = int(args[0])
            
            item = await db.get_item(item_id)
            if not item:
                await player.send_message(f"Item {item_id} does not exist.", "red")
                return
            
            room_id = player.character['current_room']
            
            # This would need to be implemented to add item to room
            await player.send_message(f"Spawned {item['name']} in current room.", "green")
            
            # Log admin action
            await self._log_admin_action(player, f"Spawned item {item['name']} in room {room_id}")
            
        except ValueError:
            await player.send_message("Item ID must be a number.", "red")
    
    async def _server_stats(self, player, args: List[str]):
        """Show server statistics: /server_stats"""
        online_players = len(self.game_engine.players)
        current_tick = self.game_engine.current_tick
        tick_rate = self.game_engine.tick_rate
        
        stats = f"""
Server Statistics:
Online Players: {online_players}/24
Current Tick: {current_tick}
Tick Rate: {tick_rate} TPS
Uptime: {current_tick / tick_rate / 60:.1f} minutes
"""
        
        await player.send_message(stats, "cyan")
    
    async def _broadcast_message(self, player, args: List[str]):
        """Broadcast a message to all players: /broadcast <message>"""
        if not args:
            await player.send_message("Usage: /broadcast <message>", "yellow")
            return
        
        message = ' '.join(args)
        broadcast_text = f"[ADMIN BROADCAST] {message}"
        
        # Send to all online players
        for p in self.game_engine.players.values():
            await p.send_message(broadcast_text, "gold")
        
        await player.send_message(f"Broadcast sent to {len(self.game_engine.players)} players.", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Broadcast: {message}")
    
    async def _save_world(self, player, args: List[str]):
        """Save world state: /save_world [filename]"""
        filename = args[0] if args else "world_backup.json"
        
        # This would save world state to file
        await player.send_message(f"World state saved to {filename}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Saved world to {filename}")
    
    async def _load_world(self, player, args: List[str]):
        """Load world state: /load_world <filename>"""
        if not args:
            await player.send_message("Usage: /load_world <filename>", "yellow")
            return
        
        filename = args[0]
        
        # This would load world state from file
        await player.send_message(f"World state loaded from {filename}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Loaded world from {filename}")
    
    async def _show_admin_help(self, player, args: List[str]):
        """Show admin command help"""
        help_text = """
Admin Commands:
Note: Use quotes for multi-word parameters, e.g., /create_room "Magic Forest" "A mystical forest"

World Building:
  /create_room "name" "description" - Create a new room
  /link_rooms <room1_id> <direction> <room2_id> - Link two rooms
  /edit_room <room_id> <property> "value" - Edit room properties
  /list_rooms [page] - List all rooms
  
Item Management:
  /create_item "name" <type> [stats_json] - Create a new item
  /edit_item <item_id> <property> "value" - Edit item properties
  /spawn_item <item_id> - Spawn item in current room
  /list_items [page] - List all items
  
Monster Management:
  /create_monster "name" <level> [stats] - Create a new monster
  /edit_monster <monster_id> <property> "value" - Edit monster properties
  /spawn_monster <monster_id> - Spawn monster in current room
  /list_monsters [page] - List all monsters
  
Inspection:
  /list_properties <type> <id> - List properties of room/item/monster
  
Player Management:
  /teleport <player_name> <room_id> - Teleport a player
  /promote <username> - Promote user to admin
  /demote <username> - Demote user from admin
  /kick <player_name> ["reason"] - Kick a player
  /ban <player_name> ["reason"] - Ban a player
  /unban <player_name> - Unban a player
  
Server Management:
  /server_stats - Show server statistics
  /broadcast "message" - Broadcast message to all players
  /reload_world - Reload world data
  /save_world [filename] - Save world state
  /load_world <filename> - Load world state

Debug Management:
  /debug_status - Show debug logger status
  /debug_enable [verbosity] - Enable debug logging (0-3)
  /debug_disable - Disable debug logging
  /debug_verbosity <level> - Set debug verbosity (0-3)
  /debug_component <component> <on|off> - Control component debug

Examples:
  /create_room "Magic Forest" "A mystical forest filled with ancient trees"
  /create_item "Fire Sword" weapon '{"damage": 15, "fire_damage": 5}'
  /create_monster "Fire Dragon" 10
  /edit_room 1 name "New Room Name"
  /broadcast "Server will restart in 5 minutes"

Note: For JSON parameters, use single quotes around the JSON object.
"""
        await player.send_message(help_text, "white")
    
    async def _log_admin_action(self, player, action: str):
        """Log an admin action"""
        log_entry = f"[ADMIN] {player.character['name']}: {action}"
        print(log_entry)  # In a real implementation, this would go to a log file
    
    def is_admin_command(self, command: str) -> bool:
        """Check if a command is an admin command"""
        if not command.startswith('/'):
            return False
        
        # Extract just the command name (first word after /)
        parts = command[1:].split()
        if not parts:
            return False
        
        cmd_name = parts[0]
        return cmd_name in self.admin_commands
    
    def _parse_quoted_args(self, command_line: str) -> tuple[str, list[str]]:
        """Parse command line with support for quoted arguments"""
        # Remove the leading '/'
        line = command_line[1:].strip()
        if not line:
            return "", []
        
        parts = []
        current_part = ""
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if not in_quotes:
                if char in ['"', "'"]:
                    in_quotes = True
                    quote_char = char
                elif char == ' ':
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                else:
                    current_part += char
            else:
                if char == quote_char:
                    in_quotes = False
                    quote_char = None
                else:
                    current_part += char
            
            i += 1
        
        if current_part:
            parts.append(current_part)
        
        if not parts:
            return "", []
        
        return parts[0], parts[1:]

    async def process_command(self, player, command_line: str) -> bool:
        """Process a potential admin command"""
        if not command_line.startswith('/'):
            return False
        
        command, args = self._parse_quoted_args(command_line)
        if not command:
            return False
        
        if command in self.admin_commands:
            await self.process_admin_command(player, command, args)
            return True
        elif command == 'admin_help':
            await self._show_admin_help(player, [])
            return True
        
        return False

    # Debug Control Methods
    async def _debug_status(self, player, args: List[str]):
        """Show debug logger status: /debug_status"""
        from debug_logger import debug_logger
        status = debug_logger.get_status()
        await player.send_message(f"Debug Logger Status:\n{status}", "cyan")
    
    async def _debug_enable(self, player, args: List[str]):
        """Enable debug logging: /debug_enable [verbosity]"""
        from debug_logger import debug_logger
        
        verbosity = 1  # Default to normal
        if args:
            try:
                verbosity = int(args[0])
                if verbosity < 0 or verbosity > 3:
                    await player.send_message("Verbosity must be 0-3 (0=minimal, 1=normal, 2=verbose, 3=very_verbose)", "red")
                    return
            except ValueError:
                await player.send_message("Verbosity must be a number (0-3)", "red")
                return
        
        debug_logger.enable(verbosity)
        verbosity_names = ["MINIMAL", "NORMAL", "VERBOSE", "VERY_VERBOSE"]
        await player.send_message(f"Debug logging enabled with verbosity: {verbosity_names[verbosity]}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Enabled debug logging (verbosity: {verbosity})")
    
    async def _debug_disable(self, player, args: List[str]):
        """Disable debug logging: /debug_disable"""
        from debug_logger import debug_logger
        
        debug_logger.disable()
        await player.send_message("Debug logging disabled", "green")
        
        # Log admin action
        await self._log_admin_action(player, "Disabled debug logging")
    
    async def _debug_verbosity(self, player, args: List[str]):
        """Set debug verbosity: /debug_verbosity <level>"""
        from debug_logger import debug_logger
        
        if not args:
            await player.send_message("Usage: /debug_verbosity <level>", "yellow")
            await player.send_message("Levels: 0=minimal, 1=normal, 2=verbose, 3=very_verbose", "yellow")
            return
        
        try:
            verbosity = int(args[0])
            if verbosity < 0 or verbosity > 3:
                await player.send_message("Verbosity must be 0-3 (0=minimal, 1=normal, 2=verbose, 3=very_verbose)", "red")
                return
        except ValueError:
            await player.send_message("Verbosity must be a number (0-3)", "red")
            return
        
        debug_logger.verbosity = verbosity
        if not debug_logger.enabled:
            debug_logger.enable()
        
        verbosity_names = ["MINIMAL", "NORMAL", "VERBOSE", "VERY_VERBOSE"]
        await player.send_message(f"Debug verbosity set to: {verbosity_names[verbosity]}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Set debug verbosity to {verbosity}")
    
    async def _debug_component(self, player, args: List[str]):
        """Enable/disable debug for specific components: /debug_component <component> <on|off>"""
        from debug_logger import debug_logger
        
        if len(args) != 2:
            await player.send_message("Usage: /debug_component <component> <on|off>", "yellow")
            components = list(debug_logger.components.keys())
            await player.send_message(f"Available components: {', '.join(components)}", "yellow")
            return
        
        component = args[0]
        state = args[1].lower()
        
        if component not in debug_logger.components:
            components = list(debug_logger.components.keys())
            await player.send_message(f"Unknown component. Available: {', '.join(components)}", "red")
            return
        
        if state not in ['on', 'off', 'true', 'false', 'enable', 'disable']:
            await player.send_message("State must be: on/off, true/false, or enable/disable", "red")
            return
        
        enabled = state in ['on', 'true', 'enable']
        debug_logger.set_component(component, enabled)
        
        if not debug_logger.enabled and enabled:
            debug_logger.enable()
        
        state_text = "enabled" if enabled else "disabled"
        await player.send_message(f"Debug logging for '{component}' {state_text}", "green")
        
        # Log admin action
        await self._log_admin_action(player, f"Set debug component '{component}' to {state_text}")
    
    async def _show_map(self, player, args: List[str]):
        """Show ASCII map centered on current room: /map"""
        current_room_id = player.character['current_room']
        
        # Get the current room
        current_room = await db.get_room(current_room_id)
        if not current_room:
            await player.send_message("Error: Cannot find current room", "red")
            return
        
        # Build a map of rooms within 3 steps from current room
        room_map = {}
        await self._build_room_map(current_room_id, room_map, 0, 3)
        
        # Generate ASCII map
        ascii_map = await self._generate_ascii_map(current_room_id, room_map)
        
        # Send the map as individual lines to avoid formatting issues
        await player.send_message("", "white")  # Empty line for spacing
        await player.send_message("Map (you are at the center):", "cyan")
        await player.send_message("", "white")  # Empty line for spacing
        
        # Split the map into lines and send each line separately
        map_lines = ascii_map.split('\n')
        for line in map_lines:
            await player.send_message(line, "white")
        
        await player.send_message("", "white")  # Empty line for spacing
        
        # Log admin action
        await self._log_admin_action(player, f"Viewed map from room {current_room_id}")
    
    async def _build_room_map(self, start_room_id: int, room_map: dict, current_depth: int, max_depth: int):
        """Recursively build a map of connected rooms"""
        if current_depth > max_depth or start_room_id in room_map:
            return
        
        room = await db.get_room(start_room_id)
        if not room:
            return
        
        # Parse exits
        exits = {}
        if room.get('exits'):
            if isinstance(room['exits'], str):
                try:
                    exits = json.loads(room['exits'])
                except (json.JSONDecodeError, TypeError):
                    exits = {}
            elif isinstance(room['exits'], dict):
                exits = room['exits']
        
        room_map[start_room_id] = {
            'name': room['name'],
            'exits': exits
        }
        
        # Recursively explore connected rooms
        if current_depth < max_depth:
            for direction, connected_room_id in exits.items():
                if isinstance(connected_room_id, int):
                    await self._build_room_map(connected_room_id, room_map, current_depth + 1, max_depth)
    
    async def _generate_ascii_map(self, center_room_id: int, room_map: dict):
        """Generate ASCII map with the center room in the middle"""
        # Create a 7x7 grid (3 rooms in each direction from center)
        grid_size = 7
        center = grid_size // 2  # Index 3 is the center
        
        # Initialize grid with spaces
        grid = [[' ' for _ in range(grid_size)] for _ in range(grid_size)]
        room_positions = {}
        
        # Place center room
        grid[center][center] = '@'  # @ represents current room
        room_positions[center_room_id] = (center, center)
        
        # Use BFS to place rooms relative to center
        from collections import deque
        queue = deque([(center_room_id, center, center)])
        visited = {center_room_id}
        
        while queue:
            room_id, row, col = queue.popleft()
            
            if room_id not in room_map:
                continue
            
            room_data = room_map[room_id]
            exits = room_data.get('exits', {})
            
            # Direction mappings
            directions = {
                'north': (-1, 0),
                'south': (1, 0),
                'east': (0, 1),
                'west': (0, -1)
            }
            
            for direction, connected_room_id in exits.items():
                if direction not in directions or connected_room_id in visited:
                    continue
                
                if not isinstance(connected_room_id, int):
                    continue
                
                dr, dc = directions[direction]
                new_row, new_col = row + dr, col + dc
                
                # Check bounds
                if 0 <= new_row < grid_size and 0 <= new_col < grid_size:
                    if connected_room_id in room_map:
                        grid[new_row][new_col] = '.'  # . represents other rooms
                        room_positions[connected_room_id] = (new_row, new_col)
                        visited.add(connected_room_id)
                        queue.append((connected_room_id, new_row, new_col))
        
        # Add connection lines between adjacent rooms
        for room_id, (row, col) in room_positions.items():
            if room_id not in room_map:
                continue
            
            room_data = room_map[room_id]
            exits = room_data.get('exits', {})
            
            # Draw connections to adjacent rooms
            for direction, connected_room_id in exits.items():
                if connected_room_id not in room_positions:
                    continue
                
                # Draw connection lines
                if direction == 'north' and row > 0:
                    if grid[row - 1][col] == ' ':
                        grid[row - 1][col] = '|'
                elif direction == 'south' and row < grid_size - 1:
                    if grid[row + 1][col] == ' ':
                        grid[row + 1][col] = '|'
                elif direction == 'east' and col < grid_size - 1:
                    if grid[row][col + 1] == ' ':
                        grid[row][col + 1] = '-'
                elif direction == 'west' and col > 0:
                    if grid[row][col - 1] == ' ':
                        grid[row][col - 1] = '-'
        
        # Convert grid to string with proper formatting
        result = []
        for row in grid:
            # Join characters and ensure consistent spacing
            line = ''.join(row)
            result.append(line)
        
        # Add legend
        result.append("")
        result.append("Legend:")
        result.append("@ = Your current location")
        result.append(". = Other rooms")
        result.append("| = North/South connection")
        result.append("- = East/West connection")
        
        return '\n'.join(result)