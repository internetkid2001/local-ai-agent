"""
Workflow Parser

Parses workflow definitions from various formats (JSON, YAML, Python dict)
and creates WorkflowDefinition objects.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import json
import yaml
import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

from .workflow_engine import WorkflowDefinition, WorkflowStep
from .step_executor import StepType
from ...utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowParser:
    """
    Parses workflow definitions from various formats.
    
    Supported formats:
    - JSON
    - YAML
    - Python dictionary
    - DSL (Domain Specific Language) strings
    """
    
    def __init__(self):
        """Initialize workflow parser"""
        logger.info("Workflow parser initialized")
    
    def parse_from_dict(self, workflow_dict: Dict[str, Any]) -> WorkflowDefinition:
        """
        Parse workflow from Python dictionary.
        
        Args:
            workflow_dict: Workflow definition as dictionary
            
        Returns:
            WorkflowDefinition object
        """
        try:
            # Extract basic workflow info
            workflow_id = workflow_dict.get('id', str(uuid.uuid4()))
            name = workflow_dict.get('name', 'Unnamed Workflow')
            description = workflow_dict.get('description', '')
            
            # Parse steps
            steps_data = workflow_dict.get('steps', [])
            steps = []
            
            for step_data in steps_data:
                step = self._parse_step(step_data)
                steps.append(step)
            
            # Parse workflow-level settings
            global_timeout = workflow_dict.get('global_timeout', 1800.0)
            max_retries = workflow_dict.get('max_retries', 3)
            failure_strategy = workflow_dict.get('failure_strategy', 'stop')
            context = workflow_dict.get('context', {})
            
            workflow = WorkflowDefinition(
                id=workflow_id,
                name=name,
                description=description,
                steps=steps,
                global_timeout=global_timeout,
                max_retries=max_retries,
                failure_strategy=failure_strategy,
                context=context
            )
            
            # Validate workflow
            self._validate_workflow(workflow)
            
            logger.info(f"Parsed workflow: {name} with {len(steps)} steps")
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to parse workflow from dict: {e}")
            raise ValueError(f"Workflow parsing failed: {e}")
    
    def parse_from_json(self, json_str: str) -> WorkflowDefinition:
        """Parse workflow from JSON string"""
        try:
            workflow_dict = json.loads(json_str)
            return self.parse_from_dict(workflow_dict)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def parse_from_yaml(self, yaml_str: str) -> WorkflowDefinition:
        """Parse workflow from YAML string"""
        try:
            workflow_dict = yaml.safe_load(yaml_str)
            return self.parse_from_dict(workflow_dict)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
    
    def parse_from_file(self, file_path: str) -> WorkflowDefinition:
        """Parse workflow from file (JSON or YAML based on extension)"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            if file_path.endswith('.json'):
                return self.parse_from_json(content)
            elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                return self.parse_from_yaml(content)
            else:
                # Try to auto-detect format
                try:
                    return self.parse_from_json(content)
                except:
                    return self.parse_from_yaml(content)
                    
        except Exception as e:
            logger.error(f"Failed to parse workflow from file {file_path}: {e}")
            raise ValueError(f"File parsing failed: {e}")
    
    def parse_from_dsl(self, dsl_str: str) -> WorkflowDefinition:
        """
        Parse workflow from simple DSL format.
        
        Example DSL:
        workflow "Example Workflow"
        step "Step 1" llm_query "Analyze the data"
        step "Step 2" file_operation "read_file" file_path="/path/to/file"
        step "Step 3" depends_on="Step 1,Step 2" mcp_tool "analyze_data"
        """
        try:
            lines = [line.strip() for line in dsl_str.split('\n') if line.strip()]
            
            workflow_name = "DSL Workflow"
            workflow_description = ""
            steps = []
            
            for line in lines:
                if line.startswith('workflow '):
                    # Extract workflow name
                    workflow_name = line[9:].strip().strip('"\'')
                elif line.startswith('description '):
                    # Extract description
                    workflow_description = line[12:].strip().strip('"\'')
                elif line.startswith('step '):
                    # Parse step
                    step = self._parse_dsl_step(line)
                    steps.append(step)
            
            workflow = WorkflowDefinition(
                id=str(uuid.uuid4()),
                name=workflow_name,
                description=workflow_description,
                steps=steps
            )
            
            self._validate_workflow(workflow)
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to parse DSL workflow: {e}")
            raise ValueError(f"DSL parsing failed: {e}")
    
    def _parse_step(self, step_data: Dict[str, Any]) -> WorkflowStep:
        """Parse individual step from dictionary"""
        step_id = step_data.get('id', str(uuid.uuid4()))
        name = step_data.get('name', f'Step {step_id}')
        
        # Parse step type
        step_type_str = step_data.get('type', 'llm_query')
        try:
            step_type = StepType(step_type_str)
        except ValueError:
            logger.warning(f"Unknown step type: {step_type_str}, defaulting to LLM_QUERY")
            step_type = StepType.LLM_QUERY
        
        action = step_data.get('action', '')
        parameters = step_data.get('parameters', {})
        dependencies = step_data.get('dependencies', [])
        conditions = step_data.get('conditions', [])
        retry_count = step_data.get('retry_count', 3)
        timeout = step_data.get('timeout', 300.0)
        parallel_group = step_data.get('parallel_group')
        
        return WorkflowStep(
            id=step_id,
            name=name,
            step_type=step_type,
            action=action,
            parameters=parameters,
            dependencies=dependencies,
            conditions=conditions,
            retry_count=retry_count,
            timeout=timeout,
            parallel_group=parallel_group
        )
    
    def _parse_dsl_step(self, line: str) -> WorkflowStep:
        """Parse step from DSL line"""
        # Simple parsing for DSL format
        # Format: step "name" [depends_on="dep1,dep2"] type "action" [param1="value1" param2="value2"]
        
        parts = line.split()
        step_name = ""
        step_type = StepType.LLM_QUERY
        action = ""
        parameters = {}
        dependencies = []
        
        i = 1  # Skip 'step'
        
        # Extract step name
        if i < len(parts) and parts[i].startswith('"'):
            name_parts = []
            while i < len(parts):
                part = parts[i]
                name_parts.append(part.strip('"'))
                if part.endswith('"'):
                    break
                i += 1
            step_name = ' '.join(name_parts).strip('"')
            i += 1
        
        # Parse remaining parts
        while i < len(parts):
            part = parts[i]
            
            if part.startswith('depends_on='):
                deps_str = part.split('=', 1)[1].strip('"\'')
                dependencies = [dep.strip() for dep in deps_str.split(',')]
            elif part in [e.value for e in StepType]:
                step_type = StepType(part)
                # Next part should be action
                if i + 1 < len(parts):
                    action = parts[i + 1].strip('"\'')
                    i += 1
            elif '=' in part:
                # Parameter
                key, value = part.split('=', 1)
                parameters[key] = value.strip('"\'')
            
            i += 1
        
        return WorkflowStep(
            id=str(uuid.uuid4()),
            name=step_name,
            step_type=step_type,
            action=action,
            parameters=parameters,
            dependencies=dependencies
        )
    
    def _validate_workflow(self, workflow: WorkflowDefinition):
        """Validate workflow definition"""
        # Check for duplicate step IDs
        step_ids = [step.id for step in workflow.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Duplicate step IDs found")
        
        # Check dependency references
        for step in workflow.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Step {step.id} depends on non-existent step: {dep}")
        
        # Check for circular dependencies
        self._check_circular_dependencies(workflow)
        
        # Validate step actions
        for step in workflow.steps:
            if not step.action:
                logger.warning(f"Step {step.id} has empty action")
    
    def _check_circular_dependencies(self, workflow: WorkflowDefinition):
        """Check for circular dependencies in workflow"""
        step_deps = {step.id: set(step.dependencies) for step in workflow.steps}
        
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in step_deps.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for step_id in step_deps:
            if step_id not in visited:
                if has_cycle(step_id, visited, set()):
                    raise ValueError("Circular dependency detected in workflow")
    
    def to_dict(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Convert workflow definition to dictionary"""
        return {
            'id': workflow.id,
            'name': workflow.name,
            'description': workflow.description,
            'global_timeout': workflow.global_timeout,
            'max_retries': workflow.max_retries,
            'failure_strategy': workflow.failure_strategy,
            'context': workflow.context,
            'steps': [
                {
                    'id': step.id,
                    'name': step.name,
                    'type': step.step_type.value,
                    'action': step.action,
                    'parameters': step.parameters,
                    'dependencies': step.dependencies,
                    'conditions': step.conditions,
                    'retry_count': step.retry_count,
                    'timeout': step.timeout,
                    'parallel_group': step.parallel_group
                }
                for step in workflow.steps
            ]
        }
    
    def to_json(self, workflow: WorkflowDefinition, indent: int = 2) -> str:
        """Convert workflow to JSON string"""
        return json.dumps(self.to_dict(workflow), indent=indent)
    
    def to_yaml(self, workflow: WorkflowDefinition) -> str:
        """Convert workflow to YAML string"""
        return yaml.dump(self.to_dict(workflow), default_flow_style=False)