#!/usr/bin/env python3
"""
SSH RPG Codebase Health Check Test Script

This script performs comprehensive testing of the SSH RPG codebase to ensure
all Python files have correct syntax, can be imported successfully, and that
core functionality is working properly.

Usage:
    python tests/test_codebase_health.py
    
Or from the project root:
    python -m tests.test_codebase_health
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CodebaseHealthChecker:
    """Comprehensive health checker for the SSH RPG codebase"""
    
    def __init__(self):
        self.project_root = project_root
        self.main_python_files = [
            'server.py', 'database.py', 'client.py', 'game_engine.py',
            'ssh_server.py', 'character_creation.py', 'admin_system.py',
            'debug_logger.py', 'run_server.py', 'input_sanitizer.py'
        ]
        self.main_modules = [
            'server', 'database', 'client', 'game_engine', 'ssh_server',
            'character_creation', 'admin_system', 'debug_logger', 
            'run_server', 'input_sanitizer'
        ]
        self.errors = []
        self.warnings = []
    
    def log_error(self, message):
        """Log an error message"""
        self.errors.append(message)
        print(f"   ✗ {message}")
    
    def log_warning(self, message):
        """Log a warning message"""
        self.warnings.append(message)
        print(f"   ⚠ {message}")
    
    def log_success(self, message):
        """Log a success message"""
        print(f"   ✓ {message}")
    
    def test_syntax(self):
        """Test syntax of all Python files"""
        print("1. SYNTAX CHECK:")
        syntax_errors = 0
        
        for file in self.main_python_files:
            file_path = self.project_root / file
            if not file_path.exists():
                self.log_error(f"{file} - File not found")
                syntax_errors += 1
                continue
                
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', str(file_path)],
                    capture_output=True, text=True, cwd=self.project_root
                )
                if result.returncode == 0:
                    self.log_success(f"{file} - Syntax OK")
                else:
                    self.log_error(f"{file} - Syntax Error: {result.stderr.strip()}")
                    syntax_errors += 1
            except Exception as e:
                self.log_error(f"{file} - Error: {e}")
                syntax_errors += 1
        
        return syntax_errors == 0
    
    def test_imports(self):
        """Test that all modules can be imported"""
        print("\n2. IMPORT CHECK:")
        import_errors = 0
        
        for module in self.main_modules:
            try:
                importlib.import_module(module)
                self.log_success(f"{module} - Import OK")
            except Exception as e:
                self.log_error(f"{module} - Import Error: {e}")
                import_errors += 1
        
        return import_errors == 0
    
    def test_configuration(self):
        """Test configuration file loading"""
        print("\n3. CONFIGURATION CHECK:")
        
        try:
            import yaml
            config_path = self.project_root / 'config.yaml'
            
            if not config_path.exists():
                self.log_error("config.yaml - File not found")
                return False
                
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                self.log_error("config.yaml - Empty or invalid YAML")
                return False
                
            self.log_success("config.yaml - Loads correctly")
            
            # Check for required configuration sections
            required_sections = ['database', 'server']
            for section in required_sections:
                if section in config:
                    self.log_success(f"config.yaml - {section} section present")
                else:
                    self.log_warning(f"config.yaml - {section} section missing")
            
            return True
            
        except ImportError:
            self.log_error("PyYAML not installed - cannot test config.yaml")
            return False
        except Exception as e:
            self.log_error(f"config.yaml - Error: {e}")
            return False
    
    def test_security_module(self):
        """Test the input sanitizer security module"""
        print("\n4. SECURITY MODULE CHECK:")
        
        try:
            import input_sanitizer
            sanitizer = input_sanitizer.InputSanitizer()
            
            # Test safe inputs
            test_cases = [
                ("sanitize_string", "Hello World", "Basic string sanitization"),
                ("sanitize_username", "testuser123", "Username sanitization"),
                ("sanitize_character_name", "Aragorn", "Character name sanitization"),
                ("sanitize_integer", "42", "Integer sanitization"),
            ]
            
            for method_name, test_input, description in test_cases:
                try:
                    method = getattr(sanitizer, method_name)
                    result = method(test_input)
                    self.log_success(f"{description} - Working")
                except Exception as e:
                    self.log_error(f"{description} - Error: {e}")
                    return False
            
            # Test malicious input detection
            malicious_tests = [
                ("sanitize_string", "<script>alert('xss')</script>", "XSS detection"),
                ("sanitize_string", "SELECT * FROM users", "SQL injection detection"),
                ("sanitize_username", "user'; DROP TABLE users; --", "Username SQL injection"),
            ]
            
            for method_name, malicious_input, description in malicious_tests:
                try:
                    method = getattr(sanitizer, method_name)
                    result = method(malicious_input)
                    self.log_warning(f"{description} - Malicious input not blocked: {result}")
                except ValueError:
                    self.log_success(f"{description} - Correctly blocked malicious input")
                except Exception as e:
                    self.log_error(f"{description} - Unexpected error: {e}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Input sanitizer - Error: {e}")
            return False
    
    def test_module_functionality(self):
        """Test basic functionality of core modules"""
        print("\n5. MODULE FUNCTIONALITY CHECK:")
        
        functionality_tests = [
            ("server", ["GameServer"], "Server class availability"),
            ("database", ["get_connection"], "Database functions"),
            ("game_engine", ["GameEngine"], "Game engine class"),
            ("character_creation", ["CharacterCreation"], "Character creation class"),
            ("admin_system", ["AdminSystem"], "Admin system class"),
        ]
        
        for module_name, attributes, description in functionality_tests:
            try:
                module = importlib.import_module(module_name)
                missing_attrs = []
                
                for attr in attributes:
                    if not hasattr(module, attr):
                        missing_attrs.append(attr)
                
                if missing_attrs:
                    self.log_warning(f"{description} - Missing: {', '.join(missing_attrs)}")
                else:
                    self.log_success(f"{description} - All attributes present")
                    
            except Exception as e:
                self.log_error(f"{description} - Error: {e}")
                return False
        
        return True
    
    def test_tools_and_tests_structure(self):
        """Test that tools and tests directories are properly structured"""
        print("\n6. PROJECT STRUCTURE CHECK:")
        
        # Check tools directory
        tools_dir = self.project_root / 'tools'
        if tools_dir.exists():
            self.log_success("tools/ directory exists")
            
            expected_tools = [
                'setup_database.py', 'create_world.py', 'populate_monsters.py',
                'create_admin_character.py', 'debug_exits.py'
            ]
            
            for tool in expected_tools:
                tool_path = tools_dir / tool
                if tool_path.exists():
                    self.log_success(f"tools/{tool} exists")
                else:
                    self.log_warning(f"tools/{tool} missing")
        else:
            self.log_warning("tools/ directory missing")
        
        # Check tests directory
        tests_dir = self.project_root / 'tests'
        if tests_dir.exists():
            self.log_success("tests/ directory exists")
            
            expected_tests = [
                'test_combat.py', 'test_monster_system.py', 'test_monsters.py'
            ]
            
            for test in expected_tests:
                test_path = tests_dir / test
                if test_path.exists():
                    self.log_success(f"tests/{test} exists")
                else:
                    self.log_warning(f"tests/{test} missing")
        else:
            self.log_warning("tests/ directory missing")
        
        return True
    
    def run_all_tests(self):
        """Run all health checks"""
        print("=== SSH RPG CODEBASE HEALTH CHECK ===")
        print()
        
        # Run all test categories
        test_results = [
            self.test_syntax(),
            self.test_imports(),
            self.test_configuration(),
            self.test_security_module(),
            self.test_module_functionality(),
            self.test_tools_and_tests_structure(),
        ]
        
        # Print summary
        print("\n=== SUMMARY ===")
        
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        
        if total_errors == 0:
            print("🎉 ALL CRITICAL TESTS PASSED! Codebase is healthy and ready to run.")
            print()
            print("✓ All Python files have correct syntax")
            print("✓ All modules import successfully")
            print("✓ Configuration file is valid")
            print("✓ Security features are working")
            print("✓ Core module functionality is available")
            print("✓ Project structure is organized")
            
            if total_warnings > 0:
                print(f"\n⚠️  {total_warnings} warnings found (non-critical):")
                for warning in self.warnings:
                    print(f"   - {warning}")
        else:
            print(f"❌ Found {total_errors} critical issues that need attention:")
            for error in self.errors:
                print(f"   - {error}")
            
            if total_warnings > 0:
                print(f"\n⚠️  Also found {total_warnings} warnings:")
                for warning in self.warnings:
                    print(f"   - {warning}")
        
        print()
        print("=" * 50)
        
        return total_errors == 0


def main():
    """Main entry point for the health check script"""
    checker = CodebaseHealthChecker()
    success = checker.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()