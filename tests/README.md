# Tests Directory

This directory contains test files for the SSH RPG game system.

## Test Files

### `test_codebase_health.py` ⭐ **NEW**
Comprehensive health check script that validates the entire codebase:
- **Syntax Check**: Verifies all Python files compile without errors
- **Import Check**: Ensures all modules can be imported successfully
- **Configuration Check**: Validates config.yaml structure and content
- **Security Check**: Tests input sanitization and security features
- **Functionality Check**: Verifies core module functionality
- **Structure Check**: Validates project organization (tools/, tests/ directories)

**Usage:**
```bash
# Run from project root
python tests/test_codebase_health.py

# Or as a module
python -m tests.test_codebase_health
```

### `test_combat.py`
Tests the combat system functionality including:
- Combat mechanics
- Damage calculations
- Turn-based combat flow
- Monster interactions

### `test_monster_system.py`
Tests the monster system including:
- Monster spawning
- Monster behavior
- Monster stats and abilities
- Monster-player interactions

### `test_monsters.py`
Tests individual monster functionality:
- Monster creation
- Monster properties
- Monster special abilities
- Monster loot systems

## Running Tests

### Individual Test Files
```bash
# Run from project root
python tests/test_combat.py
python tests/test_monster_system.py
python tests/test_monsters.py
```

### All Tests (if using pytest)
```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_combat.py
```

## Test Structure

Tests are designed to:
- Verify core game mechanics work correctly
- Ensure database operations function properly
- Test edge cases and error conditions
- Validate game balance and fairness

## Dependencies

Tests may require additional dependencies:
```bash
pip install pytest  # For advanced test running
```

## Notes

- Tests should be run in a test environment, not production
- Some tests may require database setup
- Mock data is used where possible to avoid affecting real game data
- Tests help ensure code quality and prevent regressions