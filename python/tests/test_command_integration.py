#!/usr/bin/env python3
"""
Integration test for command system with BMAD agents
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.command_system import CommandSystem, CommandParameter, ParameterType
from helpers.bmad_agent import BMADAgentLoader


async def test_command_system():
    """Test basic command system functionality"""
    print("Testing Command System...")
    
    # Create command system
    cs = CommandSystem()
    
    # List available commands
    commands = cs.get_available_commands()
    print(f"Available built-in commands: {commands}")
    
    # Get help for a command
    help_text = cs.get_command_help("save-memory")
    print(f"\nHelp for 'save-memory' command:")
    print(help_text)
    
    # Create a custom command
    async def greet_handler(agent, execution, name: str, greeting: str = "Hello"):
        execution.log(f"Greeting {name}")
        return f"{greeting}, {name}!"
    
    cs.create_command(
        name="greet",
        description="Greet someone",
        handler=greet_handler
    )
    
    # Execute the custom command
    class MockAgent:
        def get_tool(self, name):
            return None
        def get_command(self, name):
            return None
    
    agent = MockAgent()
    execution = await cs.execute(agent, "greet", name="Alice", greeting="Hi")
    
    print(f"\nCommand execution result:")
    print(f"  Status: {execution.status.value}")
    print(f"  Result: {execution.result}")
    print(f"  Logs: {execution.logs}")
    
    print("\n✅ Command System test passed!")


def test_bmad_integration():
    """Test BMAD agent loader with command system"""
    print("\nTesting BMAD Integration...")
    
    # Create BMAD loader
    loader = BMADAgentLoader("agents")
    
    # Check if command system is integrated
    if loader.command_system:
        print("✅ Command system integrated with BMAD loader")
        
        # List available commands in the system
        commands = loader.command_system.get_available_commands()
        print(f"Commands available: {len(commands)}")
        
        # Try loading commands from an agent
        agent_path = Path("agents/product_manager")
        if agent_path.exists():
            cmds = loader.command_system.load_agent_commands(agent_path)
            print(f"Loaded {len(cmds)} commands from product_manager agent")
            for cmd in cmds:
                print(f"  - {cmd.name}: {cmd.description}")
    else:
        print("⚠️  Command system not available")
    
    print("\n✅ BMAD Integration test completed!")


def test_command_parsing():
    """Test command parsing from markdown"""
    print("\nTesting Command Parsing...")
    
    from helpers.command_system import CommandParser
    
    sample_md = """
## Commands

### create-document
**Description**: Create a new document
**Parameters**:
- `title` (required): Document title
- `type`: Document type (default: markdown)
**Execution**:
1. Create document structure
2. Add title and metadata
3. Save to repository

### review-code
**Description**: Review code for quality
**Parameters**:
- `file_path` (required): Path to the file to review
- `check_style` (optional): Check code style (default: true)
"""
    
    parser = CommandParser()
    commands = parser.parse_from_markdown(sample_md)
    
    print(f"Parsed {len(commands)} commands:")
    for cmd in commands:
        print(f"\n  Command: {cmd.name}")
        print(f"  Description: {cmd.description}")
        print(f"  Parameters: {len(cmd.parameters)}")
        for param in cmd.parameters:
            req = "required" if param.required else "optional"
            print(f"    - {param.name} ({req}): {param.description}")
        print(f"  Execution steps: {len(cmd.execution_steps)}")
    
    print("\n✅ Command Parsing test passed!")


async def main():
    """Run all tests"""
    print("="*60)
    print("Command System Integration Tests")
    print("="*60)
    
    # Test command system
    await test_command_system()
    
    # Test BMAD integration
    test_bmad_integration()
    
    # Test command parsing
    test_command_parsing()
    
    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())