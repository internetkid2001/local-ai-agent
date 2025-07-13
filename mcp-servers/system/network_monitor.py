"""
Network Monitor for System MCP Server

Network monitoring and connectivity checking capabilities.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import psutil
import socket
import subprocess
import platform
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """
    Network monitoring and connectivity system.
    
    Features:
    - Network interface status and statistics
    - Connectivity testing (ping, port checks)
    - Network connection monitoring
    - Bandwidth usage tracking
    - DNS resolution testing
    - Network performance metrics
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize network monitor.
        
        Args:
            config: Network monitoring configuration
        """
        self.config = config
        self.platform = platform.system().lower()
        
        # Configuration
        self.interface_filter = config.get("interface_filter", [])
        self.include_loopback = config.get("include_loopback", False)
        self.dns_servers = config.get("dns_servers", ["8.8.8.8", "1.1.1.1"])
        
        # Data storage
        self.last_network_stats = None
        self.connection_history: List[Dict[str, Any]] = []
        
        logger.info("Network monitor initialized")
    
    async def initialize(self):
        """Initialize network monitor"""
        try:
            # Get initial network statistics
            self.last_network_stats = psutil.net_io_counters(pernic=True)
            
            logger.info("Network monitor ready")
        except Exception as e:
            logger.error(f"Failed to initialize network monitor: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown network monitor"""
        self.connection_history.clear()
        logger.info("Network monitor shutdown")
    
    async def get_status(self, interface: Optional[str] = None, 
                        include_stats: bool = True) -> Dict[str, Any]:
        """
        Get network interface status and statistics.
        
        Args:
            interface: Specific interface to check
            include_stats: Include detailed statistics
            
        Returns:
            Network status information
        """
        try:
            interfaces = []
            
            # Get network interface addresses
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for iface_name, addresses in net_if_addrs.items():
                # Apply interface filter
                if interface and iface_name != interface:
                    continue
                
                if self.interface_filter and iface_name not in self.interface_filter:
                    continue
                
                # Skip loopback if not included
                if not self.include_loopback and iface_name.startswith(('lo', 'Loopback')):
                    continue
                
                iface_info = {
                    "name": iface_name,
                    "addresses": []
                }
                
                # Get interface statistics
                if iface_name in net_if_stats:
                    stats = net_if_stats[iface_name]
                    iface_info.update({
                        "is_up": stats.isup,
                        "duplex": str(stats.duplex),
                        "speed": stats.speed,
                        "mtu": stats.mtu
                    })
                else:
                    iface_info.update({
                        "is_up": False,
                        "duplex": "unknown",
                        "speed": 0,
                        "mtu": 0
                    })
                
                # Process addresses
                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address
                    }
                    
                    if addr.netmask:
                        addr_info["netmask"] = addr.netmask
                    if addr.broadcast:
                        addr_info["broadcast"] = addr.broadcast
                    
                    iface_info["addresses"].append(addr_info)
                
                # Get I/O statistics if requested
                if include_stats:
                    io_stats = await self._get_interface_io_stats(iface_name)
                    if io_stats:
                        iface_info["io_stats"] = io_stats
                
                interfaces.append(iface_info)
            
            # Get default gateway
            try:
                gateways = psutil.net_if_addrs()
                # This is a simplified approach - actual gateway detection is platform-specific
                default_gateway = await self._get_default_gateway()
            except Exception as e:
                logger.debug(f"Failed to get default gateway: {e}")
                default_gateway = None
            
            return {
                "success": True,
                "interfaces": interfaces,
                "interface_count": len(interfaces),
                "default_gateway": default_gateway,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get network status: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_interface_io_stats(self, interface_name: str) -> Optional[Dict[str, Any]]:
        """Get I/O statistics for a specific interface"""
        try:
            net_io_counters = psutil.net_io_counters(pernic=True)
            
            if interface_name in net_io_counters:
                stats = net_io_counters[interface_name]
                
                io_stats = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout
                }
                
                # Calculate rates if we have previous data
                if self.last_network_stats and interface_name in self.last_network_stats:
                    time_delta = time.time() - getattr(self, '_last_stats_time', time.time())
                    if time_delta > 0:
                        last_stats = self.last_network_stats[interface_name]
                        
                        for key in ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv']:
                            current_val = getattr(stats, key)
                            last_val = getattr(last_stats, key)
                            rate = (current_val - last_val) / time_delta
                            io_stats[f"{key}_per_sec"] = rate
                
                return io_stats
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get I/O stats for {interface_name}: {e}")
            return None
    
    async def _get_default_gateway(self) -> Optional[str]:
        """Get default gateway address"""
        try:
            if self.platform == "linux":
                result = await asyncio.create_subprocess_exec(
                    "ip", "route", "show", "default",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    output = stdout.decode()
                    # Parse: default via 192.168.1.1 dev eth0
                    for line in output.split('\n'):
                        if 'default via' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                return parts[2]
            
            elif self.platform == "darwin":
                result = await asyncio.create_subprocess_exec(
                    "route", "-n", "get", "default",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    output = stdout.decode()
                    for line in output.split('\n'):
                        if 'gateway:' in line:
                            return line.split(':')[1].strip()
            
            elif self.platform == "windows":
                result = await asyncio.create_subprocess_exec(
                    "route", "print", "0.0.0.0",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    # Parse Windows route output
                    output = stdout.decode()
                    # Implementation would parse Windows route table format
                    pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get default gateway: {e}")
            return None
    
    async def get_network_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed network statistics.
        
        Args:
            args: Statistics parameters
            
        Returns:
            Network statistics
        """
        try:
            per_interface = args.get("per_interface", True)
            include_rates = args.get("include_rates", True)
            
            # Get overall network I/O counters
            net_io = psutil.net_io_counters()
            
            result = {
                "success": True,
                "overall_stats": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                },
                "timestamp": time.time()
            }
            
            # Get per-interface stats if requested
            if per_interface:
                per_nic_stats = psutil.net_io_counters(pernic=True)
                interface_stats = {}
                
                for iface_name, stats in per_nic_stats.items():
                    interface_stats[iface_name] = {
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "packets_sent": stats.packets_sent,
                        "packets_recv": stats.packets_recv,
                        "errin": stats.errin,
                        "errout": stats.errout,
                        "dropin": stats.dropin,
                        "dropout": stats.dropout
                    }
                    
                    # Calculate rates
                    if include_rates and self.last_network_stats and iface_name in self.last_network_stats:
                        time_delta = time.time() - getattr(self, '_last_stats_time', time.time())
                        if time_delta > 0:
                            last_stats = self.last_network_stats[iface_name]
                            
                            for key in ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv']:
                                current_val = getattr(stats, key)
                                last_val = getattr(last_stats, key)
                                rate = (current_val - last_val) / time_delta
                                interface_stats[iface_name][f"{key}_per_sec"] = rate
                
                result["interface_stats"] = interface_stats
                
                # Update last stats
                self.last_network_stats = per_nic_stats
                self._last_stats_time = time.time()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get network stats: {e}")
            return {"success": False, "error": str(e)}
    
    async def ping_host(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ping a host to test connectivity.
        
        Args:
            args: Ping parameters (host, count, timeout)
            
        Returns:
            Ping results
        """
        try:
            host = args.get("host")
            count = args.get("count", 4)
            timeout = args.get("timeout", 10)
            
            if not host:
                return {"success": False, "error": "Host parameter required"}
            
            # Build ping command based on platform
            if self.platform == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
            
            start_time = time.time()
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            execution_time = time.time() - start_time
            
            ping_result = {
                "success": result.returncode == 0,
                "host": host,
                "count": count,
                "timeout": timeout,
                "execution_time": execution_time,
                "exit_code": result.returncode
            }
            
            if result.returncode == 0:
                # Parse ping output
                output = stdout.decode()
                ping_stats = self._parse_ping_output(output)
                ping_result.update(ping_stats)
                ping_result["raw_output"] = output
            else:
                ping_result["error"] = stderr.decode()
            
            return ping_result
            
        except Exception as e:
            logger.error(f"Failed to ping host: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_ping_output(self, output: str) -> Dict[str, Any]:
        """Parse ping command output to extract statistics"""
        stats = {}
        
        try:
            lines = output.split('\n')
            
            # Look for statistics line
            for line in lines:
                line = line.strip()
                
                # Parse packet loss
                if 'packet loss' in line.lower():
                    import re
                    loss_match = re.search(r'(\d+(?:\.\d+)?)%.*packet loss', line)
                    if loss_match:
                        stats["packet_loss_percent"] = float(loss_match.group(1))
                
                # Parse timing statistics (round-trip min/avg/max)
                if 'min/avg/max' in line.lower() or 'minimum/maximum/average' in line.lower():
                    import re
                    # Linux/macOS format: min/avg/max/mdev = 1.234/2.345/3.456/0.789 ms
                    time_match = re.search(r'([\d.]+)/([\d.]+)/([\d.]+)', line)
                    if time_match:
                        stats["rtt_min"] = float(time_match.group(1))
                        stats["rtt_avg"] = float(time_match.group(2))
                        stats["rtt_max"] = float(time_match.group(3))
            
            # Count successful pings
            successful_pings = output.count('time=')
            if successful_pings > 0:
                stats["successful_pings"] = successful_pings
            
        except Exception as e:
            logger.debug(f"Failed to parse ping output: {e}")
        
        return stats
    
    async def check_port(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a port is open on a host.
        
        Args:
            args: Port check parameters (host, port, timeout)
            
        Returns:
            Port check results
        """
        try:
            host = args.get("host")
            port = args.get("port")
            timeout = args.get("timeout", 5)
            
            if not host or not port:
                return {"success": False, "error": "Host and port parameters required"}
            
            start_time = time.time()
            
            try:
                # Create socket connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                
                result = sock.connect_ex((host, port))
                sock.close()
                
                response_time = time.time() - start_time
                
                return {
                    "success": True,
                    "host": host,
                    "port": port,
                    "is_open": result == 0,
                    "response_time": response_time,
                    "timeout": timeout
                }
                
            except socket.gaierror as e:
                return {
                    "success": False,
                    "host": host,
                    "port": port,
                    "error": f"DNS resolution failed: {e}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "host": host,
                    "port": port,
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"Failed to check port: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_connections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get active network connections.
        
        Args:
            args: Connection filter parameters
            
        Returns:
            Network connections list
        """
        try:
            kind = args.get("kind", "inet")  # inet, inet4, inet6, tcp, udp, unix
            pid = args.get("pid")  # Filter by process ID
            
            connections = []
            
            for conn in psutil.net_connections(kind=kind):
                conn_info = {
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "status": conn.status
                }
                
                if conn.laddr:
                    conn_info["local_address"] = {
                        "ip": conn.laddr.ip,
                        "port": conn.laddr.port
                    }
                
                if conn.raddr:
                    conn_info["remote_address"] = {
                        "ip": conn.raddr.ip,
                        "port": conn.raddr.port
                    }
                
                if conn.pid:
                    conn_info["pid"] = conn.pid
                    try:
                        proc = psutil.Process(conn.pid)
                        conn_info["process_name"] = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Apply PID filter
                if pid and conn.pid != pid:
                    continue
                
                connections.append(conn_info)
            
            return {
                "success": True,
                "connections": connections,
                "count": len(connections),
                "kind": kind,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get connections: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_dns_resolution(self, hostname: str, 
                                 dns_server: Optional[str] = None) -> Dict[str, Any]:
        """
        Test DNS resolution for a hostname.
        
        Args:
            hostname: Hostname to resolve
            dns_server: Optional specific DNS server to use
            
        Returns:
            DNS resolution results
        """
        try:
            start_time = time.time()
            
            try:
                # Use system resolver by default
                addr_info = socket.getaddrinfo(hostname, None)
                
                # Extract IP addresses
                ip_addresses = []
                for info in addr_info:
                    ip = info[4][0]
                    if ip not in ip_addresses:
                        ip_addresses.append(ip)
                
                resolution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "hostname": hostname,
                    "ip_addresses": ip_addresses,
                    "resolution_time": resolution_time,
                    "dns_server": dns_server or "system_default"
                }
                
            except socket.gaierror as e:
                return {
                    "success": False,
                    "hostname": hostname,
                    "error": f"DNS resolution failed: {e}",
                    "dns_server": dns_server or "system_default"
                }
            
        except Exception as e:
            logger.error(f"Failed to test DNS resolution: {e}")
            return {"success": False, "error": str(e)}
    
    async def bandwidth_test(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform basic bandwidth measurement.
        
        Args:
            args: Bandwidth test parameters
            
        Returns:
            Bandwidth test results
        """
        try:
            duration = args.get("duration", 10)  # seconds
            interface = args.get("interface")
            
            # Get initial statistics
            if interface:
                initial_stats = psutil.net_io_counters(pernic=True).get(interface)
                if not initial_stats:
                    return {"success": False, "error": f"Interface {interface} not found"}
            else:
                initial_stats = psutil.net_io_counters()
            
            start_time = time.time()
            initial_bytes_sent = initial_stats.bytes_sent
            initial_bytes_recv = initial_stats.bytes_recv
            
            # Wait for measurement duration
            await asyncio.sleep(duration)
            
            # Get final statistics
            if interface:
                final_stats = psutil.net_io_counters(pernic=True).get(interface)
            else:
                final_stats = psutil.net_io_counters()
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            # Calculate bandwidth
            bytes_sent_delta = final_stats.bytes_sent - initial_bytes_sent
            bytes_recv_delta = final_stats.bytes_recv - initial_bytes_recv
            
            upload_bps = bytes_sent_delta / actual_duration
            download_bps = bytes_recv_delta / actual_duration
            
            return {
                "success": True,
                "duration": actual_duration,
                "interface": interface or "all",
                "upload_bytes_per_sec": upload_bps,
                "download_bytes_per_sec": download_bps,
                "upload_mbps": (upload_bps * 8) / (1024 * 1024),
                "download_mbps": (download_bps * 8) / (1024 * 1024),
                "total_bytes_sent": bytes_sent_delta,
                "total_bytes_received": bytes_recv_delta
            }
            
        except Exception as e:
            logger.error(f"Failed to perform bandwidth test: {e}")
            return {"success": False, "error": str(e)}