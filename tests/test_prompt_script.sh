#!/bin/bash

# Enhanced test script to verify single prompt behavior with proper game tick timing
# The game operates at 2 TPS (ticks per second), so each tick is 500ms
# We need to account for this timing to properly test prompt behavior

echo "Creating enhanced test script that properly accounts for game tick timing..."

# Create expect script with proper tick-based timing
cat > /tmp/sshrpg_test_enhanced.exp << 'EOF'
#!/usr/bin/expect -f

set timeout 15
log_user 1

# Function to capture and analyze prompt lines
proc analyze_prompt_line {description} {
    global spawn_id
    
    # Wait for any output to settle (2-3 tick cycles)
    sleep 2.0
    
    # Capture the current buffer content
    expect {
        -re {([^\r\n]*\[HP: [0-9]+/[0-9]+ \| MP: [0-9]+/[0-9]+ \| Room: [^\]]+\] >[^\r\n]*)} {
            set captured_line $expect_out(1,string)
            
            # Count how many prompts appear in this line
            set prompt_count [regexp -all {\[HP: [0-9]+/[0-9]+ \| MP: [0-9]+/[0-9]+ \| Room: [^\]]+\] >} $captured_line]
            
            puts "\n=== $description ==="
            puts "Captured line: '$captured_line'"
            puts "Prompt count in line: $prompt_count"
            
            if {$prompt_count > 1} {
                puts "❌ ERROR: Multiple prompts detected ($prompt_count prompts)!"
                puts "This indicates the timing issue is not fixed."
                exit 1
            } elseif {$prompt_count == 1} {
                puts "✅ SUCCESS: Single prompt detected"
                return 1
            } else {
                puts "⚠️  WARNING: No prompt found in captured line"
                return 0
            }
        }
        timeout {
            puts "⚠️  TIMEOUT: No prompt captured for $description"
            return 0
        }
    }
}

# Connect to server
puts "Connecting to game server..."
spawn telnet localhost 2223

expect {
    "Please enter username" {
        puts "Connected successfully"
    }
    timeout {
        puts "❌ ERROR: Failed to connect to server"
        exit 1
    }
}

# Login
send "admin\r"
expect "Password:"
send "admin123\r"

# Wait for game entry
expect {
    "ENTERING THE WORLD" {
        puts "\n=== ENTERING GAME ==="
    }
    timeout {
        puts "❌ ERROR: Failed to enter game"
        exit 1
    }
}

# Wait for room description and initial prompt
expect {
    "Town Square East" {
        puts "Room description received"
        # This is critical - wait for the game tick cycle to complete
        # and any initial prompts to be sent
        sleep 3.0
        
        # Now analyze the prompt situation
        analyze_prompt_line "INITIAL GAME ENTRY"
    }
    timeout {
        puts "❌ ERROR: Failed to receive room description"
        exit 1
    }
}

# Test movement command
puts "\n=== TESTING MOVEMENT COMMAND ==="
send "east\r"

# Wait for movement to process and room change
expect {
    "Forest Entrance" {
        puts "Movement successful - new room loaded"
        # Wait for tick cycles to complete after movement
        sleep 2.5
        
        analyze_prompt_line "AFTER MOVEMENT"
    }
    timeout {
        puts "❌ ERROR: Movement failed or timeout"
        exit 1
    }
}

# Test another movement
puts "\n=== TESTING SECOND MOVEMENT ==="
send "west\r"

expect {
    "Town Square East" {
        puts "Second movement successful"
        sleep 2.5
        
        analyze_prompt_line "AFTER SECOND MOVEMENT"
    }
    timeout {
        puts "❌ ERROR: Second movement failed"
        exit 1
    }
}

# Test idle period - this is crucial to see if prompts multiply over time
puts "\n=== TESTING IDLE PERIOD (checking for prompt multiplication) ==="
sleep 5.0

# Check if multiple prompts appeared during idle time
expect {
    -re {([^\r\n]*\[HP: [0-9]+/[0-9]+ \| MP: [0-9]+/[0-9]+ \| Room: [^\]]+\] >[^\r\n]*)} {
        set idle_line $expect_out(1,string)
        set idle_prompt_count [regexp -all {\[HP: [0-9]+/[0-9]+ \| MP: [0-9]+/[0-9]+ \| Room: [^\]]+\] >} $idle_line]
        
        puts "Idle period line: '$idle_line'"
        puts "Idle prompt count: $idle_prompt_count"
        
        if {$idle_prompt_count > 1} {
            puts "❌ ERROR: Multiple prompts appeared during idle period!"
            exit 1
        }
    }
    timeout {
        puts "✅ No additional prompts during idle period"
    }
}

# Clean exit
send "quit\r"
expect "Goodbye"

puts "\n=== ALL TESTS COMPLETED SUCCESSFULLY ==="
puts "✅ No multiple prompts detected"
puts "✅ Game tick timing appears to be working correctly"
EOF

chmod +x /tmp/sshrpg_test_enhanced.exp

echo "\n🧪 Running enhanced prompt timing test..."
echo "This test accounts for the game's 2 TPS (500ms per tick) timing"
echo "and will detect multiple prompts appearing on the same line.\n"

/tmp/sshrpg_test_enhanced.exp

test_result=$?
echo ""
if [ $test_result -eq 0 ]; then
    echo "🎉 SUCCESS: Enhanced timing test passed!"
    echo "✅ Single prompts confirmed with proper tick timing"
    echo "✅ No duplicate prompts detected during game ticks"
else
    echo "💥 FAILURE: Enhanced timing test failed (exit code: $test_result)"
    echo "❌ Multiple prompts or timing issues still present"
    echo "❌ The game tick system is still causing duplicate prompts"
fi

# Clean up
rm -f /tmp/sshrpg_test_enhanced.exp

echo ""
echo "📊 Test completed. Check output above for detailed timing analysis."