#!/bin/bash

# Test script to verify prompts are sent BEFORE user input (proper MUD behavior)
# This script connects to the TCP server and validates prompt placement

echo "Testing correct prompt placement (prompts BEFORE commands)..."

# Create a temporary file to capture all output
TEST_OUTPUT="/tmp/prompt_test_output.txt"
rm -f "$TEST_OUTPUT"

# Function to test prompt placement
test_prompt_placement() {
    echo "Connecting to TCP server and testing prompt placement..."
    
    # Use expect to interact with the server and capture timing
    expect << 'EOF' > "$TEST_OUTPUT" 2>&1
set timeout 10
spawn telnet localhost 2223

# Wait for initial connection
expect {
    "Username:" {
        send "testuser\r"
        exp_continue
    }
    "Password:" {
        send "testpass\r"
        exp_continue
    }
    "Enter your character name" {
        send "TestChar\r"
        exp_continue
    }
    "Choose your class" {
        send "1\r"
        exp_continue
    }
    "HP:" {
        # We've entered the game and should see a prompt
        puts "PROMPT_DETECTED_AFTER_ENTRY"
        
        # Now test if prompt appears BEFORE we send a command
        # Send a movement command
        send "east\r"
        
        # Check if we get a prompt after the command
        expect {
            "HP:" {
                puts "PROMPT_DETECTED_AFTER_FIRST_COMMAND"
                
                # Send another command
                send "west\r"
                
                expect {
                    "HP:" {
                        puts "PROMPT_DETECTED_AFTER_SECOND_COMMAND"
                        
                        # Exit the game
                        send "quit\r"
                        expect eof
                    }
                    timeout {
                        puts "TIMEOUT_WAITING_FOR_SECOND_PROMPT"
                        send "quit\r"
                        expect eof
                    }
                }
            }
            timeout {
                puts "TIMEOUT_WAITING_FOR_FIRST_PROMPT"
                send "quit\r"
                expect eof
            }
        }
    }
    timeout {
        puts "TIMEOUT_DURING_INITIAL_CONNECTION"
        exit 1
    }
}
EOF
}

# Run the test
test_prompt_placement

# Analyze the results
echo "\nAnalyzing test results..."
echo "Full output:"
cat "$TEST_OUTPUT"

echo "\n=== PROMPT PLACEMENT ANALYSIS ==="

# Check for proper prompt flow
if grep -q "PROMPT_DETECTED_AFTER_ENTRY" "$TEST_OUTPUT"; then
    echo "✓ Initial prompt detected after game entry"
else
    echo "✗ No initial prompt detected after game entry"
fi

if grep -q "PROMPT_DETECTED_AFTER_FIRST_COMMAND" "$TEST_OUTPUT"; then
    echo "✓ Prompt detected after first command"
else
    echo "✗ No prompt detected after first command"
fi

if grep -q "PROMPT_DETECTED_AFTER_SECOND_COMMAND" "$TEST_OUTPUT"; then
    echo "✓ Prompt detected after second command"
else
    echo "✗ No prompt detected after second command"
fi

# Check for timeouts (indicating missing prompts)
if grep -q "TIMEOUT" "$TEST_OUTPUT"; then
    echo "✗ Timeout detected - prompts may not be appearing when expected"
    grep "TIMEOUT" "$TEST_OUTPUT"
else
    echo "✓ No timeouts - prompts appearing as expected"
fi

echo "\n=== EXPECTED BEHAVIOR ==="
echo "In a proper MUD:"
echo "1. Player sees prompt BEFORE typing command"
echo "2. Player types command and presses enter"
echo "3. Server processes command and shows results"
echo "4. Server shows NEW prompt reflecting updated status"
echo "5. Cycle repeats"

echo "\n=== CURRENT BEHAVIOR ANALYSIS ==="
echo "Based on debug output, we need to verify:"
echo "- Prompts appear BEFORE user input (not after command processing)"
echo "- Each command cycle: PROMPT -> USER_INPUT -> COMMAND_RESULT -> NEW_PROMPT"

# Clean up
rm -f "$TEST_OUTPUT"

echo "\nTest completed. Check server debug output for detailed timing information."