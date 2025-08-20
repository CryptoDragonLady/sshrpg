import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from input_sanitizer import InputSanitizer

@dataclass
class CombatState:
    """Represents an active combat session"""
    player_id: int
    monster_instance_id: int
    room_id: int
    rounds: int = 0
    last_action_tick: int = 0
    player_can_flee: bool = True

class ActionType(Enum):
    MOVE = "move"
    ATTACK = "attack"
    USE_ITEM = "use_item"
    CAST_SPELL = "cast_spell"
    REST = "rest"
    LOOK = "look"
    SAY = "say"

@dataclass
class Action:
    player_id: int
    action_type: ActionType
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    tick_delay: int = 1  # How many ticks this action takes
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class GameEvent:
    event_type: str
    data: Dict[str, Any]
    recipients: Optional[List[int]] = None  # Player IDs to send to, None = all
    
    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []

class Player:
    def __init__(self, user_id: int, character_data: Dict, connection):
        self.user_id = user_id
        self.character = character_data
        self.connection = connection
        self.pending_actions = []
        self.action_cooldown = 0
        self.last_activity = time.time()
        self.is_online = True
        
    def add_action(self, action: Action):
        """Add an action to the player's queue"""
        if self.action_cooldown <= 0:
            self.pending_actions.append(action)
            self.action_cooldown = action.tick_delay
            return True
        return False
    
    def update_cooldown(self):
        """Decrease action cooldown"""
        if self.action_cooldown > 0:
            self.action_cooldown -= 1
    
    async def send_message(self, message: str, color: str = "white"):
        """Send a message to the player"""
        if self.connection and self.is_online:
            try:
                await self.connection.send_message(message, color)
            except Exception as e:
                print(f"DEBUG: Player {self.user_id} send_message failed: {e}, setting is_online=False")
                self.is_online = False

class GameEngine:
    def __init__(self, database):
        self.db = database
        self.players: Dict[int, Player] = {}
        self.tick_rate = 2.0  # Ticks per second
        self.current_tick = 0
        self.running = False
        self.event_queue = []
        
        # Game world state
        self.room_instances = {}  # Runtime room state
        self.monster_instances = {}  # Active monsters
        self.combat_sessions: Dict[int, CombatState] = {}  # Active combat sessions (player_id -> CombatState)
        
    async def start(self):
        """Start the game engine"""
        self.running = True
        print(f"Game engine started with tick rate: {self.tick_rate} TPS")
        
        # Initialize default world
        await self._initialize_world()
        
        # Start the main game loop
        asyncio.create_task(self._game_loop())
    
    async def stop(self):
        """Stop the game engine"""
        self.running = False
        print("Game engine stopped")
    
    async def _game_loop(self):
        """Main game loop running on ticks"""
        while self.running:
            start_time = time.time()
            
            # Process tick
            await self._process_tick()
            
            # Calculate sleep time to maintain tick rate
            elapsed = time.time() - start_time
            sleep_time = max(0, (1.0 / self.tick_rate) - elapsed)
            await asyncio.sleep(sleep_time)
    
    async def _process_tick(self):
        """Process a single game tick"""
        self.current_tick += 1
        
        # Update player cooldowns
        for player in self.players.values():
            player.update_cooldown()
        
        # Process pending actions
        await self._process_actions()
        
        # Update monsters and NPCs
        await self._update_monsters()
        
        # Process combat
        await self._process_combat()
        
        # Clean up disconnected players
        await self._cleanup_players()
        
        # Process events
        await self._process_events()
    
    async def _process_actions(self):
        """Process all pending player actions"""
        for player in self.players.values():
            if player.pending_actions and player.action_cooldown <= 0:
                action = player.pending_actions.pop(0)
                await self._execute_action(player, action)
    
    async def _execute_action(self, player: Player, action: Action):
        """Execute a specific player action"""
        try:
            # Debug logging
            print(f"DEBUG: Executing action {action.action_type}, target: {action.target}, target type: {type(action.target)}, parameters type: {type(action.parameters)}, value: {action.parameters}")
            
            if action.action_type == ActionType.MOVE:
                if action.target:
                    await self._handle_move(player, action.target)
                else:
                    await player.send_message("Move where?", "yellow")
            elif action.action_type == ActionType.ATTACK:
                print(f"DEBUG: About to call _handle_attack with target: {action.target}")
                if action.target:
                    await self._handle_attack(player, action.target)
                else:
                    await player.send_message("Attack what?", "yellow")
            elif action.action_type == ActionType.USE_ITEM:
                if action.target:
                    await self._handle_use_item(player, action.target)
                else:
                    await player.send_message("Use what?", "yellow")
            elif action.action_type == ActionType.LOOK:
                await self._handle_look(player)
            elif action.action_type == ActionType.SAY:
                message = action.parameters.get('message', '') if action.parameters else ''
                await self._handle_say(player, message)
            elif action.action_type == ActionType.REST:
                await self._handle_rest(player)
        except Exception as e:
            print(f"DEBUG: Error in _execute_action: {e}, action type: {action.action_type}, target: {action.target}, parameters: {action.parameters}")
            await player.send_message(f"Error executing action: {e}", "red")
    
    async def _handle_move(self, player: Player, direction: str):
        """Handle player movement"""
        current_room_id = player.character['current_room']
        
        # Check if player is in combat
        if player.user_id in self.combat_sessions:
            combat = self.combat_sessions[player.user_id]
            if not combat.player_can_flee:
                await player.send_message("You cannot flee from combat right now!", "red")
                return
            
            # Attempt to flee from combat
            flee_chance = 0.7  # 70% chance to successfully flee
            if random.random() > flee_chance:
                await player.send_message("You failed to escape from combat!", "yellow")
                return
            
            await player.send_message("You successfully flee from combat!", "green")
            await self._broadcast_to_room(current_room_id, 
                f"{player.character['name']} flees from combat!", 
                exclude_player=player.user_id)
        
        room = await self.db.get_room(current_room_id)
        
        if not room:
            await player.send_message("You are in an invalid location!", "red")
            return
        
        exits = room.get('exits', {})
        # Handle case where exits might be a JSON string from PostgreSQL
        if isinstance(exits, str):
            try:
                exits = json.loads(exits)
            except (json.JSONDecodeError, TypeError):
                exits = {}
        
        if direction not in exits:
            await player.send_message(f"You cannot go {direction} from here.", "yellow")
            return
        
        new_room_id = exits[direction]
        new_room = await self.db.get_room(new_room_id)
        
        if not new_room:
            await player.send_message("That exit leads nowhere!", "red")
            return
        
        # Handle monster following if player was in combat
        following_monster = None
        if player.user_id in self.combat_sessions:
            combat = self.combat_sessions[player.user_id]
            # Get the monster instance
            room_monsters = await self.db.get_room_monsters(current_room_id)
            for monster_instance in room_monsters:
                if monster_instance['id'] == combat.monster_instance_id:
                    following_monster = monster_instance
                    break
        
        # Update character location
        player.character['current_room'] = new_room_id
        await self.db.update_character(player.character['id'], {'current_room': new_room_id})
        
        # Notify players in old room
        await self._broadcast_to_room(current_room_id, 
            f"{player.character['name']} leaves {direction}.", 
            exclude_player=player.user_id)
        
        # Move following monster if any
        if following_monster:
            # Move monster to new room
            await self.db.update_room_monster_room(following_monster['id'], new_room_id)
            
            # Update combat session room
            if player.user_id in self.combat_sessions:
                self.combat_sessions[player.user_id].room_id = new_room_id
            
            await self._broadcast_to_room(current_room_id, 
                f"{following_monster.get('name', 'Monster')} follows {player.character['name']}!", 
                exclude_player=player.user_id)
        
        # Notify players in new room
        await self._broadcast_to_room(new_room_id, 
            f"{player.character['name']} arrives.", 
            exclude_player=player.user_id)
        
        if following_monster:
            await self._broadcast_to_room(new_room_id, 
                f"{following_monster.get('name', 'Monster')} follows {player.character['name']} into the room!", 
                exclude_player=player.user_id)
        
        # Show new room to player
        await self._handle_look(player)
        
        # Send prompt after room description for movement commands
        await self.send_status_prompt(player)
    
    async def _find_target_monster(self, room_monsters: List[Dict], target_name: str) -> Optional[Dict]:
        """Find a monster using intelligent matching"""
        target_name_lower = target_name.lower().strip()
        
        # First pass: exact match (case insensitive)
        for monster_instance in room_monsters:
            monster = await self.db.get_monster(monster_instance['monster_id'])
            if monster and monster['name'].lower() == target_name_lower:
                return self._prepare_monster_instance(monster_instance, monster)
        
        # Second pass: partial match (case insensitive)
        matches = []
        for monster_instance in room_monsters:
            monster = await self.db.get_monster(monster_instance['monster_id'])
            if monster:
                monster_name_lower = monster['name'].lower()
                # Check if target is a substring of monster name or vice versa
                if target_name_lower in monster_name_lower or any(word in monster_name_lower for word in target_name_lower.split()):
                    matches.append(self._prepare_monster_instance(monster_instance, monster))
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return the first one but suggest alternatives
            return matches[0]
        
        return None
    
    def _prepare_monster_instance(self, monster_instance: Dict, monster: Dict) -> Dict:
        """Prepare monster instance with full monster data"""
        monster_instance['name'] = monster['name']
        monster_instance['attack'] = monster['attack']
        monster_instance['defense'] = monster['defense']
        monster_instance['experience_reward'] = monster['experience_reward']
        monster_instance['loot_table'] = monster['loot_table']
        return monster_instance
    
    async def _handle_attack(self, player: Player, target_name: str):
        """Handle player attacking a monster"""
        room_id = player.character['current_room']
        
        # Check if room is a safe zone
        room = await self.db.get_room(room_id)
        if room:
            properties = room.get('properties', {})
            # Handle case where properties might be a JSON string from PostgreSQL
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except (json.JSONDecodeError, TypeError):
                    properties = {}
            
            if properties.get('safe_zone', False):
                await player.send_message("You cannot attack in this sacred place!", "yellow")
                return
        
        # Find monster instance in room using intelligent matching
        room_monsters = await self.db.get_room_monsters(room_id)
        target_monster_instance = await self._find_target_monster(room_monsters, target_name)
        
        if not target_monster_instance:
            # Suggest available targets if no match found
            if room_monsters:
                available_monsters = []
                for monster_instance in room_monsters:
                    monster = await self.db.get_monster(monster_instance['monster_id'])
                    if monster:
                        available_monsters.append(monster['name'])
                
                if available_monsters:
                    await player.send_message(f"There is no '{target_name}' here to attack. Available targets: {', '.join(available_monsters)}", "yellow")
                else:
                    await player.send_message(f"There is no {target_name} here to attack.", "yellow")
            else:
                await player.send_message(f"There is no {target_name} here to attack.", "yellow")
            return
        
        # Create or update combat session
        if player.user_id not in self.combat_sessions:
            self.combat_sessions[player.user_id] = CombatState(
                player_id=player.user_id,
                monster_instance_id=target_monster_instance['id'],
                room_id=room_id,
                last_action_tick=self.current_tick
            )
            await player.send_message("You enter combat!", "red")
            await self._broadcast_to_room(room_id, 
                f"{player.character['name']} enters combat with {target_monster_instance['name']}!", 
                exclude_player=player.user_id)
        else:
            # Update last action tick
            self.combat_sessions[player.user_id].last_action_tick = self.current_tick
        
        # Perform the attack
        print(f"DEBUG: About to call _player_attack")
        await self._player_attack(player, target_monster_instance, room_id)
        print(f"DEBUG: _player_attack completed")
    
    async def _player_attack(self, player: Player, monster: Dict, room_id: int):
        """Handle player attacking a monster"""
        # Calculate damage
        player_attack = player.character.get('strength', 10) + random.randint(1, 6)
        monster_defense = monster.get('defense', 0)
        damage = max(1, player_attack - monster_defense)
        
        # Apply damage to monster instance
        new_health = monster['health'] - damage
        await self.db.update_room_monster_health(monster['id'], new_health)
        monster['health'] = new_health
        
        await player.send_message(f"You attack {monster['name']} for {damage} damage!", "green")
        await self._broadcast_to_room(room_id, 
            f"{player.character['name']} attacks {monster['name']}!", 
            exclude_player=player.user_id)
        
        # Check if monster dies
        if monster['health'] <= 0:
            await self._handle_monster_death(player, monster, room_id)
            # End combat session
            if player.user_id in self.combat_sessions:
                del self.combat_sessions[player.user_id]
                await player.send_message("Combat ends!", "green")
    
    async def _handle_monster_death(self, player: Player, monster: Dict, room_id: int):
        """Handle monster death and rewards"""
        exp_reward = monster.get('experience_reward', 10)
        player.character['experience'] += exp_reward
        
        await player.send_message(f"{monster['name']} dies! You gain {exp_reward} experience.", "cyan")
        await self._broadcast_to_room(room_id, 
            f"{monster['name']} dies!", 
            exclude_player=player.user_id)
        
        # Check for level up
        await self._check_level_up(player)
        
        # Handle loot drops (simplified for now)
        loot_table = monster.get('loot_table', {})
        if loot_table:
            # Simple loot drop logic - could be expanded
            await player.send_message(f"You find some loot from {monster['name']}!", "yellow")
        
        # Remove monster instance from room
        await self.db.remove_room_monster(monster['id'])
    
    async def _monster_attack(self, monster: Dict, player: Player, room_id: int):
        """Handle monster attacking player"""
        monster_attack = monster.get('attack', 5) + random.randint(1, 4)
        player_defense = player.character.get('constitution', 10) // 2
        damage = max(1, monster_attack - player_defense)
        
        player.character['health'] -= damage
        
        await player.send_message(f"{monster['name']} attacks you for {damage} damage!", "red")
        await self._broadcast_to_room(room_id, 
            f"{monster['name']} attacks {player.character['name']}!", 
            exclude_player=player.user_id)
        
        # Check if player dies
        if player.character['health'] <= 0:
            await self._handle_player_death(player)
    
    async def _handle_player_death(self, player: Player):
        """Handle player death"""
        # End any combat session
        if player.user_id in self.combat_sessions:
            del self.combat_sessions[player.user_id]
        
        # Notify room of death
        room_id = player.character['current_room']
        await self._broadcast_to_room(room_id, 
            f"{player.character['name']} has died!", 
            exclude_player=player.user_id)
        
        # Respawn player
        player.character['health'] = player.character['max_health'] // 2
        player.character['current_room'] = 2  # Respawn in temple (safe room)
        
        await player.send_message("You have died! You respawn in the Temple of Healing.", "red")
        await self.db.update_character(player.character['id'], {
            'health': player.character['health'],
            'current_room': 2
        })
        
        # Show new room to player
        await self._handle_look(player)
    
    async def _check_level_up(self, player: Player):
        """Check if player should level up"""
        current_level = player.character['level']
        exp_needed = current_level * 100  # Simple formula
        
        if player.character['experience'] >= exp_needed:
            player.character['level'] += 1
            player.character['max_health'] += 10
            player.character['health'] = player.character['max_health']
            
            await player.send_message(f"Congratulations! You reached level {player.character['level']}!", "gold")
            await self.db.update_character(player.character['id'], {
                'level': player.character['level'],
                'max_health': player.character['max_health'],
                'health': player.character['health']
            })
    
    async def _handle_use_item(self, player: Player, item_name: str):
        """Handle player using an item"""
        inventory = player.character.get('inventory', [])
        
        for item_id in inventory:
            item = await self.db.get_item(item_id)
            if item and item['name'].lower() == item_name.lower():
                await self._apply_item_effect(player, item)
                inventory.remove(item_id)
                await self.db.update_character(player.character['id'], {'inventory': inventory})
                return
        
        await player.send_message(f"You don't have a {item_name}.", "yellow")
    
    async def _apply_item_effect(self, player: Player, item: Dict):
        """Apply item effects to player"""
        item_type = item.get('item_type', 'misc')
        stats = item.get('stats', {})
        
        if item_type == 'potion':
            if 'health' in stats:
                heal_amount = stats['health']
                player.character['health'] = min(
                    player.character['max_health'],
                    player.character['health'] + heal_amount
                )
                await player.send_message(f"You drink {item['name']} and recover {heal_amount} health!", "green")
        
        await self.db.update_character(player.character['id'], {'health': player.character['health']})
    
    async def _handle_look(self, player: Player):
        """Handle player looking around"""
        room_id = player.character['current_room']
        room = await self.db.get_room(room_id)
        
        print(f"DEBUG: _handle_look - room_id: {room_id}, room type: {type(room)}, room value: {repr(room)}")
        
        if not room:
            await player.send_message("You are in a void...", "red")
            return
        
        # Send room name in dark yellow
        await player.send_message(f"\n{room['name']}", "dark_yellow")
        
        # Send room description in light green
        await player.send_message(f"{room['description']}", "light_green")
        
        # Show exits in blue
        exits = room.get('exits', {})
        print(f"DEBUG: exits type: {type(exits)}, value: {repr(exits)}")
        # Handle case where exits might be a JSON string from PostgreSQL
        if isinstance(exits, str):
            print(f"DEBUG: exits is string, parsing...")
            try:
                exits = json.loads(exits)
                print(f"DEBUG: parsed exits: {type(exits)}, value: {repr(exits)}")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"DEBUG: JSON parsing failed: {e}")
                exits = {}
        
        if exits and isinstance(exits, dict):
            print(f"DEBUG: about to call exits.keys() on: {type(exits)}")
            await player.send_message(f"Exits: {', '.join(exits.keys())}", "blue")
        
        # Show other players
        other_players = [p for p in self.players.values() 
                        if p.character['current_room'] == room_id and p.user_id != player.user_id]
        if other_players:
            player_names = [p.character['name'] for p in other_players]
            await player.send_message(f"Players here: {', '.join(player_names)}", "white")
        
        # Show monsters (from room_monsters table)
        room_monsters = await self.db.get_room_monsters(room_id)
        if room_monsters:
            monster_names = []
            for monster_instance in room_monsters:
                monster = await self.db.get_monster(monster_instance['monster_id'])
                if monster:
                    health_info = f" ({monster_instance['health']}/{monster_instance['max_health']} HP)"
                    monster_names.append(f"{monster['name']}{health_info}")
            if monster_names:
                await player.send_message(f"Monsters: {', '.join(monster_names)}", "red")
        
        # Show visible items in room
        room_items = await self.db.get_room_items(room_id)
        if room_items:
            visible_items = [item for item in room_items if not item.get('hidden', False)]
            if visible_items:
                item_names = [item['name'] for item in visible_items]
                await player.send_message(f"Items: {', '.join(item_names)}", "yellow")
    
    async def _handle_search(self, player: Player):
        """Handle player searching for hidden items"""
        room_id = player.character['current_room']
        
        # Get all items in room
        room_items = await self.db.get_room_items(room_id)
        hidden_items = [item for item in room_items if item.get('hidden', False)]
        
        if not hidden_items:
            await player.send_message("You search the area thoroughly but find nothing hidden.", "white")
            return
        
        # Calculate search success based on intellect
        intellect = player.character.get('intelligence', 10)
        base_chance = 0.3  # 30% base chance
        intellect_bonus = (intellect - 10) * 0.05  # 5% per point above 10
        search_chance = min(0.9, base_chance + intellect_bonus)  # Cap at 90%
        
        found_items = []
        for item in hidden_items:
            if random.random() < search_chance:
                found_items.append(item)
        
        if found_items:
            # Remove hidden status from found items
            for item in found_items:
                await self.db.remove_item_from_room(room_id, item['id'])
                await self.db.add_item_to_room(room_id, item['id'], hidden=False)
            
            item_names = [item['name'] for item in found_items]
            if len(found_items) == 1:
                await player.send_message(f"You search carefully and discover a {item_names[0]}!", "green")
            else:
                await player.send_message(f"You search carefully and discover: {', '.join(item_names)}!", "green")
            
            # Notify other players
            await self._broadcast_to_room(room_id, 
                f"{player.character['name']} searches the area and finds something!", 
                exclude_player=player.user_id)
        else:
            await player.send_message("You search the area but don't find anything this time.", "white")
    
    async def _handle_say(self, player: Player, message: str):
        """Handle player speaking"""
        room_id = player.character['current_room']
        formatted_message = f"{player.character['name']} says: {message}"
        
        await self._broadcast_to_room(room_id, formatted_message, exclude_player=player.user_id)
        await player.send_message(f"You say: {message}", "cyan")
    
    async def _handle_rest(self, player: Player):
        """Handle player resting to recover health/mana"""
        heal_amount = player.character['max_health'] // 4
        player.character['health'] = min(
            player.character['max_health'],
            player.character['health'] + heal_amount
        )
        
        await player.send_message(f"You rest and recover {heal_amount} health.", "green")
        await self.db.update_character(player.character['id'], {'health': player.character['health']})
    
    async def _broadcast_to_room(self, room_id: int, message: str, exclude_player: Optional[int] = None):
        """Send a message to all players in a room"""
        for player in self.players.values():
            if (player.character['current_room'] == room_id and 
                player.user_id != exclude_player):
                await player.send_message(message, "white")
    
    async def _update_monsters(self):
        """Update monster AI and behavior"""
        # Simple monster AI - could be expanded significantly
        pass
    
    async def _process_combat(self):
        """Process ongoing combat situations"""
        current_time = self.current_tick
        combat_sessions_to_remove = []
        
        # Create a copy of the items to avoid "dictionary changed size during iteration" error
        for player_id, combat in list(self.combat_sessions.items()):
            player = self.players.get(player_id)
            if not player or not player.is_online:
                combat_sessions_to_remove.append(player_id)
                continue
            
            # Check if player is dead
            if player.character['health'] <= 0:
                combat_sessions_to_remove.append(player_id)
                continue
            
            # Check if monster still exists
            room_monsters = await self.db.get_room_monsters(combat.room_id)
            monster_exists = any(m['id'] == combat.monster_instance_id for m in room_monsters)
            
            if not monster_exists:
                combat_sessions_to_remove.append(player_id)
                await player.send_message("The monster has disappeared. Combat ends.", "yellow")
                continue
            
            # Auto-attack every 3 ticks (1.5 seconds at 2 TPS)
            if current_time - combat.last_action_tick >= 3:
                # Find the monster instance
                target_monster = None
                for monster_instance in room_monsters:
                    if monster_instance['id'] == combat.monster_instance_id:
                        monster = await self.db.get_monster(monster_instance['monster_id'])
                        if monster:
                            target_monster = monster_instance
                            target_monster['name'] = monster['name']
                            target_monster['attack'] = monster['attack']
                            target_monster['defense'] = monster['defense']
                            target_monster['experience_reward'] = monster['experience_reward']
                            target_monster['loot_table'] = monster['loot_table']
                            break
                
                if target_monster:
                    # Alternate between player and monster attacks
                    if combat.rounds % 2 == 0:
                        # Player's turn to attack
                        await self._player_attack(player, target_monster, combat.room_id)
                    else:
                        # Monster's turn to attack
                        await self._monster_attack(target_monster, player, combat.room_id)
                    
                    combat.last_action_tick = current_time
                    combat.rounds += 1
                    
                    # Check if player died
                    if player.character['health'] <= 0:
                        await self._handle_player_death(player)
                        combat_sessions_to_remove.append(player_id)
                        continue
                    
                    # Check if monster died (handled in _player_attack)
                    if target_monster['health'] <= 0:
                        combat_sessions_to_remove.append(player_id)
                        continue
        
        # Remove ended combat sessions
        for player_id in combat_sessions_to_remove:
            if player_id in self.combat_sessions:
                del self.combat_sessions[player_id]
    
    async def _cleanup_players(self):
        """Remove disconnected players"""
        disconnected = []
        for pid, player in self.players.items():
            if not player.is_online:
                disconnected.append(pid)
        
        for pid in disconnected:
            del self.players[pid]
        
        # Cleanup completed silently
    
    async def _process_events(self):
        """Process queued game events"""
        while self.event_queue:
            event = self.event_queue.pop(0)
            await self._handle_event(event)
    
    async def _handle_event(self, event: GameEvent):
        """Handle a specific game event"""
        # Process different types of events
        pass
    
    async def _initialize_world(self):
        """Initialize the default game world"""
        # Create starting room if it doesn't exist
        starting_room = await self.db.get_room(1)
        if not starting_room:
            await self.db.create_room(
                "Town Square",
                "A bustling town square with a fountain in the center. This is where new adventurers begin their journey.",
                {"safe_zone": True}
            )
        
        # Create temple room if it doesn't exist
        temple_room = await self.db.get_room(2)
        if not temple_room:
            await self.db.create_room(
                "Temple of Healing",
                "A sacred temple filled with divine light. The air hums with protective magic, and no violence can occur here. Fallen adventurers find themselves restored to life in this holy sanctuary.",
                {"safe_zone": True, "temple": True}
            )
            
            # Link the rooms
            await self.db.link_rooms(1, "north", 2)  # Town Square north to Temple
        
        # Create some basic items
        health_potion = await self.db.get_item(1)
        if not health_potion:
            await self.db.create_item(
                "Health Potion",
                "A red potion that restores health when consumed.",
                "potion",
                {"consumable": True},
                {"health": 25}
            )
        
        # Create a basic monster
        goblin = await self.db.get_monster(1)
        if not goblin:
            await self.db.create_monster(
                "Goblin",
                "A small, green creature with sharp teeth and beady eyes.",
                1, 30, 8, 2, 15, [1]  # level, health, attack, defense, exp_reward, loot_table
            )
    
    async def add_player(self, user_id: int, character_data: Dict, connection):
        """Add a player to the game"""
        player = Player(user_id, character_data, connection)
        self.players[user_id] = player
        
        # Welcome message
        await player.send_message(f"Welcome to the world, {character_data['name']}!", "green")
        
        return player
    
    async def remove_player(self, user_id: int):
        """Remove a player from the game"""
        if user_id in self.players:
            player = self.players[user_id]
            room_id = player.character['current_room']
            
            # Notify other players
            await self._broadcast_to_room(room_id, 
                f"{player.character['name']} disappears in a puff of smoke.", 
                exclude_player=user_id)
            
            del self.players[user_id]
    
    async def process_command(self, user_id: int, command: str) -> bool:
        """Process a command from a player"""
        if user_id not in self.players:
            return False
        
        player = self.players[user_id]
        parts = command.strip().split()
        
        if not parts:
            return True
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Handle different commands
        if cmd in ['move', 'go', 'n', 'north', 's', 'south', 'e', 'east', 'w', 'west', 'u', 'up', 'd', 'down']:
            direction = cmd if cmd in ['north', 'south', 'east', 'west', 'up', 'down'] else args[0] if args else cmd
            direction_map = {'n': 'north', 's': 'south', 'e': 'east', 'w': 'west', 'u': 'up', 'd': 'down'}
            direction = direction_map.get(direction, direction)
            
            action = Action(user_id, ActionType.MOVE, target=direction, parameters={}, tick_delay=1)
            return player.add_action(action)
        
        elif cmd in ['attack', 'kill', 'fight', 'a']:
            if args:
                action = Action(user_id, ActionType.ATTACK, target=' '.join(args), parameters={}, tick_delay=2)
                return player.add_action(action)
            else:
                await player.send_message("Attack what?", "yellow")
        
        elif cmd in ['use', 'drink', 'eat']:
            if args:
                action = Action(user_id, ActionType.USE_ITEM, target=' '.join(args), parameters={}, tick_delay=1)
                return player.add_action(action)
            else:
                await player.send_message("Use what?", "yellow")
        
        elif cmd in ['look', 'l']:
            await self._handle_look(player)
            # Don't send prompt here - let the main handler do it
            return True
        
        elif cmd in ['say', 'speak']:
            if args:
                try:
                    message = InputSanitizer.sanitize_message(' '.join(args))
                    action = Action(user_id, ActionType.SAY, parameters={'message': message}, tick_delay=0)
                    return player.add_action(action)
                except ValueError as e:
                    await player.send_message(f"Invalid message: {e}", "red")
                    return False
            else:
                await player.send_message("Say what?", "yellow")
        
        elif cmd in ['rest', 'sleep']:
            action = Action(user_id, ActionType.REST, target=None, parameters={}, tick_delay=3)
            return player.add_action(action)
        
        elif cmd in ['stats', 'status']:
            await self._show_stats(player)
            return True
        
        elif cmd in ['inventory', 'inv']:
            await self._show_inventory(player)
            return True
        
        elif cmd == 'who':
            await self._show_online_players(player)
            return True
        
        elif cmd == 'help':
            if args:
                await self._show_command_help(player, args[0])
            else:
                await self._show_help(player)
            return True
        
        elif cmd == 'statusline':
            if args:
                if args[0] == 'set':
                    if len(args) > 1:
                        try:
                            new_status_line = InputSanitizer.sanitize_status_line(' '.join(args[1:]))
                            await self._set_status_line(player, new_status_line)
                        except ValueError as e:
                            await player.send_message(f"Invalid status line format: {e}", "red")
                    else:
                        await player.send_message("Usage: statusline set <format>", "yellow")
                elif args[0] == 'show':
                    await self._show_status_line(player)
                elif args[0] == 'help':
                    await self._show_status_line_help(player)
                else:
                    await player.send_message("Usage: statusline [set <format>|show|help]", "yellow")
            else:
                await self._show_status_line(player)
        
        elif cmd in ['search', 'find']:
            await self._handle_search(player)
            return True
        
        else:
            await player.send_message(f"Unknown command: {cmd}. Type 'help' for available commands.", "yellow")
            return True
        
        return True
    
    async def _show_stats(self, player: Player):
        """Show player statistics"""
        char = player.character
        stats = f"""
Character Stats for {char['name']}:
Level: {char['level']} ({char['race']} {char['class']})
Experience: {char['experience']}
Health: {char['health']}/{char['max_health']}
Mana: {char.get('mana', 0)}/{char.get('max_mana', 0)}

Attributes:
Strength: {char['strength']}
Dexterity: {char['dexterity']}
Constitution: {char['constitution']}
Intelligence: {char['intelligence']}
Wisdom: {char['wisdom']}
Charisma: {char['charisma']}
"""
        await player.send_message(stats, "cyan")
    
    async def _show_inventory(self, player: Player):
        """Show player inventory"""
        inventory = player.character.get('inventory', [])
        
        if not inventory:
            await player.send_message("Your inventory is empty.", "yellow")
            return
        
        items_text = "Inventory:\n"
        for item_id in inventory:
            item = await self.db.get_item(item_id)
            if item:
                items_text += f"- {item['name']}\n"
        
        await player.send_message(items_text, "cyan")
    
    async def _show_online_players(self, player: Player):
        """Show list of online players"""
        online_players = [p.character['name'] for p in self.players.values()]
        
        if online_players:
            players_text = f"Online players ({len(online_players)}):\n"
            players_text += "\n".join(f"- {name}" for name in online_players)
        else:
            players_text = "No players online."
        
        await player.send_message(players_text, "cyan")
    
    async def _show_help(self, player: Player):
        """Show help information"""
        help_text = """
Available Commands:
- move/go <direction> (or n/s/e/w/u/d) - Move in a direction
its - look/l - Look around the current room
- attack/kill/fight <target> - Attack a monster
- use/drink/eat <item> - Use an item from inventory
- say/speak <message> - Speak to other players in the room
- rest/sleep - Rest to recover health
- stats/status - View your character statistics
- inventory/inv - View your inventory
- who - List online players
- search/find - Search for hidden items in the room
- statusline [set <format>|show|help] - Customize your status display
- help [command] - Show this help message or help for specific command
- quit/exit - Exit the game
"""
        
        # Check if player has admin access and add admin commands section
        try:
            # Import here to avoid circular imports
            from database import db
            has_admin = False
            
            if not db.pool:
                # Memory storage fallback
                for user in db.users.values():
                    if user.get('id') == player.user_id:
                        has_admin = user.get('access_level', 1) >= 2
                        break
            else:
                async with db.pool.acquire() as conn:
                    user = await conn.fetchrow('SELECT * FROM users WHERE id = $1', player.user_id)
                    if user:
                        has_admin = user['access_level'] >= 2
            
            if has_admin:
                help_text += """
Admin Commands:
- /admin_help [command] - Show admin help or help for specific admin command
- /create_room "name" "description" - Create a new room
- /link_rooms <room1_id> <direction> <room2_id> - Link rooms
- /create_item "name" <type> [stats] - Create an item
- /create_monster "name" <level> - Create a monster
- /teleport <player> <room_id> - Teleport a player
- /server_stats - Show server statistics
- /broadcast "message" - Send message to all players
- And many more... (use /admin_help for complete list)
"""
        except Exception:
            # If there's any error checking admin status, just show regular help
            pass
        
        await player.send_message(help_text, "white")

    async def _show_command_help(self, player: Player, command: str):
        """Show help for a specific command"""
        command = command.lower()
        
        # Define help text for each command
        command_help = {
            'move': """Command: move/go <direction>
Aliases: n, s, e, w, u, d, north, south, east, west, up, down
Description: Move your character in the specified direction
Usage:
  move north
  go east
  n (shortcut for north)
  s (shortcut for south)
Example: move north""",
            
            'go': """Command: move/go <direction>
Aliases: n, s, e, w, u, d, north, south, east, west, up, down
Description: Move your character in the specified direction
Usage:
  move north
  go east
  n (shortcut for north)
  s (shortcut for south)
Example: go west""",
            
            'look': """Command: look
Aliases: l
Description: Examine your current surroundings, showing room description, exits, items, monsters, and other players
Usage: look
Example: look""",
            
            'l': """Command: look
Aliases: l
Description: Examine your current surroundings, showing room description, exits, items, monsters, and other players
Usage: look
Example: l""",
            
            'attack': """Command: attack <target>
Aliases: kill
Description: Attack a monster in your current room. Cannot be used in safe zones.
Usage: attack <monster_name>
Example: attack goblin
Note: Combat is turn-based and you cannot flee immediately after attacking""",
            
            'kill': """Command: attack <target>
Aliases: kill, fight
Description: Attack a monster in your current room. Cannot be used in safe zones.
Usage: kill <monster_name>
Example: kill orc
Note: Combat is turn-based and you cannot flee immediately after attacking""",
            
            'fight': """Command: attack <target>
Aliases: kill, fight
Description: Attack a monster in your current room. Cannot be used in safe zones.
Usage: fight <monster_name>
Example: fight goblin
Note: Combat is turn-based and you cannot flee immediately after attacking""",
            
            'use': """Command: use <item>
Aliases: drink, eat
Description: Use, drink, or eat an item from your inventory
Usage: use <item_name>
Examples:
  use health potion
  drink mana potion
  eat bread
Note: Items must be in your inventory to use them""",
            
            'drink': """Command: use <item>
Aliases: drink, eat
Description: Use, drink, or eat an item from your inventory
Usage: drink <item_name>
Example: drink health potion
Note: Items must be in your inventory to use them""",
            
            'eat': """Command: use <item>
Aliases: drink, eat
Description: Use, drink, or eat an item from your inventory
Usage: eat <item_name>
Example: eat bread
Note: Items must be in your inventory to use them""",
            
            'say': """Command: say <message>
Aliases: speak
Description: Speak to other players in your current room
Usage: say <message>
Example: say Hello everyone!
Note: Only players in the same room will see your message""",
            
            'speak': """Command: say <message>
Aliases: speak
Description: Speak to other players in your current room
Usage: speak <message>
Example: speak How is everyone doing?
Note: Only players in the same room will see your message""",
            
            'rest': """Command: rest
Aliases: sleep
Description: Rest to recover health and mana over time
Usage: rest
Example: rest
Note: Resting takes several game ticks to complete and you cannot perform other actions while resting""",
            
            'sleep': """Command: rest
Aliases: sleep
Description: Rest to recover health and mana over time
Usage: sleep
Example: sleep
Note: Resting takes several game ticks to complete and you cannot perform other actions while resting""",
            
            'stats': """Command: stats
Aliases: status
Description: Display your character's statistics including level, experience, health, mana, and attributes
Usage: stats
Example: stats""",
            
            'status': """Command: stats
Aliases: status
Description: Display your character's statistics including level, experience, health, mana, and attributes
Usage: status
Example: status""",
            
            'inventory': """Command: inventory
Aliases: inv
Description: Display all items in your inventory
Usage: inventory
Example: inventory""",
            
            'inv': """Command: inventory
Aliases: inv
Description: Display all items in your inventory
Usage: inv
Example: inv""",
            
            'who': """Command: who
Description: Display a list of all players currently online
Usage: who
Example: who""",
            
            'statusline': """Command: statusline [set <format>|show|help]
Description: Customize your status display with variables
Usage:
  statusline - Show current status line
  statusline show - Display current status line
  statusline set <format> - Set custom status line format
  statusline help - Show formatting help and available variables
Examples:
  statusline set HP: {health}/{max_health} | MP: {mana}/{max_mana}
  statusline set {name} (Lv.{level}) | {room_name}
Note: Use 'statusline help' for available variables""",
            
            'quit': """Command: quit
Aliases: exit
Description: Exit the game and disconnect from the server
Usage: quit
Example: quit
Note: Your character progress is automatically saved""",
            
            'exit': """Command: quit
Aliases: exit
Description: Exit the game and disconnect from the server
Usage: exit
Example: exit
Note: Your character progress is automatically saved""",
            
            'search': """Command: search
Aliases: find
Description: Search for hidden items in your current room. Success depends on your intelligence stat.
Usage: search
Example: search
Note: Higher intelligence increases your chance of finding hidden items""",
            
            'find': """Command: search
Aliases: find
Description: Search for hidden items in your current room. Success depends on your intelligence stat.
Usage: find
Example: find
Note: Higher intelligence increases your chance of finding hidden items""",
            
            'help': """Command: help [command]
Description: Show general help or help for a specific command
Usage:
  help - Show general help
  help <command> - Show help for specific command
Examples:
  help
  help attack
  help statusline"""
        }
        
        # Check for direction shortcuts
        direction_shortcuts = {
            'n': 'move', 'north': 'move',
            's': 'move', 'south': 'move', 
            'e': 'move', 'east': 'move',
            'w': 'move', 'west': 'move',
            'u': 'move', 'up': 'move',
            'd': 'move', 'down': 'move'
        }
        
        if command in direction_shortcuts:
            command = direction_shortcuts[command]
        
        if command in command_help:
            await player.send_message(command_help[command], "cyan")
        else:
            await player.send_message(f"No help available for command '{command}'. Type 'help' for a list of available commands.", "yellow")

    async def _set_status_line(self, player: Player, status_line: str):
        """Set the player's custom status line"""
        # Update character in database
        await self.db.update_character(player.character['id'], {'status_line': status_line})
        
        # Update local character data
        player.character['status_line'] = status_line
        
        await player.send_message(f"Status line updated to: {status_line}", "green")
        await player.send_message("Preview:", "cyan")
        await self._show_status_line(player)
    
    async def _show_status_line(self, player: Player):
        """Display the player's current status line"""
        status_line = player.character.get('status_line', 'HP: {health}/{max_health} | MP: {mana}/{max_mana} | Room: {room_name}')
        formatted_status = await self._format_status_line(player, status_line)
        
        await player.send_message("=" * 60, "white")
        await player.send_message(formatted_status, "cyan")
        await player.send_message("=" * 60, "white")
    
    async def _show_status_line_help(self, player: Player):
        """Show help for status line formatting"""
        help_text = """
Status Line Formatting Help:

Available Variables:
{name} - Character name
{level} - Character level
{race} - Character race
{class} - Character class
{health} - Current health
{max_health} - Maximum health
{mana} - Current mana
{max_mana} - Maximum mana
{experience} - Current experience
{strength} - Strength attribute
{dexterity} - Dexterity attribute
{constitution} - Constitution attribute
{intelligence} - Intelligence attribute
{wisdom} - Wisdom attribute
{charisma} - Charisma attribute
{room_name} - Current room name
{room_id} - Current room ID
{exits} - Available exits (comma-separated)

Examples:
statusline set HP: {health}/{max_health} | MP: {mana}/{max_mana}
statusline set {name} (Lv.{level}) | HP:{health} MP:{mana} | {room_name}
statusline set [{race} {class}] HP:{health}/{max_health} Exits: {exits}

Commands:
statusline - Show current status line
statusline show - Show current status line
statusline set <format> - Set new status line format
statusline help - Show this help
"""
        await player.send_message(help_text, "white")
    
    async def _format_status_line(self, player: Player, status_line: str) -> str:
        """Format the status line with current player data"""
        char = player.character
        
        # Get current room information
        room = await self.db.get_room(char['current_room'])
        room_name = room['name'] if room else "Unknown"
        
        # Get exits
        exits = []
        if room and room.get('exits'):
            room_exits = room['exits']
            if isinstance(room_exits, str):
                try:
                    import json
                    room_exits = json.loads(room_exits)
                except:
                    room_exits = {}
            exits = list(room_exits.keys()) if room_exits else []
        
        # Format variables
        format_vars = {
            'name': char.get('name', 'Unknown'),
            'level': char.get('level', 1),
            'race': char.get('race', 'Unknown'),
            'class': char.get('class', 'Unknown'),
            'health': char.get('health', 0),
            'max_health': char.get('max_health', 0),
            'mana': char.get('mana', 0),
            'max_mana': char.get('max_mana', 0),
            'experience': char.get('experience', 0),
            'strength': char.get('strength', 10),
            'dexterity': char.get('dexterity', 10),
            'constitution': char.get('constitution', 10),
            'intelligence': char.get('intelligence', 10),
            'wisdom': char.get('wisdom', 10),
            'charisma': char.get('charisma', 10),
            'room_name': room_name,
            'room_id': char.get('current_room', 1),
            'exits': ', '.join(exits) if exits else 'none'
        }
        
        try:
            return status_line.format(**format_vars)
        except KeyError as e:
            return f"Status line error: Unknown variable {e}"
        except Exception as e:
            return f"Status line error: {e}"
    
    async def send_status_prompt(self, player: Player):
        """Send a bash-like prompt with status line to the player"""
        try:
            # Get the player's status line format
            status_line = player.character.get('status_line', 'HP: {health}/{max_health} | MP: {mana}/{max_mana} | Room: {room_name}')
            formatted_status = await self._format_status_line(player, status_line)
            
            # Send the prompt with status line (no newline at end for prompt)
            prompt = f"[{formatted_status}] > "
            
            # Mark that the engine has sent a prompt to avoid duplicates
            if hasattr(player.connection, '_prompt_sent_by_engine'):
                player.connection._prompt_sent_by_engine = True
            else:
                # Add the flag if it doesn't exist
                setattr(player.connection, '_prompt_sent_by_engine', True)
            
            # Send without newline to create a proper prompt
            if hasattr(player.connection, 'send_prompt'):
                await player.connection.send_prompt(prompt)
            else:
                # Fallback for connections that don't support send_prompt
                await player.send_message(prompt, "cyan")
                
        except Exception as e:
            print(f"Error sending status prompt: {e}")
            # Fallback to simple prompt
            await player.send_message("> ", "cyan")

# Global game engine instance
game_engine = None