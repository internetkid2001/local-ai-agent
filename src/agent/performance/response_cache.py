#!/usr/bin/env python3
"""
Response Cache System

High-performance caching system for MCP responses to reduce redundant operations
and improve response times for frequently accessed data.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6 - Performance Optimization
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import pickle
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    MIXED = "mixed"  # LRU + TTL


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float] = None
    size: int = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if self.last_accessed == 0:
            self.last_accessed = time.time()
        if self.size == 0:
            self.size = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value"""
        try:
            return len(pickle.dumps(self.value))
        except:
            return len(str(self.value))
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update access time and count"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheConfig:
    """Cache configuration"""
    max_size: int = 10000  # Maximum number of entries
    max_memory: int = 100 * 1024 * 1024  # 100MB
    default_ttl: float = 3600.0  # 1 hour
    cleanup_interval: float = 300.0  # 5 minutes
    strategy: CacheStrategy = CacheStrategy.MIXED
    enable_persistence: bool = True
    persistence_file: str = "cache.pkl"
    compression: bool = True


class ResponseCache:
    """
    High-performance response cache with multiple eviction strategies.
    
    Features:
    - Multiple cache strategies (LRU, LFU, TTL, Mixed)
    - Memory-aware caching with size limits
    - Automatic cleanup of expired entries
    - Persistent cache storage
    - Compression support
    - Statistics and monitoring
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired": 0,
            "size": 0,
            "memory_usage": 0
        }
        
        # Background tasks
        self._cleanup_task = None
        self._running = False
        
        # Load persistent cache if enabled
        if self.config.enable_persistence:
            self._load_cache()
    
    async def initialize(self):
        """Initialize cache system"""
        logger.info("Initializing response cache...")
        
        self._running = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Response cache initialized with {len(self.cache)} entries")
    
    def _generate_key(self, prefix: str, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for tool call"""
        # Create deterministic hash of parameters
        param_str = json.dumps(parameters, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        
        return f"{prefix}:{tool_name}:{param_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            entry = self.cache.get(key)
            
            if entry is None:
                self.stats["misses"] += 1
                return None
            
            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                self.stats["expired"] += 1
                self.stats["misses"] += 1
                return None
            
            # Update access info
            entry.touch()
            
            # Move to end for LRU
            if self.config.strategy in [CacheStrategy.LRU, CacheStrategy.MIXED]:
                self.cache.move_to_end(key)
            
            self.stats["hits"] += 1
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in cache"""
        with self.lock:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.config.default_ttl
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl
            )
            
            # Check if we need to evict entries
            self._ensure_capacity(entry.size)
            
            # Add to cache
            self.cache[key] = entry
            
            # Update stats
            self.stats["size"] += 1
            self.stats["memory_usage"] += entry.size
            
            logger.debug(f"Cached entry {key} (size: {entry.size} bytes)")
    
    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry"""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all entries with given prefix"""
        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if key.startswith(prefix)]
            
            for key in keys_to_remove:
                self._remove_entry(key)
            
            return len(keys_to_remove)
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats["size"] = 0
            self.stats["memory_usage"] = 0
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        entry = self.cache.pop(key, None)
        if entry:
            self.stats["size"] -= 1
            self.stats["memory_usage"] -= entry.size
    
    def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry"""
        # Check memory limit
        while (self.stats["memory_usage"] + new_entry_size > self.config.max_memory and 
               self.cache):
            self._evict_entry()
        
        # Check size limit
        while len(self.cache) >= self.config.max_size and self.cache:
            self._evict_entry()
    
    def _evict_entry(self):
        """Evict entry based on strategy"""
        if not self.cache:
            return
        
        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used (first in OrderedDict)
            key = next(iter(self.cache))
            self._remove_entry(key)
            
        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_access_count = min(entry.access_count for entry in self.cache.values())
            for key, entry in self.cache.items():
                if entry.access_count == min_access_count:
                    self._remove_entry(key)
                    break
                    
        elif self.config.strategy == CacheStrategy.TTL:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].created_at)
            self._remove_entry(oldest_key)
            
        elif self.config.strategy == CacheStrategy.MIXED:
            # Try TTL first, then LRU
            current_time = time.time()
            expired_keys = [key for key, entry in self.cache.items() 
                          if entry.is_expired()]
            
            if expired_keys:
                self._remove_entry(expired_keys[0])
            else:
                # Fall back to LRU
                key = next(iter(self.cache))
                self._remove_entry(key)
        
        self.stats["evictions"] += 1
    
    async def _cleanup_loop(self):
        """Background task to clean up expired entries"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
    
    def _cleanup_expired(self):
        """Clean up expired entries"""
        with self.lock:
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
                self.stats["expired"] += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _load_cache(self):
        """Load cache from persistent storage"""
        try:
            cache_file = Path(self.config.persistence_file)
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    self.cache = data.get('cache', OrderedDict())
                    self.stats = data.get('stats', self.stats)
                    
                # Clean up expired entries
                self._cleanup_expired()
                
                logger.info(f"Loaded {len(self.cache)} entries from cache file")
        except Exception as e:
            logger.error(f"Error loading cache from file: {e}")
    
    def _save_cache(self):
        """Save cache to persistent storage"""
        try:
            cache_file = Path(self.config.persistence_file)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, 'wb') as f:
                data = {
                    'cache': self.cache,
                    'stats': self.stats
                }
                pickle.dump(data, f)
                
            logger.debug(f"Saved {len(self.cache)} entries to cache file")
        except Exception as e:
            logger.error(f"Error saving cache to file: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            hit_rate = 0.0
            total_requests = self.stats["hits"] + self.stats["misses"]
            if total_requests > 0:
                hit_rate = self.stats["hits"] / total_requests
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self.stats["evictions"],
                "expired": self.stats["expired"],
                "size": self.stats["size"],
                "memory_usage": self.stats["memory_usage"],
                "max_size": self.config.max_size,
                "max_memory": self.config.max_memory,
                "strategy": self.config.strategy.value
            }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self.lock:
            entries_by_age = []
            entries_by_access = []
            
            current_time = time.time()
            
            for key, entry in self.cache.items():
                age = current_time - entry.created_at
                entries_by_age.append({
                    "key": key,
                    "age": age,
                    "size": entry.size,
                    "access_count": entry.access_count
                })
                
                entries_by_access.append({
                    "key": key,
                    "access_count": entry.access_count,
                    "last_accessed": current_time - entry.last_accessed,
                    "size": entry.size
                })
            
            # Sort by age and access count
            entries_by_age.sort(key=lambda x: x["age"], reverse=True)
            entries_by_access.sort(key=lambda x: x["access_count"], reverse=True)
            
            return {
                "total_entries": len(self.cache),
                "oldest_entries": entries_by_age[:10],
                "most_accessed": entries_by_access[:10],
                "config": {
                    "max_size": self.config.max_size,
                    "max_memory": self.config.max_memory,
                    "default_ttl": self.config.default_ttl,
                    "strategy": self.config.strategy.value
                }
            }
    
    async def shutdown(self):
        """Shutdown cache system"""
        logger.info("Shutting down response cache...")
        
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Save cache if persistence is enabled
        if self.config.enable_persistence:
            self._save_cache()
        
        logger.info("Response cache shutdown complete")


class CachedMCPClient:
    """
    Wrapper for MCP clients that adds caching capabilities.
    """
    
    def __init__(self, client, cache: ResponseCache, cache_ttl: float = 3600.0):
        self.client = client
        self.cache = cache
        self.cache_ttl = cache_ttl
        self.client_type = getattr(client, 'client_type', 'unknown')
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call tool with caching"""
        # Generate cache key
        cache_key = self.cache._generate_key(self.client_type, tool_name, parameters)
        
        # Try to get from cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {tool_name} on {self.client_type}")
            return cached_result
        
        # Call actual tool
        result = await self.client.call_tool(tool_name, parameters)
        
        # Cache result if successful
        if self._should_cache(tool_name, result):
            self.cache.put(cache_key, result, self.cache_ttl)
            logger.debug(f"Cached result for {tool_name} on {self.client_type}")
        
        return result
    
    def _should_cache(self, tool_name: str, result: Any) -> bool:
        """Determine if result should be cached"""
        # Don't cache errors
        if isinstance(result, dict) and result.get("error"):
            return False
        
        # Don't cache operations that modify state
        modify_operations = ["write", "create", "delete", "update", "move", "copy"]
        if any(op in tool_name.lower() for op in modify_operations):
            return False
        
        # Don't cache real-time data
        realtime_tools = ["take_screenshot", "get_processes", "get_system_metrics"]
        if tool_name in realtime_tools:
            return False
        
        return True
    
    def invalidate_cache(self, tool_name: str = None):
        """Invalidate cache entries"""
        if tool_name:
            prefix = f"{self.client_type}:{tool_name}"
            self.cache.invalidate_prefix(prefix)
        else:
            prefix = f"{self.client_type}:"
            self.cache.invalidate_prefix(prefix)
    
    def __getattr__(self, name):
        """Delegate other attributes to wrapped client"""
        return getattr(self.client, name)