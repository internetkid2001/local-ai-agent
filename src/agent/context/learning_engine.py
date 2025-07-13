"""
Learning Engine

Continuous learning and improvement based on task execution patterns and feedback.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .memory_store import MemoryStore, MemoryType
from .pattern_recognizer import PatternRecognizer, TaskPattern
from .context_manager import ContextManager, ContextType, ContextScope
from ...utils.logger import get_logger

logger = get_logger(__name__)


class LearningType(Enum):
    """Types of learning"""
    TASK_OPTIMIZATION = "task_optimization"
    ERROR_PREVENTION = "error_prevention"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    USER_PREFERENCE = "user_preference"
    STRATEGY_REFINEMENT = "strategy_refinement"


@dataclass
class LearningFeedback:
    """Feedback for learning system"""
    task_id: str
    feedback_type: LearningType
    success: bool
    improvement_suggestion: str
    context: Dict[str, Any]
    confidence: float = 1.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class LearningEngine:
    """
    Continuous learning engine for agent improvement.
    
    Features:
    - Task execution optimization
    - Error pattern learning
    - Performance improvement tracking
    - User preference adaptation
    - Strategy refinement based on outcomes
    """
    
    def __init__(self, memory_store: Optional[MemoryStore] = None,
                 pattern_recognizer: Optional[PatternRecognizer] = None,
                 context_manager: Optional[ContextManager] = None):
        """
        Initialize learning engine.
        
        Args:
            memory_store: Memory store for learning persistence
            pattern_recognizer: Pattern recognizer for analysis
            context_manager: Context manager for contextual learning
        """
        self.memory_store = memory_store or MemoryStore()
        self.pattern_recognizer = pattern_recognizer or PatternRecognizer(self.memory_store)
        self.context_manager = context_manager or ContextManager(self.memory_store)
        
        # Learning configuration
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        self.min_samples_for_learning = 5
        
        # Learning state
        self.learned_optimizations: Dict[str, Dict[str, Any]] = {}
        self.error_prevention_rules: Dict[str, List[str]] = {}
        self.performance_baselines: Dict[str, float] = {}
        self.user_preferences: Dict[str, Any] = {}
        
        logger.info("Learning engine initialized")
    
    async def process_task_feedback(self, task_id: str, task_description: str,
                                  success: bool, execution_time: float,
                                  error: Optional[str] = None,
                                  user_feedback: Optional[str] = None) -> List[LearningFeedback]:
        """
        Process feedback from task execution for learning.
        
        Args:
            task_id: Task identifier
            task_description: Task description
            success: Whether task succeeded
            execution_time: Task execution time
            error: Error message if failed
            user_feedback: Optional user feedback
            
        Returns:
            List of learning insights generated
        """
        feedbacks = []
        
        # Analyze task patterns
        pattern_feedback = await self._analyze_task_patterns(
            task_description, success, execution_time, error
        )
        if pattern_feedback:
            feedbacks.extend(pattern_feedback)
        
        # Analyze performance
        performance_feedback = await self._analyze_performance(
            task_description, execution_time, success
        )
        if performance_feedback:
            feedbacks.append(performance_feedback)
        
        # Analyze errors for prevention
        if error:
            error_feedback = await self._analyze_error_for_learning(
                task_description, error, task_id
            )
            if error_feedback:
                feedbacks.append(error_feedback)
        
        # Process user feedback
        if user_feedback:
            user_feedback_obj = await self._process_user_feedback(
                task_id, task_description, user_feedback
            )
            if user_feedback_obj:
                feedbacks.append(user_feedback_obj)
        
        # Store learning insights
        for feedback in feedbacks:
            await self._store_learning_insight(feedback)
        
        # Update learning models
        await self._update_learning_models(task_description, feedbacks)
        
        return feedbacks
    
    async def get_task_recommendations(self, task_description: str,
                                     task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get learned recommendations for task execution.
        
        Args:
            task_description: Task description
            task_context: Task context
            
        Returns:
            Learned recommendations
        """
        recommendations = {
            "optimizations": [],
            "error_prevention": [],
            "performance_tips": [],
            "user_preferences": {},
            "confidence": 0.0
        }
        
        # Get pattern-based recommendations
        pattern_recommendations = await self.pattern_recognizer.get_pattern_recommendations(
            task_description, task_context
        )
        
        # Apply learned optimizations
        optimizations = await self._get_optimization_recommendations(task_description)
        recommendations["optimizations"] = optimizations
        
        # Apply error prevention rules
        error_prevention = await self._get_error_prevention_recommendations(task_description)
        recommendations["error_prevention"] = error_prevention
        
        # Apply performance insights
        performance_tips = await self._get_performance_recommendations(task_description)
        recommendations["performance_tips"] = performance_tips
        
        # Apply user preferences
        user_prefs = await self._get_user_preference_recommendations(task_description)
        recommendations["user_preferences"] = user_prefs
        
        # Calculate overall confidence
        confidence_scores = []
        if optimizations:
            confidence_scores.extend([opt.get("confidence", 0.5) for opt in optimizations])
        if error_prevention:
            confidence_scores.extend([prev.get("confidence", 0.5) for prev in error_prevention])
        
        recommendations["confidence"] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return recommendations
    
    async def update_user_preferences(self, preference_type: str, 
                                    preference_value: Any,
                                    context: Dict[str, Any]) -> bool:
        """Update user preferences based on behavior"""
        preference_key = f"{preference_type}_{hash(str(context))}"
        
        self.user_preferences[preference_key] = {
            "type": preference_type,
            "value": preference_value,
            "context": context,
            "timestamp": time.time(),
            "confidence": 1.0
        }
        
        # Store in context manager
        await self.context_manager.add_context(
            context_type=ContextType.USER_PREFERENCES,
            scope=ContextScope.USER,
            data={
                "preference_type": preference_type,
                "preference_value": preference_value,
                "context": context
            },
            tags={"user_preference", preference_type}
        )
        
        logger.info(f"Updated user preference: {preference_type}")
        return True
    
    async def _analyze_task_patterns(self, task_description: str, success: bool,
                                   execution_time: float, error: Optional[str]) -> List[LearningFeedback]:
        """Analyze task execution for pattern learning"""
        feedbacks = []
        
        # Analyze with pattern recognizer
        task_pattern = await self.pattern_recognizer.analyze_task_execution(
            task_description, {}, success, execution_time, error
        )
        
        if task_pattern and task_pattern.frequency >= self.min_samples_for_learning:
            # Generate optimization suggestions
            if task_pattern.success_rate < 0.8:
                # Low success rate - suggest strategy refinement
                feedbacks.append(LearningFeedback(
                    task_id="",
                    feedback_type=LearningType.STRATEGY_REFINEMENT,
                    success=False,
                    improvement_suggestion=f"Task pattern '{task_pattern.description}' has low success rate ({task_pattern.success_rate:.1%}). Consider alternative approaches.",
                    context={"pattern": task_pattern.pattern_id, "success_rate": task_pattern.success_rate},
                    confidence=0.8
                ))
            
            # Performance optimization suggestions
            avg_time = task_pattern.metadata.get("avg_execution_time", 0)
            if avg_time > 0 and execution_time > avg_time * 1.5:
                feedbacks.append(LearningFeedback(
                    task_id="",
                    feedback_type=LearningType.PERFORMANCE_IMPROVEMENT,
                    success=success,
                    improvement_suggestion=f"Task took {execution_time:.1f}s, significantly longer than average {avg_time:.1f}s",
                    context={"pattern": task_pattern.pattern_id, "execution_time": execution_time, "avg_time": avg_time},
                    confidence=0.7
                ))
        
        return feedbacks
    
    async def _analyze_performance(self, task_description: str, execution_time: float,
                                 success: bool) -> Optional[LearningFeedback]:
        """Analyze performance for learning"""
        # Get or create performance baseline
        task_key = hash(task_description)
        baseline = self.performance_baselines.get(str(task_key))
        
        if baseline is None:
            # Set initial baseline
            self.performance_baselines[str(task_key)] = execution_time
            return None
        
        # Check for significant performance deviation
        if execution_time > baseline * 2:
            return LearningFeedback(
                task_id="",
                feedback_type=LearningType.PERFORMANCE_IMPROVEMENT,
                success=success,
                improvement_suggestion=f"Performance degraded: {execution_time:.1f}s vs baseline {baseline:.1f}s",
                context={"baseline": baseline, "current": execution_time, "degradation": execution_time / baseline},
                confidence=0.8
            )
        elif execution_time < baseline * 0.5:
            # Performance improved - update baseline
            self.performance_baselines[str(task_key)] = (baseline + execution_time) / 2
            return LearningFeedback(
                task_id="",
                feedback_type=LearningType.PERFORMANCE_IMPROVEMENT,
                success=success,
                improvement_suggestion=f"Performance improved: {execution_time:.1f}s vs baseline {baseline:.1f}s",
                context={"baseline": baseline, "current": execution_time, "improvement": baseline / execution_time},
                confidence=0.9
            )
        
        return None
    
    async def _analyze_error_for_learning(self, task_description: str, error: str,
                                        task_id: str) -> Optional[LearningFeedback]:
        """Analyze errors for prevention learning"""
        # Analyze error pattern
        error_pattern = await self.pattern_recognizer.analyze_error_pattern(
            task_description, error, "general", {"task_id": task_id}
        )
        
        if error_pattern and error_pattern.frequency >= 2:
            # Recurring error - generate prevention rule
            prevention_rule = f"For tasks like '{task_description}', watch for error: {error}"
            
            error_key = error_pattern.pattern_id
            if error_key not in self.error_prevention_rules:
                self.error_prevention_rules[error_key] = []
            
            self.error_prevention_rules[error_key].append(prevention_rule)
            
            return LearningFeedback(
                task_id=task_id,
                feedback_type=LearningType.ERROR_PREVENTION,
                success=False,
                improvement_suggestion=f"Recurring error pattern detected. Prevention rule added: {prevention_rule}",
                context={"error_pattern": error_pattern.pattern_id, "frequency": error_pattern.frequency},
                confidence=0.85
            )
        
        return None
    
    async def _process_user_feedback(self, task_id: str, task_description: str,
                                   user_feedback: str) -> Optional[LearningFeedback]:
        """Process explicit user feedback"""
        # Simple sentiment analysis (can be enhanced)
        positive_keywords = ["good", "great", "excellent", "perfect", "correct", "right"]
        negative_keywords = ["bad", "wrong", "terrible", "slow", "incorrect", "failed"]
        
        feedback_lower = user_feedback.lower()
        
        is_positive = any(keyword in feedback_lower for keyword in positive_keywords)
        is_negative = any(keyword in feedback_lower for keyword in negative_keywords)
        
        if is_positive or is_negative:
            # Extract preference from feedback
            preference_suggestion = f"User feedback indicates preference for tasks like '{task_description}'"
            
            if is_negative:
                preference_suggestion = f"User feedback indicates issues with tasks like '{task_description}'. Consider alternative approaches."
            
            return LearningFeedback(
                task_id=task_id,
                feedback_type=LearningType.USER_PREFERENCE,
                success=is_positive,
                improvement_suggestion=preference_suggestion,
                context={"user_feedback": user_feedback, "sentiment": "positive" if is_positive else "negative"},
                confidence=0.7
            )
        
        return None
    
    async def _store_learning_insight(self, feedback: LearningFeedback):
        """Store learning insight in memory"""
        await self.memory_store.store_memory(
            memory_type=MemoryType.LEARNING,
            content={
                "feedback_type": feedback.feedback_type.value,
                "success": feedback.success,
                "improvement_suggestion": feedback.improvement_suggestion,
                "context": feedback.context,
                "confidence": feedback.confidence
            },
            metadata={
                "task_id": feedback.task_id,
                "learning_type": feedback.feedback_type.value,
                "timestamp": feedback.timestamp
            }
        )
    
    async def _update_learning_models(self, task_description: str, feedbacks: List[LearningFeedback]):
        """Update internal learning models based on feedback"""
        # Update optimizations
        for feedback in feedbacks:
            if feedback.feedback_type == LearningType.TASK_OPTIMIZATION and feedback.confidence >= self.confidence_threshold:
                task_hash = str(hash(task_description))
                if task_hash not in self.learned_optimizations:
                    self.learned_optimizations[task_hash] = {}
                
                self.learned_optimizations[task_hash][feedback.improvement_suggestion] = {
                    "confidence": feedback.confidence,
                    "context": feedback.context,
                    "timestamp": feedback.timestamp
                }
    
    async def _get_optimization_recommendations(self, task_description: str) -> List[Dict[str, Any]]:
        """Get learned optimization recommendations"""
        task_hash = str(hash(task_description))
        optimizations = self.learned_optimizations.get(task_hash, {})
        
        recommendations = []
        for suggestion, data in optimizations.items():
            if data["confidence"] >= self.confidence_threshold:
                recommendations.append({
                    "suggestion": suggestion,
                    "confidence": data["confidence"],
                    "context": data["context"]
                })
        
        return recommendations
    
    async def _get_error_prevention_recommendations(self, task_description: str) -> List[Dict[str, Any]]:
        """Get error prevention recommendations"""
        recommendations = []
        
        # Find similar patterns in error prevention rules
        task_keywords = self.pattern_recognizer._extract_keywords(task_description)
        
        for error_key, rules in self.error_prevention_rules.items():
            for rule in rules:
                rule_keywords = self.pattern_recognizer._extract_keywords(rule)
                similarity = self.pattern_recognizer._calculate_keyword_similarity(task_keywords, rule_keywords)
                
                if similarity >= 0.5:
                    recommendations.append({
                        "prevention_rule": rule,
                        "confidence": similarity,
                        "error_pattern": error_key
                    })
        
        return recommendations
    
    async def _get_performance_recommendations(self, task_description: str) -> List[Dict[str, Any]]:
        """Get performance recommendations"""
        task_key = str(hash(task_description))
        baseline = self.performance_baselines.get(task_key)
        
        recommendations = []
        if baseline:
            recommendations.append({
                "baseline_time": baseline,
                "suggestion": f"Expected execution time: ~{baseline:.1f} seconds",
                "confidence": 0.8
            })
        
        return recommendations
    
    async def _get_user_preference_recommendations(self, task_description: str) -> Dict[str, Any]:
        """Get user preference recommendations"""
        preferences = {}
        
        # Find relevant user preferences
        task_keywords = self.pattern_recognizer._extract_keywords(task_description)
        
        for pref_key, pref_data in self.user_preferences.items():
            pref_context = pref_data.get("context", {})
            context_text = str(pref_context)
            context_keywords = self.pattern_recognizer._extract_keywords(context_text)
            
            similarity = self.pattern_recognizer._calculate_keyword_similarity(task_keywords, context_keywords)
            
            if similarity >= 0.3:
                preferences[pref_data["type"]] = {
                    "value": pref_data["value"],
                    "confidence": pref_data["confidence"] * similarity,
                    "context": pref_context
                }
        
        return preferences
    
    async def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning progress"""
        return {
            "optimizations_learned": len(self.learned_optimizations),
            "error_prevention_rules": sum(len(rules) for rules in self.error_prevention_rules.values()),
            "performance_baselines": len(self.performance_baselines),
            "user_preferences": len(self.user_preferences),
            "pattern_summary": await self.pattern_recognizer.get_pattern_summary()
        }