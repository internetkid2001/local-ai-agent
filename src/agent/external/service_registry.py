"""
Service Registry

Central registry for external service configurations and capabilities.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from .api_client import APIConfig
from .rate_limiter import RateLimitConfig, RateLimitStrategy
from .auth_manager import AuthMethod
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ServiceType(Enum):
    """Types of external services"""
    WEB_SEARCH = "web_search"
    REST_API = "rest_api"
    DATABASE = "database"
    CLOUD_STORAGE = "cloud_storage"
    AI_SERVICE = "ai_service"
    NOTIFICATION = "notification"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class ServiceStatus(Enum):
    """Service availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Individual service endpoint definition"""
    name: str
    method: str  # HTTP method
    path: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    response_format: str = "json"
    rate_limit: Optional[RateLimitConfig] = None


@dataclass
class ServiceDefinition:
    """Complete service definition"""
    service_id: str
    name: str
    service_type: ServiceType
    description: str
    api_config: APIConfig
    auth_method: AuthMethod
    endpoints: List[ServiceEndpoint] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_checked: Optional[float] = None
    error_count: int = 0
    success_count: int = 0


class ServiceRegistry:
    """
    Central registry for external service management.
    
    Features:
    - Service discovery and registration
    - Health monitoring and status tracking
    - Capability-based service lookup
    - Configuration management
    - Service dependency tracking
    - Load balancing and failover
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize service registry.
        
        Args:
            config_dir: Directory for service configurations
        """
        self.config_dir = Path(config_dir or "config/services")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.services: Dict[str, ServiceDefinition] = {}
        self.service_groups: Dict[str, List[str]] = {}
        self.health_checkers: Dict[str, Callable] = {}
        
        # Built-in service definitions
        self._register_builtin_services()
        
        logger.info("Service registry initialized")
    
    def _register_builtin_services(self):
        """Register built-in service definitions"""
        
        # DuckDuckGo Search
        duckduckgo = ServiceDefinition(
            service_id="duckduckgo",
            name="DuckDuckGo Search",
            service_type=ServiceType.WEB_SEARCH,
            description="Privacy-focused web search engine",
            api_config=APIConfig(
                base_url="https://api.duckduckgo.com",
                timeout=10.0,
                auth_required=False
            ),
            auth_method=AuthMethod.API_KEY,  # Not required but for consistency
            endpoints=[
                ServiceEndpoint(
                    name="instant_answer",
                    method="GET",
                    path="/",
                    description="Get instant answers and search results",
                    parameters={"q": "search query", "format": "json", "no_html": "1"}
                )
            ],
            capabilities=["web_search", "instant_answers", "no_tracking"]
        )
        
        # Brave Search
        brave_search = ServiceDefinition(
            service_id="brave_search",
            name="Brave Search API",
            service_type=ServiceType.WEB_SEARCH,
            description="Independent web search with API access",
            api_config=APIConfig(
                base_url="https://api.search.brave.com/res/v1",
                timeout=15.0,
                auth_required=True,
                auth_type="api_key",
                default_headers={"Accept": "application/json"}
            ),
            auth_method=AuthMethod.API_KEY,
            endpoints=[
                ServiceEndpoint(
                    name="web_search",
                    method="GET",
                    path="/web/search",
                    description="Web search with rich results",
                    parameters={"q": "search query", "count": 10, "mkt": "en-US"},
                    rate_limit=RateLimitConfig(
                        max_requests=2000,
                        time_window=2592000,  # 30 days
                        strategy=RateLimitStrategy.FIXED_WINDOW
                    )
                )
            ],
            capabilities=["web_search", "image_search", "news_search", "api_access"]
        )
        
        # Serper.dev (Google Search API)
        serper = ServiceDefinition(
            service_id="serper",
            name="Serper.dev Google Search",
            service_type=ServiceType.WEB_SEARCH,
            description="Google Search API through Serper.dev",
            api_config=APIConfig(
                base_url="https://google.serper.dev",
                timeout=10.0,
                auth_required=True,
                auth_type="api_key",
                default_headers={"Content-Type": "application/json"}
            ),
            auth_method=AuthMethod.API_KEY,
            endpoints=[
                ServiceEndpoint(
                    name="search",
                    method="POST",
                    path="/search",
                    description="Google search results",
                    parameters={"q": "search query", "num": 10, "hl": "en", "gl": "us"},
                    rate_limit=RateLimitConfig(
                        max_requests=2500,
                        time_window=2592000,  # 30 days
                        strategy=RateLimitStrategy.FIXED_WINDOW
                    )
                )
            ],
            capabilities=["web_search", "news_search", "google_results"]
        )
        
        # OpenWeatherMap (Example REST API)
        openweather = ServiceDefinition(
            service_id="openweather",
            name="OpenWeatherMap API",
            service_type=ServiceType.REST_API,
            description="Weather data and forecasts",
            api_config=APIConfig(
                base_url="https://api.openweathermap.org/data/2.5",
                timeout=10.0,
                auth_required=True,
                auth_type="api_key"
            ),
            auth_method=AuthMethod.API_KEY,
            endpoints=[
                ServiceEndpoint(
                    name="current_weather",
                    method="GET",
                    path="/weather",
                    description="Current weather data",
                    parameters={"q": "city name", "appid": "api_key", "units": "metric"}
                ),
                ServiceEndpoint(
                    name="forecast",
                    method="GET",
                    path="/forecast",
                    description="5-day weather forecast",
                    parameters={"q": "city name", "appid": "api_key", "units": "metric"}
                )
            ],
            capabilities=["weather_current", "weather_forecast", "global_coverage"],
            metadata={"free_tier": True, "calls_per_minute": 60}
        )
        
        # Register services
        for service in [duckduckgo, brave_search, serper, openweather]:
            self.services[service.service_id] = service
        
        # Create service groups
        self.service_groups["web_search"] = ["duckduckgo", "brave_search", "serper"]
        self.service_groups["weather"] = ["openweather"]
        
        logger.info(f"Registered {len(self.services)} built-in services")
    
    def register_service(self, service: ServiceDefinition) -> bool:
        """
        Register a new service.
        
        Args:
            service: Service definition
            
        Returns:
            True if registration was successful
        """
        try:
            self.services[service.service_id] = service
            logger.info(f"Registered service: {service.service_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service {service.service_id}: {e}")
            return False
    
    def get_service(self, service_id: str) -> Optional[ServiceDefinition]:
        """Get service definition by ID"""
        return self.services.get(service_id)
    
    def list_services(self, service_type: Optional[ServiceType] = None,
                     capability: Optional[str] = None,
                     status: Optional[ServiceStatus] = None) -> List[ServiceDefinition]:
        """
        List services with optional filtering.
        
        Args:
            service_type: Filter by service type
            capability: Filter by capability
            status: Filter by status
            
        Returns:
            List of matching services
        """
        services = list(self.services.values())
        
        if service_type:
            services = [s for s in services if s.service_type == service_type]
        
        if capability:
            services = [s for s in services if capability in s.capabilities]
        
        if status:
            services = [s for s in services if s.status == status]
        
        return services
    
    def find_services_by_capability(self, capability: str) -> List[ServiceDefinition]:
        """Find all services that provide a specific capability"""
        return [
            service for service in self.services.values()
            if capability in service.capabilities
        ]
    
    def get_service_group(self, group_name: str) -> List[ServiceDefinition]:
        """Get all services in a group"""
        service_ids = self.service_groups.get(group_name, [])
        return [self.services[sid] for sid in service_ids if sid in self.services]
    
    async def check_service_health(self, service_id: str) -> ServiceStatus:
        """
        Check health status of a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Current service status
        """
        if service_id not in self.services:
            return ServiceStatus.UNKNOWN
        
        service = self.services[service_id]
        
        try:
            # Use custom health checker if available
            if service_id in self.health_checkers:
                health_checker = self.health_checkers[service_id]
                status = await health_checker(service)
                service.status = status
                service.last_checked = __import__('time').time()
                return status
            
            # Default health check - simple ping to base URL
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    service.api_config.base_url,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status < 500:
                        service.status = ServiceStatus.AVAILABLE
                        service.success_count += 1
                    else:
                        service.status = ServiceStatus.UNAVAILABLE
                        service.error_count += 1
            
        except Exception as e:
            logger.warning(f"Health check failed for {service_id}: {e}")
            service.status = ServiceStatus.UNAVAILABLE
            service.error_count += 1
        
        service.last_checked = __import__('time').time()
        return service.status
    
    async def check_all_services_health(self) -> Dict[str, ServiceStatus]:
        """Check health of all registered services"""
        results = {}
        
        tasks = []
        for service_id in self.services.keys():
            task = asyncio.create_task(self.check_service_health(service_id))
            tasks.append((service_id, task))
        
        for service_id, task in tasks:
            try:
                status = await task
                results[service_id] = status
            except Exception as e:
                logger.error(f"Health check failed for {service_id}: {e}")
                results[service_id] = ServiceStatus.UNKNOWN
        
        return results
    
    def register_health_checker(self, service_id: str, health_checker: Callable):
        """Register custom health checker for a service"""
        self.health_checkers[service_id] = health_checker
        logger.info(f"Registered health checker for {service_id}")
    
    def get_service_stats(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a service"""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        total_calls = service.success_count + service.error_count
        
        return {
            "service_id": service_id,
            "name": service.name,
            "type": service.service_type.value,
            "status": service.status.value,
            "last_checked": service.last_checked,
            "total_calls": total_calls,
            "success_count": service.success_count,
            "error_count": service.error_count,
            "success_rate": service.success_count / max(total_calls, 1),
            "capabilities": service.capabilities,
            "endpoints": len(service.endpoints)
        }
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of entire service registry"""
        by_type = {}
        by_status = {}
        
        for service in self.services.values():
            # Count by type
            type_name = service.service_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # Count by status
            status_name = service.status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1
        
        return {
            "total_services": len(self.services),
            "service_groups": len(self.service_groups),
            "by_type": by_type,
            "by_status": by_status,
            "capabilities": self._get_all_capabilities()
        }
    
    def _get_all_capabilities(self) -> List[str]:
        """Get list of all unique capabilities"""
        capabilities = set()
        for service in self.services.values():
            capabilities.update(service.capabilities)
        return sorted(list(capabilities))
    
    async def save_registry(self, file_path: Optional[str] = None):
        """Save service registry to file"""
        if not file_path:
            file_path = self.config_dir / "service_registry.json"
        
        try:
            registry_data = {}
            for service_id, service in self.services.items():
                # Convert to serializable format
                registry_data[service_id] = {
                    "service_id": service.service_id,
                    "name": service.name,
                    "service_type": service.service_type.value,
                    "description": service.description,
                    "api_config": {
                        "base_url": service.api_config.base_url,
                        "timeout": service.api_config.timeout,
                        "auth_required": service.api_config.auth_required,
                        "auth_type": service.api_config.auth_type,
                        "default_headers": service.api_config.default_headers
                    },
                    "auth_method": service.auth_method.value,
                    "capabilities": service.capabilities,
                    "metadata": service.metadata,
                    "endpoints": [
                        {
                            "name": ep.name,
                            "method": ep.method,
                            "path": ep.path,
                            "description": ep.description,
                            "parameters": ep.parameters
                        }
                        for ep in service.endpoints
                    ]
                }
            
            data = {
                "services": registry_data,
                "service_groups": self.service_groups
            }
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved service registry to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save service registry: {e}")
    
    async def load_registry(self, file_path: Optional[str] = None):
        """Load service registry from file"""
        if not file_path:
            file_path = self.config_dir / "service_registry.json"
        
        if not Path(file_path).exists():
            logger.warning(f"Registry file not found: {file_path}")
            return
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Load services
            for service_id, service_data in data.get("services", {}).items():
                # Reconstruct service definition
                api_config_data = service_data["api_config"]
                api_config = APIConfig(
                    base_url=api_config_data["base_url"],
                    timeout=api_config_data["timeout"],
                    auth_required=api_config_data["auth_required"],
                    auth_type=api_config_data.get("auth_type", "bearer"),
                    default_headers=api_config_data.get("default_headers", {})
                )
                
                endpoints = []
                for ep_data in service_data.get("endpoints", []):
                    endpoint = ServiceEndpoint(
                        name=ep_data["name"],
                        method=ep_data["method"],
                        path=ep_data["path"],
                        description=ep_data["description"],
                        parameters=ep_data.get("parameters", {})
                    )
                    endpoints.append(endpoint)
                
                service = ServiceDefinition(
                    service_id=service_data["service_id"],
                    name=service_data["name"],
                    service_type=ServiceType(service_data["service_type"]),
                    description=service_data["description"],
                    api_config=api_config,
                    auth_method=AuthMethod(service_data["auth_method"]),
                    endpoints=endpoints,
                    capabilities=service_data.get("capabilities", []),
                    metadata=service_data.get("metadata", {})
                )
                
                self.services[service_id] = service
            
            # Load service groups
            self.service_groups.update(data.get("service_groups", {}))
            
            logger.info(f"Loaded service registry from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load service registry: {e}")
    
    def get_available_services(self, capability: Optional[str] = None) -> List[ServiceDefinition]:
        """Get list of currently available services"""
        services = self.list_services(status=ServiceStatus.AVAILABLE)
        
        if capability:
            services = [s for s in services if capability in s.capabilities]
        
        return services