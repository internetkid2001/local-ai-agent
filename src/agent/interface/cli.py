"""
Agent CLI Interface

Command-line interface for interacting with the local AI agent.
Provides an interactive shell for task submission and monitoring.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import asyncio
import sys
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse
import logging

from ..core.orchestrator import AgentOrchestrator, AgentConfig, Task, TaskPriority, TaskStatus
from ..core.task_router import TaskRouter
from ..core.decision_engine import DecisionEngine
from ..llm.ollama_client import OllamaConfig, ModelType
from ...mcp_client.filesystem_client import FilesystemMCPClient
from ...utils.logger import get_logger

logger = get_logger(__name__)


class AgentCLI:
    """
    Interactive command-line interface for the local AI agent.
    
    Features:
    - Interactive task submission
    - Real-time task monitoring
    - Agent status information
    - Configuration management
    - Session management
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize CLI interface.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Core components
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.router: Optional[TaskRouter] = None
        self.decision_engine: Optional[DecisionEngine] = None
        self.mcp_client: Optional[FilesystemMCPClient] = None
        
        # CLI state
        self.running = False
        self.session_id = f"session_{int(time.time())}"
        self.command_history: List[str] = []
        
        logger.info("Agent CLI initialized")
    
    def _load_config(self) -> AgentConfig:
        """Load agent configuration"""
        try:
            if self.config_path and Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                logger.info(f"Loaded config from {self.config_path}")
                return self._parse_config(config_data)
            else:
                logger.info("Using default configuration")
                return self._create_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> AgentConfig:
        """Create default agent configuration"""
        ollama_config = OllamaConfig(
            host="http://localhost:11434",
            models={
                ModelType.PRIMARY: "llama3.1:8b",
                ModelType.CODE: "codellama:7b"
            }
        )
        
        # MCP config will be handled by FilesystemMCPClient's default config
        mcp_config = None
        
        return AgentConfig(
            ollama_config=ollama_config,
            mcp_config=mcp_config,
            max_concurrent_tasks=3,
            task_timeout=300.0,
            enable_screenshots=True,
            screenshot_interval=30.0
        )
    
    def _parse_config(self, config_data: Dict[str, Any]) -> AgentConfig:
        """Parse configuration from dictionary"""
        # Implementation would parse the config JSON
        # For now, return default config
        return self._create_default_config()
    
    async def initialize(self) -> bool:
        """
        Initialize all agent components.
        
        Returns:
            True if initialization successful
        """
        try:
            print("🤖 Initializing Local AI Agent...")
            
            # Initialize MCP client
            print("📁 Connecting to filesystem MCP server...")
            self.mcp_client = FilesystemMCPClient()
            if not await self.mcp_client.initialize():
                print("⚠️  Warning: Filesystem MCP server not available")
                # Continue without MCP for now
            
            # Initialize orchestrator
            print("🎭 Starting agent orchestrator...")
            self.orchestrator = AgentOrchestrator(self.config)
            if not await self.orchestrator.initialize():
                print("❌ Failed to initialize orchestrator")
                return False
            
            # Initialize router
            print("🗺️  Initializing task router...")
            self.router = TaskRouter()
            
            # Initialize decision engine
            print("🧠 Starting decision engine...")
            self.decision_engine = DecisionEngine(self.orchestrator, self.router)
            
            # Start orchestrator processing
            asyncio.create_task(self.orchestrator.start_processing())
            
            print("✅ Agent initialization complete!\n")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            logger.error(f"CLI initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Gracefully shutdown the agent"""
        print("\n🔄 Shutting down agent...")
        
        self.running = False
        
        if self.orchestrator:
            await self.orchestrator.stop_processing()
            await self.orchestrator.shutdown()
        
        if self.mcp_client:
            await self.mcp_client.shutdown()
        
        print("👋 Agent shutdown complete")
    
    async def run_interactive(self):
        """Run interactive CLI session"""
        if not await self.initialize():
            return
        
        self.running = True
        print(f"🚀 Local AI Agent CLI - Session {self.session_id}")
        print("Type 'help' for commands, 'exit' to quit\n")
        
        try:
            while self.running:
                try:
                    # Get user input
                    user_input = await self._get_user_input()
                    
                    if not user_input.strip():
                        continue
                    
                    # Add to command history
                    self.command_history.append(user_input)
                    
                    # Process command
                    await self._process_command(user_input)
                    
                except KeyboardInterrupt:
                    print("\n⚠️  Use 'exit' to quit properly")
                except EOFError:
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    logger.error(f"Command processing error: {e}")
        
        finally:
            await self.shutdown()
    
    async def _get_user_input(self) -> str:
        """Get user input asynchronously"""
        # Simple input for now - could be enhanced with readline/rich
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "agent> ")
    
    async def _process_command(self, user_input: str):
        """Process user command"""
        command_parts = user_input.strip().split()
        if not command_parts:
            return
        
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        # Handle built-in commands
        if command == "help":
            self._show_help()
        
        elif command == "exit" or command == "quit":
            self.running = False
        
        elif command == "status":
            await self._show_status()
        
        elif command == "tasks":
            await self._show_tasks()
        
        elif command == "history":
            self._show_history()
        
        elif command == "config":
            self._show_config()
        
        elif command == "clear":
            self._clear_screen()
        
        elif command == "submit":
            if args:
                task_description = " ".join(args)
                await self._submit_task(task_description)
            else:
                print("❌ Usage: submit <task description>")
        
        elif command == "analyze":
            if args:
                task_description = " ".join(args)
                await self._analyze_task(task_description)
            else:
                print("❌ Usage: analyze <task description>")
        
        elif command == "approve":
            if args:
                approval_id = args[0]
                await self._approve_task(approval_id, True)
            else:
                await self._show_pending_approvals()
        
        elif command == "reject":
            if args:
                approval_id = args[0]
                await self._approve_task(approval_id, False)
            else:
                print("❌ Usage: reject <approval_id>")
        
        else:
            # Treat as task submission
            await self._submit_task(user_input)
    
    def _show_help(self):
        """Show help information"""
        help_text = """
🤖 Local AI Agent Commands:

Task Management:
  submit <description>   - Submit a task for execution
  analyze <description>  - Analyze task without executing
  tasks                  - Show active and recent tasks
  
Approval Management:
  approve [id]          - Approve pending task or list pending
  reject <id>           - Reject pending task
  
Agent Status:
  status                - Show agent status
  config                - Show current configuration
  
Session Management:
  history               - Show command history
  clear                 - Clear screen
  help                  - Show this help
  exit                  - Exit the agent

Examples:
  submit read config.yaml and summarize
  analyze create a new Python script
  approve task_123
  tasks
"""
        print(help_text)
    
    async def _show_status(self):
        """Show agent status"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized")
            return
        
        queue_status = self.orchestrator.get_queue_status()
        active_tasks = self.orchestrator.get_active_tasks()
        
        print("📊 Agent Status:")
        print(f"   Running: {'✅' if queue_status['running'] else '❌'}")
        print(f"   Pending Tasks: {queue_status['pending_tasks']}")
        print(f"   Active Tasks: {queue_status['active_tasks']}")
        print(f"   Completed Tasks: {queue_status['completed_tasks']}")
        print(f"   Session: {self.session_id}")
        
        if active_tasks:
            print("\n🔄 Active Tasks:")
            for task in active_tasks:
                status_icon = "🟡" if task.status == TaskStatus.IN_PROGRESS else "⚪"
                print(f"   {status_icon} {task.id}: {task.description[:50]}...")
        
        # Show MCP client status
        if self.mcp_client:
            try:
                health = await self.mcp_client.health_check()
                print("\n📁 MCP Client Status:")
                for server, status in health.items():
                    icon = "✅" if status['status'] == 'healthy' else "❌"
                    print(f"   {icon} {server}: {status['status']}")
            except Exception as e:
                print(f"   ⚠️  MCP status check failed: {e}")
        
        print()
    
    async def _show_tasks(self):
        """Show task information"""
        if not self.orchestrator:
            print("❌ Orchestrator not initialized")
            return
        
        active_tasks = self.orchestrator.get_active_tasks()
        completed_tasks = self.orchestrator.get_completed_tasks(limit=5)
        
        print("📋 Task Overview:")
        
        if active_tasks:
            print("\n🔄 Active Tasks:")
            for task in active_tasks:
                print(f"   🟡 {task.id}")
                print(f"      Description: {task.description}")
                print(f"      Status: {task.status.value}")
                print(f"      Priority: {task.priority.value}")
                print()
        
        if completed_tasks:
            print("✅ Recent Completed Tasks:")
            for task in completed_tasks:
                status_icon = "✅" if task.status == TaskStatus.COMPLETED else "❌"
                print(f"   {status_icon} {task.id}: {task.description[:50]}...")
                if task.error:
                    print(f"      Error: {task.error}")
        
        print()
    
    def _show_history(self):
        """Show command history"""
        print("📜 Command History:")
        for i, command in enumerate(self.command_history[-10:], 1):
            print(f"   {i:2d}. {command}")
        print()
    
    def _show_config(self):
        """Show current configuration"""
        print("⚙️  Agent Configuration:")
        print(f"   Session ID: {self.session_id}")
        print(f"   Config Path: {self.config_path or 'Default'}")
        print(f"   Max Concurrent Tasks: {self.config.max_concurrent_tasks}")
        print(f"   Task Timeout: {self.config.task_timeout}s")
        print(f"   Screenshots: {'Enabled' if self.config.enable_screenshots else 'Disabled'}")
        print(f"   Ollama Host: {self.config.ollama_config.host}")
        print()
    
    def _clear_screen(self):
        """Clear terminal screen"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    async def _submit_task(self, description: str):
        """Submit a task for execution"""
        if not self.orchestrator or not self.decision_engine:
            print("❌ Agent not initialized")
            return
        
        print(f"📤 Submitting task: {description}")
        
        try:
            # Create task
            task_id = f"task_{int(time.time() * 1000)}"
            task = Task(
                id=task_id,
                description=description,
                task_type="general",
                priority=TaskPriority.MEDIUM
            )
            
            # Make execution decision
            decision = await self.decision_engine.make_execution_decision(task)
            
            print(f"🧠 Decision: {decision.decision_type.value}")
            print(f"📊 Confidence: {decision.routing_decision.confidence:.1%}")
            print(f"🎯 Strategy: {decision.routing_decision.strategy.value}")
            
            # Execute decision
            result_id = await self.decision_engine.execute_decision(decision, task)
            
            if decision.decision_type.value == "request_approval":
                print(f"⏳ Task requires approval: {result_id}")
                print(f"   Reason: {decision.approval_reason}")
                print(f"   Use 'approve {result_id}' to approve")
            elif decision.decision_type.value == "gather_context":
                print(f"⏳ Task requires additional context: {result_id}")
                print(f"   Requirements: {', '.join(decision.context_requirements)}")
            else:
                print(f"✅ Task submitted: {result_id}")
            
        except Exception as e:
            print(f"❌ Task submission failed: {e}")
            logger.error(f"Task submission error: {e}")
    
    async def _analyze_task(self, description: str):
        """Analyze a task without executing it"""
        if not self.decision_engine:
            print("❌ Decision engine not initialized")
            return
        
        print(f"🔍 Analyzing task: {description}")
        
        try:
            # Create temporary task for analysis
            task = Task(
                id="analysis_temp",
                description=description,
                task_type="general"
            )
            
            # Get decision summary
            summary = await self.decision_engine.get_decision_summary(task)
            print("\n" + summary)
            
        except Exception as e:
            print(f"❌ Task analysis failed: {e}")
    
    async def _show_pending_approvals(self):
        """Show pending approval requests"""
        if not self.decision_engine:
            print("❌ Decision engine not initialized")
            return
        
        approvals = self.decision_engine.get_pending_approvals()
        
        if not approvals:
            print("✅ No pending approvals")
            return
        
        print("⏳ Pending Approvals:")
        for approval_id, info in approvals.items():
            print(f"   🟡 {approval_id}")
            print(f"      Reason: {info['reason']}")
            print(f"      Complexity: {info['complexity']}/5")
            print(f"      Strategy: {info['strategy']}")
            print(f"      Tools: {', '.join(info['tools']) if info['tools'] else 'None'}")
            print()
    
    async def _approve_task(self, approval_id: str, approved: bool):
        """Approve or reject a task"""
        if not self.decision_engine:
            print("❌ Decision engine not initialized")
            return
        
        try:
            result = await self.decision_engine.approve_task(approval_id, approved)
            
            if result:
                action = "approved" if approved else "rejected"
                print(f"✅ Task {action}: {result}")
            else:
                print(f"❌ Approval ID not found: {approval_id}")
                
        except Exception as e:
            print(f"❌ Approval failed: {e}")
    
    async def run_single_command(self, command: str):
        """Run a single command (for non-interactive use)"""
        if not await self.initialize():
            return False
        
        try:
            await self._process_command(command)
            return True
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return False
        finally:
            await self.shutdown()


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Local AI Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.agent.interface.cli                    # Interactive mode
  python -m src.agent.interface.cli --command "help"   # Single command
  python -m src.agent.interface.cli --config config.json  # Custom config
"""
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--command",
        type=str,
        help="Single command to execute (non-interactive)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


async def main():
    """Main CLI entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Create CLI instance
    cli = AgentCLI(config_path=args.config)
    
    try:
        if args.command:
            # Single command mode
            success = await cli.run_single_command(args.command)
            sys.exit(0 if success else 1)
        else:
            # Interactive mode
            await cli.run_interactive()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.error(f"CLI fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())