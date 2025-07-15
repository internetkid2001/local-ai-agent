#!/usr/bin/env python3
"""
Quick test script for natural language processing functionality
"""

import sys
import os
sys.path.append('.')

from simple_terminal_bridge import TerminalBridge

def test_nlp():
    """Test natural language processing"""
    bridge = TerminalBridge()
    
    test_phrases = [
        "take a screenshot",
        "show system info", 
        "list processes",
        "memory usage",
        "disk usage",
        "what processes are running?",
        "show me the system information",
        "how much memory is being used?",
        "hello world"  # Should not match any pattern
    ]
    
    print("Testing Natural Language Processing:")
    print("=" * 50)
    
    for phrase in test_phrases:
        print(f"\nInput: '{phrase}'")
        
        # Test NLP directly
        nlp_result = bridge.handle_nlp_command(phrase)
        if nlp_result:
            print(f"NLP Result: {nlp_result[:100]}...")
        else:
            print("NLP Result: No match (would go to AI)")
        
        # Test full command execution
        cmd_result = bridge.execute_command(phrase)
        if cmd_result:
            print(f"Command Result: {cmd_result[:100]}...")
        else:
            print("Command Result: None (would go to AI)")

if __name__ == "__main__":
    test_nlp()
