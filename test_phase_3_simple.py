#!/usr/bin/env python3
"""
Phase 3 Simple Integration Test

Basic test to verify Phase 3 AI modules can be imported and instantiated.
"""

import sys
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all Phase 3 modules can be imported"""
    print("🧪 Testing Phase 3 Module Imports...")
    
    test_results = []
    
    # Test Model Orchestrator
    try:
        from agent.ai.model_orchestrator import ModelOrchestrator, ModelConfig, ModelType
        print("✅ Model Orchestrator import successful")
        test_results.append(("Model Orchestrator Import", True))
    except Exception as e:
        print(f"❌ Model Orchestrator import failed: {e}")
        test_results.append(("Model Orchestrator Import", False))
    
    # Test Conversation Manager
    try:
        from agent.ai.conversation_manager import ConversationManager, ConversationConfig
        print("✅ Conversation Manager import successful")
        test_results.append(("Conversation Manager Import", True))
    except Exception as e:
        print(f"❌ Conversation Manager import failed: {e}")
        test_results.append(("Conversation Manager Import", False))
    
    # Test Reasoning Engine
    try:
        from agent.ai.reasoning_engine import ReasoningEngine, ReasoningStrategy
        print("✅ Reasoning Engine import successful")
        test_results.append(("Reasoning Engine Import", True))
    except Exception as e:
        print(f"❌ Reasoning Engine import failed: {e}")
        test_results.append(("Reasoning Engine Import", False))
    
    # Test Planning Engine
    try:
        from agent.ai.planning_engine import PlanningEngine, PlanningStrategy, PlanningConfig
        print("✅ Planning Engine import successful")
        test_results.append(("Planning Engine Import", True))
    except Exception as e:
        print(f"❌ Planning Engine import failed: {e}")
        test_results.append(("Planning Engine Import", False))
    
    # Test Memory System
    try:
        from agent.ai.memory_system import MemorySystem, MemoryType, ModelMetric
        print("✅ Memory System import successful")
        test_results.append(("Memory System Import", True))
    except Exception as e:
        print(f"❌ Memory System import failed: {e}")
        test_results.append(("Memory System Import", False))
    
    # Test Adaptation Engine
    try:
        from agent.ai.adaptation_engine import AdaptationEngine, AdaptationType
        print("✅ Adaptation Engine import successful")
        test_results.append(("Adaptation Engine Import", True))
    except Exception as e:
        print(f"❌ Adaptation Engine import failed: {e}")
        test_results.append(("Adaptation Engine Import", False))
    
    return test_results

def test_basic_instantiation():
    """Test basic instantiation of components"""
    print("\n🧪 Testing Basic Component Instantiation...")
    
    test_results = []
    
    try:
        from agent.ai.memory_system import MemorySystem
        memory_system = MemorySystem(storage_path="./test_memory")
        print("✅ Memory System instantiation successful")
        test_results.append(("Memory System Instantiation", True))
    except Exception as e:
        print(f"❌ Memory System instantiation failed: {e}")
        test_results.append(("Memory System Instantiation", False))
    
    try:
        from agent.ai.adaptation_engine import AdaptationEngine
        adaptation_engine = AdaptationEngine(storage_path="./test_adaptation")
        print("✅ Adaptation Engine instantiation successful")
        test_results.append(("Adaptation Engine Instantiation", True))
    except Exception as e:
        print(f"❌ Adaptation Engine instantiation failed: {e}")
        test_results.append(("Adaptation Engine Instantiation", False))
    
    try:
        from agent.ai.conversation_manager import ConversationManager
        conv_manager = ConversationManager(storage_path="./test_conversations")
        print("✅ Conversation Manager instantiation successful")
        test_results.append(("Conversation Manager Instantiation", True))
    except Exception as e:
        print(f"❌ Conversation Manager instantiation failed: {e}")
        test_results.append(("Conversation Manager Instantiation", False))
    
    return test_results

def print_test_summary(all_results):
    """Print test summary"""
    print("\n" + "="*50)
    print("🧪 PHASE 3 SIMPLE TEST SUMMARY")
    print("="*50)
    
    total_tests = len(all_results)
    passed_tests = sum(1 for _, passed in all_results if passed)
    failed_tests = total_tests - passed_tests
    
    print(f"📊 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ FAILED TESTS:")
        for test_name, passed in all_results:
            if not passed:
                print(f"   • {test_name}")
    
    print("\n" + "="*50)
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Phase 3 modules are properly implemented.")
    elif passed_tests >= total_tests * 0.8:
        print("🟡 MOSTLY SUCCESSFUL! Phase 3 mostly working with minor issues.")
    else:
        print("🔴 ISSUES DETECTED! Phase 3 requires fixes.")
    
    print("="*50)

def main():
    """Run simple Phase 3 tests"""
    print("🧪 PHASE 3: ADVANCED AI CAPABILITIES - SIMPLE TEST")
    print("="*50)
    
    all_results = []
    
    try:
        # Test imports
        import_results = test_imports()
        all_results.extend(import_results)
        
        # Test basic instantiation
        instantiation_results = test_basic_instantiation()
        all_results.extend(instantiation_results)
        
        # Print summary
        print_test_summary(all_results)
        
    except Exception as e:
        print(f"💥 CRITICAL TEST FAILURE: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()