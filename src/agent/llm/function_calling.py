"""
Function Calling Support

Handles function calling integration for local LLMs with Ollama,
including schema validation and result processing.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import json
import asyncio
import inspect
from typing import Dict, List, Any, Callable, Optional, Union, get_type_hints
from dataclasses import dataclass
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ParameterType(Enum):
    """Parameter types for function schemas"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class FunctionParameter:
    """Function parameter definition"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format"""
        schema = {
            "type": self.type.value,
            "description": self.description
        }
        
        if self.enum:
            schema["enum"] = self.enum
        
        return schema


@dataclass 
class FunctionSchema:
    """Complete function schema for LLM function calling"""
    name: str
    description: str
    parameters: List[FunctionParameter]
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible function schema"""
        required_params = [p.name for p in self.parameters if p.required]
        
        properties = {
            param.name: param.to_schema() 
            for param in self.parameters
        }
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }


class FunctionCallHandler:
    """
    Handles function calling for local LLMs.
    
    Features:
    - Automatic schema generation from Python functions
    - Parameter validation and type conversion
    - Async and sync function support
    - Error handling and result formatting
    - Function registry management
    """
    
    def __init__(self):
        """Initialize function call handler"""
        self._functions: Dict[str, Callable] = {}
        self._schemas: Dict[str, FunctionSchema] = {}
        
        logger.info("Function call handler initialized")
    
    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameter_descriptions: Optional[Dict[str, str]] = None
    ) -> FunctionSchema:
        """
        Register a function for LLM calling.
        
        Args:
            func: Function to register
            name: Optional custom name (defaults to function name)
            description: Function description
            parameter_descriptions: Parameter descriptions
            
        Returns:
            Generated function schema
        """
        function_name = name or func.__name__
        function_description = description or func.__doc__ or f"Function {function_name}"
        
        # Generate schema from function signature
        schema = self._generate_schema(func, function_name, function_description, parameter_descriptions)
        
        self._functions[function_name] = func
        self._schemas[function_name] = schema
        
        logger.info(f"Registered function: {function_name}")
        return schema
    
    def unregister_function(self, name: str):
        """Remove a function from the registry"""
        if name in self._functions:
            del self._functions[name]
            del self._schemas[name]
            logger.info(f"Unregistered function: {name}")
    
    async def call_function(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a registered function with validation.
        
        Args:
            name: Function name
            arguments: Function arguments
            
        Returns:
            Function call result with metadata
        """
        if name not in self._functions:
            error_msg = f"Function not found: {name}"
            logger.error(error_msg)
            return {"error": error_msg, "success": False}
        
        function = self._functions[name]
        schema = self._schemas[name]
        
        try:
            # Validate and convert arguments
            validated_args = self._validate_arguments(schema, arguments)
            
            # Call function (async or sync)
            if asyncio.iscoroutinefunction(function):
                result = await function(**validated_args)
            else:
                result = function(**validated_args)
            
            logger.debug(f"Function {name} executed successfully")
            
            return {
                "result": result,
                "success": True,
                "function_name": name,
                "arguments": validated_args
            }
            
        except Exception as e:
            error_msg = f"Function {name} execution failed: {str(e)}"
            logger.error(error_msg)
            
            return {
                "error": error_msg,
                "success": False,
                "function_name": name,
                "arguments": arguments
            }
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get all function schemas in OpenAI format"""
        return [
            {
                "type": "function",
                "function": schema.to_schema()
            }
            for schema in self._schemas.values()
        ]
    
    def get_function_list(self) -> List[str]:
        """Get list of registered function names"""
        return list(self._functions.keys())
    
    def get_function_schema(self, name: str) -> Optional[FunctionSchema]:
        """Get schema for a specific function"""
        return self._schemas.get(name)
    
    def _generate_schema(
        self,
        func: Callable,
        name: str,
        description: str,
        parameter_descriptions: Optional[Dict[str, str]]
    ) -> FunctionSchema:
        """Generate function schema from Python function"""
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        param_descriptions = parameter_descriptions or {}
        
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue
            
            # Get type information
            param_type = type_hints.get(param_name, str)
            json_type = self._python_type_to_json_type(param_type)
            
            # Get description
            param_desc = param_descriptions.get(param_name, f"Parameter {param_name}")
            
            # Check if required (has no default)
            required = param.default == inspect.Parameter.empty
            default_value = None if required else param.default
            
            function_param = FunctionParameter(
                name=param_name,
                type=json_type,
                description=param_desc,
                required=required,
                default=default_value
            )
            
            parameters.append(function_param)
        
        return FunctionSchema(
            name=name,
            description=description,
            parameters=parameters
        )
    
    def _python_type_to_json_type(self, python_type: type) -> ParameterType:
        """Convert Python type to JSON schema type"""
        if python_type == str:
            return ParameterType.STRING
        elif python_type == int:
            return ParameterType.INTEGER
        elif python_type == float:
            return ParameterType.NUMBER
        elif python_type == bool:
            return ParameterType.BOOLEAN
        elif python_type == list or hasattr(python_type, "__origin__") and python_type.__origin__ == list:
            return ParameterType.ARRAY
        elif python_type == dict or hasattr(python_type, "__origin__") and python_type.__origin__ == dict:
            return ParameterType.OBJECT
        else:
            # Default to string for unknown types
            return ParameterType.STRING
    
    def _validate_arguments(self, schema: FunctionSchema, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and convert function arguments"""
        validated = {}
        
        # Check required parameters
        required_params = {p.name for p in schema.parameters if p.required}
        provided_params = set(arguments.keys())
        
        missing_params = required_params - provided_params
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Validate and convert each parameter
        for param in schema.parameters:
            param_name = param.name
            
            if param_name in arguments:
                value = arguments[param_name]
                validated[param_name] = self._convert_parameter_value(param, value)
            elif not param.required and param.default is not None:
                validated[param_name] = param.default
        
        return validated
    
    def _convert_parameter_value(self, param: FunctionParameter, value: Any) -> Any:
        """Convert and validate parameter value"""
        if value is None:
            if param.required:
                raise ValueError(f"Required parameter {param.name} cannot be None")
            return None
        
        # Type conversion
        try:
            if param.type == ParameterType.STRING:
                return str(value)
            elif param.type == ParameterType.INTEGER:
                return int(value)
            elif param.type == ParameterType.NUMBER:
                return float(value)
            elif param.type == ParameterType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            elif param.type == ParameterType.ARRAY:
                if not isinstance(value, list):
                    raise ValueError(f"Expected list for {param.name}, got {type(value)}")
                return value
            elif param.type == ParameterType.OBJECT:
                if not isinstance(value, dict):
                    raise ValueError(f"Expected dict for {param.name}, got {type(value)}")
                return value
            else:
                return value
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for parameter {param.name}: {e}")
    
    def create_function_call_prompt(self, available_functions: List[str]) -> str:
        """Create a prompt describing available functions for the LLM"""
        if not available_functions:
            return "No functions are currently available."
        
        prompt_parts = ["You have access to the following functions:"]
        
        for func_name in available_functions:
            if func_name in self._schemas:
                schema = self._schemas[func_name]
                prompt_parts.append(f"\n{func_name}: {schema.description}")
                
                if schema.parameters:
                    prompt_parts.append("Parameters:")
                    for param in schema.parameters:
                        required_str = "required" if param.required else "optional"
                        prompt_parts.append(f"  - {param.name} ({param.type.value}, {required_str}): {param.description}")
        
        prompt_parts.append("\nTo call a function, respond with JSON in this format:")
        prompt_parts.append('{"function_call": {"name": "function_name", "arguments": {"param1": "value1"}}}')
        
        return "\n".join(prompt_parts)


# Utility decorators for easy function registration
def llm_function(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameter_descriptions: Optional[Dict[str, str]] = None
):
    """
    Decorator to mark functions for LLM calling.
    
    Args:
        name: Optional custom function name
        description: Function description
        parameter_descriptions: Parameter descriptions
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function for later registration
        func._llm_function_name = name
        func._llm_function_description = description
        func._llm_parameter_descriptions = parameter_descriptions
        return func
    
    return decorator


def auto_register_functions(handler: FunctionCallHandler, module_or_object: Any):
    """
    Automatically register all functions marked with @llm_function decorator.
    
    Args:
        handler: Function call handler
        module_or_object: Module or object to scan for functions
    """
    functions_registered = 0
    
    for attr_name in dir(module_or_object):
        attr = getattr(module_or_object, attr_name)
        
        if callable(attr) and hasattr(attr, "_llm_function_name"):
            name = attr._llm_function_name or attr.__name__
            description = attr._llm_function_description
            param_descriptions = attr._llm_parameter_descriptions
            
            handler.register_function(attr, name, description, param_descriptions)
            functions_registered += 1
    
    logger.info(f"Auto-registered {functions_registered} functions from {module_or_object}")


# Example usage functions for testing
@llm_function(
    description="Get current weather information for a location",
    parameter_descriptions={
        "location": "City name or coordinates",
        "units": "Temperature units (celsius, fahrenheit)"
    }
)
async def get_weather(location: str, units: str = "celsius") -> Dict[str, Any]:
    """Example weather function for testing"""
    return {
        "location": location,
        "temperature": 22,
        "condition": "sunny",
        "units": units
    }


@llm_function(
    description="Calculate the sum of two numbers",
    parameter_descriptions={
        "a": "First number",
        "b": "Second number"
    }
)
def calculate_sum(a: float, b: float) -> float:
    """Example calculation function for testing"""
    return a + b