import random
from typing import Dict, List, Tuple
from input_sanitizer import InputSanitizer

class CharacterCreation:
    """Handles character creation process including race/class selection and stat rolling"""
    
    RACES = {
        'human': {
            'name': 'Human',
            'description': 'Versatile and adaptable, humans excel in all areas.',
            'stat_bonuses': {'strength': 1, 'dexterity': 1, 'constitution': 1, 
                           'intelligence': 1, 'wisdom': 1, 'charisma': 1},
            'special_abilities': ['Versatility: +1 to all stats']
        },
        'elf': {
            'name': 'Elf',
            'description': 'Graceful and magical, elves are natural spellcasters.',
            'stat_bonuses': {'dexterity': 2, 'intelligence': 2, 'wisdom': 1, 'constitution': -1},
            'special_abilities': ['Keen Senses: +2 to perception', 'Magic Affinity: +10 max mana']
        },
        'dwarf': {
            'name': 'Dwarf',
            'description': 'Hardy and strong, dwarves are excellent warriors and craftsmen.',
            'stat_bonuses': {'strength': 2, 'constitution': 3, 'wisdom': 1, 'dexterity': -1, 'charisma': -1},
            'special_abilities': ['Toughness: +15 max health', 'Weapon Expertise: +1 attack damage']
        },
        'halfling': {
            'name': 'Halfling',
            'description': 'Small but nimble, halflings make excellent rogues and scouts.',
            'stat_bonuses': {'dexterity': 3, 'charisma': 2, 'strength': -2, 'constitution': -1},
            'special_abilities': ['Lucky: Reroll 1s on dice', 'Stealth: +2 to hiding']
        },
        'orc': {
            'name': 'Orc',
            'description': 'Powerful and fierce, orcs are natural warriors.',
            'stat_bonuses': {'strength': 3, 'constitution': 2, 'intelligence': -2, 'charisma': -1},
            'special_abilities': ['Rage: +2 damage when below 50% health', 'Intimidation: +2 to fear effects']
        }
    }
    
    CLASSES = {
        'warrior': {
            'name': 'Warrior',
            'description': 'Masters of combat, warriors excel in melee fighting.',
            'stat_bonuses': {'strength': 3, 'constitution': 2, 'intelligence': -1},
            'starting_equipment': ['iron_sword', 'leather_armor', 'health_potion'],
            'special_abilities': ['Combat Expertise: +2 attack damage', 'Armor Mastery: +1 defense'],
            'health_bonus': 20,
            'mana_bonus': 0
        },
        'mage': {
            'name': 'Mage',
            'description': 'Wielders of arcane magic, mages cast powerful spells.',
            'stat_bonuses': {'intelligence': 3, 'wisdom': 2, 'strength': -2},
            'starting_equipment': ['wooden_staff', 'mage_robes', 'mana_potion'],
            'special_abilities': ['Spellcasting: Can cast magic spells', 'Mana Efficiency: -1 mana cost'],
            'health_bonus': -10,
            'mana_bonus': 30
        },
        'rogue': {
            'name': 'Rogue',
            'description': 'Stealthy and cunning, rogues strike from the shadows.',
            'stat_bonuses': {'dexterity': 3, 'charisma': 1, 'constitution': -1},
            'starting_equipment': ['dagger', 'leather_armor', 'lockpicks'],
            'special_abilities': ['Sneak Attack: +50% damage from behind', 'Stealth: Can hide in shadows'],
            'health_bonus': 5,
            'mana_bonus': 10
        },
        'cleric': {
            'name': 'Cleric',
            'description': 'Divine spellcasters who heal allies and smite enemies.',
            'stat_bonuses': {'wisdom': 3, 'constitution': 1, 'dexterity': -1},
            'starting_equipment': ['mace', 'chain_mail', 'healing_potion'],
            'special_abilities': ['Divine Magic: Can cast healing spells', 'Turn Undead: Frighten undead'],
            'health_bonus': 10,
            'mana_bonus': 20
        },
        'ranger': {
            'name': 'Ranger',
            'description': 'Masters of nature and archery, rangers protect the wilderness.',
            'stat_bonuses': {'dexterity': 2, 'wisdom': 2, 'strength': 1},
            'starting_equipment': ['bow', 'arrows', 'leather_armor'],
            'special_abilities': ['Tracking: Can track creatures', 'Nature Magic: Basic nature spells'],
            'health_bonus': 15,
            'mana_bonus': 15
        }
    }
    
    @staticmethod
    def roll_stats() -> Dict[str, int]:
        """Roll character stats using 4d6 drop lowest method"""
        stats = {}
        stat_names = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        
        for stat in stat_names:
            # Roll 4d6, drop lowest
            rolls = [random.randint(1, 6) for _ in range(4)]
            rolls.sort(reverse=True)
            stats[stat] = sum(rolls[:3])  # Take highest 3
        
        return stats
    
    @staticmethod
    def apply_racial_bonuses(base_stats: Dict[str, int], race: str) -> Dict[str, int]:
        """Apply racial stat bonuses to base stats"""
        if race not in CharacterCreation.RACES:
            return base_stats
        
        modified_stats = base_stats.copy()
        bonuses = CharacterCreation.RACES[race]['stat_bonuses']
        
        for stat, bonus in bonuses.items():
            modified_stats[stat] = max(3, modified_stats[stat] + bonus)  # Minimum stat of 3
        
        return modified_stats
    
    @staticmethod
    def apply_class_bonuses(base_stats: Dict[str, int], char_class: str) -> Dict[str, int]:
        """Apply class stat bonuses to base stats"""
        if char_class not in CharacterCreation.CLASSES:
            return base_stats
        
        modified_stats = base_stats.copy()
        bonuses = CharacterCreation.CLASSES[char_class]['stat_bonuses']
        
        for stat, bonus in bonuses.items():
            modified_stats[stat] = max(3, modified_stats[stat] + bonus)  # Minimum stat of 3
        
        return modified_stats
    
    @staticmethod
    def calculate_derived_stats(stats: Dict[str, int], race: str, char_class: str) -> Dict[str, int]:
        """Calculate derived stats like health and mana"""
        derived = {}
        
        # Base health and mana
        base_health = 50 + (stats['constitution'] * 2)
        base_mana = 20 + (stats['intelligence'] * 2)
        
        # Apply class bonuses
        if char_class in CharacterCreation.CLASSES:
            class_data = CharacterCreation.CLASSES[char_class]
            base_health += class_data.get('health_bonus', 0)
            base_mana += class_data.get('mana_bonus', 0)
        
        # Apply racial bonuses
        if race == 'elf':
            base_mana += 10
        elif race == 'dwarf':
            base_health += 15
        
        derived['health'] = base_health
        derived['max_health'] = base_health
        derived['mana'] = base_mana
        derived['max_mana'] = base_mana
        
        return derived
    
    @staticmethod
    def get_starting_equipment(char_class: str) -> List[str]:
        """Get starting equipment for a class"""
        if char_class in CharacterCreation.CLASSES:
            return CharacterCreation.CLASSES[char_class]['starting_equipment'].copy()
        return ['rusty_dagger', 'tattered_clothes']
    
    @staticmethod
    def create_character(name: str, race: str, char_class: str, 
                        custom_stats: Dict[str, int] = None) -> Dict[str, any]:
        """Create a complete character with all stats and equipment"""
        
        # Validate inputs
        if race not in CharacterCreation.RACES:
            raise ValueError(f"Invalid race: {race}")
        if char_class not in CharacterCreation.CLASSES:
            raise ValueError(f"Invalid class: {char_class}")
        
        # Roll or use provided stats
        if custom_stats:
            base_stats = custom_stats
        else:
            base_stats = CharacterCreation.roll_stats()
        
        # Apply racial bonuses
        stats_with_race = CharacterCreation.apply_racial_bonuses(base_stats, race)
        
        # Apply class bonuses
        final_stats = CharacterCreation.apply_class_bonuses(stats_with_race, char_class)
        
        # Calculate derived stats
        derived_stats = CharacterCreation.calculate_derived_stats(final_stats, race, char_class)
        
        # Get starting equipment
        starting_equipment = CharacterCreation.get_starting_equipment(char_class)
        
        # Create character data
        character = {
            'name': name,
            'race': race,
            'class': char_class,
            'level': 1,
            'experience': 0,
            'current_room': 1,  # Starting room
            'inventory': starting_equipment,
            'equipment': {},
            **final_stats,
            **derived_stats
        }
        
        return character
    
    @staticmethod
    def get_race_info(race: str) -> str:
        """Get formatted information about a race"""
        if race not in CharacterCreation.RACES:
            return "Unknown race"
        
        race_data = CharacterCreation.RACES[race]
        info = f"{race_data['name']}: {race_data['description']}\n"
        
        # Stat bonuses
        bonuses = race_data['stat_bonuses']
        bonus_text = []
        for stat, bonus in bonuses.items():
            if bonus > 0:
                bonus_text.append(f"+{bonus} {stat}")
            elif bonus < 0:
                bonus_text.append(f"{bonus} {stat}")
        
        if bonus_text:
            info += f"Stat Bonuses: {', '.join(bonus_text)}\n"
        
        # Special abilities
        if race_data['special_abilities']:
            info += f"Special Abilities: {', '.join(race_data['special_abilities'])}\n"
        
        return info
    
    @staticmethod
    def get_class_info(char_class: str) -> str:
        """Get formatted information about a class"""
        if char_class not in CharacterCreation.CLASSES:
            return "Unknown class"
        
        class_data = CharacterCreation.CLASSES[char_class]
        info = f"{class_data['name']}: {class_data['description']}\n"
        
        # Stat bonuses
        bonuses = class_data['stat_bonuses']
        bonus_text = []
        for stat, bonus in bonuses.items():
            if bonus > 0:
                bonus_text.append(f"+{bonus} {stat}")
            elif bonus < 0:
                bonus_text.append(f"{bonus} {stat}")
        
        if bonus_text:
            info += f"Stat Bonuses: {', '.join(bonus_text)}\n"
        
        # Health/Mana bonuses
        health_bonus = class_data.get('health_bonus', 0)
        mana_bonus = class_data.get('mana_bonus', 0)
        
        if health_bonus != 0:
            info += f"Health Bonus: {health_bonus:+d}\n"
        if mana_bonus != 0:
            info += f"Mana Bonus: {mana_bonus:+d}\n"
        
        # Starting equipment
        equipment = class_data['starting_equipment']
        info += f"Starting Equipment: {', '.join(equipment)}\n"
        
        # Special abilities
        if class_data['special_abilities']:
            info += f"Special Abilities: {', '.join(class_data['special_abilities'])}\n"
        
        return info
    
    @staticmethod
    def list_races() -> str:
        """Get a formatted list of all available races"""
        race_list = "Available Races:\n"
        for race_key, race_data in CharacterCreation.RACES.items():
            race_list += f"- {race_key}: {race_data['name']}\n"
        return race_list
    
    @staticmethod
    def list_classes() -> str:
        """Get a formatted list of all available classes"""
        class_list = "Available Classes:\n"
        for class_key, class_data in CharacterCreation.CLASSES.items():
            class_list += f"- {class_key}: {class_data['name']}\n"
        return class_list
    
    @staticmethod
    def format_stats(stats: Dict[str, int]) -> str:
        """Format stats for display"""
        stat_order = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        formatted = "Stats:\n"
        
        for stat in stat_order:
            if stat in stats:
                formatted += f"  {stat.capitalize()}: {stats[stat]}\n"
        
        return formatted
    
    @staticmethod
    def get_stat_modifier(stat_value: int) -> int:
        """Calculate D&D-style stat modifier"""
        return (stat_value - 10) // 2

class CharacterCreationSession:
    """Manages the character creation process for a user"""
    
    def __init__(self):
        self.stage = 'name'  # name, race, class, stats, confirm
        self.character_data = {}
        self.rolled_stats = None
    
    async def process_input(self, user_input: str, connection) -> Tuple[bool, str]:
        """
        Process user input during character creation
        Returns (is_complete, response_message)
        """
        
        if self.stage == 'name':
            return await self._handle_name_input(user_input, connection)
        elif self.stage == 'race':
            return await self._handle_race_input(user_input, connection)
        elif self.stage == 'class':
            return await self._handle_class_input(user_input, connection)
        elif self.stage == 'stats':
            return await self._handle_stats_input(user_input, connection)
        elif self.stage == 'confirm':
            return await self._handle_confirm_input(user_input, connection)
        
        return False, "Unknown stage in character creation."
    
    async def _handle_name_input(self, name: str, connection) -> Tuple[bool, str]:
        """Handle character name input"""
        try:
            # Use input sanitizer for character name validation
            sanitized_name = InputSanitizer.sanitize_character_name(name)
            
            # Store the name
            self.character_data['name'] = sanitized_name
            self.stage = 'race'
            
            response = f"Welcome, {sanitized_name}!\n\n"
            response += CharacterCreation.list_races()
            response += "\nPlease choose a race (or type 'info <race>' for details):"
            
            return False, response
        except ValueError as e:
            return False, str(e)
    
    async def _handle_race_input(self, input_text: str, connection) -> Tuple[bool, str]:
        """Handle race selection input"""
        parts = input_text.strip().lower().split()
        
        if len(parts) == 2 and parts[0] == 'info':
            race = parts[1]
            if race in CharacterCreation.RACES:
                info = CharacterCreation.get_race_info(race)
                return False, f"{info}\nPlease choose a race:"
            else:
                return False, f"Unknown race: {race}. Please choose a valid race:"
        
        race = input_text.strip().lower()
        if race not in CharacterCreation.RACES:
            response = f"Invalid race: {race}\n"
            response += CharacterCreation.list_races()
            response += "\nPlease choose a valid race:"
            return False, response
        
        self.character_data['race'] = race
        self.stage = 'class'
        
        response = f"You have chosen {CharacterCreation.RACES[race]['name']}.\n\n"
        response += CharacterCreation.list_classes()
        response += "\nPlease choose a class (or type 'info <class>' for details):"
        
        return False, response
    
    async def _handle_class_input(self, input_text: str, connection) -> Tuple[bool, str]:
        """Handle class selection input"""
        parts = input_text.strip().lower().split()
        
        if len(parts) == 2 and parts[0] == 'info':
            char_class = parts[1]
            if char_class in CharacterCreation.CLASSES:
                info = CharacterCreation.get_class_info(char_class)
                return False, f"{info}\nPlease choose a class:"
            else:
                return False, f"Unknown class: {char_class}. Please choose a valid class:"
        
        char_class = input_text.strip().lower()
        if char_class not in CharacterCreation.CLASSES:
            response = f"Invalid class: {char_class}\n"
            response += CharacterCreation.list_classes()
            response += "\nPlease choose a valid class:"
            return False, response
        
        self.character_data['class'] = char_class
        self.stage = 'stats'
        
        # Roll stats
        self.rolled_stats = CharacterCreation.roll_stats()
        
        response = f"You have chosen {CharacterCreation.CLASSES[char_class]['name']}.\n\n"
        response += "Rolling your character stats...\n\n"
        response += CharacterCreation.format_stats(self.rolled_stats)
        response += "\nType 'accept' to keep these stats, or 'reroll' to roll again:"
        
        return False, response
    
    async def _handle_stats_input(self, input_text: str, connection) -> Tuple[bool, str]:
        """Handle stats confirmation input"""
        choice = input_text.strip().lower()
        
        if choice == 'reroll':
            self.rolled_stats = CharacterCreation.roll_stats()
            response = "Rolling new stats...\n\n"
            response += CharacterCreation.format_stats(self.rolled_stats)
            response += "\nType 'accept' to keep these stats, or 'reroll' to roll again:"
            return False, response
        
        elif choice == 'accept':
            self.character_data['stats'] = self.rolled_stats
            self.stage = 'confirm'
            
            # Show final character summary
            response = "Character Summary:\n"
            response += f"Name: {self.character_data['name']}\n"
            response += f"Race: {CharacterCreation.RACES[self.character_data['race']]['name']}\n"
            response += f"Class: {CharacterCreation.CLASSES[self.character_data['class']]['name']}\n\n"
            
            # Apply bonuses for display
            final_stats = CharacterCreation.apply_racial_bonuses(self.rolled_stats, self.character_data['race'])
            final_stats = CharacterCreation.apply_class_bonuses(final_stats, self.character_data['class'])
            
            response += "Final Stats (with racial and class bonuses):\n"
            response += CharacterCreation.format_stats(final_stats)
            
            response += "\nType 'confirm' to create this character, or 'restart' to start over:"
            return False, response
        
        else:
            return False, "Please type 'accept' to keep these stats, or 'reroll' to roll again:"
    
    async def _handle_confirm_input(self, input_text: str, connection) -> Tuple[bool, str]:
        """Handle final confirmation input"""
        choice = input_text.strip().lower()
        
        if choice == 'confirm':
            # Character creation is complete
            return True, "Character created successfully! Welcome to the world!"
        
        elif choice == 'restart':
            # Reset the session
            self.__init__()
            return False, "Character creation restarted. Please enter your character's name:"
        
        else:
            return False, "Please type 'confirm' to create this character, or 'restart' to start over:"
    
    def get_character_data(self) -> Dict[str, any]:
        """Get the final character data"""
        if self.stage != 'confirm':
            return None
        
        return CharacterCreation.create_character(
            self.character_data['name'],
            self.character_data['race'],
            self.character_data['class'],
            self.character_data['stats']
        )