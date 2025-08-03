#!/usr/bin/env python3

import asyncio
import asyncpg
import json

async def debug_exits():
    """Debug the exits issue by checking the database directly"""
    
    # Connect to database
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='password',
        database='sshrpg'
    )
    
    try:
        # Get room data
        room = await conn.fetchrow("SELECT * FROM rooms WHERE id = 1")
        print(f"Room 1 data: {dict(room)}")
        
        exits = room['exits'] if room else None
        print(f"Exits type: {type(exits)}")
        print(f"Exits value: {exits}")
        print(f"Exits repr: {repr(exits)}")
        
        # Test the parsing logic
        if isinstance(exits, str):
            print("Exits is a string, attempting to parse...")
            try:
                parsed_exits = json.loads(exits)
                print(f"Parsed exits: {parsed_exits}")
                print(f"Parsed exits type: {type(parsed_exits)}")
                if isinstance(parsed_exits, dict):
                    print(f"Keys: {list(parsed_exits.keys())}")
                else:
                    print("Parsed exits is not a dict!")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"JSON parsing failed: {e}")
        else:
            print("Exits is not a string")
            if hasattr(exits, 'keys'):
                print(f"Keys: {list(exits.keys())}")
            else:
                print("Exits has no keys method")
                
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_exits())