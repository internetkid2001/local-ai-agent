"""
System Monitoring MCP Client

Client adapter for the system monitoring MCP server.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from .base_client import BaseMCPClient, MCPClientConfig, MCPServerConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SystemMCPClient(BaseMCPClient):
    """
    System monitoring MCP client.
    
    Features:
    - Process monitoring and management
    - System resource tracking (CPU, memory, disk, network)
    - Log file parsing and analysis
    - Network connectivity testing
    - Service status checking
    """
    
    def __init__(self, config: MCPClientConfig = None):
        """
        Initialize system MCP client.
        
        Args:
            config: Client configuration, creates default if None
        """
        if config is None:
            config = self._create_default_config()
        
        super().__init__(config)
        logger.info("System MCP client initialized")
    
    @classmethod
    def _create_default_config(cls) -> MCPClientConfig:
        """Create default configuration for system monitoring"""
        system_server = MCPServerConfig(
            name="system",
            url="ws://localhost:8767",
            enabled=True,
            tools=[
                "list_processes", "kill_process", "get_process_info", "check_service",
                "get_cpu_stats", "get_memory_stats", "get_disk_stats", "get_network_stats",
                "parse_log_file", "analyze_log_patterns", "ping_host", "check_port"
            ]
        )
        
        return MCPClientConfig(
            servers=[system_server],
            connection_timeout=5.0,
            default_timeout=30.0,
            max_concurrent_connections=3
        )
    
    async def process_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process system monitoring tasks.
        
        Args:
            task: Task description
            context: Task context
            
        Returns:
            Task result
        """
        logger.info(f"Processing system task: {task}")
        
        task_lower = task.lower()
        
        try:
            # Route to appropriate system operation
            if any(keyword in task_lower for keyword in ['process', 'processes', 'kill', 'terminate']):
                return await self._handle_process_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['cpu', 'memory', 'disk', 'network', 'resource']):
                return await self._handle_resource_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['log', 'logs', 'parse', 'analyze']):
                return await self._handle_log_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['ping', 'network', 'connectivity', 'port']):
                return await self._handle_network_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['service', 'daemon', 'status']):
                return await self._handle_service_operation(task, context)
            
            else:
                # Default to system overview
                return await self._handle_general_operation(task, context)
        
        except Exception as e:
            logger.error(f"System task failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _handle_process_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process management operations"""
        task_lower = task.lower()
        
        if 'list' in task_lower:
            return await self.execute_tool("list_processes", {
                "filter_name": context.get("process_name"),
                "filter_user": context.get("user"),
                "include_system": context.get("include_system", True)
            })
        
        elif any(keyword in task_lower for keyword in ['kill', 'terminate', 'stop']):
            pid = context.get("pid")
            process_name = context.get("process_name")
            
            if not pid and not process_name:
                # Try to extract from task description
                words = task.split()
                for i, word in enumerate(words):
                    if word.lower() in ['kill', 'terminate', 'stop'] and i + 1 < len(words):
                        try:
                            pid = int(words[i + 1])
                        except ValueError:
                            process_name = words[i + 1]
                        break
            
            if not pid and not process_name:
                return {
                    "success": False,
                    "error": "Process ID or name required for kill operation"
                }
            
            return await self.execute_tool("kill_process", {
                "pid": pid,
                "process_name": process_name,
                "force": context.get("force", False)
            })
        
        elif 'info' in task_lower or 'details' in task_lower:
            pid = context.get("pid")
            if not pid:
                return {
                    "success": False,
                    "error": "Process ID required for process info"
                }
            
            return await self.execute_tool("get_process_info", {
                "pid": pid
            })
        
        else:
            # Default to listing processes
            return await self.execute_tool("list_processes", {})
    
    async def _handle_resource_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system resource monitoring"""
        task_lower = task.lower()
        
        if 'cpu' in task_lower:
            return await self.execute_tool("get_cpu_stats", {
                "interval": context.get("interval", 1.0),
                "per_cpu": context.get("per_cpu", False)
            })
        
        elif 'memory' in task_lower:
            return await self.execute_tool("get_memory_stats", {
                "include_swap": context.get("include_swap", True)
            })
        
        elif 'disk' in task_lower:
            return await self.execute_tool("get_disk_stats", {
                "path": context.get("path", "/"),
                "include_usage": context.get("include_usage", True)
            })
        
        elif 'network' in task_lower:
            return await self.execute_tool("get_network_stats", {
                "interface": context.get("interface"),
                "include_io": context.get("include_io", True)
            })
        
        else:
            # Return all resource stats
            results = {}
            try:
                results["cpu"] = await self.execute_tool("get_cpu_stats", {})
                results["memory"] = await self.execute_tool("get_memory_stats", {})
                results["disk"] = await self.execute_tool("get_disk_stats", {})
                results["network"] = await self.execute_tool("get_network_stats", {})
                return {
                    "success": True,
                    "data": results
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to get resource stats: {e}"
                }
    
    async def _handle_log_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle log file operations"""
        task_lower = task.lower()
        
        if 'parse' in task_lower:
            log_file = context.get("log_file")
            if not log_file:
                return {
                    "success": False,
                    "error": "Log file path required for parsing"
                }
            
            return await self.execute_tool("parse_log_file", {
                "file_path": log_file,
                "log_format": context.get("log_format", "auto"),
                "max_lines": context.get("max_lines", 1000),
                "filter_level": context.get("filter_level")
            })
        
        elif 'analyze' in task_lower or 'pattern' in task_lower:
            log_file = context.get("log_file")
            if not log_file:
                return {
                    "success": False,
                    "error": "Log file path required for analysis"
                }
            
            return await self.execute_tool("analyze_log_patterns", {
                "file_path": log_file,
                "pattern": context.get("pattern"),
                "time_range": context.get("time_range"),
                "severity_filter": context.get("severity_filter")
            })
        
        else:
            return {
                "success": False,
                "error": "Specify 'parse' or 'analyze' for log operations"
            }
    
    async def _handle_network_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle network operations"""
        task_lower = task.lower()
        
        if 'ping' in task_lower:
            host = context.get("host")
            if not host:
                # Try to extract from task description
                words = task.split()
                for i, word in enumerate(words):
                    if word.lower() == 'ping' and i + 1 < len(words):
                        host = words[i + 1]
                        break
            
            if not host:
                return {
                    "success": False,
                    "error": "Host required for ping operation"
                }
            
            return await self.execute_tool("ping_host", {
                "host": host,
                "count": context.get("count", 4),
                "timeout": context.get("timeout", 5)
            })
        
        elif 'port' in task_lower or 'check' in task_lower:
            host = context.get("host", "localhost")
            port = context.get("port")
            
            if not port:
                return {
                    "success": False,
                    "error": "Port required for port check operation"
                }
            
            return await self.execute_tool("check_port", {
                "host": host,
                "port": port,
                "timeout": context.get("timeout", 5)
            })
        
        else:
            # Default to network stats
            return await self.execute_tool("get_network_stats", {})
    
    async def _handle_service_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service status operations"""
        service_name = context.get("service_name")
        
        if not service_name:
            # Try to extract from task description
            words = task.split()
            for i, word in enumerate(words):
                if word.lower() in ['service', 'status'] and i + 1 < len(words):
                    service_name = words[i + 1]
                    break
        
        if not service_name:
            return {
                "success": False,
                "error": "Service name required for service operations"
            }
        
        return await self.execute_tool("check_service", {
            "service_name": service_name
        })
    
    async def _handle_general_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general system operations"""
        # Default to getting CPU stats for general system queries
        return await self.execute_tool("get_cpu_stats", {})
    
    # Convenience methods for common operations
    async def list_processes(self, filter_name: Optional[str] = None, 
                           filter_user: Optional[str] = None) -> Dict[str, Any]:
        """List running processes"""
        return await self.execute_tool("list_processes", {
            "filter_name": filter_name,
            "filter_user": filter_user
        })
    
    async def kill_process(self, pid: Optional[int] = None, 
                          process_name: Optional[str] = None,
                          force: bool = False) -> Dict[str, Any]:
        """Kill a process by PID or name"""
        return await self.execute_tool("kill_process", {
            "pid": pid,
            "process_name": process_name,
            "force": force
        })
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        try:
            cpu_stats = await self.execute_tool("get_cpu_stats", {})
            memory_stats = await self.execute_tool("get_memory_stats", {})
            disk_stats = await self.execute_tool("get_disk_stats", {})
            network_stats = await self.execute_tool("get_network_stats", {})
            
            return {
                "success": True,
                "data": {
                    "cpu": cpu_stats.get("data"),
                    "memory": memory_stats.get("data"),
                    "disk": disk_stats.get("data"),
                    "network": network_stats.get("data")
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get system stats: {e}"
            }
    
    async def ping_host(self, host: str, count: int = 4) -> Dict[str, Any]:
        """Ping a host"""
        return await self.execute_tool("ping_host", {
            "host": host,
            "count": count
        })
    
    async def check_port(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Check if a port is open on a host"""
        return await self.execute_tool("check_port", {
            "host": host,
            "port": port,
            "timeout": timeout
        })
    
    async def parse_log_file(self, file_path: str, max_lines: int = 1000) -> Dict[str, Any]:
        """Parse a log file"""
        return await self.execute_tool("parse_log_file", {
            "file_path": file_path,
            "max_lines": max_lines
        })
    
    async def check_service(self, service_name: str) -> Dict[str, Any]:
        """Check service status"""
        return await self.execute_tool("check_service", {
            "service_name": service_name
        })