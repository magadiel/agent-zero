#!/bin/bash

# Script to run Claude Code with Agent Zero prompt in a loop
# Usage: ./SOLTA-O-FOGUETE.sh <number_of_iterations>

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Error: Please provide the number of iterations as an argument"
    echo "Usage: $0 <number_of_iterations>"
    exit 1
fi

# Validate that the argument is a positive integer
if ! [[ "$1" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Argument must be a positive integer"
    exit 1
fi

ITERATIONS=$1
PROMPT="Project Overview
  Agent Zero is a dynamic, organic agentic framework that grows and learns through use. It's fully transparent, customizable, and interactive, designed as a general-purpose AI assistant
   that uses the computer as a tool.
  Core Architecture
  - Main Entry: agent.py - Contains the Agent class and AgentContext management
  - Multi-agent System: Hierarchical agent structure where agents can create subordinates
  - Context Management: Each agent has its own context with logging, memory, and state
  - Tool System: Extensible tool framework with both local and MCP (Model Context Protocol) tools
  Key Features
  1. General-purpose Assistant - Not pre-programmed for specific tasks
  2. Computer as Tool - Agents execute code and use terminal directly
  3. Multi-agent Cooperation - Superior/subordinate agent hierarchy
  4. Fully Customizable - All prompts and behaviors are configurable
  5. Communication-focused - Real-time streamed, interactive interface
  Tools Available
  - Code execution (local/SSH)
  - Browser automation
  - Memory management (save/load/delete)
  - Document query
  - Search engine integration
  - Scheduler for tasks
  - Vision/image processing
  - MCP client/server support
  - Agent-to-Agent (A2A) communication
  Connectivity Options
  - External API endpoints for integration
  - MCP server/client capabilities
  - A2A protocol for agent communication
  - Docker support with speech-to-text and TTS
  - Web UI with settings and file browser
  Memory & Knowledge
  - Vector database (FAISS) for semantic search
  - Persistent memory across sessions
  - Knowledge base integration
  - Memory consolidation and filtering
  - Solution memorization
  Configuration
  - Model-agnostic (supports OpenAI, Anthropic, local models via LiteLLM)
  - Customizable prompts in /prompts directory
  - Agent profiles in /agents directory
  - Extensions system for adding functionality
  - Docker containerization for safe execution
  We will change Agent-Zero to build an international class AI company, running only AI agents. We will implement the changes detailed and planned in following files:
	a) ./docs/agent-zero-new-agile-ai-agent-org.md 
	b) ./docs/agile-ai-company-implementation-analysis.md
	c) ./docs/bmad-methodology-analysis.md
	d) ./docs/IMPLEMENTATION_ROADMAP.md
The implementation will follow this workflow step by step until the last task (no jumps or gaps on tasks):
1) Refresh the context of project with the current state of the project, including the updated files agent-zero-new-agile-ai-agent-org.md , agile-ai-company-implementation-analysis.md, bmad-methodology-analysis.md, IMPLEMENTATION_ROADMAP.md
2) Analize IMPLEMENTATION_ROADMAP.md kanban file to define the next task to be done
3) Plan the task with all the requirements and follow the DoD
4) Update Kanban with proper status to start the task
5) Implement the task properly following the plan in step 3 and accordingly to task definition
6) After task completion, update Kanban with proper status to Done
8) Ask for human validation and wait. 
Please do all the tasks carefully, following the plan and taking extra care to do not introduce breaking changes. When having compilation errors, or runtime errors, please do global analysis before making local changes. DO NOT STRIP FEATURES TO CORRECT COMPILATION OR RUNTIME ERROR. Do a global analysis and replan changes. When running tests take a conservative approach following defined test plan carefully. Do not Jump Tests. If a test fail, do a global analysis to find the root cause and replan activities to fix code or test definition. DO NOT STRIP FEATURES TO CORRECT FAILED TESTS. DO NOT JUMP THROUGH TESTS. Don't forget to commit and merge changes to repository."

echo "Starting Claude Code loop with $ITERATIONS iterations..."
echo "=========================================="

# Check if claude command is available
if ! command -v claude &> /dev/null; then
    echo "Error: 'claude' command not found. Please ensure Claude Code is installed and in your PATH."
    exit 1
fi

# Loop for the specified number of iterations
for ((i=1; i<=ITERATIONS; i++)); do
    echo ""
    echo "=========================================="
    echo "Starting iteration $i of $ITERATIONS"
    echo "=========================================="
    
    # Run Claude Code with the prompt in interactive mode
    echo "$PROMPT" | claude --dangerously-skip-permissions
    
    # Check the exit status of the claude command
    exit_code=$?
    
    echo "Completed iteration $i of $ITERATIONS with code $exit_code"
    
    # Add a small delay between iterations if not the last one
    if [ $i -lt $ITERATIONS ]; then
        echo "Waiting 60 seconds before next iteration..."
        sleep 60
    fi
done

echo ""
echo "=========================================="
echo "All $ITERATIONS iterations completed successfully!"
echo "=========================================="

