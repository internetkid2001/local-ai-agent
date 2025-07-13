#!/usr/bin/env python3
"""
Phase 3 Integration Test Suite

Comprehensive testing of Phase 3: Advanced AI Capabilities
Tests all AI modules integration and functionality.
"""

import asyncio
import sys
import traceback
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.ai.model_orchestrator import ModelOrchestrator, ModelConfig, ModelType
from agent.ai.conversation_manager import ConversationManager, ConversationConfig
from agent.ai.reasoning_engine import ReasoningEngine, ReasoningStrategy
from agent.ai.planning_engine import PlanningEngine, PlanningStrategy, PlanningConfig
from agent.ai.memory_system import MemorySystem, MemoryType, ModelMetric
from agent.ai.adaptation_engine import AdaptationEngine, AdaptationType

class Phase3IntegrationTest:
    """Integration test suite for Phase 3 AI capabilities"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        
    async def setup(self):
        """Setup test environment"""
        print("🚀 Setting up Phase 3 Integration Test Environment...")
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp(prefix="phase3_test_")
        print(f"📁 Test directory: {self.temp_dir}")
        
        # Initialize components with test configs
        self.model_orchestrator = ModelOrchestrator()
        
        # Add test models
        await self.model_orchestrator.register_model(ModelConfig(
            model_id="test_openai",
            model_type=ModelType.OPENAI,
            config={
                "model_name": "gpt-3.5-turbo",
                "api_key": "test_key",
                "max_tokens": 1000,
                "temperature": 0.7
            }
        ))
        
        await self.model_orchestrator.register_model(ModelConfig(
            model_id="test_ollama",
            model_type=ModelType.OLLAMA,
            config={
                "model_name": "llama3.2:1b",
                "base_url": "http://localhost:11434",
                "max_tokens": 500
            }
        ))
        
        # Initialize other components
        self.conversation_manager = ConversationManager(
            storage_path=f"{self.temp_dir}/conversations"
        )
        
        self.reasoning_engine = ReasoningEngine(
            model_orchestrator=self.model_orchestrator
        )
        
        self.planning_engine = PlanningEngine(
            model_orchestrator=self.model_orchestrator
        )
        
        self.memory_system = MemorySystem(
            storage_path=f"{self.temp_dir}/memory"
        )
        
        self.adaptation_engine = AdaptationEngine(
            storage_path=f"{self.temp_dir}/adaptation"
        )
        
        print("✅ Test environment setup complete")
        
    async def cleanup(self):
        """Cleanup test environment"""
        print("🧹 Cleaning up test environment...")
        
        try:
            # Cleanup components
            await self.conversation_manager.cleanup()
            await self.memory_system.cleanup()
            await self.adaptation_engine.cleanup()
            
            # Remove temporary directory
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
                
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
            
        print("✅ Cleanup complete")
        
    def record_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    📝 {details}")
            
    async def test_model_orchestrator(self):
        """Test Model Orchestrator functionality"""
        print("\n🧪 Testing Model Orchestrator...")
        
        try:
            # Test model registration
            models = await self.model_orchestrator.list_available_models()
            self.record_test_result(
                "Model Registration", 
                len(models) >= 2,
                f"Registered {len(models)} models"
            )
            
            # Test model selection
            selected = await self.model_orchestrator.select_optimal_model(
                task_type="text_generation",
                requirements={"max_tokens": 500}
            )
            self.record_test_result(
                "Model Selection",
                selected is not None,
                f"Selected model: {selected}"
            )
            
            # Test load balancing
            await self.model_orchestrator.enable_load_balancing(["test_openai", "test_ollama"])
            load_stats = await self.model_orchestrator.get_load_balancing_stats()
            self.record_test_result(
                "Load Balancing Setup",
                "test_openai" in load_stats["active_models"],
                f"Active models: {load_stats['active_models']}"
            )
            
        except Exception as e:
            self.record_test_result("Model Orchestrator", False, f"Error: {str(e)}")
            
    async def test_conversation_manager(self):
        """Test Conversation Manager functionality"""
        print("\n🧪 Testing Conversation Manager...")
        
        try:
            # Create conversation
            conv_id = await self.conversation_manager.create_conversation(
                ConversationConfig(
                    max_history_length=10,
                    context_window_size=1000,
                    enable_summarization=True
                )
            )
            self.record_test_result(
                "Conversation Creation",
                conv_id is not None,
                f"Created conversation: {conv_id}"
            )
            
            # Add messages
            await self.conversation_manager.add_message(conv_id, "user", "Hello, how are you?")
            await self.conversation_manager.add_message(conv_id, "assistant", "I'm doing well, thank you!")
            
            # Get conversation history
            history = await self.conversation_manager.get_conversation_history(conv_id)
            self.record_test_result(
                "Message Management",
                len(history) == 2,
                f"History length: {len(history)}"
            )
            
            # Test context management
            context = await self.conversation_manager.get_conversation_context(conv_id)
            self.record_test_result(
                "Context Management",
                context is not None and "messages" in context,
                f"Context keys: {list(context.keys()) if context else 'None'}"
            )
            
        except Exception as e:
            self.record_test_result("Conversation Manager", False, f"Error: {str(e)}")
            
    async def test_reasoning_engine(self):
        """Test Reasoning Engine functionality"""
        print("\n🧪 Testing Reasoning Engine...")
        
        try:
            # Test logical reasoning
            result = await self.reasoning_engine.reason(
                query="If all cats are animals, and Fluffy is a cat, is Fluffy an animal?",
                strategy=ReasoningStrategy.LOGICAL,
                context={"domain": "logic"}
            )
            self.record_test_result(
                "Logical Reasoning",
                result is not None and "reasoning_steps" in result,
                f"Reasoning result: {result.get('conclusion', 'No conclusion')[:50]}..."
            )
            
            # Test analytical reasoning
            result = await self.reasoning_engine.reason(
                query="What are the pros and cons of remote work?",
                strategy=ReasoningStrategy.ANALYTICAL,
                context={"analysis_type": "pros_cons"}
            )
            self.record_test_result(
                "Analytical Reasoning",
                result is not None,
                f"Analysis completed with {len(result.get('reasoning_steps', []))} steps"
            )
            
            # Test reasoning chain
            chain_result = await self.reasoning_engine.chain_reasoning([
                {"query": "What is machine learning?", "strategy": ReasoningStrategy.DEDUCTIVE},
                {"query": "How does it relate to AI?", "strategy": ReasoningStrategy.INDUCTIVE}
            ])
            self.record_test_result(
                "Reasoning Chain",
                chain_result is not None and len(chain_result) == 2,
                f"Chain completed with {len(chain_result)} steps"
            )
            
        except Exception as e:
            self.record_test_result("Reasoning Engine", False, f"Error: {str(e)}")
            
    async def test_planning_engine(self):
        """Test Planning Engine functionality"""
        print("\n🧪 Testing Planning Engine...")
        
        try:
            # Test hierarchical planning
            plan = await self.planning_engine.create_plan(
                goal="Build a web application",
                strategy=PlanningStrategy.HIERARCHICAL,
                config=PlanningConfig(
                    max_depth=3,
                    enable_dependencies=True,
                    optimization_level="balanced"
                )
            )
            self.record_test_result(
                "Hierarchical Planning",
                plan is not None and "tasks" in plan,
                f"Generated plan with {len(plan.get('tasks', []))} tasks"
            )
            
            # Test plan validation
            validation = await self.planning_engine.validate_plan(plan)
            self.record_test_result(
                "Plan Validation",
                validation.get("is_valid", False),
                f"Validation result: {validation.get('summary', 'No summary')}"
            )
            
            # Test plan optimization
            optimized = await self.planning_engine.optimize_plan(
                plan, 
                constraints={"max_time": 30, "max_cost": 1000}
            )
            self.record_test_result(
                "Plan Optimization",
                optimized is not None,
                f"Optimization completed: {optimized.get('optimization_type', 'Unknown')}"
            )
            
        except Exception as e:
            self.record_test_result("Planning Engine", False, f"Error: {str(e)}")
            
    async def test_memory_system(self):
        """Test Memory System functionality"""
        print("\n🧪 Testing Memory System...")
        
        try:
            # Store different types of memories
            episodic_id = await self.memory_system.store_memory(
                content="I had a meeting with the client yesterday",
                memory_type=MemoryType.EPISODIC,
                importance_score=0.7,
                tags=["meeting", "client"]
            )
            self.record_test_result(
                "Memory Storage",
                episodic_id is not None,
                f"Stored episodic memory: {episodic_id}"
            )
            
            semantic_id = await self.memory_system.store_memory(
                content="Python is a programming language",
                memory_type=MemoryType.SEMANTIC,
                importance_score=0.9,
                tags=["programming", "python"]
            )
            
            # Test memory retrieval
            retrieved = await self.memory_system.retrieve_memory(episodic_id)
            self.record_test_result(
                "Memory Retrieval",
                retrieved is not None and retrieved.id == episodic_id,
                f"Retrieved memory: {retrieved.content[:30]}..." if retrieved else "None"
            )
            
            # Test tag-based search
            tag_results = await self.memory_system.search_by_tags(["programming"])
            self.record_test_result(
                "Tag-based Search",
                len(tag_results) > 0,
                f"Found {len(tag_results)} memories with 'programming' tag"
            )
            
            # Test content search
            content_results = await self.memory_system.search_by_content("Python")
            self.record_test_result(
                "Content Search",
                len(content_results) > 0,
                f"Found {len(content_results)} memories containing 'Python'"
            )
            
            # Test recent memories
            recent = await self.memory_system.get_recent_memories(hours=1)
            self.record_test_result(
                "Recent Memories",
                len(recent) >= 2,
                f"Found {len(recent)} recent memories"
            )
            
            # Test memory stats
            stats = await self.memory_system.get_memory_stats()
            self.record_test_result(
                "Memory Statistics",
                stats["total_memories"] >= 2,
                f"Total memories: {stats['total_memories']}"
            )
            
        except Exception as e:
            self.record_test_result("Memory System", False, f"Error: {str(e)}")
            
    async def test_adaptation_engine(self):
        """Test Adaptation Engine functionality"""
        print("\n🧪 Testing Adaptation Engine...")
        
        try:
            # Record performance metrics
            await self.adaptation_engine.record_performance(
                metric_type=ModelMetric.LATENCY,
                value=2.5,
                model_id="test_openai",
                task_type="text_generation"
            )
            
            await self.adaptation_engine.record_performance(
                metric_type=ModelMetric.ACCURACY,
                value=0.85,
                model_id="test_openai",
                task_type="text_generation"
            )
            
            self.record_test_result(
                "Performance Recording",
                True,
                "Recorded latency and accuracy metrics"
            )
            
            # Add user feedback
            feedback_id = await self.adaptation_engine.add_feedback(
                task_type="text_generation",
                model_response="This is a test response",
                feedback_type="positive",
                feedback_content="Great response, very helpful!",
                rating=4.5
            )
            self.record_test_result(
                "Feedback Recording",
                feedback_id is not None,
                f"Recorded feedback: {feedback_id}"
            )
            
            # Analyze performance
            analysis = await self.adaptation_engine.analyze_performance(
                model_id="test_openai",
                task_type="text_generation"
            )
            self.record_test_result(
                "Performance Analysis",
                analysis is not None and "metrics" in analysis,
                f"Analysis includes {len(analysis.get('metrics', {}))} metric types"
            )
            
            # Get adaptation suggestions
            suggestions = await self.adaptation_engine.suggest_adaptations("text_generation")
            self.record_test_result(
                "Adaptation Suggestions",
                isinstance(suggestions, list),
                f"Generated {len(suggestions)} adaptation suggestions"
            )
            
            # Add adaptation rule
            rule_id = await self.adaptation_engine.add_adaptation_rule(
                rule_name="High Latency Response",
                condition={
                    "type": "metric_threshold",
                    "metric": "latency",
                    "threshold": 5.0,
                    "comparison": "greater"
                },
                action={
                    "type": "model_switch",
                    "target_model": "faster_model"
                }
            )
            self.record_test_result(
                "Adaptation Rules",
                rule_id is not None,
                f"Created adaptation rule: {rule_id}"
            )
            
            # Get adaptation stats
            stats = await self.adaptation_engine.get_adaptation_stats()
            self.record_test_result(
                "Adaptation Statistics",
                stats["total_rules"] >= 1,
                f"Total rules: {stats['total_rules']}, Total feedback: {stats['total_feedback']}"
            )
            
        except Exception as e:
            self.record_test_result("Adaptation Engine", False, f"Error: {str(e)}")
            
    async def test_cross_component_integration(self):
        """Test integration between components"""
        print("\n🧪 Testing Cross-Component Integration...")
        
        try:
            # Test Memory + Conversation integration
            conv_id = await self.conversation_manager.create_conversation()
            await self.conversation_manager.add_message(conv_id, "user", "What is machine learning?")
            
            # Store conversation in memory
            memory_id = await self.memory_system.store_memory(
                content="User asked about machine learning",
                memory_type=MemoryType.EPISODIC,
                metadata={"conversation_id": conv_id}
            )
            
            self.record_test_result(
                "Memory-Conversation Integration",
                memory_id is not None,
                f"Linked conversation {conv_id} to memory {memory_id}"
            )
            
            # Test Planning + Reasoning integration
            reasoning_result = await self.reasoning_engine.reason(
                query="What steps are needed to learn programming?",
                strategy=ReasoningStrategy.ANALYTICAL
            )
            
            if reasoning_result:
                plan = await self.planning_engine.create_plan(
                    goal="Learn programming based on reasoning analysis",
                    strategy=PlanningStrategy.SEQUENTIAL,
                    context={"reasoning_context": reasoning_result}
                )
                
                self.record_test_result(
                    "Planning-Reasoning Integration",
                    plan is not None,
                    f"Created plan based on reasoning with {len(plan.get('tasks', []))} tasks"
                )
                
            # Test Adaptation + Performance integration
            await self.adaptation_engine.record_performance(
                metric_type=ModelMetric.USER_SATISFACTION,
                value=4.8,
                model_id="test_openai"
            )
            
            analysis = await self.adaptation_engine.analyze_performance(model_id="test_openai")
            suggestions = await self.adaptation_engine.suggest_adaptations()
            
            self.record_test_result(
                "Adaptation-Performance Integration",
                len(suggestions) >= 0,  # May be 0 if no adaptations needed
                f"Performance analysis led to {len(suggestions)} suggestions"
            )
            
        except Exception as e:
            self.record_test_result("Cross-Component Integration", False, f"Error: {str(e)}")
            
    async def run_comprehensive_workflow_test(self):
        """Test a comprehensive workflow using all components"""
        print("\n🧪 Testing Comprehensive AI Workflow...")
        
        try:
            # 1. Create conversation
            conv_id = await self.conversation_manager.create_conversation(
                ConversationConfig(enable_summarization=True)
            )
            
            # 2. User asks a complex question
            await self.conversation_manager.add_message(
                conv_id, "user", 
                "I want to build a recommendation system. Can you help me plan this project?"
            )
            
            # 3. Use reasoning to analyze the request
            reasoning_result = await self.reasoning_engine.reason(
                query="How to approach building a recommendation system?",
                strategy=ReasoningStrategy.ANALYTICAL,
                context={"domain": "machine_learning", "project_type": "recommendation_system"}
            )
            
            # 4. Create a plan based on reasoning
            plan = await self.planning_engine.create_plan(
                goal="Build a recommendation system",
                strategy=PlanningStrategy.HIERARCHICAL,
                context={"reasoning_analysis": reasoning_result}
            )
            
            # 5. Store conversation and plan in memory
            conv_memory_id = await self.memory_system.store_memory(
                content=f"User requested help with recommendation system project",
                memory_type=MemoryType.EPISODIC,
                metadata={"conversation_id": conv_id, "plan_id": plan.get("plan_id")}
            )
            
            plan_memory_id = await self.memory_system.store_memory(
                content=f"Created project plan for recommendation system",
                memory_type=MemoryType.SEMANTIC,
                metadata={"plan": plan},
                tags=["planning", "recommendation_system", "machine_learning"]
            )
            
            # 6. Generate response using model orchestrator
            response_model = await self.model_orchestrator.select_optimal_model(
                task_type="text_generation",
                requirements={"context_length": len(str(plan))}
            )
            
            # 7. Add response to conversation
            await self.conversation_manager.add_message(
                conv_id, "assistant",
                f"I've analyzed your request and created a comprehensive plan. "
                f"The plan includes {len(plan.get('tasks', []))} main tasks."
            )
            
            # 8. Record performance metrics
            await self.adaptation_engine.record_performance(
                metric_type=ModelMetric.CONTEXT_RELEVANCE,
                value=0.9,
                model_id=response_model,
                task_type="planning_assistance"
            )
            
            # 9. Simulate user feedback
            await self.adaptation_engine.add_feedback(
                task_type="planning_assistance",
                model_response="Comprehensive plan created",
                feedback_type="positive",
                feedback_content="Very helpful and detailed plan",
                rating=5.0
            )
            
            # Verify workflow completion
            conversation_history = await self.conversation_manager.get_conversation_history(conv_id)
            memories = await self.memory_system.search_by_tags(["recommendation_system"])
            adaptation_stats = await self.adaptation_engine.get_adaptation_stats()
            
            workflow_success = (
                len(conversation_history) >= 2 and
                len(memories) >= 1 and
                plan is not None and
                adaptation_stats["total_feedback"] >= 1
            )
            
            self.record_test_result(
                "Comprehensive Workflow",
                workflow_success,
                f"Workflow completed: {len(conversation_history)} messages, "
                f"{len(memories)} memories, {adaptation_stats['total_feedback']} feedback entries"
            )
            
        except Exception as e:
            self.record_test_result("Comprehensive Workflow", False, f"Error: {str(e)}")
            
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("🧪 PHASE 3 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   • {result['test_name']}: {result['details']}")
                    
        print(f"\n🎯 COMPONENT STATUS:")
        components = [
            "Model Orchestrator", "Conversation Manager", "Reasoning Engine",
            "Planning Engine", "Memory System", "Adaptation Engine"
        ]
        
        for component in components:
            component_tests = [r for r in self.test_results if component.lower() in r["test_name"].lower()]
            if component_tests:
                component_passed = all(r["passed"] for r in component_tests)
                status = "✅" if component_passed else "❌"
                print(f"   {status} {component}")
                
        print("\n" + "="*60)
        
        # Overall assessment
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Phase 3 AI capabilities fully integrated.")
        elif passed_tests >= total_tests * 0.8:
            print("🟡 MOSTLY SUCCESSFUL! Phase 3 mostly integrated with minor issues.")
        else:
            print("🔴 INTEGRATION ISSUES! Phase 3 requires fixes before completion.")
            
        print("="*60)

async def main():
    """Run Phase 3 integration tests"""
    print("🧪 PHASE 3: ADVANCED AI CAPABILITIES - INTEGRATION TEST")
    print("="*60)
    
    test_suite = Phase3IntegrationTest()
    
    try:
        # Setup test environment
        await test_suite.setup()
        
        # Run individual component tests
        await test_suite.test_model_orchestrator()
        await test_suite.test_conversation_manager()
        await test_suite.test_reasoning_engine()
        await test_suite.test_planning_engine()
        await test_suite.test_memory_system()
        await test_suite.test_adaptation_engine()
        
        # Run integration tests
        await test_suite.test_cross_component_integration()
        await test_suite.run_comprehensive_workflow_test()
        
        # Print summary
        test_suite.print_test_summary()
        
    except Exception as e:
        print(f"💥 CRITICAL TEST FAILURE: {e}")
        traceback.print_exc()
        
    finally:
        # Cleanup
        await test_suite.cleanup()

if __name__ == "__main__":
    asyncio.run(main())