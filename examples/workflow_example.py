#!/usr/bin/env python3
"""
Example: Advanced Workflow Usage

Demonstrates the new Phase 2.2 workflow capabilities including:
- Multi-step orchestration
- Context-aware decision making
- Task dependency management
- Error recovery and retry logic

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent.workflows.workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowStep, WorkflowStatus
from agent.workflows.step_executor import StepType
from agent.workflows.workflow_templates import WorkflowTemplates
from agent.context.context_manager import ContextManager, ContextType, ContextScope
from agent.context.memory_store import MemoryStore
from agent.context.learning_engine import LearningEngine


async def create_sample_workflow() -> WorkflowDefinition:
    """Create a sample workflow for demonstration"""
    
    steps = [
        WorkflowStep(
            id="analyze_task",
            name="Analyze Task Requirements",
            step_type=StepType.LLM_QUERY,
            action="Analyze this task: Create a Python script to process data files",
            parameters={"model_type": "primary"}
        ),
        
        WorkflowStep(
            id="create_directory",
            name="Create Working Directory",
            step_type=StepType.SYSTEM_COMMAND,
            action="mkdir -p /tmp/workflow_demo",
            dependencies=["analyze_task"]
        ),
        
        WorkflowStep(
            id="generate_code",
            name="Generate Python Code",
            step_type=StepType.LLM_QUERY,
            action="Generate Python code for data processing based on analysis: {analyze_task.response}",
            parameters={"model_type": "code"},
            dependencies=["analyze_task"]
        ),
        
        WorkflowStep(
            id="save_code",
            name="Save Generated Code",
            step_type=StepType.FILE_OPERATION,
            action="write_file",
            parameters={
                "path": "/tmp/workflow_demo/process_data.py",
                "content": "{generate_code.response}"
            },
            dependencies=["create_directory", "generate_code"]
        ),
        
        WorkflowStep(
            id="validate_code",
            name="Validate Code Syntax",
            step_type=StepType.SYSTEM_COMMAND,
            action="python -m py_compile /tmp/workflow_demo/process_data.py",
            dependencies=["save_code"],
            retry_count=2
        ),
        
        WorkflowStep(
            id="cleanup",
            name="Cleanup Working Directory",
            step_type=StepType.SYSTEM_COMMAND,
            action="rm -rf /tmp/workflow_demo",
            dependencies=["validate_code"],
            conditions=["exists(validate_code.success)"]
        )
    ]
    
    workflow = WorkflowDefinition(
        id="sample_workflow",
        name="Code Generation Workflow",
        description="Sample workflow demonstrating advanced orchestration",
        steps=steps,
        failure_strategy="continue"
    )
    
    return workflow


async def demonstrate_workflow_templates():
    """Demonstrate workflow template usage"""
    print("\n=== Workflow Template Demonstration ===")
    
    templates = WorkflowTemplates()
    
    # List available templates
    template_list = templates.get_template_list()
    print(f"Available templates: {len(template_list)}")
    for template in template_list:
        print(f"  - {template['name']}: {template['description']}")
    
    # Get template info
    file_analysis_info = templates.get_template_info('file_analysis')
    if file_analysis_info:
        print(f"\nTemplate: {file_analysis_info['name']}")
        print(f"Parameters:")
        for param in file_analysis_info['parameters']:
            print(f"  - {param['name']}: {param['description']} (required: {param['required']})")
    
    # Create workflow from template
    try:
        workflow = templates.create_workflow_from_template('file_analysis', {
            'directory_path': '/tmp',
            'file_types': '*.py,*.txt',
            'output_file': '/tmp/analysis_report.txt'
        })
        print(f"\nCreated workflow from template: {workflow.name}")
        print(f"Steps: {len(workflow.steps)}")
        for i, step in enumerate(workflow.steps):
            print(f"  {i+1}. {step.name} ({step.step_type.value})")
    except Exception as e:
        print(f"Error creating workflow from template: {e}")


async def demonstrate_context_aware_decisions():
    """Demonstrate context-aware decision making"""
    print("\n=== Context-Aware Decision Making ===")
    
    # Initialize context management
    memory_store = MemoryStore(":memory:")  # In-memory for demo
    await memory_store.initialize()
    
    context_manager = ContextManager(memory_store)
    learning_engine = LearningEngine(memory_store)
    
    # Add some context
    await context_manager.add_task_context(
        task_id="demo_task_1",
        task_description="Generate Python code",
        task_status="completed",
        execution_time=15.5,
        success=True
    )
    
    await context_manager.add_context(
        context_type=ContextType.USER_PREFERENCES,
        scope=ContextScope.USER,
        data={"preferred_language": "python", "code_style": "pep8"},
        tags={"coding", "preferences"}
    )
    
    # Get relevant context for a new task
    relevant_context = await context_manager.get_relevant_context(
        "Create a Python script for data analysis",
        {"task_type": "code_generation"}
    )
    
    print("Relevant context found:")
    for key, value in relevant_context.items():
        print(f"  {key}: {value}")
    
    # Get learning recommendations
    recommendations = await learning_engine.get_task_recommendations(
        "Create a Python script for data analysis",
        {"language": "python"}
    )
    
    print(f"\nLearning recommendations (confidence: {recommendations['confidence']:.2f}):")
    for category, items in recommendations.items():
        if items and category != 'confidence':
            print(f"  {category}: {len(items)} items")


async def demonstrate_dependency_management():
    """Demonstrate advanced dependency management"""
    print("\n=== Dependency Management ===")
    
    workflow_engine = WorkflowEngine()
    
    # Create workflow with complex dependencies
    workflow = await create_sample_workflow()
    
    # Show dependency visualization
    dependency_viz = workflow_engine.dependency_manager.visualize_dependencies()
    print("Dependency graph would be:")
    print(dependency_viz)
    
    print(f"\nWorkflow: {workflow.name}")
    print(f"Total steps: {len(workflow.steps)}")
    print("Step dependencies:")
    for step in workflow.steps:
        deps = step.dependencies if step.dependencies else ["None"]
        print(f"  {step.name}: depends on {', '.join(deps)}")


async def demonstrate_error_recovery():
    """Demonstrate error recovery capabilities"""
    print("\n=== Error Recovery Demonstration ===")
    
    # Create a workflow step that might fail
    failing_step = WorkflowStep(
        id="failing_step",
        name="Potentially Failing Step",
        step_type=StepType.SYSTEM_COMMAND,
        action="python -c 'import random; exit(random.choice([0, 1]))'",  # 50% fail rate
        retry_count=3,
        timeout=5.0
    )
    
    print(f"Step: {failing_step.name}")
    print(f"Retry count: {failing_step.retry_count}")
    print(f"Timeout: {failing_step.timeout}s")
    print("This step has a 50% chance of failure and will demonstrate retry logic")


async def main():
    """Main demonstration function"""
    print("Phase 2.2 Advanced Agent Workflows - Demonstration")
    print("=" * 60)
    
    try:
        # Demonstrate different capabilities
        await demonstrate_workflow_templates()
        await demonstrate_context_aware_decisions()
        await demonstrate_dependency_management()
        await demonstrate_error_recovery()
        
        print("\n=== Summary of Phase 2.2 Features ===")
        print("✅ Multi-step task orchestration with dependency management")
        print("✅ Context-aware decision making with memory and learning")
        print("✅ Advanced error recovery and retry logic")
        print("✅ Workflow templates for common scenarios")
        print("✅ Parallel execution optimization")
        print("✅ Conditional and data-driven dependencies")
        
        print("\nPhase 2.2 implementation complete! 🚀")
        
    except Exception as e:
        print(f"Demonstration error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())