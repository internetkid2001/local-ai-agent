#!/usr/bin/env python3
"""
System Monitoring MCP Server

Provides system monitoring and process management capabilities including
resource monitoring, process control, log analysis, and system health checks.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import logging
import sys
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from process_monitor import ProcessMonitor
from resource_monitor import ResourceMonitor
from log_parser import LogParser
from network_monitor import NetworkMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_mcp.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SystemMCPServer:
    """
    System monitoring MCP server providing comprehensive system oversight capabilities.
    
    Features:
    - Process monitoring and management
    - System resource monitoring (CPU, memory, disk, network)
    - Log file parsing and analysis
    - Network status and connectivity monitoring
    - Performance metrics collection
    - System health checks
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize system MCP server.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize monitoring components
        self.process_monitor = ProcessMonitor(self.config.get("process", {}))
        self.resource_monitor = ResourceMonitor(self.config.get("resource", {}))
        self.log_parser = LogParser(self.config.get("logging", {}))
        self.network_monitor = NetworkMonitor(self.config.get("network", {}))
        
        # Server state
        self.connections: Dict[str, Any] = {}
        self.running = False
        
        # Tool registry
        self.tools = {
            # Process management
            "list_processes": self._list_processes,
            "get_process_info": self._get_process_info,
            "kill_process": self._kill_process,
            "find_processes": self._find_processes,
            "monitor_process": self._monitor_process,
            
            # Resource monitoring
            "get_system_metrics": self._get_system_metrics,
            "get_cpu_usage": self._get_cpu_usage,
            "get_memory_usage": self._get_memory_usage,
            "get_disk_usage": self._get_disk_usage,
            "get_network_stats": self._get_network_stats,
            "monitor_resources": self._monitor_resources,
            
            # Log analysis
            "parse_logs": self._parse_logs,
            "search_logs": self._search_logs,
            "tail_log": self._tail_log,
            "analyze_log_patterns": self._analyze_log_patterns,
            
            # Network monitoring
            "network_status": self._network_status,
            "ping_host": self._ping_host,
            "check_port": self._check_port,
            "get_connections": self._get_connections,
            
            # System health
            "health_check": self._health_check,
            "get_uptime": self._get_uptime,
            "get_load_average": self._get_load_average,
            "check_services": self._check_services,
            
            # Performance analysis
            "performance_report": self._performance_report,
            "top_processes": self._top_processes,
            "system_summary": self._system_summary
        }
        
        logger.info("System MCP server initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load server configuration"""
        default_config = {
            "server": {
                "host": "localhost",
                "port": 8767,
                "name": "system-monitoring"
            },
            "security": {
                "allow_process_kill": False,
                "allowed_signals": ["TERM", "HUP"],
                "blocked_processes": ["init", "kernel", "systemd"],
                "require_confirmation": True
            },
            "monitoring": {
                "update_interval": 5.0,
                "history_limit": 100,
                "alert_thresholds": {
                    "cpu_percent": 90,
                    "memory_percent": 85,
                    "disk_percent": 90
                }
            },
            "process": {
                "track_children": True,
                "include_threads": False,
                "sort_by": "cpu_percent"
            },
            "resource": {
                "collect_interval": 1.0,
                "smooth_values": True,
                "include_per_cpu": False
            },
            "logging": {
                "log_paths": [
                    "/var/log/syslog",
                    "/var/log/messages", 
                    "/var/log/auth.log",
                    "/var/log/kern.log"
                ],
                "max_lines": 1000,
                "follow_logs": True
            },
            "network": {
                "interface_filter": [],
                "include_loopback": False,
                "dns_servers": ["8.8.8.8", "1.1.1.1"]
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    return config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    async def start_server(self):
        """Start the MCP server"""
        self.running = True
        host = self.config["server"]["host"]
        port = self.config["server"]["port"]
        
        logger.info(f"Starting system MCP server on {host}:{port}")
        
        try:
            # Initialize monitoring components
            await self.process_monitor.initialize()
            await self.resource_monitor.initialize()
            await self.log_parser.initialize()
            await self.network_monitor.initialize()
            
            server = await asyncio.start_server(
                self._handle_client,
                host,
                port
            )
            
            logger.info(f"System MCP server running on {host}:{port}")
            
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def _handle_client(self, reader, writer):
        """Handle client connections"""
        client_addr = writer.get_extra_info('peername')
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            while self.running:
                # Read message length
                length_bytes = await reader.read(4)
                if not length_bytes:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Read message data
                message_data = await reader.read(message_length)
                if not message_data:
                    break
                
                # Parse message
                try:
                    message_json = message_data.decode('utf-8')
                    message = json.loads(message_json)
                    
                    # Process message
                    response = await self._process_message(message)
                    
                    # Send response
                    response_json = json.dumps(response)
                    response_bytes = response_json.encode('utf-8')
                    response_length = len(response_bytes)
                    
                    writer.write(response_length.to_bytes(4, byteorder='big'))
                    writer.write(response_bytes)
                    await writer.drain()
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    response_json = json.dumps(error_response)
                    response_bytes = response_json.encode('utf-8')
                    response_length = len(response_bytes)
                    
                    writer.write(response_length.to_bytes(4, byteorder='big'))
                    writer.write(response_bytes)
                    await writer.drain()
        
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        
        finally:
            logger.info(f"Client disconnected: {client_id}")
            writer.close()
            await writer.wait_closed()
    
    async def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming MCP message"""
        method = message.get("method")
        params = message.get("params", {})
        message_id = message.get("id")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": self._get_tool_schemas()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name in self.tools:
                try:
                    result = await self.tools[tool_name](arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
                    }
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(e)}"
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for all available tools"""
        return [
            {
                "name": "list_processes",
                "description": "List all running processes with details",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sort_by": {"type": "string", "enum": ["pid", "name", "cpu_percent", "memory_percent"], "default": "cpu_percent"},
                        "limit": {"type": "integer", "default": 50},
                        "filter": {"type": "string", "description": "Filter processes by name pattern"}
                    }
                }
            },
            {
                "name": "get_process_info",
                "description": "Get detailed information about a specific process",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pid": {"type": "integer", "description": "Process ID"},
                        "name": {"type": "string", "description": "Process name (alternative to PID)"}
                    }
                }
            },
            {
                "name": "kill_process",
                "description": "Terminate a process (requires permission)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pid": {"type": "integer"},
                        "signal": {"type": "string", "enum": ["TERM", "KILL", "HUP"], "default": "TERM"},
                        "force": {"type": "boolean", "default": false}
                    },
                    "required": ["pid"]
                }
            },
            {
                "name": "get_system_metrics",
                "description": "Get comprehensive system resource metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_history": {"type": "boolean", "default": false},
                        "detailed": {"type": "boolean", "default": true}
                    }
                }
            },
            {
                "name": "get_cpu_usage",
                "description": "Get CPU usage statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "per_cpu": {"type": "boolean", "default": false},
                        "interval": {"type": "number", "default": 1.0}
                    }
                }
            },
            {
                "name": "get_memory_usage",
                "description": "Get memory usage statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_swap": {"type": "boolean", "default": true},
                        "human_readable": {"type": "boolean", "default": true}
                    }
                }
            },
            {
                "name": "get_disk_usage",
                "description": "Get disk usage for all mounted filesystems",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Specific path to check"},
                        "human_readable": {"type": "boolean", "default": true}
                    }
                }
            },
            {
                "name": "parse_logs",
                "description": "Parse and analyze system log files",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "log_path": {"type": "string", "description": "Path to log file"},
                        "pattern": {"type": "string", "description": "Regex pattern to search for"},
                        "lines": {"type": "integer", "default": 100},
                        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]}
                    }
                }
            },
            {
                "name": "network_status",
                "description": "Get network interface status and statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "interface": {"type": "string", "description": "Specific interface to check"},
                        "include_stats": {"type": "boolean", "default": true}
                    }
                }
            },
            {
                "name": "health_check",
                "description": "Perform comprehensive system health check",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "detailed": {"type": "boolean", "default": true},
                        "check_services": {"type": "boolean", "default": false}
                    }
                }
            }
        ]
    
    # Tool implementations
    async def _list_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all running processes"""
        sort_by = args.get("sort_by", "cpu_percent")
        limit = args.get("limit", 50)
        filter_pattern = args.get("filter")
        return await self.process_monitor.list_processes(sort_by, limit, filter_pattern)
    
    async def _get_process_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed process information"""
        pid = args.get("pid")
        name = args.get("name")
        return await self.process_monitor.get_process_info(pid, name)
    
    async def _kill_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a process"""
        pid = args["pid"]
        signal = args.get("signal", "TERM")
        force = args.get("force", False)
        return await self.process_monitor.kill_process(pid, signal, force)
    
    async def _find_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find processes by criteria"""
        return await self.process_monitor.find_processes(args)
    
    async def _monitor_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor a specific process"""
        return await self.process_monitor.monitor_process(args)
    
    async def _get_system_metrics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        include_history = args.get("include_history", False)
        detailed = args.get("detailed", True)
        return await self.resource_monitor.get_system_metrics(include_history, detailed)
    
    async def _get_cpu_usage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get CPU usage statistics"""
        per_cpu = args.get("per_cpu", False)
        interval = args.get("interval", 1.0)
        return await self.resource_monitor.get_cpu_usage(per_cpu, interval)
    
    async def _get_memory_usage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory usage statistics"""
        include_swap = args.get("include_swap", True)
        human_readable = args.get("human_readable", True)
        return await self.resource_monitor.get_memory_usage(include_swap, human_readable)
    
    async def _get_disk_usage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get disk usage statistics"""
        path = args.get("path")
        human_readable = args.get("human_readable", True)
        return await self.resource_monitor.get_disk_usage(path, human_readable)
    
    async def _get_network_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get network statistics"""
        return await self.network_monitor.get_network_stats(args)
    
    async def _monitor_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor system resources continuously"""
        return await self.resource_monitor.monitor_resources(args)
    
    async def _parse_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Parse log files"""
        log_path = args.get("log_path")
        pattern = args.get("pattern")
        lines = args.get("lines", 100)
        level = args.get("level")
        return await self.log_parser.parse_logs(log_path, pattern, lines, level)
    
    async def _search_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search log files"""
        return await self.log_parser.search_logs(args)
    
    async def _tail_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tail log files"""
        return await self.log_parser.tail_log(args)
    
    async def _analyze_log_patterns(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze log patterns"""
        return await self.log_parser.analyze_patterns(args)
    
    async def _network_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get network status"""
        interface = args.get("interface")
        include_stats = args.get("include_stats", True)
        return await self.network_monitor.get_status(interface, include_stats)
    
    async def _ping_host(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Ping a host"""
        return await self.network_monitor.ping_host(args)
    
    async def _check_port(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a port is open"""
        return await self.network_monitor.check_port(args)
    
    async def _get_connections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get network connections"""
        return await self.network_monitor.get_connections(args)
    
    async def _health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform system health check"""
        detailed = args.get("detailed", True)
        check_services = args.get("check_services", False)
        
        # Collect health data from all monitors
        health_data = {
            "timestamp": asyncio.get_event_loop().time(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        try:
            # CPU health
            cpu_data = await self.resource_monitor.get_cpu_usage(False, 1.0)
            cpu_percent = cpu_data.get("cpu_percent", 0)
            health_data["checks"]["cpu"] = {
                "status": "warning" if cpu_percent > 80 else "healthy",
                "value": cpu_percent,
                "threshold": 80
            }
            
            # Memory health
            memory_data = await self.resource_monitor.get_memory_usage(True, False)
            memory_percent = memory_data.get("memory_percent", 0)
            health_data["checks"]["memory"] = {
                "status": "warning" if memory_percent > 85 else "healthy",
                "value": memory_percent,
                "threshold": 85
            }
            
            # Disk health
            disk_data = await self.resource_monitor.get_disk_usage(None, False)
            max_disk_percent = max([d.get("percent", 0) for d in disk_data.get("filesystems", [])], default=0)
            health_data["checks"]["disk"] = {
                "status": "warning" if max_disk_percent > 90 else "healthy",
                "value": max_disk_percent,
                "threshold": 90
            }
            
            # Network health
            network_data = await self.network_monitor.get_status(None, True)
            health_data["checks"]["network"] = {
                "status": "healthy" if network_data.get("success") else "error",
                "interfaces_up": len([i for i in network_data.get("interfaces", []) if i.get("is_up")])
            }
            
            # Determine overall status
            warning_checks = [check for check in health_data["checks"].values() if check.get("status") == "warning"]
            error_checks = [check for check in health_data["checks"].values() if check.get("status") == "error"]
            
            if error_checks:
                health_data["overall_status"] = "error"
            elif warning_checks:
                health_data["overall_status"] = "warning"
            
            return {"success": True, "health": health_data}
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_uptime(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system uptime"""
        return await self.resource_monitor.get_uptime()
    
    async def _get_load_average(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system load average"""
        return await self.resource_monitor.get_load_average()
    
    async def _check_services(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check system services status"""
        return await self.process_monitor.check_services(args)
    
    async def _performance_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance report"""
        try:
            report = {
                "timestamp": asyncio.get_event_loop().time(),
                "summary": {}
            }
            
            # Collect data from all monitors
            cpu_data = await self.resource_monitor.get_cpu_usage(True, 1.0)
            memory_data = await self.resource_monitor.get_memory_usage(True, True)
            disk_data = await self.resource_monitor.get_disk_usage(None, True)
            process_data = await self.process_monitor.list_processes("cpu_percent", 10)
            network_data = await self.network_monitor.get_status(None, True)
            
            report["cpu"] = cpu_data
            report["memory"] = memory_data
            report["disk"] = disk_data
            report["top_processes"] = process_data
            report["network"] = network_data
            
            return {"success": True, "report": report}
            
        except Exception as e:
            logger.error(f"Performance report failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _top_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get top processes by resource usage"""
        sort_by = args.get("sort_by", "cpu_percent")
        limit = args.get("limit", 10)
        return await self.process_monitor.list_processes(sort_by, limit)
    
    async def _system_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system summary"""
        try:
            summary = {
                "timestamp": asyncio.get_event_loop().time(),
                "platform": await self.resource_monitor.get_platform_info()
            }
            
            # Quick metrics
            cpu_data = await self.resource_monitor.get_cpu_usage(False, 1.0)
            memory_data = await self.resource_monitor.get_memory_usage(False, True)
            uptime_data = await self.resource_monitor.get_uptime()
            
            summary["metrics"] = {
                "cpu_percent": cpu_data.get("cpu_percent"),
                "memory_percent": memory_data.get("memory_percent"),
                "uptime": uptime_data.get("uptime_formatted")
            }
            
            return {"success": True, "summary": summary}
            
        except Exception as e:
            logger.error(f"System summary failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_server(self):
        """Stop the MCP server"""
        self.running = False
        
        # Shutdown monitoring components
        await self.process_monitor.shutdown()
        await self.resource_monitor.shutdown()
        await self.log_parser.shutdown()
        await self.network_monitor.shutdown()
        
        logger.info("System MCP server stopped")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="System Monitoring MCP Server")
    parser.add_argument("--config", "-c", type=str, help="Configuration file path")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8767, help="Server port")
    
    args = parser.parse_args()
    
    # Create server
    server = SystemMCPServer(config_path=args.config)
    
    # Override config with command line args
    if args.host:
        server.config["server"]["host"] = args.host
    if args.port:
        server.config["server"]["port"] = args.port
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())