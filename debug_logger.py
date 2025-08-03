#!/usr/bin/env python3
"""
Debug Logging System for SSH RPG Server
Provides configurable debug logging with different verbosity levels and component filtering
"""

import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class DebugLogger:
    """Configurable debug logging system"""
    
    # Verbosity levels
    MINIMAL = 0
    NORMAL = 1
    VERBOSE = 2
    VERY_VERBOSE = 3
    
    def __init__(self):
        self.enabled = False
        self.verbosity = self.NORMAL
        self.components = {
            'admin_commands': True,
            'database': False,
            'game_engine': False,
            'server': False,
            'character_creation': False,
            'combat': False
        }
        self.output_console = True
        self.output_file = False
        self.file_path = "debug.log"
        self._file_handle = None
    
    def configure(self, config: Dict[str, Any]):
        """Configure debug logger from config dictionary"""
        debug_config = config.get('debug', {})
        
        self.enabled = debug_config.get('enabled', False)
        self.verbosity = debug_config.get('verbosity', self.NORMAL)
        
        # Update component settings
        components_config = debug_config.get('components', {})
        for component, enabled in components_config.items():
            if component in self.components:
                self.components[component] = enabled
        
        # Update output settings
        output_config = debug_config.get('output', {})
        self.output_console = output_config.get('console', True)
        self.output_file = output_config.get('file', False)
        self.file_path = output_config.get('file_path', "debug.log")
        
        # Open file if needed
        if self.output_file and self.enabled:
            self._open_file()
    
    def enable(self, verbosity: int = NORMAL):
        """Enable debug logging with specified verbosity"""
        self.enabled = True
        self.verbosity = verbosity
        if self.output_file:
            self._open_file()
    
    def disable(self):
        """Disable debug logging"""
        self.enabled = False
        self._close_file()
    
    def set_component(self, component: str, enabled: bool):
        """Enable/disable logging for a specific component"""
        if component in self.components:
            self.components[component] = enabled
    
    def _open_file(self):
        """Open debug log file"""
        try:
            self._file_handle = open(self.file_path, 'a', encoding='utf-8')
            self._write_to_file(f"\n=== Debug session started at {datetime.now()} ===\n")
        except Exception as e:
            print(f"Warning: Could not open debug log file {self.file_path}: {e}")
            self.output_file = False
    
    def _close_file(self):
        """Close debug log file"""
        if self._file_handle:
            try:
                self._write_to_file(f"=== Debug session ended at {datetime.now()} ===\n")
                self._file_handle.close()
            except:
                pass
            self._file_handle = None
    
    def _write_to_file(self, message: str):
        """Write message to debug file"""
        if self._file_handle:
            try:
                self._file_handle.write(message)
                self._file_handle.flush()
            except:
                pass
    
    def _format_message(self, component: str, message: str, level: int) -> str:
        """Format debug message with timestamp and component"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        level_str = ["MIN", "NOR", "VER", "VVR"][min(level, 3)]
        return f"[{timestamp}] DEBUG-{level_str} [{component.upper()}] {message}"
    
    def log(self, component: str, message: str, level: int = NORMAL):
        """Log a debug message"""
        if not self.enabled:
            return
        
        # Check if component is enabled
        if component not in self.components or not self.components[component]:
            return
        
        # Check verbosity level
        if level > self.verbosity:
            return
        
        formatted_message = self._format_message(component, message, level)
        
        # Output to console
        if self.output_console:
            print(formatted_message)
        
        # Output to file
        if self.output_file:
            self._write_to_file(formatted_message + "\n")
    
    def admin(self, message: str, level: int = NORMAL):
        """Log admin command debug message"""
        self.log('admin_commands', message, level)
    
    def database(self, message: str, level: int = NORMAL):
        """Log database debug message"""
        self.log('database', message, level)
    
    def game_engine(self, message: str, level: int = NORMAL):
        """Log game engine debug message"""
        self.log('game_engine', message, level)
    
    def server(self, message: str, level: int = NORMAL):
        """Log server debug message"""
        self.log('server', message, level)
    
    def character_creation(self, message: str, level: int = NORMAL):
        """Log character creation debug message"""
        self.log('character_creation', message, level)
    
    def combat(self, message: str, level: int = NORMAL):
        """Log combat debug message"""
        self.log('combat', message, level)
    
    def get_status(self) -> str:
        """Get current debug logger status"""
        if not self.enabled:
            return "Debug logging: DISABLED"
        
        verbosity_names = ["MINIMAL", "NORMAL", "VERBOSE", "VERY_VERBOSE"]
        verbosity_name = verbosity_names[min(self.verbosity, 3)]
        
        enabled_components = [comp for comp, enabled in self.components.items() if enabled]
        
        status = f"Debug logging: ENABLED (Verbosity: {verbosity_name})\n"
        status += f"Components: {', '.join(enabled_components) if enabled_components else 'None'}\n"
        status += f"Output: Console={self.output_console}, File={self.output_file}"
        if self.output_file:
            status += f" ({self.file_path})"
        
        return status

# Global debug logger instance
debug_logger = DebugLogger()

# Convenience functions for easy access
def debug_admin(message: str, level: int = DebugLogger.NORMAL):
    """Log admin command debug message"""
    debug_logger.admin(message, level)

def debug_database(message: str, level: int = DebugLogger.NORMAL):
    """Log database debug message"""
    debug_logger.database(message, level)

def debug_game_engine(message: str, level: int = DebugLogger.NORMAL):
    """Log game engine debug message"""
    debug_logger.game_engine(message, level)

def debug_server(message: str, level: int = DebugLogger.NORMAL):
    """Log server debug message"""
    debug_logger.server(message, level)

def debug_character_creation(message: str, level: int = DebugLogger.NORMAL):
    """Log character creation debug message"""
    debug_logger.character_creation(message, level)

def debug_combat(message: str, level: int = DebugLogger.NORMAL):
    """Log combat debug message"""
    debug_logger.combat(message, level)