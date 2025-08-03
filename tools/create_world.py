#!/usr/bin/env python3
"""
World Creation Script for SSH RPG
Creates a default world with town, forest, and graveyard areas
Includes monetary system and monsters
"""

import asyncio
import json
import sys
import os
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

async def clean_database():
    """Clean up existing world data"""
    print("Cleaning up existing world data...")
    
    if not db.pool:
        print("Database not connected")
        return
    
    async with db.pool.acquire() as conn:
        # Clean up tables in order (respecting foreign key constraints)
        cleanup_queries = [
            "DELETE FROM items WHERE id > 1",  # Keep basic items
            "DELETE FROM monsters WHERE id > 0",
            "DELETE FROM rooms WHERE id > 1",  # Keep the starting room
            "UPDATE characters SET current_room = 1 WHERE current_room > 1"  # Move players to starting room
        ]
        
        for query in cleanup_queries:
            try:
                await conn.execute(query)
                print(f"Executed: {query}")
            except Exception as e:
                print(f"Warning: {query} - {e}")
    
    print("Database cleanup completed.")

async def create_currency_items():
    """Create currency items (Silver, Gold, Platinum)"""
    print("Creating currency items...")
    
    currencies = [
        {
            'name': 'Silver Coin',
            'description': 'A shiny silver coin, the basic currency of the realm.',
            'type': 'currency',
            'stats': {'value': 1, 'stackable': True}
        },
        {
            'name': 'Gold Coin', 
            'description': 'A valuable gold coin worth 10 silver coins.',
            'type': 'currency',
            'stats': {'value': 10, 'stackable': True}
        },
        {
            'name': 'Platinum Coin',
            'description': 'A rare platinum coin worth 100 silver coins.',
            'type': 'currency', 
            'stats': {'value': 100, 'stackable': True}
        }
    ]
    
    for currency in currencies:
        await db.create_item(
            currency['name'], 
            currency['description'], 
            currency['type'], 
            stats=currency['stats']
        )
    
    print("Currency items created.")

async def create_town_rooms():
    """Create the town area (6-8 rooms in east-west direction)"""
    print("Creating town rooms...")
    
    # Town rooms from west to east
    town_rooms = [
        {
            'name': 'Town Square West',
            'description': 'The western side of the bustling town square. A large fountain sits in the center, and you can see shops and buildings stretching to the east. To the west, a path leads toward an old graveyard.',
            'exits': {'east': 3, 'west': 10}  # Will be updated with actual IDs
        },
        {
            'name': 'Town Square Center', 
            'description': 'The heart of the town, where merchants and travelers gather around an ornate fountain. The town hall stands majestically to the north, while shops line the streets to the east and west.',
            'exits': {'east': 4, 'west': 2, 'north': 5, 'south': 6}
        },
        {
            'name': 'Town Square East',
            'description': 'The eastern edge of the town square. Here the cobblestones give way to a dirt path that leads toward a dense forest. The sounds of the town fade as you look eastward.',
            'exits': {'west': 3, 'east': 19, 'north': 7}  # Forest starts at 19
        },
        {
            'name': 'Town Hall',
            'description': 'A grand building with marble columns and ornate decorations. This is where the town council meets and important announcements are made.',
            'exits': {'south': 3}
        },
        {
            'name': 'Market Street',
            'description': 'A busy street lined with shops and stalls. Merchants hawk their wares while customers browse for goods and supplies.',
            'exits': {'north': 3, 'east': 8, 'west': 9}
        },
        {
            'name': 'Residential District',
            'description': 'A quiet area where the townspeople live. Small houses with well-tended gardens line the peaceful streets.',
            'exits': {'south': 4}
        },
        {
            'name': 'Blacksmith Quarter',
            'description': 'The sound of hammering on anvils echoes through this district. Smoke rises from several forges where skilled craftsmen work.',
            'exits': {'west': 6}
        },
        {
            'name': 'Inn District',
            'description': 'A cozy area with several inns and taverns. The warm glow of lanterns and the sound of laughter spill out onto the streets.',
            'exits': {'east': 6}
        }
    ]
    
    async with db.pool.acquire() as conn:
        for i, room in enumerate(town_rooms, start=2):  # Start from ID 2
            await conn.execute("""
                INSERT INTO rooms (id, name, description, exits)
                VALUES ($1, $2, $3, $4)
            """, i, room['name'], room['description'], json.dumps(room['exits']))
    
    print("Town rooms created.")

async def create_forest_rooms():
    """Create the forest area (6-10 rooms in a circle)"""
    print("Creating forest rooms...")
    
    # Forest rooms arranged in a circle
    forest_rooms = [
        {
            'name': 'Forest Entrance',
            'description': 'The edge of a mysterious forest. Ancient trees tower overhead, their branches forming a canopy that filters the sunlight into dancing patterns on the forest floor.',
            'exits': {'west': 4, 'north': 20, 'east': 21}  # Connect to town
        },
        {
            'name': 'Forest Path North',
            'description': 'The northern path through the forest. Tall pines stretch toward the sky, and the ground is carpeted with fallen needles.',
            'exits': {'south': 19, 'west': 26, 'east': 22}
        },
        {
            'name': 'Forest Clearing',
            'description': 'A small clearing in the forest where wildflowers grow in abundance. The air is filled with the sweet scent of blooming flowers and the sound of buzzing insects.',
            'exits': {'west': 19, 'north': 22, 'south': 23}
        },
        {
            'name': 'Forest Thicket',
            'description': 'A dense thicket where the undergrowth grows wild. Thorny bushes and tangled vines make passage difficult, but you can hear the rustling of small creatures.',
            'exits': {'west': 20, 'south': 21}
        },
        {
            'name': 'Forest Stream',
            'description': 'A babbling brook winds through the forest here. The clear water reflects the sky above, and you can see small fish darting between the rocks.',
            'exits': {'north': 21, 'west': 24, 'south': 25}
        },
        {
            'name': 'Forest Grove',
            'description': 'A peaceful grove where deer often come to graze. Shafts of sunlight pierce through the canopy, illuminating patches of soft grass.',
            'exits': {'east': 23, 'south': 27, 'north': 26}
        },
        {
            'name': 'Forest Deep South',
            'description': 'The deepest part of the forest to the south. The trees grow thick here, and strange sounds echo from the shadows between the trunks.',
            'exits': {'north': 23, 'west': 27}
        },
        {
            'name': 'Forest Path West',
            'description': 'A winding path through the western part of the forest. The trees here are younger, and you can hear the distant sounds of the town.',
            'exits': {'south': 24, 'east': 20}
        },
        {
            'name': 'Forest Ancient Grove',
            'description': 'An ancient grove where the oldest trees in the forest stand. Their massive trunks are covered in moss, and the air feels heavy with old magic.',
            'exits': {'east': 25, 'north': 24}
        }
    ]
    
    async with db.pool.acquire() as conn:
        for i, room in enumerate(forest_rooms, start=19):  # Start from ID 19
            await conn.execute("""
                INSERT INTO rooms (id, name, description, exits)
                VALUES ($1, $2, $3, $4)
            """, i, room['name'], room['description'], json.dumps(room['exits']))
    
    print("Forest rooms created.")

async def create_graveyard_rooms():
    """Create the graveyard area (6-10 rooms)"""
    print("Creating graveyard rooms...")
    
    # Graveyard rooms
    graveyard_rooms = [
        {
            'name': 'Graveyard Entrance',
            'description': 'The entrance to an old graveyard. Weathered stone gates stand open, and a mist seems to cling to the ground between the ancient tombstones.',
            'exits': {'east': 2, 'north': 11, 'west': 12}  # Connect to town
        },
        {
            'name': 'Graveyard Old Section',
            'description': 'The oldest part of the graveyard, where the tombstones are so weathered that the names can barely be read. Ancient oak trees cast long shadows.',
            'exits': {'south': 10, 'west': 13, 'north': 14}
        },
        {
            'name': 'Graveyard Chapel',
            'description': 'A small, crumbling chapel sits among the graves. Its windows are broken, and ivy climbs up its stone walls. An eerie silence pervades the area.',
            'exits': {'east': 10, 'north': 13, 'south': 17}
        },
        {
            'name': 'Graveyard Crypts',
            'description': 'A section of the graveyard filled with stone crypts and mausoleums. Some of the doors hang open, revealing dark interiors.',
            'exits': {'south': 12, 'east': 11, 'north': 15}
        },
        {
            'name': 'Graveyard Mausoleum',
            'description': 'A grand mausoleum stands here, larger than all the others. Its marble facade is stained with age, and strange symbols are carved into its walls.',
            'exits': {'south': 11, 'west': 15}
        },
        {
            'name': 'Graveyard Haunted',
            'description': 'The most unsettling part of the graveyard. The air is cold here, and you feel as though unseen eyes are watching you from the shadows.',
            'exits': {'south': 13, 'east': 14, 'west': 16}
        },
        {
            'name': 'Graveyard Deep',
            'description': 'The deepest part of the graveyard, where the oldest and most mysterious graves lie. The mist is thickest here, and strange sounds echo in the distance.',
            'exits': {'east': 15, 'south': 17}
        },
        {
            'name': 'Graveyard Forgotten',
            'description': 'A forgotten corner of the graveyard where unmarked graves and broken monuments tell stories of those lost to time.',
            'exits': {'north': 16, 'east': 12}
        }
    ]
    
    async with db.pool.acquire() as conn:
        for i, room in enumerate(graveyard_rooms, start=10):  # Start from ID 10
            await conn.execute("""
                INSERT INTO rooms (id, name, description, exits)
                VALUES ($1, $2, $3, $4)
            """, i, room['name'], room['description'], json.dumps(room['exits']))
    
    print("Graveyard rooms created.")

async def create_monsters():
    """Create monsters for the forest and graveyard"""
    print("Creating monsters...")
    
    # Forest monsters (easy to medium difficulty)
    forest_monsters = [
        {
            'name': 'Forest Wolf',
            'description': 'A lean gray wolf with piercing yellow eyes. Its fur is matted and it looks hungry.',
            'level': 2,
            'health': 25,
            'max_health': 25,
            'attack': 8,
            'defense': 3,
            'experience_reward': 15,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '2-4', 'chance': 80},
                {'item': 'Gold Coin', 'quantity': '1', 'chance': 20}
            ]
        },
        {
            'name': 'Giant Spider',
            'description': 'A massive spider with hairy legs and venomous fangs. Its eight eyes glisten in the dim forest light.',
            'level': 3,
            'health': 30,
            'max_health': 30,
            'attack': 10,
            'defense': 2,
            'experience_reward': 20,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '3-5', 'chance': 75},
                {'item': 'Gold Coin', 'quantity': '1-2', 'chance': 25}
            ]
        },
        {
            'name': 'Forest Bear',
            'description': 'A large brown bear with powerful claws and a fierce temperament. It stands on its hind legs, towering above you.',
            'level': 5,
            'health': 60,
            'max_health': 60,
            'attack': 15,
            'defense': 8,
            'experience_reward': 40,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '5-8', 'chance': 90},
                {'item': 'Gold Coin', 'quantity': '2-3', 'chance': 50},
                {'item': 'Platinum Coin', 'quantity': '1', 'chance': 10}
            ]
        }
    ]
    
    # Graveyard monsters (medium to hard difficulty)
    graveyard_monsters = [
        {
            'name': 'Skeleton Warrior',
            'description': 'The animated bones of a long-dead warrior. It clutches a rusty sword and its empty eye sockets glow with an eerie light.',
            'level': 4,
            'health': 40,
            'max_health': 40,
            'attack': 12,
            'defense': 6,
            'experience_reward': 30,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '4-6', 'chance': 85},
                {'item': 'Gold Coin', 'quantity': '1-2', 'chance': 40}
            ]
        },
        {
            'name': 'Restless Spirit',
            'description': 'A translucent figure that phases in and out of visibility. Its mournful wails echo through the graveyard.',
            'level': 6,
            'health': 45,
            'max_health': 45,
            'attack': 14,
            'defense': 4,
            'experience_reward': 45,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '6-9', 'chance': 80},
                {'item': 'Gold Coin', 'quantity': '2-4', 'chance': 60},
                {'item': 'Platinum Coin', 'quantity': '1', 'chance': 15}
            ]
        },
        {
            'name': 'Grave Wraith',
            'description': 'A powerful undead creature wreathed in shadows. Its touch drains the life from the living.',
            'level': 8,
            'health': 80,
            'max_health': 80,
            'attack': 18,
            'defense': 10,
            'experience_reward': 70,
            'loot_table': [
                {'item': 'Silver Coin', 'quantity': '8-12', 'chance': 95},
                {'item': 'Gold Coin', 'quantity': '3-5', 'chance': 75},
                {'item': 'Platinum Coin', 'quantity': '1-2', 'chance': 25}
            ]
        }
    ]
    
    all_monsters = forest_monsters + graveyard_monsters
    
    async with db.pool.acquire() as conn:
        for monster in all_monsters:
            await conn.execute("""
                INSERT INTO monsters (name, description, level, health, max_health, attack, defense, experience_reward, loot_table, properties)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, 
                monster['name'], monster['description'], monster['level'],
                monster['health'], monster['max_health'], monster['attack'],
                monster['defense'], monster['experience_reward'], json.dumps(monster['loot_table']),
                json.dumps({})  # Empty properties
            )
    
    print("Monsters created.")

async def update_starting_room():
    """Update the starting room to connect to the town"""
    print("Updating starting room...")
    
    async with db.pool.acquire() as conn:
        # Update the original starting room to connect to town square center
        await conn.execute("""
            UPDATE rooms 
            SET name = $1, description = $2, exits = $3
            WHERE id = 1
        """, 
            'Town Outskirts',
            'You stand at the outskirts of a bustling town. To the north, you can see the town square with its central fountain and busy marketplace.',
            json.dumps({'north': 3})  # Connect to Town Square Center
        )
    
    print("Starting room updated.")

async def main():
    """Main function to create the world"""
    print("=== SSH RPG World Creation ===")
    
    # Connect to database
    success = await db.connect()
    if not success:
        print("Failed to connect to database. Exiting.")
        sys.exit(1)
    
    try:
        # Ensure tables exist
        await db.create_tables()
        
        # Clean up existing data
        await clean_database()
        
        # Create currency system
        await create_currency_items()
        
        # Create world areas
        await create_town_rooms()
        await create_forest_rooms()
        await create_graveyard_rooms()
        
        # Create monsters
        await create_monsters()
        
        # Update starting room
        await update_starting_room()
        
        print("\n=== World Creation Complete ===")
        print("Created areas:")
        print("- Town: 8 rooms (IDs 2-9)")
        print("- Graveyard: 8 rooms (IDs 10-17)")
        print("- Forest: 9 rooms (IDs 19-27)")
        print("- Currency: Silver, Gold, Platinum coins")
        print("- Monsters: 6 different types with loot tables")
        print("\nThe world is ready for adventure!")
        
    except Exception as e:
        print(f"Error creating world: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())