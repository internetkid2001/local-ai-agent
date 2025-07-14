#!/usr/bin/env python3
"""
Performance Monitoring System

Comprehensive monitoring and metrics collection for the MCP orchestration system
with real-time performance tracking and optimization recommendations.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6 - Performance Optimization
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to collect"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Single metric value with timestamp"""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    name: str
    metric_type: MetricType
    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float
    rate: float  # per second
    last_update: float


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Features:
    - Real-time metrics collection
    - Performance trend analysis
    - Automatic performance optimization recommendations
    - Resource utilization monitoring
    - SLA tracking and alerting
    - Custom metric definitions
    """
    
    def __init__(self, collection_interval: float = 10.0):
        self.collection_interval = collection_interval
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.metric_types: Dict[str, MetricType] = {}
        self.locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        
        # System metrics
        self.system_metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_io_read": 0.0,
            "disk_io_write": 0.0,
            "network_sent": 0.0,
            "network_recv": 0.0
        }
        
        # Performance thresholds
        self.thresholds = {
            "response_time_p95": 2.0,  # seconds
            "error_rate": 0.01,  # 1%
            "cpu_percent": 80.0,  # 80%
            "memory_percent": 90.0,  # 90%
            "connection_pool_utilization": 0.8  # 80%
        }
        
        # Alerts
        self.alerts: List[Dict[str, Any]] = []
        self.alert_callbacks: List[Callable] = []
        
        # Background tasks
        self._collection_task = None
        self._running = False
        
        # Initialize default metrics
        self._initialize_default_metrics()
    
    def _initialize_default_metrics(self):
        """Initialize default metrics"""
        
        # MCP operation metrics
        self.register_metric("mcp_operations_total", MetricType.COUNTER)
        self.register_metric("mcp_operation_duration", MetricType.HISTOGRAM)
        self.register_metric("mcp_operation_errors", MetricType.COUNTER)
        
        # Connection pool metrics
        self.register_metric("connection_pool_size", MetricType.GAUGE)
        self.register_metric("connection_pool_active", MetricType.GAUGE)
        self.register_metric("connection_pool_idle", MetricType.GAUGE)
        self.register_metric("connection_pool_hits", MetricType.COUNTER)
        self.register_metric("connection_pool_misses", MetricType.COUNTER)
        
        # Cache metrics
        self.register_metric("cache_hits", MetricType.COUNTER)
        self.register_metric("cache_misses", MetricType.COUNTER)
        self.register_metric("cache_size", MetricType.GAUGE)
        self.register_metric("cache_memory_usage", MetricType.GAUGE)
        
        # Error handling metrics
        self.register_metric("error_handler_retries", MetricType.COUNTER)
        self.register_metric("circuit_breaker_trips", MetricType.COUNTER)
        self.register_metric("graceful_degradations", MetricType.COUNTER)
        
        # System metrics
        self.register_metric("system_cpu_percent", MetricType.GAUGE)
        self.register_metric("system_memory_percent", MetricType.GAUGE)
        self.register_metric("system_disk_io_read", MetricType.GAUGE)
        self.register_metric("system_disk_io_write", MetricType.GAUGE)
        self.register_metric("system_network_sent", MetricType.GAUGE)
        self.register_metric("system_network_recv", MetricType.GAUGE)
    
    async def initialize(self):
        """Initialize monitoring system"""
        logger.info("Initializing performance monitoring...")
        
        self._running = True
        
        # Start collection task
        self._collection_task = asyncio.create_task(self._collection_loop())
        
        logger.info("Performance monitoring initialized")
    
    def register_metric(self, name: str, metric_type: MetricType):
        """Register a new metric"""
        self.metric_types[name] = metric_type
        logger.debug(f"Registered metric: {name} ({metric_type.value})")
    
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value"""
        if name not in self.metric_types:
            logger.warning(f"Unknown metric: {name}")
            return
        
        with self.locks[name]:
            metric_value = MetricValue(
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            )
            self.metrics[name].append(metric_value)
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        self.record_metric(name, value, labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        self.record_metric(name, value, labels)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric value"""
        self.record_metric(name, value, labels)
    
    def time_operation(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        return TimingContext(self, name, labels)
    
    def get_metric_summary(self, name: str, window_seconds: float = 300.0) -> Optional[MetricSummary]:
        """Get summary statistics for a metric"""
        if name not in self.metrics:
            return None
        
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        with self.locks[name]:
            # Filter values within time window
            values = [
                mv.value for mv in self.metrics[name]
                if mv.timestamp >= cutoff_time
            ]
        
        if not values:
            return None
        
        # Calculate statistics
        count = len(values)
        sum_val = sum(values)
        min_val = min(values)
        max_val = max(values)
        avg_val = sum_val / count
        
        # Calculate percentiles
        sorted_values = sorted(values)
        p50 = self._percentile(sorted_values, 0.5)
        p95 = self._percentile(sorted_values, 0.95)
        p99 = self._percentile(sorted_values, 0.99)
        
        # Calculate rate (per second)
        rate = count / window_seconds
        
        return MetricSummary(
            name=name,
            metric_type=self.metric_types[name],
            count=count,
            sum=sum_val,
            min=min_val,
            max=max_val,
            avg=avg_val,
            p50=p50,
            p95=p95,
            p99=p99,
            rate=rate,
            last_update=current_time
        )
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_all_metrics(self, window_seconds: float = 300.0) -> Dict[str, MetricSummary]:
        """Get summary for all metrics"""
        summaries = {}
        
        for name in self.metric_types:
            summary = self.get_metric_summary(name, window_seconds)
            if summary:
                summaries[name] = summary
        
        return summaries
    
    def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        summaries = self.get_all_metrics()
        
        # Check response time threshold
        if "mcp_operation_duration" in summaries:
            duration_summary = summaries["mcp_operation_duration"]
            if duration_summary.p95 > self.thresholds["response_time_p95"]:
                alerts.append({
                    "type": "threshold_breach",
                    "metric": "mcp_operation_duration",
                    "threshold": self.thresholds["response_time_p95"],
                    "current_value": duration_summary.p95,
                    "severity": "warning",
                    "message": f"High response time: {duration_summary.p95:.2f}s (threshold: {self.thresholds['response_time_p95']}s)"
                })
        
        # Check error rate threshold
        if "mcp_operations_total" in summaries and "mcp_operation_errors" in summaries:
            total_ops = summaries["mcp_operations_total"]
            error_ops = summaries["mcp_operation_errors"]
            
            if total_ops.sum > 0:
                error_rate = error_ops.sum / total_ops.sum
                if error_rate > self.thresholds["error_rate"]:
                    alerts.append({
                        "type": "threshold_breach",
                        "metric": "error_rate",
                        "threshold": self.thresholds["error_rate"],
                        "current_value": error_rate,
                        "severity": "critical",
                        "message": f"High error rate: {error_rate:.2%} (threshold: {self.thresholds['error_rate']:.2%})"
                    })
        
        # Check system resource thresholds
        if "system_cpu_percent" in summaries:
            cpu_summary = summaries["system_cpu_percent"]
            if cpu_summary.avg > self.thresholds["cpu_percent"]:
                alerts.append({
                    "type": "threshold_breach",
                    "metric": "system_cpu_percent",
                    "threshold": self.thresholds["cpu_percent"],
                    "current_value": cpu_summary.avg,
                    "severity": "warning",
                    "message": f"High CPU usage: {cpu_summary.avg:.1f}% (threshold: {self.thresholds['cpu_percent']}%)"
                })
        
        if "system_memory_percent" in summaries:
            memory_summary = summaries["system_memory_percent"]
            if memory_summary.avg > self.thresholds["memory_percent"]:
                alerts.append({
                    "type": "threshold_breach",
                    "metric": "system_memory_percent",
                    "threshold": self.thresholds["memory_percent"],
                    "current_value": memory_summary.avg,
                    "severity": "critical",
                    "message": f"High memory usage: {memory_summary.avg:.1f}% (threshold: {self.thresholds['memory_percent']}%)"
                })
        
        return alerts
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []
        summaries = self.get_all_metrics()
        
        # Check connection pool utilization
        if ("connection_pool_size" in summaries and 
            "connection_pool_active" in summaries):
            
            pool_size = summaries["connection_pool_size"]
            active_connections = summaries["connection_pool_active"]
            
            if pool_size.avg > 0:
                utilization = active_connections.avg / pool_size.avg
                
                if utilization > 0.8:
                    recommendations.append({
                        "type": "performance_optimization",
                        "category": "connection_pool",
                        "priority": "high",
                        "message": f"Connection pool utilization high ({utilization:.1%}). Consider increasing pool size.",
                        "suggestion": "Increase max_connections_per_type in PoolConfig"
                    })
                elif utilization < 0.2:
                    recommendations.append({
                        "type": "resource_optimization",
                        "category": "connection_pool",
                        "priority": "low",
                        "message": f"Connection pool utilization low ({utilization:.1%}). Consider reducing pool size.",
                        "suggestion": "Decrease max_connections_per_type in PoolConfig"
                    })
        
        # Check cache hit rate
        if ("cache_hits" in summaries and "cache_misses" in summaries):
            hits = summaries["cache_hits"]
            misses = summaries["cache_misses"]
            
            if hits.sum + misses.sum > 0:
                hit_rate = hits.sum / (hits.sum + misses.sum)
                
                if hit_rate < 0.7:
                    recommendations.append({
                        "type": "performance_optimization",
                        "category": "cache",
                        "priority": "medium",
                        "message": f"Cache hit rate low ({hit_rate:.1%}). Consider increasing cache size or TTL.",
                        "suggestion": "Increase max_size or default_ttl in CacheConfig"
                    })
        
        # Check error rates
        if ("mcp_operations_total" in summaries and 
            "mcp_operation_errors" in summaries):
            
            total = summaries["mcp_operations_total"]
            errors = summaries["mcp_operation_errors"]
            
            if total.sum > 0:
                error_rate = errors.sum / total.sum
                
                if error_rate > 0.05:
                    recommendations.append({
                        "type": "reliability_optimization",
                        "category": "error_handling",
                        "priority": "high",
                        "message": f"Error rate high ({error_rate:.1%}). Review error handling configuration.",
                        "suggestion": "Check error logs and consider adjusting retry policies"
                    })
        
        # Check system resources
        if "system_cpu_percent" in summaries:
            cpu_summary = summaries["system_cpu_percent"]
            if cpu_summary.avg > 70:
                recommendations.append({
                    "type": "scaling_recommendation",
                    "category": "system_resources",
                    "priority": "medium",
                    "message": f"High CPU usage ({cpu_summary.avg:.1f}%). Consider scaling resources.",
                    "suggestion": "Add more CPU cores or distribute load"
                })
        
        return recommendations
    
    async def _collection_loop(self):
        """Background task for collecting system metrics"""
        while self._running:
            try:
                await asyncio.sleep(self.collection_interval)
                await self._collect_system_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge("system_cpu_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.set_gauge("system_memory_percent", memory.percent)
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.set_gauge("system_disk_io_read", disk_io.read_bytes)
                self.set_gauge("system_disk_io_write", disk_io.write_bytes)
            
            # Network metrics
            net_io = psutil.net_io_counters()
            if net_io:
                self.set_gauge("system_network_sent", net_io.bytes_sent)
                self.set_gauge("system_network_recv", net_io.bytes_recv)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def _trigger_alerts(self, alerts: List[Dict[str, Any]]):
        """Trigger alert callbacks"""
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        summaries = self.get_all_metrics()
        alerts = self.check_thresholds()
        recommendations = self.generate_recommendations()
        
        # Calculate key performance indicators
        kpis = {}
        
        if "mcp_operation_duration" in summaries:
            kpis["avg_response_time"] = summaries["mcp_operation_duration"].avg
            kpis["p95_response_time"] = summaries["mcp_operation_duration"].p95
        
        if ("mcp_operations_total" in summaries and 
            "mcp_operation_errors" in summaries):
            total = summaries["mcp_operations_total"].sum
            errors = summaries["mcp_operation_errors"].sum
            kpis["error_rate"] = errors / total if total > 0 else 0
        
        if ("cache_hits" in summaries and "cache_misses" in summaries):
            hits = summaries["cache_hits"].sum
            misses = summaries["cache_misses"].sum
            kpis["cache_hit_rate"] = hits / (hits + misses) if (hits + misses) > 0 else 0
        
        return {
            "kpis": kpis,
            "metrics": {name: {
                "avg": summary.avg,
                "p95": summary.p95,
                "rate": summary.rate,
                "count": summary.count
            } for name, summary in summaries.items()},
            "alerts": alerts,
            "recommendations": recommendations,
            "system_health": {
                "cpu_percent": summaries.get("system_cpu_percent", {}).get("avg", 0),
                "memory_percent": summaries.get("system_memory_percent", {}).get("avg", 0),
                "status": "healthy" if not alerts else "warning"
            },
            "timestamp": time.time()
        }
    
    async def shutdown(self):
        """Shutdown monitoring system"""
        logger.info("Shutting down performance monitoring...")
        
        self._running = False
        
        # Cancel collection task
        if self._collection_task:
            self._collection_task.cancel()
        
        logger.info("Performance monitoring shutdown complete")


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, metric_name: str, labels: Dict[str, str] = None):
        self.monitor = monitor
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.monitor.record_histogram(self.metric_name, duration, self.labels)
        
        # Record operation
        self.monitor.increment_counter("mcp_operations_total", labels=self.labels)
        
        # Record error if exception occurred
        if exc_type:
            error_labels = self.labels.copy()
            error_labels["error_type"] = exc_type.__name__
            self.monitor.increment_counter("mcp_operation_errors", labels=error_labels)


class MonitoredMCPClient:
    """
    Wrapper for MCP clients that adds performance monitoring.
    """
    
    def __init__(self, client, monitor: PerformanceMonitor):
        self.client = client
        self.monitor = monitor
        self.client_type = getattr(client, 'client_type', 'unknown')
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call tool with performance monitoring"""
        
        labels = {
            "client_type": self.client_type,
            "tool_name": tool_name
        }
        
        with self.monitor.time_operation("mcp_operation_duration", labels):
            return await self.client.call_tool(tool_name, parameters)
    
    def __getattr__(self, name):
        """Delegate other attributes to wrapped client"""
        return getattr(self.client, name)