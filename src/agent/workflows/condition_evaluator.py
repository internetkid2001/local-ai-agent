"""
Condition Evaluator

Evaluates conditional expressions in workflows for step execution control.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import re
import ast
import operator
from typing import Dict, Any, Union
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ConditionEvaluator:
    """
    Evaluates conditional expressions for workflow control.
    
    Supports:
    - Variable comparisons (==, !=, <, >, <=, >=)
    - Logical operations (and, or, not)
    - Existence checks (exists, not_exists)
    - Pattern matching (contains, starts_with, ends_with)
    - Type checking (is_number, is_string, is_empty)
    - Safe Python expression evaluation
    """
    
    def __init__(self):
        """Initialize condition evaluator"""
        self.operators = {
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '>': operator.gt,
            '<=': operator.le,
            '>=': operator.ge,
            'in': operator.contains,
            'not_in': lambda x, y: not operator.contains(y, x)
        }
        
        self.logical_operators = {
            'and': operator.and_,
            'or': operator.or_,
            'not': operator.not_
        }
        
        logger.info("Condition evaluator initialized")
    
    async def evaluate(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression.
        
        Args:
            condition: Condition string to evaluate
            context: Variable context
            
        Returns:
            Boolean result of condition evaluation
        """
        try:
            condition = condition.strip()
            logger.debug(f"Evaluating condition: {condition}")
            
            # Handle special functions
            if self._is_function_call(condition):
                return await self._evaluate_function(condition, context)
            
            # Handle logical operations (and, or)
            if ' and ' in condition or ' or ' in condition:
                return await self._evaluate_logical_expression(condition, context)
            
            # Handle comparison operations
            for op_str, op_func in self.operators.items():
                if f' {op_str} ' in condition:
                    return await self._evaluate_comparison(condition, op_str, op_func, context)
            
            # Handle single variable (truthiness check)
            if condition in context:
                return bool(context[condition])
            
            # Handle literal values
            if condition.lower() in ['true', 'false']:
                return condition.lower() == 'true'
            
            # Try safe Python evaluation as last resort
            return await self._safe_eval(condition, context)
            
        except Exception as e:
            logger.error(f"Condition evaluation failed: {condition} - {e}")
            return False
    
    def _is_function_call(self, condition: str) -> bool:
        """Check if condition is a function call"""
        function_patterns = [
            r'^exists\(',
            r'^not_exists\(',
            r'^contains\(',
            r'^starts_with\(',
            r'^ends_with\(',
            r'^is_number\(',
            r'^is_string\(',
            r'^is_empty\(',
            r'^matches\('
        ]
        
        return any(re.match(pattern, condition) for pattern in function_patterns)
    
    async def _evaluate_function(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate function-style conditions"""
        # Extract function name and arguments
        match = re.match(r'^(\w+)\((.*)\)$', condition)
        if not match:
            return False
        
        func_name, args_str = match.groups()
        args = [arg.strip().strip('"\'') for arg in args_str.split(',') if arg.strip()]
        
        if func_name == 'exists':
            return len(args) > 0 and args[0] in context
        
        elif func_name == 'not_exists':
            return len(args) > 0 and args[0] not in context
        
        elif func_name == 'contains' and len(args) >= 2:
            var_name, substring = args[0], args[1]
            if var_name in context:
                return substring in str(context[var_name])
            return False
        
        elif func_name == 'starts_with' and len(args) >= 2:
            var_name, prefix = args[0], args[1]
            if var_name in context:
                return str(context[var_name]).startswith(prefix)
            return False
        
        elif func_name == 'ends_with' and len(args) >= 2:
            var_name, suffix = args[0], args[1]
            if var_name in context:
                return str(context[var_name]).endswith(suffix)
            return False
        
        elif func_name == 'is_number' and len(args) > 0:
            var_name = args[0]
            if var_name in context:
                try:
                    float(context[var_name])
                    return True
                except (ValueError, TypeError):
                    return False
            return False
        
        elif func_name == 'is_string' and len(args) > 0:
            var_name = args[0]
            if var_name in context:
                return isinstance(context[var_name], str)
            return False
        
        elif func_name == 'is_empty' and len(args) > 0:
            var_name = args[0]
            if var_name in context:
                value = context[var_name]
                return value is None or value == "" or (hasattr(value, '__len__') and len(value) == 0)
            return True
        
        elif func_name == 'matches' and len(args) >= 2:
            var_name, pattern = args[0], args[1]
            if var_name in context:
                return bool(re.search(pattern, str(context[var_name])))
            return False
        
        return False
    
    async def _evaluate_logical_expression(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate logical expressions with and/or"""
        # Split on 'and' and 'or' while preserving operator precedence
        # For simplicity, we'll process left to right (could be enhanced)
        
        if ' or ' in condition:
            parts = condition.split(' or ')
            for part in parts:
                if await self.evaluate(part.strip(), context):
                    return True
            return False
        
        elif ' and ' in condition:
            parts = condition.split(' and ')
            for part in parts:
                if not await self.evaluate(part.strip(), context):
                    return False
            return True
        
        return False
    
    async def _evaluate_comparison(self, condition: str, op_str: str, op_func, context: Dict[str, Any]) -> bool:
        """Evaluate comparison operations"""
        parts = condition.split(f' {op_str} ', 1)
        if len(parts) != 2:
            return False
        
        left_expr, right_expr = parts[0].strip(), parts[1].strip()
        
        # Get left value
        left_value = await self._resolve_value(left_expr, context)
        
        # Get right value
        right_value = await self._resolve_value(right_expr, context)
        
        # Type coercion for comparison
        left_value, right_value = self._coerce_types(left_value, right_value)
        
        # Perform comparison
        try:
            if op_str == 'in':
                return op_func(left_value, right_value)
            elif op_str == 'not_in':
                return op_func(left_value, right_value)
            else:
                return op_func(left_value, right_value)
        except Exception as e:
            logger.warning(f"Comparison failed: {left_value} {op_str} {right_value} - {e}")
            return False
    
    async def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """Resolve an expression to its value"""
        expr = expr.strip()
        
        # Check if it's a variable
        if expr in context:
            return context[expr]
        
        # Check if it's a quoted string
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        # Check if it's a number
        try:
            if '.' in expr:
                return float(expr)
            else:
                return int(expr)
        except ValueError:
            pass
        
        # Check if it's a boolean
        if expr.lower() == 'true':
            return True
        elif expr.lower() == 'false':
            return False
        elif expr.lower() == 'null' or expr.lower() == 'none':
            return None
        
        # Return as string if nothing else matches
        return expr
    
    def _coerce_types(self, left: Any, right: Any) -> tuple:
        """Coerce types for comparison"""
        # If both are already the same type, return as-is
        if type(left) == type(right):
            return left, right
        
        # Try to convert to numbers if possible
        try:
            if isinstance(left, str) and isinstance(right, (int, float)):
                return float(left), right
            elif isinstance(right, str) and isinstance(left, (int, float)):
                return left, float(right)
        except ValueError:
            pass
        
        # Convert both to strings for string comparison
        return str(left), str(right)
    
    async def _safe_eval(self, expression: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate Python expressions"""
        try:
            # Create a restricted environment
            safe_dict = {
                '__builtins__': {},
                'True': True,
                'False': False,
                'None': None
            }
            
            # Add context variables
            safe_dict.update(context)
            
            # Parse the expression to check for dangerous operations
            tree = ast.parse(expression, mode='eval')
            
            # Check for forbidden node types
            forbidden_nodes = (
                ast.Import, ast.ImportFrom, ast.Call, ast.Attribute,
                ast.Exec, ast.Global, ast.FunctionDef, ast.ClassDef
            )
            
            for node in ast.walk(tree):
                if isinstance(node, forbidden_nodes):
                    logger.warning(f"Forbidden operation in expression: {expression}")
                    return False
            
            # Evaluate the expression
            result = eval(expression, safe_dict)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Safe eval failed: {expression} - {e}")
            return False
    
    def validate_condition_syntax(self, condition: str) -> tuple[bool, str]:
        """
        Validate condition syntax.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            condition = condition.strip()
            
            if not condition:
                return False, "Empty condition"
            
            # Check for balanced parentheses
            if condition.count('(') != condition.count(')'):
                return False, "Unbalanced parentheses"
            
            # Check for valid operators
            valid_operators = ['==', '!=', '<', '>', '<=', '>=', 'and', 'or', 'not', 'in', 'not_in']
            has_operator = any(op in condition for op in valid_operators)
            
            # Check if it's a function call
            is_function = self._is_function_call(condition)
            
            # Check if it's a simple variable
            is_variable = condition.isidentifier()
            
            if not (has_operator or is_function or is_variable or condition.lower() in ['true', 'false']):
                return False, "No valid operator, function, or variable found"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)