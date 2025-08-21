#!/usr/bin/env python3
"""
Simple test for command system
"""

import sys
import os
import asyncio

# Add path for imports
sys.path.insert(0, 'python')

from helpers.command_system import CommandSystem, CommandParser


async def test_basic():
    """Test basic command system"""
    print("Testing Command System...")
    
    # Create system
    cs = CommandSystem()
    
    # Check built-in commands
    commands = cs.get_available_commands()
    print(f"Built-in commands: {commands}")
    assert "save-memory" in commands
    assert "execute-code" in commands
    print("✅ Built-in commands loaded")
    
    # Create custom command
    async def test_handler(agent, execution, param1="default"):
        return f"Result: {param1}"
    
    cs.create_command("test", "Test command", test_handler)
    assert "test" in cs.get_available_commands()
    print("✅ Custom command created")
    
    # Mock agent
    class Agent:
        def get_tool(self, name): return None
        def get_command(self, name): return None
    
    # Execute command
    result = await cs.execute(Agent(), "test", param1="value")
    assert result.status.value == "success"
    assert result.result == "Result: value"
    print("✅ Command executed successfully")
    
    print("\n✅ All tests passed!")


def test_parser():
    """Test command parser"""
    print("\nTesting Parser...")
    
    md = """
## Commands

### cmd1
**Description**: First command
**Parameters**:
- `p1` (required): Parameter 1
- `p2`: Parameter 2

### cmd2
**Description**: Second command
"""
    
    commands = CommandParser.parse_from_markdown(md)
    assert len(commands) == 2
    assert commands[0].name == "cmd1"
    assert len(commands[0].parameters) == 2
    assert commands[0].parameters[0].required == True
    assert commands[1].name == "cmd2"
    print("✅ Parser tests passed!")


if __name__ == "__main__":
    asyncio.run(test_basic())
    test_parser()
    print("\n🎉 All tests completed successfully!")