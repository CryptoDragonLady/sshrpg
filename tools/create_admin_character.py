#!/usr/bin/env python3
"""
Script to create a character for the admin account
"""
import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database
from character_creation import CharacterCreation

async def create_admin_character():
    """Create a character for the admin account"""
    # Initialize database
    db = Database()
    await db.connect()
    
    # Check if admin user exists and get their ID
    user = await db.authenticate_user("admin", "admin123")
    if not user:
        print("Admin user not found!")
        return
    
    user_id = user['id']
    print(f"Found admin user with ID: {user_id}")
    
    # Check if admin already has a character
    existing_char = await db.get_character(user_id)
    if existing_char:
        print(f"Admin already has character: {existing_char['name']}")
        return
    
    # Create a character for the admin
    character_data = CharacterCreation.create_character(
        name="AdminHero",
        race="human",
        char_class="warrior"
    )
    
    # Create character in database
    char_id = await db.create_character(
        user_id=user_id,
        name=character_data['name'],
        race=character_data['race'],
        char_class=character_data['class'],
        stats=character_data
    )
    
    print(f"Created character 'AdminHero' with ID: {char_id}")

if __name__ == "__main__":
    asyncio.run(create_admin_character())