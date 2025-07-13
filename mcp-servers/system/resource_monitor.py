"""
Resource Monitor for System MCP Server

System resource monitoring including CPU, memory, disk, and performance metrics.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import psutil
import platform
import time
import logging
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    System resource monitoring system.
    
    Features:
    - CPU usage monitoring (overall and per-core)
    - Memory usage tracking (RAM and swap)
    - Disk usage and I/O statistics
    - Network interface statistics
    - System load and uptime monitoring
    - Performance metrics collection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize resource monitor.
        
        Args:
            config: Resource monitoring configuration
        """
        self.config = config
        self.platform = platform.system().lower()
        
        # Monitoring settings
        self.collect_interval = config.get("collect_interval", 1.0)
        self.smooth_values = config.get("smooth_values", True)
        self.include_per_cpu = config.get("include_per_cpu", False)
        self.history_limit = config.get("history_limit", 100)
        
        # Data storage
        self.metrics_history: List[Dict[str, Any]] = []
        self.last_network_stats = None
        self.last_disk_stats = None
        
        logger.info("Resource monitor initialized")
    
    async def initialize(self):
        """Initialize resource monitor"""
        try:
            # Initial readings to establish baselines
            await self.get_cpu_usage(per_cpu=False, interval=0.1)
            self.last_network_stats = psutil.net_io_counters()
            self.last_disk_stats = psutil.disk_io_counters()
            
            logger.info("Resource monitor ready")
        except Exception as e:
            logger.error(f"Failed to initialize resource monitor: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown resource monitor"""
        self.metrics_history.clear()
        logger.info("Resource monitor shutdown")
    
    async def get_cpu_usage(self, per_cpu: bool = False, interval: float = 1.0) -> Dict[str, Any]:
        """
        Get CPU usage statistics.
        
        Args:
            per_cpu: Return per-CPU core statistics
            interval: Measurement interval in seconds
            
        Returns:
            CPU usage data
        """
        try:
            # Get CPU percentages
            if per_cpu:
                cpu_percent_list = psutil.cpu_percent(interval=interval, percpu=True)
                cpu_percent = sum(cpu_percent_list) / len(cpu_percent_list)
            else:
                cpu_percent = psutil.cpu_percent(interval=interval)
                cpu_percent_list = None
            
            # Get CPU times
            cpu_times = psutil.cpu_times()
            
            # Get CPU frequency
            try:
                cpu_freq = psutil.cpu_freq()
                freq_info = {
                    "current": cpu_freq.current,
                    "min": cpu_freq.min,
                    "max": cpu_freq.max
                } if cpu_freq else None
            except (AttributeError, OSError):
                freq_info = None
            
            # Get CPU count
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            
            result = {
                "success": True,
                "cpu_percent": cpu_percent,
                "cpu_times": cpu_times._asdict(),
                "cpu_count": {
                    "logical": cpu_count_logical,
                    "physical": cpu_count_physical
                },
                "cpu_frequency": freq_info,
                "timestamp": time.time()
            }
            
            if per_cpu and cpu_percent_list:
                result["per_cpu"] = [
                    {"core": i, "percent": percent} 
                    for i, percent in enumerate(cpu_percent_list)
                ]
            
            # Get load average (Unix-like systems)
            if hasattr(psutil, 'getloadavg'):
                try:
                    load_avg = psutil.getloadavg()
                    result["load_average"] = {
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2]
                    }
                except OSError:
                    result["load_average"] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get CPU usage: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_memory_usage(self, include_swap: bool = True, 
                             human_readable: bool = True) -> Dict[str, Any]:
        """
        Get memory usage statistics.
        
        Args:
            include_swap: Include swap memory information
            human_readable: Format sizes in human-readable format
            
        Returns:
            Memory usage data
        """
        try:
            # Virtual memory (RAM)
            virtual_memory = psutil.virtual_memory()
            
            def format_bytes(bytes_value):
                if not human_readable:
                    return bytes_value
                
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_value < 1024.0:
                        return f"{bytes_value:.1f} {unit}"
                    bytes_value /= 1024.0
                return f"{bytes_value:.1f} PB"
            
            memory_info = {
                "total": format_bytes(virtual_memory.total),
                "available": format_bytes(virtual_memory.available),
                "used": format_bytes(virtual_memory.used),
                "free": format_bytes(virtual_memory.free),
                "percent": virtual_memory.percent,
                "buffers": format_bytes(getattr(virtual_memory, 'buffers', 0)),
                "cached": format_bytes(getattr(virtual_memory, 'cached', 0)),
                "shared": format_bytes(getattr(virtual_memory, 'shared', 0))
            }
            
            result = {
                "success": True,
                "memory": memory_info,
                "memory_percent": virtual_memory.percent,
                "timestamp": time.time()
            }
            
            # Raw bytes for calculations
            if not human_readable:
                result["memory_raw"] = virtual_memory._asdict()
            
            # Swap memory
            if include_swap:
                try:
                    swap_memory = psutil.swap_memory()
                    swap_info = {
                        "total": format_bytes(swap_memory.total),
                        "used": format_bytes(swap_memory.used),
                        "free": format_bytes(swap_memory.free),
                        "percent": swap_memory.percent,
                        "sin": format_bytes(swap_memory.sin),
                        "sout": format_bytes(swap_memory.sout)
                    }
                    result["swap"] = swap_info
                    result["swap_percent"] = swap_memory.percent
                    
                    if not human_readable:
                        result["swap_raw"] = swap_memory._asdict()
                        
                except Exception as e:
                    logger.debug(f"Swap memory not available: {e}")
                    result["swap"] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_disk_usage(self, path: Optional[str] = None, 
                           human_readable: bool = True) -> Dict[str, Any]:
        """
        Get disk usage statistics.
        
        Args:
            path: Specific path to check (defaults to all mounted filesystems)
            human_readable: Format sizes in human-readable format
            
        Returns:
            Disk usage data
        """
        try:
            def format_bytes(bytes_value):
                if not human_readable:
                    return bytes_value
                
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_value < 1024.0:
                        return f"{bytes_value:.1f} {unit}"
                    bytes_value /= 1024.0
                return f"{bytes_value:.1f} PB"
            
            if path:
                # Check specific path
                disk_usage = psutil.disk_usage(path)
                return {
                    "success": True,
                    "path": path,
                    "total": format_bytes(disk_usage.total),
                    "used": format_bytes(disk_usage.used),
                    "free": format_bytes(disk_usage.free),
                    "percent": (disk_usage.used / disk_usage.total) * 100,
                    "timestamp": time.time()
                }
            
            # Get all mounted filesystems
            filesystems = []
            disk_partitions = psutil.disk_partitions()
            
            for partition in disk_partitions:
                try:
                    disk_usage = psutil.disk_usage(partition.mountpoint)
                    
                    filesystem_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": format_bytes(disk_usage.total),
                        "used": format_bytes(disk_usage.used),
                        "free": format_bytes(disk_usage.free),
                        "percent": (disk_usage.used / disk_usage.total) * 100 if disk_usage.total > 0 else 0
                    }
                    
                    if not human_readable:
                        filesystem_info["raw"] = disk_usage._asdict()
                    
                    filesystems.append(filesystem_info)
                    
                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access {partition.mountpoint}: {e}")
                    continue
            
            # Get disk I/O statistics
            try:
                disk_io = psutil.disk_io_counters()
                io_stats = disk_io._asdict() if disk_io else {}
                
                # Calculate rates if we have previous data
                if self.last_disk_stats:
                    time_delta = time.time() - getattr(self, '_last_disk_time', time.time())
                    if time_delta > 0:
                        for key in ['read_bytes', 'write_bytes', 'read_count', 'write_count']:
                            if key in io_stats and hasattr(self.last_disk_stats, key):
                                current_val = getattr(disk_io, key)
                                last_val = getattr(self.last_disk_stats, key)
                                rate = (current_val - last_val) / time_delta
                                io_stats[f"{key}_per_sec"] = rate
                
                self.last_disk_stats = disk_io
                self._last_disk_time = time.time()
                
            except Exception as e:
                logger.debug(f"Disk I/O stats not available: {e}")
                io_stats = {}
            
            return {
                "success": True,
                "filesystems": filesystems,
                "io_stats": io_stats,
                "total_filesystems": len(filesystems),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_system_metrics(self, include_history: bool = False, 
                               detailed: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive system metrics.
        
        Args:
            include_history: Include historical data
            detailed: Include detailed breakdowns
            
        Returns:
            Comprehensive system metrics
        """
        try:
            metrics = {
                "timestamp": time.time(),
                "platform": await self.get_platform_info()
            }
            
            # Collect current metrics
            cpu_data = await self.get_cpu_usage(per_cpu=detailed, interval=1.0)
            memory_data = await self.get_memory_usage(include_swap=True, human_readable=detailed)
            disk_data = await self.get_disk_usage(human_readable=detailed)
            
            metrics.update({
                "cpu": cpu_data,
                "memory": memory_data,
                "disk": disk_data
            })
            
            # Network statistics
            try:
                net_io = psutil.net_io_counters()
                net_stats = net_io._asdict() if net_io else {}
                
                # Calculate rates
                if self.last_network_stats:
                    time_delta = time.time() - getattr(self, '_last_network_time', time.time())
                    if time_delta > 0:
                        for key in ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv']:
                            if hasattr(net_io, key) and hasattr(self.last_network_stats, key):
                                current_val = getattr(net_io, key)
                                last_val = getattr(self.last_network_stats, key)
                                rate = (current_val - last_val) / time_delta
                                net_stats[f"{key}_per_sec"] = rate
                
                self.last_network_stats = net_io
                self._last_network_time = time.time()
                
                metrics["network"] = {"success": True, "stats": net_stats}
                
            except Exception as e:
                logger.debug(f"Network stats not available: {e}")
                metrics["network"] = {"success": False, "error": str(e)}
            
            # System uptime and boot time
            try:
                boot_time = psutil.boot_time()
                uptime_seconds = time.time() - boot_time
                
                metrics["uptime"] = {
                    "boot_time": boot_time,
                    "boot_time_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(boot_time)),
                    "uptime_seconds": uptime_seconds,
                    "uptime_formatted": self._format_uptime(uptime_seconds)
                }
            except Exception as e:
                logger.debug(f"Uptime not available: {e}")
                metrics["uptime"] = {"error": str(e)}
            
            # Add to history
            if len(self.metrics_history) >= self.history_limit:
                self.metrics_history.pop(0)
            
            # Store simplified version in history
            history_entry = {
                "timestamp": metrics["timestamp"],
                "cpu_percent": cpu_data.get("cpu_percent", 0),
                "memory_percent": memory_data.get("memory_percent", 0),
                "disk_percent": max([fs.get("percent", 0) for fs in disk_data.get("filesystems", [])], default=0)
            }
            self.metrics_history.append(history_entry)
            
            if include_history:
                metrics["history"] = self.metrics_history.copy()
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_resources(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor system resources continuously.
        
        Args:
            args: Monitoring parameters (duration, interval, alerts)
            
        Returns:
            Resource monitoring data
        """
        try:
            duration = args.get("duration", 60)  # seconds
            interval = args.get("interval", 5)   # seconds
            enable_alerts = args.get("alerts", False)
            alert_thresholds = args.get("thresholds", {
                "cpu_percent": 90,
                "memory_percent": 85,
                "disk_percent": 90
            })
            
            monitoring_data = {
                "start_time": time.time(),
                "samples": [],
                "alerts": []
            }
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Collect sample
                sample_start = time.time()
                
                cpu_data = await self.get_cpu_usage(per_cpu=False, interval=1.0)
                memory_data = await self.get_memory_usage(include_swap=False, human_readable=False)
                
                sample = {
                    "timestamp": sample_start,
                    "cpu_percent": cpu_data.get("cpu_percent", 0),
                    "memory_percent": memory_data.get("memory_percent", 0),
                    "load_average": cpu_data.get("load_average")
                }
                
                monitoring_data["samples"].append(sample)
                
                # Check alerts
                if enable_alerts:
                    alerts = []
                    
                    if sample["cpu_percent"] > alert_thresholds.get("cpu_percent", 90):
                        alerts.append({
                            "type": "cpu_high",
                            "value": sample["cpu_percent"],
                            "threshold": alert_thresholds["cpu_percent"],
                            "timestamp": sample_start
                        })
                    
                    if sample["memory_percent"] > alert_thresholds.get("memory_percent", 85):
                        alerts.append({
                            "type": "memory_high",
                            "value": sample["memory_percent"],
                            "threshold": alert_thresholds["memory_percent"],
                            "timestamp": sample_start
                        })
                    
                    monitoring_data["alerts"].extend(alerts)
                
                # Wait for next interval
                elapsed = time.time() - sample_start
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            # Calculate statistics
            if monitoring_data["samples"]:
                cpu_values = [s["cpu_percent"] for s in monitoring_data["samples"]]
                memory_values = [s["memory_percent"] for s in monitoring_data["samples"]]
                
                monitoring_data["statistics"] = {
                    "duration": duration,
                    "sample_count": len(monitoring_data["samples"]),
                    "cpu_stats": {
                        "avg": sum(cpu_values) / len(cpu_values),
                        "min": min(cpu_values),
                        "max": max(cpu_values)
                    },
                    "memory_stats": {
                        "avg": sum(memory_values) / len(memory_values),
                        "min": min(memory_values),
                        "max": max(memory_values)
                    },
                    "alert_count": len(monitoring_data["alerts"])
                }
            
            return {
                "success": True,
                "monitoring_data": monitoring_data
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor resources: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """Get platform and system information"""
        try:
            return {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }
        except Exception as e:
            logger.error(f"Failed to get platform info: {e}")
            return {"error": str(e)}
    
    async def get_uptime(self) -> Dict[str, Any]:
        """Get system uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            return {
                "success": True,
                "boot_time": boot_time,
                "boot_time_formatted": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(boot_time)),
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": self._format_uptime(uptime_seconds)
            }
        except Exception as e:
            logger.error(f"Failed to get uptime: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_load_average(self) -> Dict[str, Any]:
        """Get system load average"""
        try:
            if hasattr(psutil, 'getloadavg'):
                load_avg = psutil.getloadavg()
                return {
                    "success": True,
                    "load_average": {
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2]
                    },
                    "cpu_count": psutil.cpu_count()
                }
            else:
                return {"success": False, "error": "Load average not available on this platform"}
        except Exception as e:
            logger.error(f"Failed to get load average: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        return ", ".join(parts) if parts else "less than a minute"
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        if limit:
            return self.metrics_history[-limit:]
        return self.metrics_history.copy()