#!/usr/bin/env python3

import sys
sys.path.insert(0, 'python')

from helpers.command_system import CommandParser

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
print(f"Found {len(commands)} commands")
for cmd in commands:
    print(f"  - {cmd.name}: {cmd.description}")