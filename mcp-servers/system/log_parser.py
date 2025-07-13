"""
Log Parser for System MCP Server

Log file parsing and analysis capabilities for system monitoring.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import re
import time
import logging
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path
import json
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class LogParser:
    """
    Log file parsing and analysis system.
    
    Features:
    - Parse various log formats (syslog, Apache, nginx, custom)
    - Search and filter log entries
    - Real-time log tailing
    - Pattern analysis and anomaly detection
    - Log level filtering and parsing
    - Performance metrics from logs
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize log parser.
        
        Args:
            config: Log parsing configuration
        """
        self.config = config
        
        # Configuration
        self.log_paths = config.get("log_paths", [
            "/var/log/syslog",
            "/var/log/messages", 
            "/var/log/auth.log",
            "/var/log/kern.log"
        ])
        self.max_lines = config.get("max_lines", 1000)
        self.follow_logs = config.get("follow_logs", True)
        
        # Log format patterns
        self.log_patterns = {
            "syslog": re.compile(
                r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s+'
                r'(?P<message>.*)'
            ),
            "apache_common": re.compile(
                r'(?P<ip>\S+)\s+\S+\s+\S+\s+'
                r'\[(?P<timestamp>[^\]]+)\]\s+'
                r'"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<protocol>\S+)"\s+'
                r'(?P<status>\d+)\s+(?P<size>\S+)'
            ),
            "apache_combined": re.compile(
                r'(?P<ip>\S+)\s+\S+\s+\S+\s+'
                r'\[(?P<timestamp>[^\]]+)\]\s+'
                r'"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<protocol>\S+)"\s+'
                r'(?P<status>\d+)\s+(?P<size>\S+)\s+'
                r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
            ),
            "nginx": re.compile(
                r'(?P<ip>\S+)\s+-\s+-\s+'
                r'\[(?P<timestamp>[^\]]+)\]\s+'
                r'"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<protocol>\S+)"\s+'
                r'(?P<status>\d+)\s+(?P<size>\d+)\s+'
                r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
            ),
            "json": re.compile(r'^\s*\{.*\}\s*$'),
            "timestamp_message": re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
                r'(?P<level>\w+)?\s*'
                r'(?P<message>.*)'
            )
        }
        
        # Log level mapping
        self.log_levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARN": 30,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
            "FATAL": 50
        }
        
        logger.info("Log parser initialized")
    
    async def initialize(self):
        """Initialize log parser"""
        try:
            # Verify log paths exist and are readable
            accessible_logs = []
            for log_path in self.log_paths:
                path = Path(log_path)
                if path.exists() and path.is_file():
                    try:
                        with open(path, 'r') as f:
                            f.read(1)  # Test read access
                        accessible_logs.append(log_path)
                    except PermissionError:
                        logger.warning(f"No read access to {log_path}")
                else:
                    logger.debug(f"Log file not found: {log_path}")
            
            self.accessible_logs = accessible_logs
            logger.info(f"Log parser ready - {len(accessible_logs)} accessible log files")
            
        except Exception as e:
            logger.error(f"Failed to initialize log parser: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown log parser"""
        logger.info("Log parser shutdown")
    
    async def parse_logs(self, log_path: Optional[str] = None, pattern: Optional[str] = None,
                        lines: int = 100, level: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse log files with filtering.
        
        Args:
            log_path: Specific log file to parse
            pattern: Regex pattern to search for
            lines: Number of lines to read (from end)
            level: Minimum log level to include
            
        Returns:
            Parsed log entries
        """
        try:
            if log_path:
                log_files = [log_path] if Path(log_path).exists() else []
            else:
                log_files = self.accessible_logs
            
            if not log_files:
                return {"success": False, "error": "No accessible log files"}
            
            all_entries = []
            
            for log_file in log_files:
                entries = await self._parse_single_log(log_file, pattern, lines, level)
                all_entries.extend(entries)
            
            # Sort by timestamp if possible
            all_entries.sort(key=lambda x: x.get('parsed_timestamp', 0), reverse=True)
            
            # Apply global line limit
            if len(all_entries) > lines:
                all_entries = all_entries[:lines]
            
            return {
                "success": True,
                "entries": all_entries,
                "count": len(all_entries),
                "log_files": log_files,
                "filters": {
                    "pattern": pattern,
                    "level": level,
                    "lines": lines
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to parse logs: {e}")
            return {"success": False, "error": str(e)}
    
    async def _parse_single_log(self, log_path: str, pattern: Optional[str], 
                               lines: int, level: Optional[str]) -> List[Dict[str, Any]]:
        """Parse a single log file"""
        entries = []
        
        try:
            # Read last N lines efficiently
            log_lines = await self._tail_file(log_path, lines * 2)  # Read extra for filtering
            
            min_level = self.log_levels.get(level.upper(), 0) if level else 0
            pattern_regex = re.compile(pattern, re.IGNORECASE) if pattern else None
            
            for line_num, line in enumerate(log_lines):
                line = line.strip()
                if not line:
                    continue
                
                # Parse line
                parsed_entry = self._parse_log_line(line, log_path, line_num)
                
                # Apply level filter
                if level and parsed_entry.get('level'):
                    entry_level = self.log_levels.get(parsed_entry['level'].upper(), 0)
                    if entry_level < min_level:
                        continue
                
                # Apply pattern filter
                if pattern_regex and not pattern_regex.search(line):
                    continue
                
                entries.append(parsed_entry)
            
            return entries[-lines:] if len(entries) > lines else entries
            
        except Exception as e:
            logger.error(f"Failed to parse {log_path}: {e}")
            return []
    
    def _parse_log_line(self, line: str, log_path: str, line_num: int) -> Dict[str, Any]:
        """Parse a single log line"""
        entry = {
            "raw_line": line,
            "log_file": log_path,
            "line_number": line_num,
            "parsed_timestamp": time.time()
        }
        
        # Try different log formats
        for format_name, pattern in self.log_patterns.items():
            match = pattern.match(line)
            if match:
                entry["format"] = format_name
                entry.update(match.groupdict())
                
                # Convert timestamp if possible
                if "timestamp" in entry:
                    entry["parsed_timestamp"] = self._parse_timestamp(entry["timestamp"])
                
                # Extract log level from message if not explicit
                if "level" not in entry and "message" in entry:
                    level = self._extract_log_level(entry["message"])
                    if level:
                        entry["level"] = level
                
                break
        else:
            # Fallback: treat as generic message
            entry["format"] = "unknown"
            entry["message"] = line
            
            # Try to extract level from line
            level = self._extract_log_level(line)
            if level:
                entry["level"] = level
        
        return entry
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse various timestamp formats to Unix timestamp"""
        import datetime
        
        # Common timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%b %d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(timestamp_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue
        
        # If all parsing fails, return current time
        return time.time()
    
    def _extract_log_level(self, message: str) -> Optional[str]:
        """Extract log level from message"""
        level_patterns = [
            r'\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\b',
            r'\[(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\]',
            r'<(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)>'
        ]
        
        for pattern in level_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    async def _tail_file(self, file_path: str, num_lines: int) -> List[str]:
        """Efficiently read last N lines from a file"""
        try:
            # Use shell tail command for efficiency on large files
            result = await asyncio.create_subprocess_exec(
                "tail", "-n", str(num_lines), file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return stdout.decode('utf-8', errors='replace').splitlines()
            else:
                # Fallback to Python implementation
                return self._tail_file_python(file_path, num_lines)
                
        except Exception:
            # Fallback to Python implementation
            return self._tail_file_python(file_path, num_lines)
    
    def _tail_file_python(self, file_path: str, num_lines: int) -> List[str]:
        """Python implementation of tail functionality"""
        try:
            with open(file_path, 'rb') as f:
                # Go to end of file
                f.seek(0, 2)
                file_size = f.tell()
                
                # Read backwards to find last N lines
                lines = []
                buffer = b''
                position = file_size
                
                while len(lines) < num_lines and position > 0:
                    # Read in chunks
                    chunk_size = min(4096, position)
                    position -= chunk_size
                    f.seek(position)
                    
                    chunk = f.read(chunk_size)
                    buffer = chunk + buffer
                    
                    # Split into lines
                    lines_in_buffer = buffer.split(b'\n')
                    buffer = lines_in_buffer[0]  # Keep incomplete line
                    
                    # Add complete lines
                    for line in reversed(lines_in_buffer[1:]):
                        if len(lines) < num_lines:
                            lines.insert(0, line.decode('utf-8', errors='replace'))
                
                # Add remaining buffer if it contains data
                if buffer and len(lines) < num_lines:
                    lines.insert(0, buffer.decode('utf-8', errors='replace'))
                
                return lines[-num_lines:]
                
        except Exception as e:
            logger.error(f"Failed to tail file {file_path}: {e}")
            return []
    
    async def search_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search logs with advanced filtering.
        
        Args:
            args: Search parameters
            
        Returns:
            Search results
        """
        try:
            query = args.get("query", "")
            log_files = args.get("log_files", self.accessible_logs)
            time_range = args.get("time_range")  # {start: timestamp, end: timestamp}
            level_filter = args.get("level")
            max_results = args.get("max_results", 1000)
            
            search_results = []
            
            for log_file in log_files:
                if not Path(log_file).exists():
                    continue
                
                file_results = await self._search_single_log(
                    log_file, query, time_range, level_filter, max_results
                )
                search_results.extend(file_results)
            
            # Sort by relevance and timestamp
            search_results.sort(key=lambda x: (x.get('relevance', 0), x.get('parsed_timestamp', 0)), reverse=True)
            
            return {
                "success": True,
                "results": search_results[:max_results],
                "total_matches": len(search_results),
                "query": query,
                "log_files_searched": len(log_files),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to search logs: {e}")
            return {"success": False, "error": str(e)}
    
    async def _search_single_log(self, log_file: str, query: str, 
                                time_range: Optional[Dict], level_filter: Optional[str],
                                max_results: int) -> List[Dict[str, Any]]:
        """Search a single log file"""
        results = []
        query_regex = re.compile(query, re.IGNORECASE) if query else None
        
        try:
            # For large files, we might want to limit the search scope
            lines = await self._tail_file(log_file, 10000)  # Search last 10k lines
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Parse line
                entry = self._parse_log_line(line, log_file, line_num)
                
                # Apply filters
                if level_filter and entry.get('level'):
                    if entry['level'].upper() != level_filter.upper():
                        continue
                
                if time_range:
                    entry_time = entry.get('parsed_timestamp', 0)
                    if time_range.get('start') and entry_time < time_range['start']:
                        continue
                    if time_range.get('end') and entry_time > time_range['end']:
                        continue
                
                # Apply query filter and calculate relevance
                if query_regex:
                    match = query_regex.search(line)
                    if not match:
                        continue
                    
                    # Calculate relevance score
                    relevance = len(query_regex.findall(line))
                    entry['relevance'] = relevance
                    entry['match_positions'] = [m.span() for m in query_regex.finditer(line)]
                
                results.append(entry)
                
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search {log_file}: {e}")
            return []
    
    async def tail_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Real-time log tailing.
        
        Args:
            args: Tailing parameters
            
        Returns:
            Log tail results
        """
        try:
            log_file = args.get("log_file")
            lines = args.get("lines", 50)
            follow = args.get("follow", False)
            duration = args.get("duration", 30) if follow else 0
            
            if not log_file or not Path(log_file).exists():
                return {"success": False, "error": "Log file not found"}
            
            # Get initial tail
            initial_lines = await self._tail_file(log_file, lines)
            
            result = {
                "success": True,
                "log_file": log_file,
                "initial_lines": [
                    self._parse_log_line(line, log_file, i) 
                    for i, line in enumerate(initial_lines)
                ],
                "follow": follow
            }
            
            if follow and duration > 0:
                # Follow the log for specified duration
                new_lines = await self._follow_log_file(log_file, duration)
                result["new_lines"] = new_lines
                result["duration"] = duration
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to tail log: {e}")
            return {"success": False, "error": str(e)}
    
    async def _follow_log_file(self, log_file: str, duration: float) -> List[Dict[str, Any]]:
        """Follow a log file for new lines"""
        new_lines = []
        
        try:
            # Get initial file position
            initial_size = Path(log_file).stat().st_size
            
            end_time = time.time() + duration
            
            while time.time() < end_time:
                current_size = Path(log_file).stat().st_size
                
                if current_size > initial_size:
                    # Read new content
                    with open(log_file, 'r') as f:
                        f.seek(initial_size)
                        new_content = f.read()
                        
                        for line_num, line in enumerate(new_content.splitlines()):
                            if line.strip():
                                parsed_line = self._parse_log_line(line, log_file, line_num)
                                new_lines.append(parsed_line)
                    
                    initial_size = current_size
                
                await asyncio.sleep(1)  # Check every second
            
            return new_lines
            
        except Exception as e:
            logger.error(f"Failed to follow log file: {e}")
            return []
    
    async def analyze_patterns(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze log patterns and anomalies.
        
        Args:
            args: Analysis parameters
            
        Returns:
            Pattern analysis results
        """
        try:
            log_files = args.get("log_files", self.accessible_logs)
            analysis_type = args.get("type", "frequency")  # frequency, errors, performance
            time_window = args.get("time_window", 3600)  # seconds
            
            analysis_results = {
                "analysis_type": analysis_type,
                "time_window": time_window,
                "log_files": log_files
            }
            
            if analysis_type == "frequency":
                analysis_results.update(await self._analyze_frequency_patterns(log_files, time_window))
            elif analysis_type == "errors":
                analysis_results.update(await self._analyze_error_patterns(log_files, time_window))
            elif analysis_type == "performance":
                analysis_results.update(await self._analyze_performance_patterns(log_files, time_window))
            
            return {
                "success": True,
                "analysis": analysis_results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_frequency_patterns(self, log_files: List[str], time_window: int) -> Dict[str, Any]:
        """Analyze frequency patterns in logs"""
        frequency_data = {
            "messages_per_hour": defaultdict(int),
            "top_processes": Counter(),
            "top_messages": Counter(),
            "hourly_distribution": defaultdict(int)
        }
        
        current_time = time.time()
        window_start = current_time - time_window
        
        for log_file in log_files:
            try:
                lines = await self._tail_file(log_file, 5000)
                
                for line in lines:
                    entry = self._parse_log_line(line, log_file, 0)
                    entry_time = entry.get('parsed_timestamp', current_time)
                    
                    if entry_time >= window_start:
                        # Count by hour
                        hour_key = int(entry_time // 3600)
                        frequency_data["messages_per_hour"][hour_key] += 1
                        
                        # Count by process
                        if 'process' in entry:
                            frequency_data["top_processes"][entry['process']] += 1
                        
                        # Count similar messages
                        message = entry.get('message', '')[:100]  # First 100 chars
                        frequency_data["top_messages"][message] += 1
                        
                        # Hourly distribution
                        hour_of_day = time.localtime(entry_time).tm_hour
                        frequency_data["hourly_distribution"][hour_of_day] += 1
                        
            except Exception as e:
                logger.debug(f"Error analyzing {log_file}: {e}")
        
        # Convert to regular dicts for JSON serialization
        return {
            "messages_per_hour": dict(frequency_data["messages_per_hour"]),
            "top_processes": dict(frequency_data["top_processes"].most_common(10)),
            "top_messages": dict(frequency_data["top_messages"].most_common(20)),
            "hourly_distribution": dict(frequency_data["hourly_distribution"])
        }
    
    async def _analyze_error_patterns(self, log_files: List[str], time_window: int) -> Dict[str, Any]:
        """Analyze error patterns in logs"""
        error_patterns = {
            "error_count": 0,
            "error_types": Counter(),
            "error_timeline": [],
            "top_error_messages": Counter()
        }
        
        current_time = time.time()
        window_start = current_time - time_window
        
        error_keywords = ['error', 'fail', 'exception', 'critical', 'fatal', 'panic', 'segfault']
        
        for log_file in log_files:
            try:
                lines = await self._tail_file(log_file, 5000)
                
                for line in lines:
                    entry = self._parse_log_line(line, log_file, 0)
                    entry_time = entry.get('parsed_timestamp', current_time)
                    
                    if entry_time >= window_start:
                        message = entry.get('message', '').lower()
                        level = entry.get('level', '').upper()
                        
                        # Check for errors
                        is_error = (level in ['ERROR', 'CRITICAL', 'FATAL'] or
                                  any(keyword in message for keyword in error_keywords))
                        
                        if is_error:
                            error_patterns["error_count"] += 1
                            error_patterns["error_types"][level or 'UNKNOWN'] += 1
                            error_patterns["error_timeline"].append({
                                "timestamp": entry_time,
                                "message": entry.get('message', '')[:200],
                                "level": level,
                                "source": log_file
                            })
                            
                            # Extract error message pattern
                            error_msg = entry.get('message', '')[:100]
                            error_patterns["top_error_messages"][error_msg] += 1
                            
            except Exception as e:
                logger.debug(f"Error analyzing {log_file}: {e}")
        
        return {
            "error_count": error_patterns["error_count"],
            "error_types": dict(error_patterns["error_types"]),
            "error_timeline": sorted(error_patterns["error_timeline"], 
                                   key=lambda x: x["timestamp"], reverse=True)[:50],
            "top_error_messages": dict(error_patterns["top_error_messages"].most_common(10))
        }
    
    async def _analyze_performance_patterns(self, log_files: List[str], time_window: int) -> Dict[str, Any]:
        """Analyze performance patterns in logs"""
        # This would analyze response times, request rates, etc.
        # Implementation depends on specific log formats
        return {
            "performance_analysis": "Not implemented - requires specific log format configuration"
        }