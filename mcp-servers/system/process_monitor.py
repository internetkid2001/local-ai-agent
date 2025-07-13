"""
Process Monitor for System MCP Server

Process management and monitoring functionality including process listing,
information gathering, control, and monitoring capabilities.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import psutil
import platform
import subprocess
import logging
import signal
import time
from typing import Dict, List, Any, Optional, Union
import re

logger = logging.getLogger(__name__)


class ProcessMonitor:
    """
    Process monitoring and management system.
    
    Features:
    - List and filter running processes
    - Get detailed process information
    - Process control (terminate, kill with safety checks)
    - Process monitoring and tracking
    - Service status checking
    - Resource usage tracking per process
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize process monitor.
        
        Args:
            config: Process monitoring configuration
        """
        self.config = config
        self.platform = platform.system().lower()
        
        # Security settings
        self.allow_kill = config.get("allow_process_kill", False)
        self.allowed_signals = config.get("allowed_signals", ["TERM", "HUP"])
        self.blocked_processes = config.get("blocked_processes", ["init", "kernel", "systemd"])
        self.require_confirmation = config.get("require_confirmation", True)
        
        # Monitoring settings
        self.track_children = config.get("track_children", True)
        self.include_threads = config.get("include_threads", False)
        self.sort_by = config.get("sort_by", "cpu_percent")
        
        # Process cache for monitoring
        self.process_cache: Dict[int, Dict[str, Any]] = {}
        self.last_update = 0
        self.update_interval = 2.0
        
        logger.info("Process monitor initialized")
    
    async def initialize(self):
        """Initialize process monitor"""
        try:
            # Initial process scan
            await self._update_process_cache()
            logger.info("Process monitor ready")
        except Exception as e:
            logger.error(f"Failed to initialize process monitor: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown process monitor"""
        self.process_cache.clear()
        logger.info("Process monitor shutdown")
    
    async def list_processes(self, sort_by: str = "cpu_percent", limit: int = 50, 
                           filter_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        List running processes with filtering and sorting.
        
        Args:
            sort_by: Sort criteria (pid, name, cpu_percent, memory_percent)
            limit: Maximum processes to return
            filter_pattern: Optional regex pattern to filter by name
            
        Returns:
            Process list with metadata
        """
        try:
            await self._update_process_cache()
            
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'status', 'create_time', 'cmdline', 'username']):
                try:
                    proc_info = proc.info
                    
                    # Apply filter if specified
                    if filter_pattern:
                        if not re.search(filter_pattern, proc_info['name'], re.IGNORECASE):
                            continue
                    
                    # Get additional info
                    try:
                        proc_info['memory_info'] = proc.memory_info()._asdict()
                        proc_info['num_threads'] = proc.num_threads()
                        proc_info['connections'] = len(proc.connections())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_info['memory_info'] = {}
                        proc_info['num_threads'] = 0
                        proc_info['connections'] = 0
                    
                    # Format timestamps
                    if proc_info['create_time']:
                        proc_info['create_time_formatted'] = time.strftime(
                            '%Y-%m-%d %H:%M:%S', 
                            time.localtime(proc_info['create_time'])
                        )
                    
                    processes.append(proc_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort processes
            if sort_by in ['cpu_percent', 'memory_percent']:
                processes.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
            elif sort_by == 'name':
                processes.sort(key=lambda x: x.get('name', '').lower())
            elif sort_by == 'pid':
                processes.sort(key=lambda x: x.get('pid', 0))
            
            # Apply limit
            processes = processes[:limit]
            
            return {
                "success": True,
                "processes": processes,
                "count": len(processes),
                "total_processes": len(list(psutil.process_iter())),
                "sort_by": sort_by,
                "filter": filter_pattern,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_process_info(self, pid: Optional[int] = None, 
                             name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific process.
        
        Args:
            pid: Process ID
            name: Process name (alternative to PID)
            
        Returns:
            Detailed process information
        """
        try:
            if pid:
                proc = psutil.Process(pid)
            elif name:
                # Find process by name
                processes = [p for p in psutil.process_iter(['pid', 'name']) 
                           if p.info['name'] == name]
                if not processes:
                    return {"success": False, "error": f"Process '{name}' not found"}
                proc = psutil.Process(processes[0].info['pid'])
            else:
                return {"success": False, "error": "Either pid or name must be specified"}
            
            # Gather comprehensive process information
            proc_info = {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "create_time": proc.create_time(),
                "create_time_formatted": time.strftime(
                    '%Y-%m-%d %H:%M:%S', 
                    time.localtime(proc.create_time())
                )
            }
            
            try:
                proc_info.update({
                    "cmdline": proc.cmdline(),
                    "cwd": proc.cwd(),
                    "username": proc.username(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_info": proc.memory_info()._asdict(),
                    "num_threads": proc.num_threads(),
                    "num_fds": proc.num_fds() if hasattr(proc, 'num_fds') else None,
                    "nice": proc.nice(),
                })
                
                # Parent/children information
                try:
                    parent = proc.parent()
                    proc_info["parent"] = {
                        "pid": parent.pid,
                        "name": parent.name()
                    } if parent else None
                except psutil.NoSuchProcess:
                    proc_info["parent"] = None
                
                if self.track_children:
                    children = proc.children(recursive=True)
                    proc_info["children"] = [
                        {"pid": child.pid, "name": child.name()} 
                        for child in children
                    ]
                
                # Network connections
                try:
                    connections = proc.connections()
                    proc_info["connections"] = [
                        {
                            "fd": conn.fd,
                            "family": str(conn.family),
                            "type": str(conn.type),
                            "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                            "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                            "status": conn.status
                        }
                        for conn in connections
                    ]
                except psutil.AccessDenied:
                    proc_info["connections"] = []
                
                # Open files
                try:
                    open_files = proc.open_files()
                    proc_info["open_files"] = [
                        {"path": f.path, "fd": f.fd, "position": getattr(f, 'position', None)}
                        for f in open_files[:10]  # Limit to first 10
                    ]
                    proc_info["open_files_count"] = len(open_files)
                except psutil.AccessDenied:
                    proc_info["open_files"] = []
                    proc_info["open_files_count"] = 0
                
            except psutil.AccessDenied as e:
                proc_info["access_denied"] = str(e)
            except psutil.NoSuchProcess:
                return {"success": False, "error": "Process no longer exists"}
            
            return {
                "success": True,
                "process": proc_info,
                "timestamp": time.time()
            }
            
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process with PID {pid} not found"}
        except Exception as e:
            logger.error(f"Failed to get process info: {e}")
            return {"success": False, "error": str(e)}
    
    async def kill_process(self, pid: int, signal_name: str = "TERM", 
                          force: bool = False) -> Dict[str, Any]:
        """
        Terminate a process with safety checks.
        
        Args:
            pid: Process ID to terminate
            signal_name: Signal to send (TERM, KILL, HUP)
            force: Force termination (bypass some safety checks)
            
        Returns:
            Termination result
        """
        try:
            if not self.allow_kill and not force:
                return {
                    "success": False,
                    "error": "Process killing is disabled in configuration"
                }
            
            if signal_name not in self.allowed_signals and not force:
                return {
                    "success": False,
                    "error": f"Signal '{signal_name}' not in allowed signals: {self.allowed_signals}"
                }
            
            # Get process info for safety checks
            proc = psutil.Process(pid)
            proc_name = proc.name()
            
            # Safety checks
            if proc_name in self.blocked_processes and not force:
                return {
                    "success": False,
                    "error": f"Process '{proc_name}' is in blocked processes list"
                }
            
            if pid <= 10 and not force:  # Protect critical system processes
                return {
                    "success": False,
                    "error": f"Refusing to kill critical system process (PID {pid})"
                }
            
            # Convert signal name to signal number
            signal_map = {
                "TERM": signal.SIGTERM,
                "KILL": signal.SIGKILL,
                "HUP": signal.SIGHUP,
                "INT": signal.SIGINT,
                "QUIT": signal.SIGQUIT
            }
            
            sig = signal_map.get(signal_name.upper())
            if not sig:
                return {
                    "success": False,
                    "error": f"Unknown signal: {signal_name}"
                }
            
            # Send signal
            proc.send_signal(sig)
            
            # Wait for process to terminate (for TERM/QUIT signals)
            if signal_name.upper() in ["TERM", "QUIT"]:
                try:
                    proc.wait(timeout=5)
                    status = "terminated"
                except psutil.TimeoutExpired:
                    status = "signal_sent_timeout"
                except psutil.NoSuchProcess:
                    status = "terminated"
            else:
                status = "signal_sent"
            
            return {
                "success": True,
                "pid": pid,
                "process_name": proc_name,
                "signal": signal_name,
                "status": status,
                "timestamp": time.time()
            }
            
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process with PID {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied to kill process {pid}"}
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
            return {"success": False, "error": str(e)}
    
    async def find_processes(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find processes by various criteria.
        
        Args:
            criteria: Search criteria (name, user, cpu_threshold, etc.)
            
        Returns:
            Matching processes
        """
        try:
            name_pattern = criteria.get("name")
            username = criteria.get("user")
            cpu_threshold = criteria.get("cpu_threshold")
            memory_threshold = criteria.get("memory_threshold")
            status_filter = criteria.get("status")
            
            matching_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                           'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Apply filters
                    if name_pattern and not re.search(name_pattern, proc_info['name'], re.IGNORECASE):
                        continue
                    
                    if username and proc_info.get('username') != username:
                        continue
                    
                    if cpu_threshold and proc_info.get('cpu_percent', 0) < cpu_threshold:
                        continue
                    
                    if memory_threshold and proc_info.get('memory_percent', 0) < memory_threshold:
                        continue
                    
                    if status_filter and proc_info.get('status') != status_filter:
                        continue
                    
                    matching_processes.append(proc_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "success": True,
                "processes": matching_processes,
                "count": len(matching_processes),
                "criteria": criteria,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to find processes: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor a specific process over time.
        
        Args:
            args: Monitoring parameters (pid, duration, interval)
            
        Returns:
            Process monitoring data
        """
        try:
            pid = args.get("pid")
            duration = args.get("duration", 60)  # seconds
            interval = args.get("interval", 2)   # seconds
            
            if not pid:
                return {"success": False, "error": "PID required for monitoring"}
            
            proc = psutil.Process(pid)
            monitoring_data = {
                "pid": pid,
                "name": proc.name(),
                "start_time": time.time(),
                "samples": []
            }
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                try:
                    sample = {
                        "timestamp": time.time(),
                        "cpu_percent": proc.cpu_percent(),
                        "memory_percent": proc.memory_percent(),
                        "memory_rss": proc.memory_info().rss,
                        "num_threads": proc.num_threads(),
                        "status": proc.status()
                    }
                    
                    monitoring_data["samples"].append(sample)
                    
                except psutil.NoSuchProcess:
                    monitoring_data["terminated"] = time.time()
                    break
                
                await asyncio.sleep(interval)
            
            # Calculate statistics
            if monitoring_data["samples"]:
                cpu_values = [s["cpu_percent"] for s in monitoring_data["samples"]]
                memory_values = [s["memory_percent"] for s in monitoring_data["samples"]]
                
                monitoring_data["statistics"] = {
                    "avg_cpu": sum(cpu_values) / len(cpu_values),
                    "max_cpu": max(cpu_values),
                    "avg_memory": sum(memory_values) / len(memory_values),
                    "max_memory": max(memory_values),
                    "sample_count": len(monitoring_data["samples"])
                }
            
            return {
                "success": True,
                "monitoring_data": monitoring_data,
                "duration": duration,
                "interval": interval
            }
            
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process with PID {pid} not found"}
        except Exception as e:
            logger.error(f"Failed to monitor process: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_services(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check status of system services.
        
        Args:
            args: Service checking parameters
            
        Returns:
            Service status information
        """
        try:
            service_names = args.get("services", [])
            check_all = args.get("check_all", False)
            
            services_status = {}
            
            if self.platform == "linux":
                # Use systemctl on Linux
                if check_all or not service_names:
                    # Get list of services
                    result = await asyncio.create_subprocess_exec(
                        "systemctl", "list-units", "--type=service", "--no-pager",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await result.communicate()
                    
                    if result.returncode == 0:
                        lines = stdout.decode().split('\n')
                        for line in lines:
                            if '.service' in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    service_name = parts[0].replace('.service', '')
                                    services_status[service_name] = {
                                        "loaded": parts[1],
                                        "active": parts[2],
                                        "sub": parts[3],
                                        "description": ' '.join(parts[4:]) if len(parts) > 4 else ""
                                    }
                
                # Check specific services
                for service in service_names:
                    result = await asyncio.create_subprocess_exec(
                        "systemctl", "is-active", f"{service}.service",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await result.communicate()
                    
                    services_status[service] = {
                        "active": stdout.decode().strip(),
                        "exit_code": result.returncode
                    }
            
            elif self.platform == "darwin":
                # Use launchctl on macOS
                result = await asyncio.create_subprocess_exec(
                    "launchctl", "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    lines = stdout.decode().split('\n')[1:]  # Skip header
                    for line in lines:
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                services_status[parts[2]] = {
                                    "pid": parts[0],
                                    "status": parts[1],
                                    "label": parts[2]
                                }
            
            elif self.platform == "windows":
                # Use sc query on Windows
                result = await asyncio.create_subprocess_exec(
                    "sc", "query",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    # Parse sc query output
                    services_status["windows_services"] = "Use 'Get-Service' in PowerShell for detailed info"
            
            return {
                "success": True,
                "services": services_status,
                "platform": self.platform,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to check services: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_process_cache(self):
        """Update process cache for monitoring"""
        try:
            current_time = time.time()
            
            if current_time - self.last_update < self.update_interval:
                return
            
            new_cache = {}
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    new_cache[proc_info['pid']] = {
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                        'last_seen': current_time
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            self.process_cache = new_cache
            self.last_update = current_time
            
        except Exception as e:
            logger.error(f"Failed to update process cache: {e}")
    
    def get_cached_processes(self) -> Dict[int, Dict[str, Any]]:
        """Get cached process information"""
        return self.process_cache.copy()