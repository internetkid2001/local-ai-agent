"""
Context Manager

Manages contextual information for enhanced decision making and task execution.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from .memory_store import MemoryStore, MemoryType
from .pattern_recognizer import PatternRecognizer
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ContextType(Enum):
    """Types of context information"""
    TASK_HISTORY = "task_history"
    USER_PREFERENCES = "user_preferences"
    SYSTEM_STATE = "system_state"
    ENVIRONMENT = "environment"
    WORKFLOW_STATE = "workflow_state"
    ERROR_HISTORY = "error_history"
    PERFORMANCE_METRICS = "performance_metrics"
    RESOURCE_USAGE = "resource_usage"


class ContextScope(Enum):
    """Scope of context information"""
    SESSION = "session"      # Current session only
    USER = "user"           # User-specific, persistent
    SYSTEM = "system"       # System-wide, persistent
    TEMPORARY = "temporary"  # Short-lived context


@dataclass
class ContextEntry:
    """Individual context entry"""
    id: str
    context_type: ContextType
    scope: ContextScope
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    expiry: Optional[float] = None
    tags: Set[str] = field(default_factory=set)
    relevance_score: float = 1.0


class ContextManager:
    """
    Manages contextual information for enhanced agent decision making.
    
    Features:
    - Multi-scope context storage (session, user, system)
    - Context relevance scoring and retrieval
    - Automatic context expiry and cleanup
    - Integration with memory and pattern recognition
    - Context-aware decision support
    """
    
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """
        Initialize context manager.
        
        Args:
            memory_store: Optional memory store for persistence
        """
        self.memory_store = memory_store or MemoryStore()
        self.pattern_recognizer = PatternRecognizer()
        
        # Context storage by scope
        self.session_context: Dict[str, ContextEntry] = {}
        self.user_context: Dict[str, ContextEntry] = {}
        self.system_context: Dict[str, ContextEntry] = {}
        self.temporary_context: Dict[str, ContextEntry] = {}
        
        # Context relationships and dependencies
        self.context_relationships: Dict[str, Set[str]] = {}
        
        # Configuration
        self.max_session_entries = 1000
        self.max_temporary_entries = 100
        self.default_temp_expiry = 3600.0  # 1 hour
        
        logger.info("Context manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the context manager.
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize memory store if not already done
            if hasattr(self.memory_store, 'initialize'):
                await self.memory_store.initialize()
            
            # Initialize pattern recognizer if needed
            if hasattr(self.pattern_recognizer, 'initialize'):
                await self.pattern_recognizer.initialize()
            
            logger.info("Context manager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize context manager: {e}")
            return False
    
    async def shutdown(self):
        """
        Shutdown the context manager and cleanup resources.
        """
        try:
            # Clear all context storage
            self.session_context.clear()
            self.user_context.clear()
            self.system_context.clear()
            self.temporary_context.clear()
            self.context_relationships.clear()
            
            # Shutdown memory store if it has shutdown method
            if hasattr(self.memory_store, 'shutdown'):
                await self.memory_store.shutdown()
            
            logger.info("Context manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during context manager shutdown: {e}")
    
    async def add_context(self, context_type: ContextType, scope: ContextScope,
                         data: Dict[str, Any], context_id: Optional[str] = None,
                         tags: Optional[Set[str]] = None, expiry: Optional[float] = None) -> str:
        """
        Add context information.
        
        Args:
            context_type: Type of context
            scope: Context scope
            data: Context data
            context_id: Optional context ID
            tags: Optional tags for categorization
            expiry: Optional expiry timestamp
            
        Returns:
            Context entry ID
        """
        if context_id is None:
            context_id = f"{context_type.value}_{scope.value}_{int(time.time())}"
        
        if tags is None:
            tags = set()
        
        # Set default expiry for temporary context
        if scope == ContextScope.TEMPORARY and expiry is None:
            expiry = time.time() + self.default_temp_expiry
        
        entry = ContextEntry(
            id=context_id,
            context_type=context_type,
            scope=scope,
            data=data,
            tags=tags,
            expiry=expiry
        )
        
        # Store in appropriate context storage
        storage = self._get_context_storage(scope)
        storage[context_id] = entry
        
        # Store in persistent memory if not temporary
        if scope != ContextScope.TEMPORARY:
            await self.memory_store.store_memory(
                memory_type=MemoryType.CONTEXT,
                content=data,
                metadata={
                    "context_type": context_type.value,
                    "scope": scope.value,
                    "tags": list(tags)
                },
                memory_id=context_id
            )
        
        # Cleanup if necessary
        await self._cleanup_context(scope)
        
        logger.debug(f"Added context: {context_id} ({context_type.value}, {scope.value})")
        return context_id
    
    async def get_context(self, context_id: str) -> Optional[ContextEntry]:
        """Get specific context entry by ID"""
        # Check all storage areas
        for storage in [self.session_context, self.user_context, 
                       self.system_context, self.temporary_context]:
            if context_id in storage:
                entry = storage[context_id]
                
                # Check expiry
                if entry.expiry and time.time() > entry.expiry:
                    await self.remove_context(context_id)
                    return None
                
                return entry
        
        return None
    
    async def query_context(self, context_type: Optional[ContextType] = None,
                           scope: Optional[ContextScope] = None,
                           tags: Optional[Set[str]] = None,
                           limit: int = 10) -> List[ContextEntry]:
        """
        Query context entries with filters.
        
        Args:
            context_type: Optional context type filter
            scope: Optional scope filter
            tags: Optional tags filter
            limit: Maximum number of results
            
        Returns:
            List of matching context entries, sorted by relevance
        """
        matches = []
        
        # Collect from all applicable storages
        storages = []
        if scope is None or scope == ContextScope.SESSION:
            storages.append(self.session_context)
        if scope is None or scope == ContextScope.USER:
            storages.append(self.user_context)
        if scope is None or scope == ContextScope.SYSTEM:
            storages.append(self.system_context)
        if scope is None or scope == ContextScope.TEMPORARY:
            storages.append(self.temporary_context)
        
        for storage in storages:
            for entry in storage.values():
                # Check expiry
                if entry.expiry and time.time() > entry.expiry:
                    continue
                
                # Apply filters
                if context_type and entry.context_type != context_type:
                    continue
                
                if tags and not tags.intersection(entry.tags):
                    continue
                
                matches.append(entry)
        
        # Sort by relevance score and timestamp
        matches.sort(key=lambda x: (x.relevance_score, x.timestamp), reverse=True)
        
        return matches[:limit]
    
    async def get_relevant_context(self, task_description: str, 
                                  task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get context relevant to a specific task.
        
        Args:
            task_description: Task description
            task_context: Current task context
            
        Returns:
            Relevant context information
        """
        relevant_context = {}
        
        # Get task history context
        task_history = await self.query_context(
            context_type=ContextType.TASK_HISTORY,
            limit=5
        )
        
        if task_history:
            relevant_context["recent_tasks"] = [
                {
                    "description": entry.data.get("description"),
                    "status": entry.data.get("status"),
                    "timestamp": entry.timestamp
                }
                for entry in task_history
            ]
        
        # Get user preferences
        user_prefs = await self.query_context(
            context_type=ContextType.USER_PREFERENCES,
            scope=ContextScope.USER,
            limit=3
        )
        
        if user_prefs:
            relevant_context["user_preferences"] = {}
            for entry in user_prefs:
                relevant_context["user_preferences"].update(entry.data)
        
        # Get system state
        system_state = await self.query_context(
            context_type=ContextType.SYSTEM_STATE,
            limit=1
        )
        
        if system_state:
            relevant_context["system_state"] = system_state[0].data
        
        # Get error history for similar tasks
        error_patterns = await self.pattern_recognizer.find_similar_patterns(
            task_description, context_type=ContextType.ERROR_HISTORY
        )
        
        if error_patterns:
            relevant_context["error_patterns"] = error_patterns
        
        # Get performance metrics
        performance_data = await self.query_context(
            context_type=ContextType.PERFORMANCE_METRICS,
            limit=3
        )
        
        if performance_data:
            relevant_context["performance_metrics"] = [
                entry.data for entry in performance_data
            ]
        
        return relevant_context
    
    async def update_context(self, context_id: str, data_updates: Dict[str, Any],
                           add_tags: Optional[Set[str]] = None,
                           remove_tags: Optional[Set[str]] = None) -> bool:
        """Update existing context entry"""
        entry = await self.get_context(context_id)
        if not entry:
            return False
        
        # Update data
        entry.data.update(data_updates)
        entry.timestamp = time.time()
        
        # Update tags
        if add_tags:
            entry.tags.update(add_tags)
        if remove_tags:
            entry.tags.difference_update(remove_tags)
        
        # Update in persistent storage if not temporary
        if entry.scope != ContextScope.TEMPORARY:
            await self.memory_store.update_memory(
                memory_id=context_id,
                content=entry.data,
                metadata={
                    "context_type": entry.context_type.value,
                    "scope": entry.scope.value,
                    "tags": list(entry.tags)
                }
            )
        
        logger.debug(f"Updated context: {context_id}")
        return True
    
    async def remove_context(self, context_id: str) -> bool:
        """Remove context entry"""
        # Remove from all storages
        removed = False
        for storage in [self.session_context, self.user_context,
                       self.system_context, self.temporary_context]:
            if context_id in storage:
                del storage[context_id]
                removed = True
        
        # Remove from persistent storage
        if removed:
            await self.memory_store.delete_memory(context_id)
            logger.debug(f"Removed context: {context_id}")
        
        return removed
    
    async def add_task_context(self, task_id: str, task_description: str,
                              task_status: str, execution_time: float,
                              success: bool, error: Optional[str] = None) -> str:
        """Add task execution context"""
        data = {
            "task_id": task_id,
            "description": task_description,
            "status": task_status,
            "execution_time": execution_time,
            "success": success,
            "error": error
        }
        
        tags = {"task_completion"}
        if success:
            tags.add("success")
        else:
            tags.add("failure")
        
        return await self.add_context(
            context_type=ContextType.TASK_HISTORY,
            scope=ContextScope.SESSION,
            data=data,
            tags=tags
        )
    
    async def add_error_context(self, task_description: str, error: str,
                               error_type: str, context: Dict[str, Any]) -> str:
        """Add error context for learning"""
        data = {
            "task_description": task_description,
            "error": error,
            "error_type": error_type,
            "context": context
        }
        
        tags = {"error", error_type}
        
        return await self.add_context(
            context_type=ContextType.ERROR_HISTORY,
            scope=ContextScope.USER,
            data=data,
            tags=tags
        )
    
    async def add_performance_metrics(self, operation: str, metrics: Dict[str, Any]) -> str:
        """Add performance metrics context"""
        data = {
            "operation": operation,
            "metrics": metrics,
            "timestamp": time.time()
        }
        
        return await self.add_context(
            context_type=ContextType.PERFORMANCE_METRICS,
            scope=ContextScope.SYSTEM,
            data=data,
            tags={"performance", operation}
        )
    
    async def update_system_state(self, state_data: Dict[str, Any]) -> str:
        """Update current system state context"""
        # Remove old system state
        old_states = await self.query_context(
            context_type=ContextType.SYSTEM_STATE,
            scope=ContextScope.SYSTEM
        )
        
        for state in old_states:
            await self.remove_context(state.id)
        
        # Add new system state
        return await self.add_context(
            context_type=ContextType.SYSTEM_STATE,
            scope=ContextScope.SYSTEM,
            data=state_data,
            tags={"current_state"}
        )
    
    def _get_context_storage(self, scope: ContextScope) -> Dict[str, ContextEntry]:
        """Get appropriate storage for scope"""
        if scope == ContextScope.SESSION:
            return self.session_context
        elif scope == ContextScope.USER:
            return self.user_context
        elif scope == ContextScope.SYSTEM:
            return self.system_context
        elif scope == ContextScope.TEMPORARY:
            return self.temporary_context
        else:
            return self.session_context
    
    async def _cleanup_context(self, scope: ContextScope):
        """Cleanup expired and excess context entries"""
        storage = self._get_context_storage(scope)
        current_time = time.time()
        
        # Remove expired entries
        expired_ids = []
        for entry_id, entry in storage.items():
            if entry.expiry and current_time > entry.expiry:
                expired_ids.append(entry_id)
        
        for entry_id in expired_ids:
            await self.remove_context(entry_id)
        
        # Limit entries for certain scopes
        max_entries = {
            ContextScope.SESSION: self.max_session_entries,
            ContextScope.TEMPORARY: self.max_temporary_entries
        }
        
        if scope in max_entries and len(storage) > max_entries[scope]:
            # Remove oldest entries
            entries = sorted(storage.values(), key=lambda x: x.timestamp)
            excess_count = len(storage) - max_entries[scope]
            
            for entry in entries[:excess_count]:
                await self.remove_context(entry.id)
    
    async def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of all context information"""
        summary = {}
        
        for scope in ContextScope:
            storage = self._get_context_storage(scope)
            summary[scope.value] = {
                "total_entries": len(storage),
                "by_type": {}
            }
            
            for entry in storage.values():
                type_name = entry.context_type.value
                if type_name not in summary[scope.value]["by_type"]:
                    summary[scope.value]["by_type"][type_name] = 0
                summary[scope.value]["by_type"][type_name] += 1
        
        return summary