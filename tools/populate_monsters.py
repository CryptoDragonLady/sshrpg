#!/usr/bin/env python3
"""
Script to populate rooms with monsters and fix monster-related issues
"""

import asyncio
import json
import random
import sys
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db

async def populate_forest_monsters():
    """Add monsters to forest rooms"""
    print("Populating forest with monsters...")
    
    # Forest monster IDs (from create_world.py)
    forest_wolf_id = 12
    giant_spider_id = 13
    forest_bear_id = 14
    
    # Forest room IDs and their monster assignments
    forest_monster_assignments = {
        20: [forest_wolf_id],  # Forest Path North - Wolf
        21: [giant_spider_id],  # Forest Clearing - Spider
        22: [forest_wolf_id],  # Forest Thicket - Wolf
        23: [giant_spider_id],  # Forest Stream - Spider
        24: [forest_wolf_id, giant_spider_id],  # Forest Grove - Wolf + Spider
        25: [forest_bear_id],  # Forest Deep South - Bear
        26: [forest_wolf_id],  # Forest Path West - Wolf
        27: [forest_bear_id, forest_wolf_id],  # Forest Ancient Grove - Bear + Wolf
    }
    
    async with db.pool.acquire() as conn:
        for room_id, monster_ids in forest_monster_assignments.items():
            await conn.execute("""
                UPDATE rooms 
                SET monsters = $1
                WHERE id = $2
            """, json.dumps(monster_ids), room_id)
            
            room = await conn.fetchrow("SELECT name FROM rooms WHERE id = $1", room_id)
            monster_names = []
            for mid in monster_ids:
                monster = await conn.fetchrow("SELECT name FROM monsters WHERE id = $1", mid)
                if monster:
                    monster_names.append(monster['name'])
            print(f"  Added to {room['name']}: {', '.join(monster_names)}")

async def populate_graveyard_monsters():
    """Add monsters to graveyard rooms"""
    print("Populating graveyard with monsters...")
    
    # Graveyard monster IDs
    skeleton_warrior_id = 15
    restless_spirit_id = 16
    grave_wraith_id = 17
    
    # Graveyard room IDs and their monster assignments
    graveyard_monster_assignments = {
        11: [skeleton_warrior_id],  # Graveyard Old Section - Skeleton
        12: [restless_spirit_id],  # Graveyard Chapel - Spirit
        13: [skeleton_warrior_id, restless_spirit_id],  # Graveyard Crypts - Skeleton + Spirit
        14: [restless_spirit_id],  # Graveyard Mausoleum - Spirit
        15: [grave_wraith_id],  # Graveyard Haunted - Wraith
        16: [grave_wraith_id, skeleton_warrior_id],  # Graveyard Deep - Wraith + Skeleton
        17: [grave_wraith_id, restless_spirit_id],  # Graveyard Forgotten - Wraith + Spirit
    }
    
    async with db.pool.acquire() as conn:
        for room_id, monster_ids in graveyard_monster_assignments.items():
            await conn.execute("""
                UPDATE rooms 
                SET monsters = $1
                WHERE id = $2
            """, json.dumps(monster_ids), room_id)
            
            room = await conn.fetchrow("SELECT name FROM rooms WHERE id = $1", room_id)
            monster_names = []
            for mid in monster_ids:
                monster = await conn.fetchrow("SELECT name FROM monsters WHERE id = $1", mid)
                if monster:
                    monster_names.append(monster['name'])
            print(f"  Added to {room['name']}: {', '.join(monster_names)}")

async def create_room_monster_instances():
    """Create individual monster instances for each room"""
    print("Creating room monster instances...")
    
    # Get all rooms with monsters
    async with db.pool.acquire() as conn:
        rooms = await conn.fetch("SELECT id, name, monsters FROM rooms WHERE monsters != '[]'")
        
        for room in rooms:
            room_id = room['id']
            room_name = room['name']
            monsters = json.loads(room['monsters']) if room['monsters'] else []
            
            for monster_id in monsters:
                # Get monster base stats
                monster = await conn.fetchrow("SELECT * FROM monsters WHERE id = $1", monster_id)
                if monster:
                    # Create instance with full health using the new database method
                    await db.create_room_monster(room_id, monster_id, monster['health'], monster['max_health'])
            
            print(f"  Created instances for {room_name}: {len(monsters)} monsters")

async def verify_monster_placement():
    """Verify that monsters are properly placed in rooms"""
    print("\nVerifying monster placement...")
    
    async with db.pool.acquire() as conn:
        rooms_with_monsters = await conn.fetch("""
            SELECT id, name, monsters, properties
            FROM rooms 
            WHERE monsters IS NOT NULL AND monsters != '[]' AND monsters != '{}'
            ORDER BY id
        """)
        
        total_rooms = len(rooms_with_monsters)
        total_monsters = 0
        
        for room in rooms_with_monsters:
            monster_ids = json.loads(room['monsters']) if isinstance(room['monsters'], str) else room['monsters']
            total_monsters += len(monster_ids)
            
            monster_names = []
            for mid in monster_ids:
                monster = await conn.fetchrow("SELECT name FROM monsters WHERE id = $1", mid)
                if monster:
                    monster_names.append(monster['name'])
            
            print(f"  Room {room['id']} ({room['name']}): {', '.join(monster_names)}")
        
        print(f"\nSummary:")
        print(f"  Rooms with monsters: {total_rooms}")
        print(f"  Total monster placements: {total_monsters}")

async def main():
    """Main function to populate monsters"""
    print("=== Monster Population Script ===")
    
    # Connect to database
    success = await db.connect()
    if not success:
        print("Failed to connect to database. Exiting.")
        sys.exit(1)
    
    # Create tables (including room_monsters)
    await db.create_tables()
    
    try:
        # Populate monsters in rooms first
        await populate_forest_monsters()
        await populate_graveyard_monsters()
        
        # Create room monster instances
        await create_room_monster_instances()
        
        # Verify placement
        await verify_monster_placement()
        
        print("\n=== Monster Population Complete ===")
        print("Monsters have been added to forest and graveyard rooms.")
        print("Players can now encounter and fight monsters!")
        
    except Exception as e:
        print(f"Error populating monsters: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())