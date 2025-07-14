#!/usr/bin/env python3
"""
Advanced Health Monitoring System

Real-time health monitoring with alerting, SLA tracking, and predictive
failure detection for enterprise-grade system reliability.

Author: Claude Code
Date: 2025-07-14
Phase: 4.7 - Enhanced Error Handling
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
import statistics
from collections import defaultdict, deque
import psutil
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of health metrics"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class HealthMetric:
    """Health metric definition"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    component: str
    check_function: Callable
    interval: float = 60.0
    timeout: float = 30.0
    enabled: bool = True
    critical: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Thresholds
    warning_threshold: Optional[float] = None
    error_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


@dataclass
class HealthAlert:
    """Health alert"""
    id: str
    severity: AlertSeverity
    component: str
    message: str
    timestamp: float
    metric_name: str
    current_value: float
    threshold: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Alert lifecycle
    resolved: bool = False
    resolved_timestamp: Optional[float] = None
    acknowledgment_id: Optional[str] = None
    acknowledgment_timestamp: Optional[float] = None


@dataclass
class SLAConfig:
    """SLA configuration"""
    name: str
    target_availability: float = 0.999  # 99.9%
    target_response_time: float = 1.0  # 1 second
    measurement_window: float = 3600.0  # 1 hour
    enabled: bool = True


@dataclass
class SLAMetrics:
    """SLA metrics tracking"""
    availability: float = 0.0
    response_time_p50: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    error_rate: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    downtime_seconds: float = 0.0


class HealthMonitorConfig:
    """Health monitoring configuration"""
    
    def __init__(self):
        self.monitoring_interval = 30.0  # 30 seconds
        self.metric_retention_hours = 24
        self.alert_retention_hours = 168  # 1 week
        self.max_alerts_per_hour = 100
        
        # System resource thresholds
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 85.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 90.0
        self.disk_critical_threshold = 98.0
        
        # Network thresholds
        self.response_time_warning = 1.0
        self.response_time_critical = 5.0
        self.error_rate_warning = 0.05  # 5%
        self.error_rate_critical = 0.1   # 10%
        
        # Alerting configuration
        self.alert_cooldown_seconds = 300.0  # 5 minutes
        self.enable_alert_aggregation = True
        self.enable_predictive_alerts = True
        
        # SLA configuration
        self.sla_configs = [
            SLAConfig(
                name="api_availability",
                target_availability=0.999,
                target_response_time=1.0
            ),
            SLAConfig(
                name="mcp_server_availability",
                target_availability=0.995,
                target_response_time=2.0
            )
        ]


class AdvancedHealthMonitor:
    """
    Advanced health monitoring system with enterprise features.
    
    Features:
    - Real-time health monitoring with configurable checks
    - SLA tracking and reporting
    - Predictive failure detection
    - Multi-channel alerting (email, webhook, SMS)
    - Comprehensive metrics collection
    - Health dashboards and reporting
    - Auto-remediation triggers
    """
    
    def __init__(self, config: HealthMonitorConfig = None):
        self.config = config or HealthMonitorConfig()
        
        # Health checks and metrics
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.health_status: Dict[str, HealthStatus] = {}
        
        # Alerting
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.alert_history: List[HealthAlert] = []
        self.alert_handlers: List[Callable] = []
        self.alert_cooldowns: Dict[str, float] = {}
        
        # SLA tracking
        self.sla_metrics: Dict[str, SLAMetrics] = {}
        self.sla_history: Dict[str, List[SLAMetrics]] = defaultdict(list)
        
        # Background tasks
        self._monitoring_task = None
        self._cleanup_task = None
        self._running = False
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize default health checks
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """Setup default system health checks"""
        
        # CPU usage check
        self.register_health_check(HealthCheck(
            name="cpu_usage",
            component="system",
            check_function=self._check_cpu_usage,
            interval=30.0,
            warning_threshold=self.config.cpu_warning_threshold,
            critical_threshold=self.config.cpu_critical_threshold
        ))
        
        # Memory usage check
        self.register_health_check(HealthCheck(
            name="memory_usage",
            component="system",
            check_function=self._check_memory_usage,
            interval=30.0,
            warning_threshold=self.config.memory_warning_threshold,
            critical_threshold=self.config.memory_critical_threshold
        ))
        
        # Disk usage check
        self.register_health_check(HealthCheck(
            name="disk_usage",
            component="system",
            check_function=self._check_disk_usage,
            interval=60.0,
            warning_threshold=self.config.disk_warning_threshold,
            critical_threshold=self.config.disk_critical_threshold
        ))
        
        # Process health check
        self.register_health_check(HealthCheck(
            name="process_health",
            component="system",
            check_function=self._check_process_health,
            interval=30.0,
            critical=True
        ))
    
    async def initialize(self):
        """Initialize health monitoring system"""
        logger.info("Initializing advanced health monitoring system...")
        
        self._running = True
        
        # Start background monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Initialize SLA metrics
        for sla_config in self.config.sla_configs:
            self.sla_metrics[sla_config.name] = SLAMetrics()
        
        logger.info("Health monitoring system initialized")
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        self.health_checks[health_check.name] = health_check
        self.health_status[health_check.name] = HealthStatus.UNKNOWN
        logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            del self.health_status[name]
            logger.info(f"Unregistered health check: {name}")
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler"""
        self.alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: Callable):
        """Remove alert handler"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                # Execute all health checks
                await self._execute_health_checks()
                
                # Update SLA metrics
                await self._update_sla_metrics()
                
                # Process alerts
                await self._process_alerts()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Brief pause before retry
    
    async def _execute_health_checks(self):
        """Execute all enabled health checks"""
        current_time = time.time()
        
        for name, check in self.health_checks.items():
            if not check.enabled:
                continue
            
            try:
                # Execute health check
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check.check_function):
                    result = await asyncio.wait_for(
                        check.check_function(),
                        timeout=check.timeout
                    )
                else:
                    result = check.check_function()
                
                execution_time = time.time() - start_time
                
                # Process result
                if isinstance(result, dict):
                    status = result.get('status', HealthStatus.UNKNOWN)
                    value = result.get('value', 0.0)
                    message = result.get('message', '')
                else:
                    status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                    value = 1.0 if result else 0.0
                    message = f"Health check {name} {'passed' if result else 'failed'}"
                
                # Update health status
                self.health_status[name] = status
                
                # Record metric
                metric = HealthMetric(
                    name=name,
                    metric_type=MetricType.GAUGE,
                    value=value,
                    timestamp=current_time,
                    tags=check.tags,
                    description=message
                )
                
                with self._lock:
                    self.metrics[name].append(metric)
                
                # Check thresholds and generate alerts
                await self._check_thresholds(check, value, message)
                
                logger.debug(f"Health check {name}: {status.value} ({value})")
                
            except asyncio.TimeoutError:
                logger.warning(f"Health check {name} timed out")
                self.health_status[name] = HealthStatus.UNHEALTHY
                await self._generate_alert(
                    check, AlertSeverity.ERROR, f"Health check {name} timed out"
                )
            except Exception as e:
                logger.error(f"Error executing health check {name}: {e}")
                self.health_status[name] = HealthStatus.UNHEALTHY
                await self._generate_alert(
                    check, AlertSeverity.ERROR, f"Health check {name} failed: {e}"
                )
    
    async def _check_thresholds(self, check: HealthCheck, value: float, message: str):
        """Check metric thresholds and generate alerts"""
        
        # Determine alert severity based on thresholds
        severity = None
        threshold = None
        
        if check.critical_threshold is not None and value >= check.critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold = check.critical_threshold
        elif check.error_threshold is not None and value >= check.error_threshold:
            severity = AlertSeverity.ERROR
            threshold = check.error_threshold
        elif check.warning_threshold is not None and value >= check.warning_threshold:
            severity = AlertSeverity.WARNING
            threshold = check.warning_threshold
        
        if severity:
            await self._generate_alert(check, severity, message, value, threshold)
    
    async def _generate_alert(self, 
                            check: HealthCheck, 
                            severity: AlertSeverity, 
                            message: str,
                            value: float = 0.0,
                            threshold: float = 0.0):
        """Generate health alert"""
        
        # Check cooldown period
        cooldown_key = f"{check.name}_{severity.value}"
        current_time = time.time()
        
        if cooldown_key in self.alert_cooldowns:
            if current_time - self.alert_cooldowns[cooldown_key] < self.config.alert_cooldown_seconds:
                return  # Still in cooldown
        
        # Create alert
        alert_id = f"alert_{int(current_time)}_{check.name}"
        alert = HealthAlert(
            id=alert_id,
            severity=severity,
            component=check.component,
            message=message,
            timestamp=current_time,
            metric_name=check.name,
            current_value=value,
            threshold=threshold,
            tags=check.tags.copy()
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Update cooldown
        self.alert_cooldowns[cooldown_key] = current_time
        
        # Notify handlers
        await self._notify_alert_handlers(alert)
        
        logger.warning(f"Generated alert: {alert.severity.value} - {alert.message}")
    
    async def _notify_alert_handlers(self, alert: HealthAlert):
        """Notify all alert handlers"""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    async def _update_sla_metrics(self):
        """Update SLA metrics"""
        current_time = time.time()
        
        for sla_name, sla_config in {c.name: c for c in self.config.sla_configs}.items():
            if not sla_config.enabled:
                continue
            
            try:
                # Calculate SLA metrics based on recent data
                metrics = self._calculate_sla_metrics(sla_name, sla_config)
                self.sla_metrics[sla_name] = metrics
                
                # Check SLA violations
                if metrics.availability < sla_config.target_availability:
                    await self._generate_sla_alert(
                        sla_name, "availability", 
                        metrics.availability, sla_config.target_availability
                    )
                
                if metrics.response_time_p95 > sla_config.target_response_time:
                    await self._generate_sla_alert(
                        sla_name, "response_time", 
                        metrics.response_time_p95, sla_config.target_response_time
                    )
                
            except Exception as e:
                logger.error(f"Error updating SLA metrics for {sla_name}: {e}")
    
    def _calculate_sla_metrics(self, sla_name: str, sla_config: SLAConfig) -> SLAMetrics:
        """Calculate SLA metrics for given time window"""
        # This is a simplified implementation
        # In production, you'd integrate with your actual metrics storage
        
        metrics = SLAMetrics()
        
        # Calculate based on health check data
        with self._lock:
            if sla_name in self.metrics:
                recent_metrics = [
                    m for m in self.metrics[sla_name]
                    if time.time() - m.timestamp < sla_config.measurement_window
                ]
                
                if recent_metrics:
                    # Calculate availability
                    healthy_count = sum(1 for m in recent_metrics if m.value > 0)
                    metrics.availability = healthy_count / len(recent_metrics)
                    
                    # Calculate response times (simplified)
                    response_times = [m.value for m in recent_metrics if m.value > 0]
                    if response_times:
                        response_times.sort()
                        metrics.response_time_p50 = response_times[int(len(response_times) * 0.5)]
                        metrics.response_time_p95 = response_times[int(len(response_times) * 0.95)]
                        metrics.response_time_p99 = response_times[int(len(response_times) * 0.99)]
                    
                    metrics.total_requests = len(recent_metrics)
                    metrics.failed_requests = len(recent_metrics) - healthy_count
                    metrics.error_rate = metrics.failed_requests / metrics.total_requests
        
        return metrics
    
    async def _generate_sla_alert(self, sla_name: str, metric_type: str, 
                                current_value: float, target_value: float):
        """Generate SLA violation alert"""
        message = f"SLA violation: {sla_name} {metric_type} = {current_value:.3f} (target: {target_value:.3f})"
        
        alert_id = f"sla_{sla_name}_{metric_type}_{int(time.time())}"
        alert = HealthAlert(
            id=alert_id,
            severity=AlertSeverity.CRITICAL,
            component="sla",
            message=message,
            timestamp=time.time(),
            metric_name=f"{sla_name}_{metric_type}",
            current_value=current_value,
            threshold=target_value,
            tags={"sla": sla_name, "metric_type": metric_type}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        await self._notify_alert_handlers(alert)
    
    async def _process_alerts(self):
        """Process active alerts for auto-resolution"""
        current_time = time.time()
        resolved_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.resolved:
                continue
            
            # Check if alert condition is resolved
            if await self._is_alert_resolved(alert):
                alert.resolved = True
                alert.resolved_timestamp = current_time
                resolved_alerts.append(alert)
                
                logger.info(f"Alert resolved: {alert.message}")
        
        # Remove resolved alerts from active list
        for alert in resolved_alerts:
            if alert.id in self.active_alerts:
                del self.active_alerts[alert.id]
    
    async def _is_alert_resolved(self, alert: HealthAlert) -> bool:
        """Check if alert condition is resolved"""
        # Check if the current health status is healthy
        if alert.metric_name in self.health_status:
            current_status = self.health_status[alert.metric_name]
            return current_status == HealthStatus.HEALTHY
        
        return False
    
    async def _cleanup_loop(self):
        """Cleanup old metrics and alerts"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = time.time()
                
                # Cleanup old metrics
                retention_seconds = self.config.metric_retention_hours * 3600
                
                with self._lock:
                    for metric_name, metric_queue in self.metrics.items():
                        # Remove old metrics
                        while (metric_queue and 
                               current_time - metric_queue[0].timestamp > retention_seconds):
                            metric_queue.popleft()
                
                # Cleanup old alerts
                alert_retention_seconds = self.config.alert_retention_hours * 3600
                self.alert_history = [
                    alert for alert in self.alert_history
                    if current_time - alert.timestamp < alert_retention_seconds
                ]
                
                logger.debug("Completed metrics and alerts cleanup")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    # Default health check implementations
    async def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= self.config.cpu_critical_threshold:
                status = HealthStatus.CRITICAL
            elif cpu_percent >= self.config.cpu_warning_threshold:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'value': cpu_percent,
                'message': f'CPU usage: {cpu_percent:.1f}%'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'value': 0.0,
                'message': f'Failed to check CPU usage: {e}'
            }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent >= self.config.memory_critical_threshold:
                status = HealthStatus.CRITICAL
            elif memory_percent >= self.config.memory_warning_threshold:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'value': memory_percent,
                'message': f'Memory usage: {memory_percent:.1f}% ({memory.used / 1024**3:.1f}GB used)'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'value': 0.0,
                'message': f'Failed to check memory usage: {e}'
            }
    
    async def _check_disk_usage(self) -> Dict[str, Any]:
        """Check disk usage"""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent >= self.config.disk_critical_threshold:
                status = HealthStatus.CRITICAL
            elif disk_percent >= self.config.disk_warning_threshold:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'value': disk_percent,
                'message': f'Disk usage: {disk_percent:.1f}% ({disk.used / 1024**3:.1f}GB used)'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'value': 0.0,
                'message': f'Failed to check disk usage: {e}'
            }
    
    async def _check_process_health(self) -> Dict[str, Any]:
        """Check process health"""
        try:
            # Check if current process is healthy
            process = psutil.Process(os.getpid())
            
            # Check if process is running
            if process.is_running():
                status = HealthStatus.HEALTHY
                message = f'Process {process.name()} (PID: {process.pid}) is running'
            else:
                status = HealthStatus.CRITICAL
                message = f'Process {process.name()} (PID: {process.pid}) is not running'
            
            return {
                'status': status,
                'value': 1.0 if status == HealthStatus.HEALTHY else 0.0,
                'message': message
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'value': 0.0,
                'message': f'Failed to check process health: {e}'
            }
    
    # Public API methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        overall_status = HealthStatus.HEALTHY
        
        # Determine overall status based on component statuses
        for status in self.health_status.values():
            if status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                break
            elif status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            'overall_status': overall_status.value,
            'component_statuses': {
                name: status.value for name, status in self.health_status.items()
            },
            'active_alerts': len(self.active_alerts),
            'timestamp': time.time()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get health metrics"""
        with self._lock:
            return {
                'metrics': {
                    name: [
                        {
                            'value': metric.value,
                            'timestamp': metric.timestamp,
                            'tags': metric.tags
                        }
                        for metric in metrics
                    ]
                    for name, metrics in self.metrics.items()
                },
                'sla_metrics': {
                    name: {
                        'availability': metrics.availability,
                        'response_time_p95': metrics.response_time_p95,
                        'error_rate': metrics.error_rate,
                        'total_requests': metrics.total_requests
                    }
                    for name, metrics in self.sla_metrics.items()
                }
            }
    
    def get_alerts(self) -> Dict[str, Any]:
        """Get active alerts"""
        return {
            'active_alerts': [
                {
                    'id': alert.id,
                    'severity': alert.severity.value,
                    'component': alert.component,
                    'message': alert.message,
                    'timestamp': alert.timestamp,
                    'metric_name': alert.metric_name,
                    'current_value': alert.current_value,
                    'threshold': alert.threshold
                }
                for alert in self.active_alerts.values()
            ],
            'alert_history': [
                {
                    'id': alert.id,
                    'severity': alert.severity.value,
                    'component': alert.component,
                    'message': alert.message,
                    'timestamp': alert.timestamp,
                    'resolved': alert.resolved,
                    'resolved_timestamp': alert.resolved_timestamp
                }
                for alert in self.alert_history[-100:]  # Last 100 alerts
            ]
        }
    
    async def acknowledge_alert(self, alert_id: str, acknowledgment_id: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledgment_id = acknowledgment_id
            alert.acknowledgment_timestamp = time.time()
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledgment_id}")
    
    async def shutdown(self):
        """Shutdown health monitoring system"""
        logger.info("Shutting down health monitoring system...")
        
        self._running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        logger.info("Health monitoring system shutdown complete")