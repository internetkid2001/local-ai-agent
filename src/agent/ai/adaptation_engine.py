"""
Adaptation Engine for Model Fine-tuning and Learning

Advanced adaptation system that provides:
- Model performance monitoring and evaluation
- Adaptive fine-tuning strategies
- Learning from user interactions and feedback
- Performance optimization and model selection
- Continuous improvement mechanisms
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from pathlib import Path
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class AdaptationType(Enum):
    PERFORMANCE_BASED = "performance"    # Based on task performance metrics
    FEEDBACK_BASED = "feedback"         # Based on user feedback
    ERROR_BASED = "error"              # Based on error patterns
    USAGE_BASED = "usage"              # Based on usage patterns
    HYBRID = "hybrid"                  # Combination of all types

class ModelMetric(Enum):
    ACCURACY = "accuracy"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    COST = "cost"
    USER_SATISFACTION = "user_satisfaction"
    ERROR_RATE = "error_rate"
    CONTEXT_RELEVANCE = "context_relevance"

@dataclass
class PerformanceMetric:
    metric_type: ModelMetric
    value: float
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    task_type: Optional[str] = None
    model_id: Optional[str] = None

@dataclass
class FeedbackEntry:
    id: str
    user_id: Optional[str]
    task_type: str
    model_response: str
    feedback_type: str  # "positive", "negative", "correction"
    feedback_content: str
    rating: Optional[float] = None  # 1-5 scale
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class AdaptationRule:
    id: str
    name: str
    condition: str  # JSON-serializable condition
    action: str     # Action to take when condition is met
    priority: int = 1
    enabled: bool = True
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class ModelPerformanceTracker:
    """Tracks model performance metrics over time"""
    
    def __init__(self, history_limit: int = 10000):
        self.history_limit = history_limit
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_limit))
        self.model_metrics: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=history_limit))
        )
        
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric"""
        metric_key = metric.metric_type.value
        self.metrics[metric_key].append(metric)
        
        if metric.model_id:
            self.model_metrics[metric.model_id][metric_key].append(metric)
            
    def get_recent_metrics(self, 
                          metric_type: ModelMetric,
                          model_id: Optional[str] = None,
                          hours: int = 24,
                          limit: int = 100) -> List[PerformanceMetric]:
        """Get recent metrics for analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if model_id:
            metrics_deque = self.model_metrics[model_id][metric_type.value]
        else:
            metrics_deque = self.metrics[metric_type.value]
            
        recent_metrics = [
            metric for metric in metrics_deque
            if metric.timestamp >= cutoff_time
        ]
        
        return sorted(recent_metrics, key=lambda m: m.timestamp, reverse=True)[:limit]
        
    def calculate_trend(self, 
                       metric_type: ModelMetric,
                       model_id: Optional[str] = None,
                       hours: int = 24) -> Optional[float]:
        """Calculate performance trend (positive = improving)"""
        recent_metrics = self.get_recent_metrics(metric_type, model_id, hours)
        
        if len(recent_metrics) < 2:
            return None
            
        values = [m.value for m in recent_metrics]
        timestamps = [m.timestamp.timestamp() for m in recent_metrics]
        
        # Simple linear regression to calculate trend
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope

class FeedbackAnalyzer:
    """Analyzes user feedback for adaptation insights"""
    
    def __init__(self, feedback_limit: int = 5000):
        self.feedback_limit = feedback_limit
        self.feedback_history: deque = deque(maxlen=feedback_limit)
        self.feedback_patterns: Dict[str, List[FeedbackEntry]] = defaultdict(list)
        
    def add_feedback(self, feedback: FeedbackEntry) -> None:
        """Add user feedback"""
        self.feedback_history.append(feedback)
        self.feedback_patterns[feedback.task_type].append(feedback)
        
    def analyze_sentiment_trend(self, task_type: Optional[str] = None, hours: int = 24) -> Dict[str, float]:
        """Analyze sentiment trends in feedback"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if task_type:
            feedback_list = [
                f for f in self.feedback_patterns[task_type]
                if f.timestamp >= cutoff_time
            ]
        else:
            feedback_list = [
                f for f in self.feedback_history
                if f.timestamp >= cutoff_time
            ]
            
        if not feedback_list:
            return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
            
        positive = sum(1 for f in feedback_list if f.feedback_type == "positive")
        negative = sum(1 for f in feedback_list if f.feedback_type == "negative")
        neutral = len(feedback_list) - positive - negative
        
        total = len(feedback_list)
        return {
            "positive": positive / total,
            "negative": negative / total,
            "neutral": neutral / total,
            "total_count": total
        }
        
    def get_common_issues(self, task_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify common issues from negative feedback"""
        if task_type:
            feedback_list = [
                f for f in self.feedback_patterns[task_type]
                if f.feedback_type == "negative"
            ]
        else:
            feedback_list = [
                f for f in self.feedback_history
                if f.feedback_type == "negative"
            ]
            
        # Simple keyword-based issue identification
        issue_counts = defaultdict(int)
        issue_examples = defaultdict(list)
        
        keywords = ["slow", "incorrect", "confusing", "error", "wrong", "bad", "poor"]
        
        for feedback in feedback_list:
            content_lower = feedback.feedback_content.lower()
            for keyword in keywords:
                if keyword in content_lower:
                    issue_counts[keyword] += 1
                    issue_examples[keyword].append(feedback.feedback_content[:100])
                    
        issues = []
        for keyword, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            issues.append({
                "issue_type": keyword,
                "count": count,
                "examples": issue_examples[keyword][:3]
            })
            
        return issues[:limit]

class AdaptationEngine:
    """Main adaptation engine for model fine-tuning and learning"""
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 adaptation_type: AdaptationType = AdaptationType.HYBRID,
                 min_samples_for_adaptation: int = 100,
                 adaptation_threshold: float = 0.1):
        
        self.storage_path = Path(storage_path) if storage_path else Path("adaptation_store")
        self.storage_path.mkdir(exist_ok=True)
        
        self.adaptation_type = adaptation_type
        self.min_samples = min_samples_for_adaptation
        self.adaptation_threshold = adaptation_threshold
        
        # Core components
        self.performance_tracker = ModelPerformanceTracker()
        self.feedback_analyzer = FeedbackAnalyzer()
        
        # Adaptation rules and history
        self.adaptation_rules: Dict[str, AdaptationRule] = {}
        self.adaptation_history: List[Dict[str, Any]] = []
        
        # Model configurations and strategies
        self.model_configs: Dict[str, Dict[str, Any]] = {}
        self.active_models: Dict[str, str] = {}  # task_type -> model_id
        
        # Load existing data
        self._load_adaptation_data()
        
    async def record_performance(self, 
                               metric_type: ModelMetric,
                               value: float,
                               model_id: Optional[str] = None,
                               task_type: Optional[str] = None,
                               context: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance metric"""
        
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            context=context,
            task_type=task_type,
            model_id=model_id
        )
        
        self.performance_tracker.record_metric(metric)
        await self._check_adaptation_triggers()
        
    async def add_feedback(self, 
                          task_type: str,
                          model_response: str,
                          feedback_type: str,
                          feedback_content: str,
                          user_id: Optional[str] = None,
                          rating: Optional[float] = None,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """Add user feedback"""
        
        feedback_id = f"feedback_{datetime.now().isoformat()}_{hash(feedback_content) % 1000}"
        
        feedback = FeedbackEntry(
            id=feedback_id,
            user_id=user_id,
            task_type=task_type,
            model_response=model_response,
            feedback_type=feedback_type,
            feedback_content=feedback_content,
            rating=rating,
            context=context
        )
        
        self.feedback_analyzer.add_feedback(feedback)
        await self._persist_feedback(feedback)
        await self._check_adaptation_triggers()
        
        return feedback_id
        
    async def analyze_performance(self, 
                                model_id: Optional[str] = None,
                                task_type: Optional[str] = None,
                                hours: int = 24) -> Dict[str, Any]:
        """Analyze model performance and suggest adaptations"""
        
        analysis = {
            "model_id": model_id,
            "task_type": task_type,
            "analysis_period_hours": hours,
            "metrics": {},
            "trends": {},
            "recommendations": []
        }
        
        # Analyze each metric type
        for metric_type in ModelMetric:
            recent_metrics = self.performance_tracker.get_recent_metrics(
                metric_type, model_id, hours
            )
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                analysis["metrics"][metric_type.value] = {
                    "count": len(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "latest": values[0] if values else None
                }
                
                # Calculate trend
                trend = self.performance_tracker.calculate_trend(metric_type, model_id, hours)
                if trend is not None:
                    analysis["trends"][metric_type.value] = trend
                    
        # Generate recommendations based on analysis
        analysis["recommendations"] = await self._generate_recommendations(analysis)
        
        return analysis
        
    async def suggest_adaptations(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Suggest specific adaptations based on current performance"""
        
        suggestions = []
        
        # Performance-based suggestions
        if self.adaptation_type in [AdaptationType.PERFORMANCE_BASED, AdaptationType.HYBRID]:
            perf_suggestions = await self._suggest_performance_adaptations(task_type)
            suggestions.extend(perf_suggestions)
            
        # Feedback-based suggestions
        if self.adaptation_type in [AdaptationType.FEEDBACK_BASED, AdaptationType.HYBRID]:
            feedback_suggestions = await self._suggest_feedback_adaptations(task_type)
            suggestions.extend(feedback_suggestions)
            
        # Error-based suggestions
        if self.adaptation_type in [AdaptationType.ERROR_BASED, AdaptationType.HYBRID]:
            error_suggestions = await self._suggest_error_adaptations(task_type)
            suggestions.extend(error_suggestions)
            
        # Usage-based suggestions
        if self.adaptation_type in [AdaptationType.USAGE_BASED, AdaptationType.HYBRID]:
            usage_suggestions = await self._suggest_usage_adaptations(task_type)
            suggestions.extend(usage_suggestions)
            
        # Sort by priority and confidence
        suggestions.sort(key=lambda s: (s.get("priority", 1), s.get("confidence", 0.5)), reverse=True)
        
        return suggestions
        
    async def apply_adaptation(self, 
                             adaptation_id: str,
                             adaptation_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a specific adaptation"""
        
        result = {
            "adaptation_id": adaptation_id,
            "status": "pending",
            "applied_at": datetime.now(),
            "config": adaptation_config,
            "result": None,
            "error": None
        }
        
        try:
            adaptation_type = adaptation_config.get("type")
            
            if adaptation_type == "model_switch":
                result["result"] = await self._apply_model_switch(adaptation_config)
            elif adaptation_type == "parameter_tuning":
                result["result"] = await self._apply_parameter_tuning(adaptation_config)
            elif adaptation_type == "prompt_optimization":
                result["result"] = await self._apply_prompt_optimization(adaptation_config)
            elif adaptation_type == "context_adjustment":
                result["result"] = await self._apply_context_adjustment(adaptation_config)
            else:
                raise ValueError(f"Unknown adaptation type: {adaptation_type}")
                
            result["status"] = "success"
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Failed to apply adaptation {adaptation_id}: {e}")
            
        # Record adaptation attempt
        self.adaptation_history.append(result)
        await self._persist_adaptation_history()
        
        return result
        
    async def add_adaptation_rule(self, 
                                rule_name: str,
                                condition: Dict[str, Any],
                                action: Dict[str, Any],
                                priority: int = 1) -> str:
        """Add a new adaptation rule"""
        
        rule_id = f"rule_{datetime.now().isoformat()}_{hash(rule_name) % 1000}"
        
        rule = AdaptationRule(
            id=rule_id,
            name=rule_name,
            condition=json.dumps(condition),
            action=json.dumps(action),
            priority=priority
        )
        
        self.adaptation_rules[rule_id] = rule
        await self._persist_adaptation_rules()
        
        return rule_id
        
    async def _check_adaptation_triggers(self) -> None:
        """Check if any adaptation rules should be triggered"""
        
        for rule in self.adaptation_rules.values():
            if not rule.enabled:
                continue
                
            try:
                condition = json.loads(rule.condition)
                if await self._evaluate_condition(condition):
                    action = json.loads(rule.action)
                    await self.apply_adaptation(f"auto_{rule.id}", action)
                    
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.id}: {e}")
                
    async def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """Evaluate whether a condition is met"""
        
        condition_type = condition.get("type")
        
        if condition_type == "metric_threshold":
            metric_type = ModelMetric(condition["metric"])
            threshold = condition["threshold"]
            comparison = condition.get("comparison", "greater")
            
            recent_metrics = self.performance_tracker.get_recent_metrics(
                metric_type, hours=condition.get("hours", 1), limit=10
            )
            
            if not recent_metrics:
                return False
                
            avg_value = np.mean([m.value for m in recent_metrics])
            
            if comparison == "greater":
                return avg_value > threshold
            elif comparison == "less":
                return avg_value < threshold
            elif comparison == "equal":
                return abs(avg_value - threshold) < 0.01
                
        elif condition_type == "feedback_sentiment":
            task_type = condition.get("task_type")
            sentiment_threshold = condition["threshold"]
            
            sentiment = self.feedback_analyzer.analyze_sentiment_trend(
                task_type, hours=condition.get("hours", 24)
            )
            
            return sentiment.get("negative", 0) > sentiment_threshold
            
        return False
        
    async def _suggest_performance_adaptations(self, task_type: Optional[str]) -> List[Dict[str, Any]]:
        """Suggest adaptations based on performance metrics"""
        
        suggestions = []
        
        # Check latency issues
        latency_metrics = self.performance_tracker.get_recent_metrics(
            ModelMetric.LATENCY, hours=24
        )
        
        if latency_metrics:
            avg_latency = np.mean([m.value for m in latency_metrics])
            if avg_latency > 5.0:  # > 5 seconds average
                suggestions.append({
                    "type": "model_switch",
                    "reason": "High latency detected",
                    "priority": 3,
                    "confidence": 0.8,
                    "config": {
                        "type": "model_switch",
                        "target_model": "faster_model",
                        "task_type": task_type
                    }
                })
                
        # Check accuracy issues
        accuracy_metrics = self.performance_tracker.get_recent_metrics(
            ModelMetric.ACCURACY, hours=24
        )
        
        if accuracy_metrics:
            trend = self.performance_tracker.calculate_trend(ModelMetric.ACCURACY)
            if trend and trend < -0.1:  # Decreasing accuracy
                suggestions.append({
                    "type": "parameter_tuning",
                    "reason": "Decreasing accuracy trend",
                    "priority": 2,
                    "confidence": 0.7,
                    "config": {
                        "type": "parameter_tuning",
                        "parameters": {"temperature": 0.7, "top_p": 0.9},
                        "task_type": task_type
                    }
                })
                
        return suggestions
        
    async def _suggest_feedback_adaptations(self, task_type: Optional[str]) -> List[Dict[str, Any]]:
        """Suggest adaptations based on user feedback"""
        
        suggestions = []
        
        # Analyze sentiment trends
        sentiment = self.feedback_analyzer.analyze_sentiment_trend(task_type, hours=24)
        
        if sentiment.get("negative", 0) > 0.3:  # > 30% negative feedback
            common_issues = self.feedback_analyzer.get_common_issues(task_type)
            
            for issue in common_issues[:3]:
                if issue["issue_type"] in ["slow", "latency"]:
                    suggestions.append({
                        "type": "model_switch",
                        "reason": f"User feedback indicates {issue['issue_type']} issues",
                        "priority": 2,
                        "confidence": 0.6,
                        "config": {
                            "type": "model_switch",
                            "target_model": "faster_model",
                            "task_type": task_type
                        }
                    })
                elif issue["issue_type"] in ["incorrect", "wrong"]:
                    suggestions.append({
                        "type": "prompt_optimization",
                        "reason": f"User feedback indicates {issue['issue_type']} responses",
                        "priority": 3,
                        "confidence": 0.7,
                        "config": {
                            "type": "prompt_optimization",
                            "optimization_type": "accuracy_focused",
                            "task_type": task_type
                        }
                    })
                    
        return suggestions
        
    async def _suggest_error_adaptations(self, task_type: Optional[str]) -> List[Dict[str, Any]]:
        """Suggest adaptations based on error patterns"""
        
        suggestions = []
        
        # Check error rate metrics
        error_metrics = self.performance_tracker.get_recent_metrics(
            ModelMetric.ERROR_RATE, hours=24
        )
        
        if error_metrics:
            avg_error_rate = np.mean([m.value for m in error_metrics])
            if avg_error_rate > 0.1:  # > 10% error rate
                suggestions.append({
                    "type": "context_adjustment",
                    "reason": "High error rate detected",
                    "priority": 3,
                    "confidence": 0.8,
                    "config": {
                        "type": "context_adjustment",
                        "adjustment_type": "increase_context",
                        "task_type": task_type
                    }
                })
                
        return suggestions
        
    async def _suggest_usage_adaptations(self, task_type: Optional[str]) -> List[Dict[str, Any]]:
        """Suggest adaptations based on usage patterns"""
        
        suggestions = []
        
        # Check cost metrics
        cost_metrics = self.performance_tracker.get_recent_metrics(
            ModelMetric.COST, hours=24
        )
        
        if cost_metrics:
            total_cost = sum(m.value for m in cost_metrics)
            if total_cost > 100.0:  # High daily cost
                suggestions.append({
                    "type": "model_switch",
                    "reason": "High cost usage detected",
                    "priority": 1,
                    "confidence": 0.9,
                    "config": {
                        "type": "model_switch",
                        "target_model": "cost_efficient_model",
                        "task_type": task_type
                    }
                })
                
        return suggestions
        
    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate human-readable recommendations"""
        
        recommendations = []
        
        # Check for performance issues
        metrics = analysis.get("metrics", {})
        trends = analysis.get("trends", {})
        
        if "latency" in metrics:
            latency_data = metrics["latency"]
            if latency_data["mean"] > 3.0:
                recommendations.append("Consider switching to a faster model to reduce latency")
                
        if "accuracy" in trends:
            if trends["accuracy"] < -0.05:
                recommendations.append("Accuracy is declining - consider parameter tuning")
                
        if "cost" in metrics:
            cost_data = metrics["cost"]
            if cost_data["mean"] > 10.0:
                recommendations.append("High cost per request - consider cost optimization")
                
        return recommendations
        
    async def _apply_model_switch(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply model switching adaptation"""
        
        task_type = config.get("task_type")
        target_model = config.get("target_model")
        
        if task_type and target_model:
            old_model = self.active_models.get(task_type, "unknown")
            self.active_models[task_type] = target_model
            
            return {
                "action": "model_switch",
                "task_type": task_type,
                "old_model": old_model,
                "new_model": target_model
            }
            
        raise ValueError("Missing task_type or target_model in config")
        
    async def _apply_parameter_tuning(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameter tuning adaptation"""
        
        task_type = config.get("task_type")
        parameters = config.get("parameters", {})
        
        if task_type:
            if task_type not in self.model_configs:
                self.model_configs[task_type] = {}
                
            self.model_configs[task_type].update(parameters)
            
            return {
                "action": "parameter_tuning",
                "task_type": task_type,
                "updated_parameters": parameters
            }
            
        raise ValueError("Missing task_type in config")
        
    async def _apply_prompt_optimization(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply prompt optimization adaptation"""
        
        optimization_type = config.get("optimization_type")
        task_type = config.get("task_type")
        
        return {
            "action": "prompt_optimization",
            "optimization_type": optimization_type,
            "task_type": task_type,
            "note": "Prompt optimization logic would be implemented here"
        }
        
    async def _apply_context_adjustment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply context adjustment adaptation"""
        
        adjustment_type = config.get("adjustment_type")
        task_type = config.get("task_type")
        
        return {
            "action": "context_adjustment",
            "adjustment_type": adjustment_type,
            "task_type": task_type,
            "note": "Context adjustment logic would be implemented here"
        }
        
    async def _persist_feedback(self, feedback: FeedbackEntry) -> None:
        """Persist feedback to storage"""
        
        feedback_file = self.storage_path / "feedback" / f"{feedback.id}.json"
        feedback_file.parent.mkdir(exist_ok=True)
        
        feedback_dict = asdict(feedback)
        feedback_dict['timestamp'] = feedback.timestamp.isoformat()
        
        with open(feedback_file, 'w') as f:
            json.dump(feedback_dict, f, indent=2)
            
    async def _persist_adaptation_rules(self) -> None:
        """Persist adaptation rules to storage"""
        
        rules_file = self.storage_path / "rules.json"
        
        rules_dict = {}
        for rule_id, rule in self.adaptation_rules.items():
            rule_dict = asdict(rule)
            rule_dict['created_at'] = rule.created_at.isoformat()
            rules_dict[rule_id] = rule_dict
            
        with open(rules_file, 'w') as f:
            json.dump(rules_dict, f, indent=2)
            
    async def _persist_adaptation_history(self) -> None:
        """Persist adaptation history to storage"""
        
        history_file = self.storage_path / "adaptation_history.json"
        
        # Convert datetime objects to ISO format
        serializable_history = []
        for entry in self.adaptation_history:
            entry_copy = entry.copy()
            if isinstance(entry_copy.get('applied_at'), datetime):
                entry_copy['applied_at'] = entry_copy['applied_at'].isoformat()
            serializable_history.append(entry_copy)
            
        with open(history_file, 'w') as f:
            json.dump(serializable_history, f, indent=2)
            
    def _load_adaptation_data(self) -> None:
        """Load adaptation data from storage"""
        
        # Load adaptation rules
        rules_file = self.storage_path / "rules.json"
        if rules_file.exists():
            try:
                with open(rules_file, 'r') as f:
                    rules_dict = json.load(f)
                    
                for rule_id, rule_data in rules_dict.items():
                    rule_data['created_at'] = datetime.fromisoformat(rule_data['created_at'])
                    self.adaptation_rules[rule_id] = AdaptationRule(**rule_data)
                    
            except Exception as e:
                logger.error(f"Failed to load adaptation rules: {e}")
                
        # Load adaptation history
        history_file = self.storage_path / "adaptation_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    self.adaptation_history = json.load(f)
                    
                # Convert ISO format back to datetime
                for entry in self.adaptation_history:
                    if 'applied_at' in entry and isinstance(entry['applied_at'], str):
                        entry['applied_at'] = datetime.fromisoformat(entry['applied_at'])
                        
            except Exception as e:
                logger.error(f"Failed to load adaptation history: {e}")
                
        # Load feedback entries
        feedback_dir = self.storage_path / "feedback"
        if feedback_dir.exists():
            for feedback_file in feedback_dir.glob("*.json"):
                try:
                    with open(feedback_file, 'r') as f:
                        feedback_dict = json.load(f)
                        
                    feedback_dict['timestamp'] = datetime.fromisoformat(feedback_dict['timestamp'])
                    feedback = FeedbackEntry(**feedback_dict)
                    self.feedback_analyzer.add_feedback(feedback)
                    
                except Exception as e:
                    logger.error(f"Failed to load feedback from {feedback_file}: {e}")
                    
    async def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation engine statistics"""
        
        return {
            "adaptation_type": self.adaptation_type.value,
            "total_rules": len(self.adaptation_rules),
            "active_rules": sum(1 for r in self.adaptation_rules.values() if r.enabled),
            "total_adaptations": len(self.adaptation_history),
            "successful_adaptations": sum(1 for a in self.adaptation_history if a.get("status") == "success"),
            "total_feedback": len(self.feedback_analyzer.feedback_history),
            "active_models": dict(self.active_models),
            "model_configs": dict(self.model_configs),
            "min_samples_threshold": self.min_samples,
            "adaptation_threshold": self.adaptation_threshold
        }
        
    async def cleanup(self) -> None:
        """Cleanup adaptation engine"""
        await self._persist_adaptation_rules()
        await self._persist_adaptation_history()
        logger.info("Adaptation engine cleanup completed")