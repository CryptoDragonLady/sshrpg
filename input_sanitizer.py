"""
Input Sanitization Module for SSHRPG

This module provides comprehensive input sanitization to prevent SQL injection,
XSS attacks, and other security vulnerabilities.
"""

import re
import html
from typing import Any, Dict, List, Optional, Union


class InputSanitizer:
    """Comprehensive input sanitization for game commands and data"""
    
    # SQL injection patterns to detect and block
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\s)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"].*['\"])",
        r"(;|\|\||&&)",
        r"(\bxp_cmdshell\b)",
        r"(\bsp_executesql\b)",
        r"(\bEXEC\s*\()",
        r"(\bCAST\s*\()",
        r"(\bCONVERT\s*\()",
        r"(\bCHAR\s*\()",
        r"(\bASCII\s*\()",
        r"(\bSUBSTRING\s*\()",
        r"(\bLEN\s*\()",
        r"(\bCOUNT\s*\()",
        r"(\bSUM\s*\()",
        r"(\bAVG\s*\()",
        r"(\bMAX\s*\()",
        r"(\bMIN\s*\()",
        r"(\bGROUP\s+BY\b)",
        r"(\bORDER\s+BY\b)",
        r"(\bHAVING\b)",
        r"(\bLIMIT\b)",
        r"(\bOFFSET\b)"
    ]
    
    # XSS patterns to detect and block
    XSS_PATTERNS = [
        r"(<script[^>]*>.*?</script>)",
        r"(<iframe[^>]*>.*?</iframe>)",
        r"(<object[^>]*>.*?</object>)",
        r"(<embed[^>]*>)",
        r"(<link[^>]*>)",
        r"(<meta[^>]*>)",
        r"(<style[^>]*>.*?</style>)",
        r"(javascript:)",
        r"(vbscript:)",
        r"(onload=)",
        r"(onerror=)",
        r"(onclick=)",
        r"(onmouseover=)",
        r"(onfocus=)",
        r"(onblur=)",
        r"(onchange=)",
        r"(onsubmit=)",
        r"(onkeydown=)",
        r"(onkeyup=)",
        r"(onkeypress=)",
        r"(onmousedown=)",
        r"(onmouseup=)",
        r"(onmousemove=)",
        r"(onmouseout=)"
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(\||&|;|\$\(|\`)",
        r"(\bcat\b|\bls\b|\bpwd\b|\bwhoami\b|\bps\b|\btop\b|\bkill\b)",
        r"(\brm\b|\bmv\b|\bcp\b|\bchmod\b|\bchown\b|\bsu\b|\bsudo\b)",
        r"(\bwget\b|\bcurl\b|\bssh\b|\bscp\b|\brsync\b)",
        r"(\bnetcat\b|\bnc\b|\btelnet\b|\bnmap\b)",
        r"(\bpython\b|\bperl\b|\bruby\b|\bphp\b|\bnode\b|\bbash\b|\bsh\b|\bzsh\b)"
    ]
    
    # Valid database column names (whitelist approach)
    VALID_DB_COLUMNS = {
        'characters': {
            'name', 'race', 'class', 'level', 'experience', 'health', 'max_health',
            'mana', 'max_mana', 'strength', 'dexterity', 'constitution', 'intelligence',
            'wisdom', 'charisma', 'current_room', 'inventory', 'equipment', 'status_line'
        },
        'monsters': {
            'name', 'description', 'level', 'health', 'max_health', 'attack', 'defense',
            'experience_reward', 'loot_table', 'properties'
        },
        'items': {
            'name', 'description', 'item_type', 'properties', 'stats'
        },
        'rooms': {
            'name', 'description', 'exits', 'properties'
        },
        'users': {
            'username', 'access_level', 'last_login'
        }
    }
    
    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """
        Sanitize a string input for safe database storage and display
        
        Args:
            input_str: The input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags (escaped)
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If input contains malicious patterns
        """
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")
        
        # Trim whitespace and limit length
        sanitized = input_str.strip()[:max_length]
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError(f"Input contains potentially malicious SQL pattern: {pattern}")
        
        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError(f"Input contains potentially malicious XSS pattern: {pattern}")
        
        # Check for command injection patterns
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError(f"Input contains potentially malicious command injection pattern: {pattern}")
        
        # HTML escape if not allowing HTML
        if not allow_html:
            sanitized = html.escape(sanitized)
        
        return sanitized
    
    @classmethod
    def sanitize_username(cls, username: str) -> str:
        """Sanitize username input"""
        if not isinstance(username, str):
            raise ValueError("Username must be a string")
        
        username = username.strip()
        
        # Username specific validation
        if len(username) < 3 or len(username) > 20:
            raise ValueError("Username must be between 3 and 20 characters")
        
        # Only allow alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        
        return cls.sanitize_string(username, max_length=20)
    
    @classmethod
    def sanitize_character_name(cls, name: str) -> str:
        """Sanitize character name input"""
        if not isinstance(name, str):
            raise ValueError("Character name must be a string")
        
        name = name.strip()
        
        # Character name specific validation
        if len(name) < 2 or len(name) > 30:
            raise ValueError("Character name must be between 2 and 30 characters")
        
        # Allow letters, spaces, apostrophes, and hyphens
        if not re.match(r"^[a-zA-Z\s'\-]+$", name):
            raise ValueError("Character name can only contain letters, spaces, apostrophes, and hyphens")
        
        return cls.sanitize_string(name, max_length=30)
    
    @classmethod
    def sanitize_room_name(cls, name: str) -> str:
        """Sanitize room name input"""
        if not isinstance(name, str):
            raise ValueError("Room name must be a string")
        
        name = name.strip()
        
        if len(name) < 3 or len(name) > 50:
            raise ValueError("Room name must be between 3 and 50 characters")
        
        return cls.sanitize_string(name, max_length=50)
    
    @classmethod
    def sanitize_description(cls, description: str) -> str:
        """Sanitize description input"""
        if not isinstance(description, str):
            raise ValueError("Description must be a string")
        
        description = description.strip()
        
        if len(description) > 500:
            raise ValueError("Description must be 500 characters or less")
        
        return cls.sanitize_string(description, max_length=500)
    
    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """Sanitize chat/say message input"""
        if not isinstance(message, str):
            raise ValueError("Message must be a string")
        
        message = message.strip()
        
        if len(message) > 200:
            raise ValueError("Message must be 200 characters or less")
        
        return cls.sanitize_string(message, max_length=200)
    
    @classmethod
    def sanitize_status_line(cls, status_line: str) -> str:
        """Sanitize status line format string"""
        if not isinstance(status_line, str):
            raise ValueError("Status line must be a string")
        
        status_line = status_line.strip()
        
        if len(status_line) > 200:
            raise ValueError("Status line must be 200 characters or less")
        
        # Check for valid format variables only
        valid_vars = {
            'name', 'level', 'race', 'class', 'health', 'max_health', 'mana', 'max_mana',
            'experience', 'strength', 'dexterity', 'constitution', 'intelligence',
            'wisdom', 'charisma', 'room_name', 'room_id'
        }
        
        # Find all format variables in the string
        format_vars = re.findall(r'\{(\w+)\}', status_line)
        for var in format_vars:
            if var not in valid_vars:
                raise ValueError(f"Invalid status line variable: {var}")
        
        return cls.sanitize_string(status_line, max_length=200)
    
    @classmethod
    def validate_db_column(cls, table: str, column: str) -> bool:
        """Validate that a database column name is allowed"""
        if table not in cls.VALID_DB_COLUMNS:
            return False
        return column in cls.VALID_DB_COLUMNS[table]
    
    @classmethod
    def sanitize_integer(cls, value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        """Sanitize integer input"""
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValueError("Value must be a valid integer")
        
        if min_val is not None and int_val < min_val:
            raise ValueError(f"Value must be at least {min_val}")
        
        if max_val is not None and int_val > max_val:
            raise ValueError(f"Value must be at most {max_val}")
        
        return int_val
    
    @classmethod
    def sanitize_command_args(cls, args: List[str]) -> List[str]:
        """Sanitize command arguments"""
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str):
                sanitized_args.append(cls.sanitize_string(arg, max_length=100))
            else:
                sanitized_args.append(str(arg))
        return sanitized_args
    
    @classmethod
    def sanitize_json_string(cls, json_str: str) -> str:
        """Sanitize JSON string input"""
        if not isinstance(json_str, str):
            raise ValueError("JSON string must be a string")
        
        # Basic JSON validation patterns
        if not (json_str.strip().startswith('{') and json_str.strip().endswith('}')):
            raise ValueError("Invalid JSON format")
        
        return cls.sanitize_string(json_str, max_length=1000)


# Convenience functions for common sanitization tasks
def sanitize_user_input(input_str: str) -> str:
    """Quick sanitization for general user input"""
    return InputSanitizer.sanitize_string(input_str)

def sanitize_chat_message(message: str) -> str:
    """Quick sanitization for chat messages"""
    return InputSanitizer.sanitize_message(message)

def validate_admin_column_access(table: str, column: str) -> bool:
    """Validate admin access to database columns"""
    return InputSanitizer.validate_db_column(table, column)