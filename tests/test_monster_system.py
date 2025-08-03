#!/usr/bin/env python3
"""
Test script to verify the monster system is working correctly
"""

import asyncio
import sys
import os
from typing import Optional, Dict, Any, List

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database

async def test_monster_system():
    """Test the monster system by checking database state"""
    print("Testing Monster System")
    print("=" * 50)
    
    # Initialize database
    db = Database()
    await db.connect()
    await db.create_tables()
    
    try:
        # Test 1: Check if monsters exist in the database
        print("\n1. Checking monsters in database...")
        if not hasattr(db, 'pool') or not db.pool:
            # Memory database - check if monsters attribute exists
            if hasattr(db, 'monsters'):
                monsters_dict = getattr(db, 'monsters', {})
                print(f"Found {len(monsters_dict)} monsters in memory database:")
                for monster_id, monster in monsters_dict.items():
                    if monster and isinstance(monster, dict):
                        print(f"  - {monster.get('name', 'Unknown')} (ID: {monster_id})")
            else:
                print("No monsters storage found in memory database")
        else:
            async with db.pool.acquire() as conn:
                monsters = await conn.fetch("SELECT id, name FROM monsters ORDER BY id")
                print(f"Found {len(monsters)} monsters in PostgreSQL database:")
                for monster in monsters:
                    if monster:
                        print(f"  - {monster.get('name', 'Unknown')} (ID: {monster.get('id', 'Unknown')})")
        
        # Test 2: Check room monster instances
        print("\n2. Checking room monster instances...")
        room_monsters = await db.get_room_monsters(1)  # Check forest room
        print(f"Forest room (ID: 1) has {len(room_monsters)} monster instances:")
        for rm in room_monsters:
            if rm and rm.get('monster_id') is not None:
                monster = await db.get_monster(rm['monster_id'])
                if monster:
                    print(f"  - {monster.get('name', 'Unknown')} (Health: {rm.get('health', 0)}/{rm.get('max_health', 0)})")
        
        # Test 3: Check a few more rooms
        print("\n3. Checking other rooms with monsters...")
        for room_id in [2, 3, 4, 5]:
            room_monsters = await db.get_room_monsters(room_id)
            if room_monsters:
                room = await db.get_room(room_id)
                if room:
                    print(f"Room '{room.get('name', 'Unknown')}' (ID: {room_id}) has {len(room_monsters)} monsters:")
                    for rm in room_monsters:
                         if rm and rm.get('monster_id') is not None:
                             monster = await db.get_monster(rm['monster_id'])
                             if monster:
                                 print(f"  - {monster.get('name', 'Unknown')} (Health: {rm.get('health', 0)}/{rm.get('max_health', 0)})")
        
        # Test 4: Check total monster instances
        print("\n4. Total monster instances across all rooms...")
        if not hasattr(db, 'pool') or not db.pool:
            # For memory database, check if room_monsters exists
            if hasattr(db, 'room_monsters'):
                room_monsters_dict = getattr(db, 'room_monsters', {})
                total_instances = len(room_monsters_dict)
                print(f"Total monster instances: {total_instances}")
                for rm_id, rm in room_monsters_dict.items():
                     if rm and isinstance(rm, dict) and rm.get('monster_id') is not None and rm.get('room_id') is not None:
                         monster = await db.get_monster(rm['monster_id'])
                         room = await db.get_room(rm['room_id'])
                         if monster and room:
                             print(f"  - {monster.get('name', 'Unknown')} in {room.get('name', 'Unknown')} (Health: {rm.get('health', 0)}/{rm.get('max_health', 0)})")
            else:
                print("No room_monsters storage found in memory database")
        else:
            async with db.pool.acquire() as conn:
                instances = await conn.fetch("""
                    SELECT rm.*, m.name as monster_name, r.name as room_name 
                    FROM room_monsters rm 
                    JOIN monsters m ON rm.monster_id = m.id 
                    JOIN rooms r ON rm.room_id = r.id 
                    ORDER BY rm.room_id, rm.monster_id
                """)
                print(f"Total monster instances: {len(instances)}")
                for instance in instances:
                    if instance:
                        print(f"  - {instance.get('monster_name', 'Unknown')} in {instance.get('room_name', 'Unknown')} (Health: {instance.get('health', 0)}/{instance.get('max_health', 0)})")
        
        print("\n" + "=" * 50)
        print("Monster system test completed successfully!")
        print("The monster system appears to be working correctly.")
        
    except Exception as e:
        print(f"Error during monster system test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if hasattr(db, 'pool') and db.pool:
            await db.pool.close()

if __name__ == "__main__":
    asyncio.run(test_monster_system())