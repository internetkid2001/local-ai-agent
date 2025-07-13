"""
Reasoning Engine

Advanced reasoning capabilities with multiple strategies including logical reasoning,
causal analysis, analogical reasoning, and chain-of-thought processing.

Author: Claude Code
Date: 2025-07-13
Session: 3.1
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ReasoningMode(Enum):
    """Reasoning strategies"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    LOGICAL_DEDUCTION = "logical_deduction"
    CAUSAL_ANALYSIS = "causal_analysis"
    ANALOGICAL = "analogical"
    ABDUCTIVE = "abductive"
    INDUCTIVE = "inductive"
    DEDUCTIVE = "deductive"
    PROBABILISTIC = "probabilistic"
    CONSTRAINT_BASED = "constraint_based"
    CASE_BASED = "case_based"


class ConfidenceLevel(Enum):
    """Confidence levels for reasoning results"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ReasoningStep:
    """Individual step in reasoning process"""
    step_id: str
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning_mode: ReasoningMode
    confidence: ConfidenceLevel
    evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningResult:
    """Result of reasoning process"""
    conclusion: str
    reasoning_mode: ReasoningMode
    confidence: ConfidenceLevel
    steps: List[ReasoningStep]
    evidence: List[str]
    assumptions: List[str]
    alternatives: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningTask:
    """Task for reasoning engine"""
    query: str
    context: Dict[str, Any]
    reasoning_modes: List[ReasoningMode]
    max_steps: int = 10
    confidence_threshold: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timeout: float = 60.0
    use_memory: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReasoningEngine:
    """
    Advanced reasoning engine with multiple strategies.
    
    Features:
    - Multiple reasoning modes (deductive, inductive, abductive, etc.)
    - Chain-of-thought processing
    - Causal analysis and logical deduction
    - Analogical reasoning
    - Confidence assessment
    - Evidence tracking
    - Memory integration for case-based reasoning
    """
    
    def __init__(self, model_orchestrator=None, memory_system=None):
        """
        Initialize reasoning engine.
        
        Args:
            model_orchestrator: Model orchestrator for AI operations
            memory_system: Memory system for case-based reasoning
        """
        self.model_orchestrator = model_orchestrator
        self.memory_system = memory_system
        
        # Reasoning templates and patterns
        self.reasoning_templates = self._load_reasoning_templates()
        self.logical_patterns = self._load_logical_patterns()
        
        # Configuration
        self.config = {
            "default_confidence_threshold": ConfidenceLevel.MEDIUM,
            "max_reasoning_depth": 10,
            "enable_parallel_reasoning": True,
            "confidence_weights": {
                "evidence_count": 0.3,
                "logical_consistency": 0.4,
                "model_confidence": 0.3
            },
            "reasoning_timeout": 60.0
        }
        
        logger.info("Reasoning engine initialized")
    
    def _load_reasoning_templates(self) -> Dict[ReasoningMode, str]:
        """Load reasoning prompt templates"""
        return {
            ReasoningMode.CHAIN_OF_THOUGHT: """
Let's think step by step about this problem:

Problem: {query}
Context: {context}

Please provide a detailed chain of reasoning with the following format:
1. First, let me understand what we're trying to figure out...
2. The key information I have is...
3. Based on this information, I can reason that...
4. This leads me to conclude that...

Show your complete reasoning process with intermediate steps.
""",
            
            ReasoningMode.LOGICAL_DEDUCTION: """
Given the following premises and information, use logical deduction to reach a conclusion:

Query: {query}
Given facts: {context}

Please apply logical deduction rules:
1. Identify the premises and given facts
2. Apply logical rules (modus ponens, modus tollens, etc.)
3. Draw valid conclusions step by step
4. State your final logical conclusion

Ensure each step follows logically from the previous ones.
""",
            
            ReasoningMode.CAUSAL_ANALYSIS: """
Analyze the causal relationships in this scenario:

Scenario: {query}
Context: {context}

Please perform causal analysis:
1. Identify potential causes and effects
2. Analyze causal chains and relationships
3. Consider alternative causal explanations
4. Evaluate the strength of causal links
5. Provide your causal conclusion

Focus on understanding why things happen and what leads to what.
""",
            
            ReasoningMode.ANALOGICAL: """
Use analogical reasoning to solve this problem:

Problem: {query}
Context: {context}

Please reason by analogy:
1. Identify similar situations or patterns you know about
2. Draw parallels between this problem and analogous cases
3. Apply insights from analogous situations
4. Adapt the analogical solution to this specific context
5. Provide your analogical reasoning conclusion

Think about what this situation is similar to and learn from those similarities.
""",
            
            ReasoningMode.ABDUCTIVE: """
Use abductive reasoning to find the best explanation:

Observation: {query}
Context: {context}

Please apply abductive reasoning:
1. Identify what needs to be explained
2. Generate multiple possible explanations
3. Evaluate each explanation for plausibility and fit
4. Consider the simplicity and likelihood of each explanation
5. Select the best explanation

Find the most likely explanation for the given observations.
""",
            
            ReasoningMode.PROBABILISTIC: """
Apply probabilistic reasoning to this problem:

Problem: {query}
Context: {context}

Please use probabilistic reasoning:
1. Identify uncertain elements and their probabilities
2. Apply probability rules and Bayesian reasoning
3. Consider base rates and conditional probabilities
4. Estimate likelihoods and update beliefs
5. Provide probabilistic conclusions with confidence levels

Think in terms of probabilities and uncertainty.
"""
        }
    
    def _load_logical_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load logical reasoning patterns"""
        return {
            "modus_ponens": {
                "pattern": "If P then Q; P; therefore Q",
                "template": "Given that {premise1} and {premise2}, we can conclude {conclusion}"
            },
            "modus_tollens": {
                "pattern": "If P then Q; not Q; therefore not P",
                "template": "Since {premise1} and {premise2}, we can conclude {conclusion}"
            },
            "syllogism": {
                "pattern": "All A are B; All B are C; therefore All A are C",
                "template": "Given {major_premise} and {minor_premise}, therefore {conclusion}"
            },
            "disjunctive_syllogism": {
                "pattern": "P or Q; not P; therefore Q",
                "template": "Either {premise1} or {premise2}; since not {premise1}, therefore {premise2}"
            }
        }
    
    async def reason(self, task: ReasoningTask) -> ReasoningResult:
        """
        Perform reasoning on a given task.
        
        Args:
            task: Reasoning task
            
        Returns:
            Reasoning result
        """
        start_time = time.time()
        
        try:
            # Try multiple reasoning modes if specified
            if len(task.reasoning_modes) > 1 and self.config["enable_parallel_reasoning"]:
                result = await self._parallel_reasoning(task)
            else:
                reasoning_mode = task.reasoning_modes[0] if task.reasoning_modes else ReasoningMode.CHAIN_OF_THOUGHT
                result = await self._single_mode_reasoning(task, reasoning_mode)
            
            result.execution_time = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return ReasoningResult(
                conclusion=f"Reasoning failed: {str(e)}",
                reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,
                confidence=ConfidenceLevel.VERY_LOW,
                steps=[],
                evidence=[],
                assumptions=[],
                execution_time=time.time() - start_time
            )
    
    async def _parallel_reasoning(self, task: ReasoningTask) -> ReasoningResult:
        """Perform reasoning using multiple modes in parallel"""
        reasoning_tasks = []
        
        for mode in task.reasoning_modes:
            mode_task = ReasoningTask(
                query=task.query,
                context=task.context,
                reasoning_modes=[mode],
                max_steps=task.max_steps,
                confidence_threshold=task.confidence_threshold,
                timeout=task.timeout / len(task.reasoning_modes),  # Distribute timeout
                use_memory=task.use_memory,
                metadata=task.metadata
            )
            reasoning_tasks.append(self._single_mode_reasoning(mode_task, mode))
        
        # Execute all reasoning modes in parallel
        results = await asyncio.gather(*reasoning_tasks, return_exceptions=True)
        
        # Filter out exceptions and get valid results
        valid_results = [r for r in results if isinstance(r, ReasoningResult)]
        
        if not valid_results:
            return ReasoningResult(
                conclusion="No valid reasoning results obtained",
                reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,
                confidence=ConfidenceLevel.VERY_LOW,
                steps=[],
                evidence=[],
                assumptions=[]
            )
        
        # Combine and synthesize results
        return await self._synthesize_reasoning_results(valid_results, task)
    
    async def _single_mode_reasoning(self, task: ReasoningTask, mode: ReasoningMode) -> ReasoningResult:
        """Perform reasoning using a single mode"""
        if not self.model_orchestrator:
            return self._fallback_reasoning(task, mode)
        
        # Get relevant memory if requested
        memory_context = ""
        if task.use_memory and self.memory_system:
            memory_context = await self._get_relevant_memory(task.query)
        
        # Prepare reasoning prompt
        prompt_template = self.reasoning_templates.get(mode, self.reasoning_templates[ReasoningMode.CHAIN_OF_THOUGHT])
        
        context_str = self._format_context(task.context)
        if memory_context:
            context_str += f"\n\nRelevant past experience:\n{memory_context}"
        
        prompt = prompt_template.format(
            query=task.query,
            context=context_str
        )
        
        # Execute reasoning with model
        from .model_orchestrator import ModelRequest, ModelCapability
        
        request = ModelRequest(
            prompt=prompt,
            capabilities_required=[ModelCapability.REASONING, ModelCapability.ANALYSIS],
            max_tokens=2048,
            temperature=0.3,  # Lower temperature for more logical reasoning
            timeout=task.timeout
        )
        
        response = await self.model_orchestrator.generate(request)
        
        if response.success:
            return await self._parse_reasoning_response(response.content, mode, task)
        else:
            return ReasoningResult(
                conclusion=f"Reasoning failed: {response.error}",
                reasoning_mode=mode,
                confidence=ConfidenceLevel.VERY_LOW,
                steps=[],
                evidence=[],
                assumptions=[]
            )
    
    def _fallback_reasoning(self, task: ReasoningTask, mode: ReasoningMode) -> ReasoningResult:
        """Fallback reasoning when no model orchestrator available"""
        # Simple rule-based reasoning for basic cases
        if "true" in task.query.lower() and "false" in task.query.lower():
            conclusion = "This appears to be a logical contradiction"
            confidence = ConfidenceLevel.HIGH
        elif "if" in task.query.lower() and "then" in task.query.lower():
            conclusion = "This appears to be a conditional statement requiring logical analysis"
            confidence = ConfidenceLevel.MEDIUM
        else:
            conclusion = "Unable to perform detailed reasoning without AI model"
            confidence = ConfidenceLevel.VERY_LOW
        
        return ReasoningResult(
            conclusion=conclusion,
            reasoning_mode=mode,
            confidence=confidence,
            steps=[],
            evidence=[],
            assumptions=["No AI model available for detailed reasoning"]
        )
    
    async def _parse_reasoning_response(self, response_text: str, mode: ReasoningMode, task: ReasoningTask) -> ReasoningResult:
        """Parse reasoning response from model"""
        # Extract reasoning steps (simplified parsing)
        steps = []
        evidence = []
        assumptions = []
        
        # Look for numbered steps
        lines = response_text.split('\n')
        step_counter = 1
        
        for line in lines:
            line = line.strip()
            if line.startswith(f"{step_counter}.") or line.startswith(f"Step {step_counter}"):
                step = ReasoningStep(
                    step_id=f"step_{step_counter}",
                    description=line,
                    input_data={},
                    output_data={},
                    reasoning_mode=mode,
                    confidence=ConfidenceLevel.MEDIUM
                )
                steps.append(step)
                step_counter += 1
            elif "evidence" in line.lower() or "fact" in line.lower():
                evidence.append(line)
            elif "assume" in line.lower() or "given" in line.lower():
                assumptions.append(line)
        
        # Extract conclusion (usually the last meaningful sentence)
        conclusion_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        conclusion = conclusion_lines[-1] if conclusion_lines else response_text[:200]
        
        # Assess confidence based on reasoning quality
        confidence = self._assess_reasoning_confidence(response_text, steps, evidence)
        
        return ReasoningResult(
            conclusion=conclusion,
            reasoning_mode=mode,
            confidence=confidence,
            steps=steps,
            evidence=evidence,
            assumptions=assumptions,
            metadata={"raw_response": response_text}
        )
    
    def _assess_reasoning_confidence(self, response_text: str, steps: List[ReasoningStep], evidence: List[str]) -> ConfidenceLevel:
        """Assess confidence level of reasoning"""
        confidence_score = 0.0
        
        # Factor 1: Number of reasoning steps
        if len(steps) >= 3:
            confidence_score += 0.3
        elif len(steps) >= 1:
            confidence_score += 0.1
        
        # Factor 2: Evidence provided
        if len(evidence) >= 2:
            confidence_score += 0.3
        elif len(evidence) >= 1:
            confidence_score += 0.15
        
        # Factor 3: Logical keywords indicating structured reasoning
        logical_keywords = ["therefore", "because", "since", "given", "thus", "hence", "consequently"]
        keyword_count = sum(1 for keyword in logical_keywords if keyword in response_text.lower())
        confidence_score += min(0.4, keyword_count * 0.1)
        
        # Convert to confidence level
        if confidence_score >= 0.8:
            return ConfidenceLevel.VERY_HIGH
        elif confidence_score >= 0.6:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.4:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    async def _synthesize_reasoning_results(self, results: List[ReasoningResult], task: ReasoningTask) -> ReasoningResult:
        """Synthesize multiple reasoning results into one"""
        if len(results) == 1:
            return results[0]
        
        # Find the highest confidence result as primary
        primary_result = max(results, key=lambda r: list(ConfidenceLevel).index(r.confidence))
        
        # Combine evidence and steps from all results
        all_evidence = []
        all_steps = []
        all_assumptions = []
        alternatives = []
        
        for result in results:
            all_evidence.extend(result.evidence)
            all_steps.extend(result.steps)
            all_assumptions.extend(result.assumptions)
            if result != primary_result:
                alternatives.append(f"{result.reasoning_mode.value}: {result.conclusion}")
        
        # Create synthesized result
        synthesized = ReasoningResult(
            conclusion=primary_result.conclusion,
            reasoning_mode=ReasoningMode.CHAIN_OF_THOUGHT,  # Combined approach
            confidence=primary_result.confidence,
            steps=all_steps,
            evidence=list(set(all_evidence)),  # Remove duplicates
            assumptions=list(set(all_assumptions)),
            alternatives=alternatives,
            metadata={
                "synthesis_source": "parallel_reasoning",
                "contributing_modes": [r.reasoning_mode.value for r in results]
            }
        )
        
        return synthesized
    
    async def _get_relevant_memory(self, query: str) -> str:
        """Get relevant memory for reasoning context"""
        if not self.memory_system:
            return ""
        
        try:
            # Search for relevant memories
            memories = await self.memory_system.search_memories(query, limit=3)
            
            if memories:
                memory_context = "Relevant past reasoning:\n"
                for memory in memories:
                    memory_context += f"- {memory.content}\n"
                return memory_context
            
        except Exception as e:
            logger.error(f"Failed to retrieve reasoning memory: {e}")
        
        return ""
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as readable text"""
        if not context:
            return "No additional context provided."
        
        formatted = []
        for key, value in context.items():
            formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    async def validate_reasoning(self, result: ReasoningResult) -> Dict[str, Any]:
        """Validate the quality of reasoning result"""
        validation = {
            "logical_consistency": 0.0,
            "evidence_quality": 0.0,
            "step_coherence": 0.0,
            "overall_score": 0.0,
            "issues": []
        }
        
        # Check logical consistency
        if len(result.steps) > 1:
            consistent_steps = 0
            for i in range(1, len(result.steps)):
                # Simple heuristic: check if steps build on each other
                if any(word in result.steps[i].description.lower() 
                      for word in ["therefore", "thus", "so", "because"]):
                    consistent_steps += 1
            
            validation["logical_consistency"] = consistent_steps / (len(result.steps) - 1)
        
        # Check evidence quality
        if result.evidence:
            validation["evidence_quality"] = min(1.0, len(result.evidence) / 3.0)
        
        # Check step coherence
        if result.steps:
            coherent_steps = sum(1 for step in result.steps if len(step.description) > 10)
            validation["step_coherence"] = coherent_steps / len(result.steps)
        
        # Calculate overall score
        validation["overall_score"] = (
            validation["logical_consistency"] * 0.4 +
            validation["evidence_quality"] * 0.3 +
            validation["step_coherence"] * 0.3
        )
        
        # Identify issues
        if validation["logical_consistency"] < 0.5:
            validation["issues"].append("Low logical consistency between reasoning steps")
        if validation["evidence_quality"] < 0.3:
            validation["issues"].append("Insufficient evidence provided")
        if validation["step_coherence"] < 0.5:
            validation["issues"].append("Reasoning steps lack detail or coherence")
        
        return validation
    
    def explain_reasoning(self, result: ReasoningResult) -> str:
        """Generate human-readable explanation of reasoning process"""
        explanation = f"Reasoning Mode: {result.reasoning_mode.value.title()}\n"
        explanation += f"Confidence: {result.confidence.value.title()}\n\n"
        
        explanation += f"Conclusion: {result.conclusion}\n\n"
        
        if result.steps:
            explanation += "Reasoning Steps:\n"
            for i, step in enumerate(result.steps, 1):
                explanation += f"{i}. {step.description}\n"
            explanation += "\n"
        
        if result.evidence:
            explanation += "Supporting Evidence:\n"
            for evidence in result.evidence:
                explanation += f"- {evidence}\n"
            explanation += "\n"
        
        if result.assumptions:
            explanation += "Key Assumptions:\n"
            for assumption in result.assumptions:
                explanation += f"- {assumption}\n"
            explanation += "\n"
        
        if result.alternatives:
            explanation += "Alternative Perspectives:\n"
            for alt in result.alternatives:
                explanation += f"- {alt}\n"
        
        return explanation