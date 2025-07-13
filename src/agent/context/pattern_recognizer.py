"""
Pattern Recognizer

Identifies patterns in task execution, errors, and user behavior for learning.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from .memory_store import MemoryStore, MemoryType
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskPattern:
    """Identified task pattern"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    success_rate: float
    examples: List[Dict[str, Any]] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternRecognizer:
    """
    Recognizes patterns in task execution and user behavior.
    
    Features:
    - Task similarity detection
    - Error pattern identification
    - User preference learning
    - Performance pattern analysis
    - Automated pattern consolidation
    """
    
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """
        Initialize pattern recognizer.
        
        Args:
            memory_store: Optional memory store for pattern persistence
        """
        self.memory_store = memory_store
        
        # Pattern storage
        self.task_patterns: Dict[str, TaskPattern] = {}
        self.error_patterns: Dict[str, TaskPattern] = {}
        self.user_patterns: Dict[str, TaskPattern] = {}
        
        # Configuration
        self.min_pattern_frequency = 3
        self.similarity_threshold = 0.7
        self.keyword_extraction_threshold = 0.6
        
        logger.info("Pattern recognizer initialized")
    
    async def analyze_task_execution(self, task_description: str, task_context: Dict[str, Any],
                                   success: bool, execution_time: float,
                                   error: Optional[str] = None) -> Optional[TaskPattern]:
        """
        Analyze task execution and update patterns.
        
        Args:
            task_description: Task description
            task_context: Task execution context
            success: Whether task succeeded
            execution_time: Task execution time
            error: Error message if failed
            
        Returns:
            Matching or new pattern
        """
        # Extract keywords from task description
        keywords = self._extract_keywords(task_description)
        
        # Find similar existing patterns
        similar_pattern = await self._find_similar_task_pattern(task_description, keywords)
        
        if similar_pattern:
            # Update existing pattern
            await self._update_task_pattern(similar_pattern, success, execution_time, error)
            return similar_pattern
        else:
            # Create new pattern if this is a recurring task type
            pattern_candidates = await self._find_pattern_candidates(task_description, keywords)
            
            if len(pattern_candidates) >= self.min_pattern_frequency - 1:
                return await self._create_task_pattern(task_description, keywords, success, execution_time, error)
        
        return None
    
    async def analyze_error_pattern(self, task_description: str, error: str,
                                  error_type: str, context: Dict[str, Any]) -> Optional[TaskPattern]:
        """
        Analyze error patterns for learning.
        
        Args:
            task_description: Task description that failed
            error: Error message
            error_type: Type of error
            context: Error context
            
        Returns:
            Matching or new error pattern
        """
        # Extract error keywords
        error_keywords = self._extract_keywords(f"{task_description} {error}")
        
        # Find similar error patterns
        similar_pattern = await self._find_similar_error_pattern(error, error_type, error_keywords)
        
        if similar_pattern:
            await self._update_error_pattern(similar_pattern, context)
            return similar_pattern
        else:
            # Create new error pattern if recurring
            error_candidates = await self._find_error_candidates(error, error_type, error_keywords)
            
            if len(error_candidates) >= self.min_pattern_frequency - 1:
                return await self._create_error_pattern(task_description, error, error_type, error_keywords, context)
        
        return None
    
    async def find_similar_patterns(self, query: str, 
                                  pattern_type: Optional[str] = None,
                                  context_type: Optional[str] = None) -> List[TaskPattern]:
        """
        Find patterns similar to a query.
        
        Args:
            query: Query string
            pattern_type: Optional pattern type filter
            context_type: Optional context type filter
            
        Returns:
            List of similar patterns
        """
        query_keywords = self._extract_keywords(query)
        similar_patterns = []
        
        # Search in appropriate pattern collections
        pattern_collections = []
        if pattern_type == "task" or pattern_type is None:
            pattern_collections.append(self.task_patterns)
        if pattern_type == "error" or pattern_type is None:
            pattern_collections.append(self.error_patterns)
        if pattern_type == "user" or pattern_type is None:
            pattern_collections.append(self.user_patterns)
        
        for patterns in pattern_collections:
            for pattern in patterns.values():
                similarity = self._calculate_keyword_similarity(query_keywords, pattern.keywords)
                
                if similarity >= self.similarity_threshold:
                    similar_patterns.append(pattern)
        
        # Sort by frequency and success rate
        similar_patterns.sort(key=lambda p: (p.frequency, p.success_rate), reverse=True)
        
        return similar_patterns[:10]
    
    async def get_pattern_recommendations(self, task_description: str,
                                        task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get pattern-based recommendations for task execution.
        
        Args:
            task_description: Task description
            task_context: Task context
            
        Returns:
            Pattern-based recommendations
        """
        recommendations = {
            "similar_tasks": [],
            "common_errors": [],
            "success_strategies": [],
            "performance_insights": []
        }
        
        # Find similar successful tasks
        similar_patterns = await self.find_similar_patterns(task_description, "task")
        
        for pattern in similar_patterns:
            if pattern.success_rate > 0.8:  # High success rate
                recommendations["similar_tasks"].append({
                    "description": pattern.description,
                    "success_rate": pattern.success_rate,
                    "frequency": pattern.frequency,
                    "avg_execution_time": pattern.metadata.get("avg_execution_time", 0)
                })
        
        # Find common error patterns
        error_patterns = await self.find_similar_patterns(task_description, "error")
        
        for pattern in error_patterns:
            recommendations["common_errors"].append({
                "error_type": pattern.pattern_type,
                "description": pattern.description,
                "frequency": pattern.frequency,
                "prevention_tips": pattern.metadata.get("prevention_tips", [])
            })
        
        # Performance insights
        if similar_patterns:
            avg_times = [p.metadata.get("avg_execution_time", 0) for p in similar_patterns if p.metadata.get("avg_execution_time")]
            if avg_times:
                recommendations["performance_insights"].append({
                    "expected_time_range": f"{min(avg_times):.1f}-{max(avg_times):.1f} seconds",
                    "sample_size": len(avg_times)
                })
        
        return recommendations
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        # Simple keyword extraction - can be enhanced with NLP
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        keywords = {word for word in words if len(word) > 2 and word not in stop_words}
        
        return keywords
    
    def _calculate_keyword_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate similarity between two keyword sets"""
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_pattern_id(self, description: str, keywords: Set[str]) -> str:
        """Generate unique pattern ID"""
        content = f"{description}_{sorted(keywords)}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    async def _find_similar_task_pattern(self, description: str, keywords: Set[str]) -> Optional[TaskPattern]:
        """Find existing task pattern similar to description"""
        for pattern in self.task_patterns.values():
            similarity = self._calculate_keyword_similarity(keywords, pattern.keywords)
            if similarity >= self.similarity_threshold:
                return pattern
        
        return None
    
    async def _find_similar_error_pattern(self, error: str, error_type: str, keywords: Set[str]) -> Optional[TaskPattern]:
        """Find existing error pattern similar to error"""
        for pattern in self.error_patterns.values():
            if pattern.pattern_type == error_type:
                similarity = self._calculate_keyword_similarity(keywords, pattern.keywords)
                if similarity >= self.similarity_threshold:
                    return pattern
        
        return None
    
    async def _find_pattern_candidates(self, description: str, keywords: Set[str]) -> List[Dict[str, Any]]:
        """Find potential pattern candidates from memory"""
        if not self.memory_store:
            return []
        
        # Search for similar tasks in memory
        search_query = " ".join(list(keywords)[:5])  # Use top 5 keywords
        memories = await self.memory_store.search_memories(search_query, MemoryType.TASK_EXECUTION)
        
        candidates = []
        for memory in memories:
            memory_keywords = self._extract_keywords(memory.content.get("description", ""))
            similarity = self._calculate_keyword_similarity(keywords, memory_keywords)
            
            if similarity >= self.keyword_extraction_threshold:
                candidates.append(memory.content)
        
        return candidates
    
    async def _find_error_candidates(self, error: str, error_type: str, keywords: Set[str]) -> List[Dict[str, Any]]:
        """Find potential error pattern candidates"""
        if not self.memory_store:
            return []
        
        memories = await self.memory_store.query_memories(
            memory_type=MemoryType.ERROR,
            metadata_filters={"error_type": error_type}
        )
        
        candidates = []
        for memory in memories:
            memory_keywords = self._extract_keywords(memory.content.get("error", ""))
            similarity = self._calculate_keyword_similarity(keywords, memory_keywords)
            
            if similarity >= self.keyword_extraction_threshold:
                candidates.append(memory.content)
        
        return candidates
    
    async def _create_task_pattern(self, description: str, keywords: Set[str],
                                 success: bool, execution_time: float,
                                 error: Optional[str] = None) -> TaskPattern:
        """Create new task pattern"""
        pattern_id = self._generate_pattern_id(description, keywords)
        
        pattern = TaskPattern(
            pattern_id=pattern_id,
            pattern_type="task",
            description=description,
            frequency=1,
            success_rate=1.0 if success else 0.0,
            keywords=keywords,
            metadata={
                "avg_execution_time": execution_time,
                "total_execution_time": execution_time,
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1
            }
        )
        
        self.task_patterns[pattern_id] = pattern
        
        # Store in memory if available
        if self.memory_store:
            await self.memory_store.store_memory(
                memory_type=MemoryType.PATTERN,
                content={
                    "pattern_type": "task",
                    "description": description,
                    "keywords": list(keywords),
                    "metadata": pattern.metadata
                },
                metadata={"pattern_id": pattern_id},
                memory_id=f"pattern_{pattern_id}"
            )
        
        logger.info(f"Created new task pattern: {pattern_id}")
        return pattern
    
    async def _create_error_pattern(self, task_description: str, error: str,
                                  error_type: str, keywords: Set[str],
                                  context: Dict[str, Any]) -> TaskPattern:
        """Create new error pattern"""
        pattern_id = self._generate_pattern_id(f"{error_type}_{error}", keywords)
        
        pattern = TaskPattern(
            pattern_id=pattern_id,
            pattern_type=error_type,
            description=f"Error in {task_description}: {error}",
            frequency=1,
            success_rate=0.0,
            keywords=keywords,
            metadata={
                "error_message": error,
                "error_type": error_type,
                "contexts": [context]
            }
        )
        
        self.error_patterns[pattern_id] = pattern
        
        # Store in memory
        if self.memory_store:
            await self.memory_store.store_memory(
                memory_type=MemoryType.PATTERN,
                content={
                    "pattern_type": "error",
                    "error_type": error_type,
                    "error_message": error,
                    "keywords": list(keywords),
                    "metadata": pattern.metadata
                },
                metadata={"pattern_id": pattern_id},
                memory_id=f"error_pattern_{pattern_id}"
            )
        
        logger.info(f"Created new error pattern: {pattern_id}")
        return pattern
    
    async def _update_task_pattern(self, pattern: TaskPattern, success: bool,
                                 execution_time: float, error: Optional[str] = None):
        """Update existing task pattern"""
        pattern.frequency += 1
        
        # Update success rate
        if success:
            pattern.metadata["success_count"] += 1
        else:
            pattern.metadata["failure_count"] += 1
        
        total_attempts = pattern.metadata["success_count"] + pattern.metadata["failure_count"]
        pattern.success_rate = pattern.metadata["success_count"] / total_attempts
        
        # Update execution time
        pattern.metadata["total_execution_time"] += execution_time
        pattern.metadata["avg_execution_time"] = pattern.metadata["total_execution_time"] / pattern.frequency
        
        # Update in memory
        if self.memory_store:
            await self.memory_store.update_memory(
                memory_id=f"pattern_{pattern.pattern_id}",
                metadata={"pattern_id": pattern.pattern_id, "frequency": pattern.frequency}
            )
        
        logger.debug(f"Updated task pattern: {pattern.pattern_id}")
    
    async def _update_error_pattern(self, pattern: TaskPattern, context: Dict[str, Any]):
        """Update existing error pattern"""
        pattern.frequency += 1
        pattern.metadata["contexts"].append(context)
        
        # Limit context history
        if len(pattern.metadata["contexts"]) > 10:
            pattern.metadata["contexts"] = pattern.metadata["contexts"][-10:]
        
        # Update in memory
        if self.memory_store:
            await self.memory_store.update_memory(
                memory_id=f"error_pattern_{pattern.pattern_id}",
                metadata={"pattern_id": pattern.pattern_id, "frequency": pattern.frequency}
            )
        
        logger.debug(f"Updated error pattern: {pattern.pattern_id}")
    
    async def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of all patterns"""
        return {
            "task_patterns": {
                "count": len(self.task_patterns),
                "avg_success_rate": sum(p.success_rate for p in self.task_patterns.values()) / len(self.task_patterns) if self.task_patterns else 0,
                "total_frequency": sum(p.frequency for p in self.task_patterns.values())
            },
            "error_patterns": {
                "count": len(self.error_patterns),
                "total_frequency": sum(p.frequency for p in self.error_patterns.values()),
                "common_types": list(set(p.pattern_type for p in self.error_patterns.values()))
            },
            "user_patterns": {
                "count": len(self.user_patterns)
            }
        }