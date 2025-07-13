"""
Workflow Templates

Pre-built workflow templates for common automation scenarios.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .workflow_engine import WorkflowDefinition, WorkflowStep
from .step_executor import StepType
from .workflow_parser import WorkflowParser


@dataclass
class TemplateParameter:
    """Template parameter definition"""
    name: str
    description: str
    type: str = "string"
    required: bool = True
    default: Any = None


class WorkflowTemplates:
    """
    Collection of pre-built workflow templates.
    
    Templates can be instantiated with parameters to create specific workflows.
    """
    
    def __init__(self):
        """Initialize workflow templates"""
        self.parser = WorkflowParser()
        self.templates = self._load_builtin_templates()
    
    def _load_builtin_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load built-in workflow templates"""
        templates = {}
        
        # File Analysis Workflow
        templates['file_analysis'] = {
            'name': 'File Analysis Workflow',
            'description': 'Analyze files in a directory and generate a report',
            'parameters': [
                TemplateParameter('directory_path', 'Directory to analyze', required=True),
                TemplateParameter('file_types', 'File types to include (e.g., .py,.js)', default='*'),
                TemplateParameter('output_file', 'Output report file', default='analysis_report.txt')
            ],
            'template': {
                'name': 'File Analysis Workflow',
                'description': 'Analyze files and generate report',
                'steps': [
                    {
                        'id': 'list_files',
                        'name': 'List Files',
                        'type': 'file_operation',
                        'action': 'list_directory',
                        'parameters': {
                            'path': '{directory_path}',
                            'recursive': True,
                            'file_types': '{file_types}'
                        }
                    },
                    {
                        'id': 'analyze_files',
                        'name': 'Analyze Files',
                        'type': 'llm_query',
                        'action': 'Analyze the file list: {list_files.result} and provide insights about file structure, types, and organization',
                        'dependencies': ['list_files']
                    },
                    {
                        'id': 'generate_report',
                        'name': 'Generate Report',
                        'type': 'file_operation',
                        'action': 'write_file',
                        'parameters': {
                            'path': '{output_file}',
                            'content': 'File Analysis Report\n\n{analyze_files.response}'
                        },
                        'dependencies': ['analyze_files']
                    }
                ]
            }
        }
        
        # Code Generation Workflow
        templates['code_generation'] = {
            'name': 'Code Generation Workflow',
            'description': 'Generate code based on requirements and save to file',
            'parameters': [
                TemplateParameter('requirements', 'Code requirements/description', required=True),
                TemplateParameter('language', 'Programming language', default='python'),
                TemplateParameter('output_file', 'Output code file', required=True),
                TemplateParameter('run_tests', 'Run tests after generation', type='boolean', default=False)
            ],
            'template': {
                'name': 'Code Generation Workflow',
                'description': 'Generate and save code',
                'steps': [
                    {
                        'id': 'generate_code',
                        'name': 'Generate Code',
                        'type': 'llm_query',
                        'action': 'Generate {language} code based on these requirements: {requirements}. Provide only the code without explanations.',
                        'parameters': {
                            'model_type': 'code'
                        }
                    },
                    {
                        'id': 'save_code',
                        'name': 'Save Code',
                        'type': 'file_operation',
                        'action': 'write_file',
                        'parameters': {
                            'path': '{output_file}',
                            'content': '{generate_code.response}'
                        },
                        'dependencies': ['generate_code']
                    },
                    {
                        'id': 'run_tests',
                        'name': 'Run Tests',
                        'type': 'system_command',
                        'action': 'python -m pytest {output_file}',
                        'conditions': ['{run_tests} == true'],
                        'dependencies': ['save_code']
                    }
                ]
            }
        }
        
        # System Monitoring Workflow
        templates['system_monitoring'] = {
            'name': 'System Monitoring Workflow',
            'description': 'Monitor system resources and generate alerts',
            'parameters': [
                TemplateParameter('cpu_threshold', 'CPU usage threshold (%)', type='number', default=80),
                TemplateParameter('memory_threshold', 'Memory usage threshold (%)', type='number', default=85),
                TemplateParameter('check_interval', 'Check interval (seconds)', type='number', default=60),
                TemplateParameter('alert_file', 'Alert output file', default='system_alerts.log')
            ],
            'template': {
                'name': 'System Monitoring Workflow',
                'description': 'Monitor system and generate alerts',
                'steps': [
                    {
                        'id': 'get_cpu_stats',
                        'name': 'Get CPU Stats',
                        'type': 'mcp_tool',
                        'action': 'get_cpu_stats',
                        'parameters': {
                            'client_type': 'system'
                        }
                    },
                    {
                        'id': 'get_memory_stats',
                        'name': 'Get Memory Stats',
                        'type': 'mcp_tool',
                        'action': 'get_memory_stats',
                        'parameters': {
                            'client_type': 'system'
                        },
                        'parallel_group': 'stats_collection'
                    },
                    {
                        'id': 'check_cpu_alert',
                        'name': 'Check CPU Alert',
                        'type': 'conditional',
                        'action': '{get_cpu_stats.cpu_percent} > {cpu_threshold}',
                        'dependencies': ['get_cpu_stats']
                    },
                    {
                        'id': 'check_memory_alert',
                        'name': 'Check Memory Alert',
                        'type': 'conditional',
                        'action': '{get_memory_stats.memory_percent} > {memory_threshold}',
                        'dependencies': ['get_memory_stats']
                    },
                    {
                        'id': 'generate_alert',
                        'name': 'Generate Alert',
                        'type': 'file_operation',
                        'action': 'append_file',
                        'parameters': {
                            'path': '{alert_file}',
                            'content': 'ALERT: High resource usage detected at {timestamp}\\nCPU: {get_cpu_stats.cpu_percent}%\\nMemory: {get_memory_stats.memory_percent}%\\n\\n'
                        },
                        'conditions': ['{check_cpu_alert.condition_result} == true or {check_memory_alert.condition_result} == true'],
                        'dependencies': ['check_cpu_alert', 'check_memory_alert']
                    }
                ]
            }
        }
        
        # Desktop Automation Workflow
        templates['desktop_automation'] = {
            'name': 'Desktop Automation Workflow',
            'description': 'Automate desktop tasks like taking screenshots and managing windows',
            'parameters': [
                TemplateParameter('window_title', 'Window title to focus', required=True),
                TemplateParameter('screenshot_path', 'Screenshot save path', default='screenshot.png'),
                TemplateParameter('text_to_type', 'Text to type in window', default=''),
                TemplateParameter('wait_seconds', 'Wait time between actions', type='number', default=2)
            ],
            'template': {
                'name': 'Desktop Automation Workflow',
                'description': 'Automate desktop interactions',
                'steps': [
                    {
                        'id': 'take_initial_screenshot',
                        'name': 'Take Initial Screenshot',
                        'type': 'desktop_action',
                        'action': 'take_screenshot',
                        'parameters': {
                            'client_type': 'desktop',
                            'path': 'before_{screenshot_path}'
                        }
                    },
                    {
                        'id': 'focus_window',
                        'name': 'Focus Target Window',
                        'type': 'desktop_action',
                        'action': 'focus_window',
                        'parameters': {
                            'client_type': 'desktop',
                            'title': '{window_title}'
                        },
                        'dependencies': ['take_initial_screenshot']
                    },
                    {
                        'id': 'wait_after_focus',
                        'name': 'Wait After Focus',
                        'type': 'wait',
                        'action': '',
                        'parameters': {
                            'duration': '{wait_seconds}'
                        },
                        'dependencies': ['focus_window']
                    },
                    {
                        'id': 'type_text',
                        'name': 'Type Text',
                        'type': 'desktop_action',
                        'action': 'type_text',
                        'parameters': {
                            'client_type': 'desktop',
                            'text': '{text_to_type}'
                        },
                        'conditions': ['not_empty(text_to_type)'],
                        'dependencies': ['wait_after_focus']
                    },
                    {
                        'id': 'take_final_screenshot',
                        'name': 'Take Final Screenshot',
                        'type': 'desktop_action',
                        'action': 'take_screenshot',
                        'parameters': {
                            'client_type': 'desktop',
                            'path': '{screenshot_path}'
                        },
                        'dependencies': ['wait_after_focus']
                    }
                ]
            }
        }
        
        # Data Processing Pipeline
        templates['data_processing'] = {
            'name': 'Data Processing Pipeline',
            'description': 'Process data files through analysis and transformation',
            'parameters': [
                TemplateParameter('input_file', 'Input data file', required=True),
                TemplateParameter('output_file', 'Output processed file', required=True),
                TemplateParameter('processing_type', 'Type of processing (analyze, transform, summarize)', default='analyze'),
                TemplateParameter('backup_original', 'Backup original file', type='boolean', default=True)
            ],
            'template': {
                'name': 'Data Processing Pipeline',
                'description': 'Process and transform data files',
                'steps': [
                    {
                        'id': 'backup_file',
                        'name': 'Backup Original File',
                        'type': 'file_operation',
                        'action': 'copy_file',
                        'parameters': {
                            'source': '{input_file}',
                            'destination': '{input_file}.backup'
                        },
                        'conditions': ['{backup_original} == true']
                    },
                    {
                        'id': 'read_data',
                        'name': 'Read Input Data',
                        'type': 'file_operation',
                        'action': 'read_file',
                        'parameters': {
                            'path': '{input_file}'
                        }
                    },
                    {
                        'id': 'validate_data',
                        'name': 'Validate Data',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'not_empty',
                            'target': 'read_data.content'
                        },
                        'dependencies': ['read_data']
                    },
                    {
                        'id': 'process_data',
                        'name': 'Process Data',
                        'type': 'llm_query',
                        'action': 'Perform {processing_type} on this data: {read_data.content}',
                        'dependencies': ['validate_data']
                    },
                    {
                        'id': 'save_result',
                        'name': 'Save Processed Data',
                        'type': 'file_operation',
                        'action': 'write_file',
                        'parameters': {
                            'path': '{output_file}',
                            'content': '{process_data.response}'
                        },
                        'dependencies': ['process_data']
                    },
                    {
                        'id': 'verify_output',
                        'name': 'Verify Output',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'exists',
                            'target': 'save_result.success'
                        },
                        'dependencies': ['save_result']
                    }
                ]
            }
        }
        
        # Web Search Workflow
        templates['web_search_research'] = {
            'name': 'Web Search Research Workflow',
            'description': 'Comprehensive web research using multiple search providers',
            'parameters': [
                TemplateParameter('search_query', 'Search query or research topic', required=True),
                TemplateParameter('max_results', 'Maximum results per provider', type='number', default=10),
                TemplateParameter('providers', 'Search providers to use (comma-separated)', default='duckduckgo,brave'),
                TemplateParameter('output_format', 'Output format (summary, detailed, json)', default='summary')
            ],
            'template': {
                'name': 'Web Search Research Workflow',
                'description': 'Multi-provider web search and analysis',
                'steps': [
                    {
                        'id': 'search_duckduckgo',
                        'name': 'Search DuckDuckGo',
                        'type': 'external_service',
                        'action': 'web_search',
                        'parameters': {
                            'service_id': 'duckduckgo',
                            'query': '{search_query}',
                            'max_results': '{max_results}',
                            'provider': 'duckduckgo'
                        },
                        'conditions': ['contains(providers, "duckduckgo")']
                    },
                    {
                        'id': 'search_brave',
                        'name': 'Search Brave',
                        'type': 'external_service', 
                        'action': 'web_search',
                        'parameters': {
                            'service_id': 'brave_search',
                            'query': '{search_query}',
                            'max_results': '{max_results}',
                            'provider': 'brave'
                        },
                        'conditions': ['contains(providers, "brave")'],
                        'parallel_group': 'search_providers'
                    },
                    {
                        'id': 'aggregate_results',
                        'name': 'Aggregate Search Results',
                        'type': 'transformation',
                        'action': '',
                        'parameters': {
                            'type': 'aggregate',
                            'sources': ['search_duckduckgo.results', 'search_brave.results'],
                            'target': 'aggregated_results'
                        },
                        'dependencies': ['search_duckduckgo', 'search_brave']
                    },
                    {
                        'id': 'analyze_results',
                        'name': 'Analyze Search Results',
                        'type': 'llm_query',
                        'action': 'Analyze these search results for "{search_query}" and provide key insights: {aggregated_results}',
                        'parameters': {
                            'model_type': 'primary'
                        },
                        'dependencies': ['aggregate_results']
                    },
                    {
                        'id': 'format_output',
                        'name': 'Format Final Output',
                        'type': 'transformation',
                        'action': '',
                        'parameters': {
                            'type': 'format',
                            'template': 'Research Results for "{search_query}":\n\nAnalysis: {analyze_results.response}\n\nSources: {aggregated_results}',
                            'target': 'final_report'
                        },
                        'dependencies': ['analyze_results']
                    }
                ]
            }
        }
        
        # API Integration Workflow
        templates['api_data_integration'] = {
            'name': 'API Data Integration Workflow',
            'description': 'Fetch and process data from external APIs',
            'parameters': [
                TemplateParameter('api_service', 'API service identifier', required=True),
                TemplateParameter('endpoint', 'API endpoint to call', required=True),
                TemplateParameter('api_method', 'HTTP method', default='GET'),
                TemplateParameter('api_params', 'API parameters (JSON)', default='{}'),
                TemplateParameter('processing_type', 'Data processing type', default='analyze')
            ],
            'template': {
                'name': 'API Data Integration Workflow',
                'description': 'Fetch, process, and analyze API data',
                'steps': [
                    {
                        'id': 'validate_service',
                        'name': 'Validate API Service',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'exists',
                            'target': 'api_service'
                        }
                    },
                    {
                        'id': 'call_api',
                        'name': 'Call External API',
                        'type': 'external_service',
                        'action': 'api_request',
                        'parameters': {
                            'service_id': '{api_service}',
                            'endpoint': '{endpoint}',
                            'method': '{api_method}',
                            'params': '{api_params}'
                        },
                        'dependencies': ['validate_service'],
                        'retry_count': 3
                    },
                    {
                        'id': 'validate_response',
                        'name': 'Validate API Response',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'not_empty',
                            'target': 'call_api.data'
                        },
                        'dependencies': ['call_api']
                    },
                    {
                        'id': 'process_data',
                        'name': 'Process API Data',
                        'type': 'llm_query',
                        'action': 'Process and {processing_type} this API data: {call_api.data}',
                        'parameters': {
                            'model_type': 'primary'
                        },
                        'dependencies': ['validate_response']
                    },
                    {
                        'id': 'store_results',
                        'name': 'Store Processed Results',
                        'type': 'file_operation',
                        'action': 'write_file',
                        'parameters': {
                            'path': '/tmp/api_results_{api_service}_{timestamp}.json',
                            'content': '{"api_data": {call_api.data}, "analysis": "{process_data.response}", "timestamp": "{timestamp}"}'
                        },
                        'dependencies': ['process_data']
                    }
                ]
            }
        }
        
        # Database Query Workflow
        templates['database_analysis'] = {
            'name': 'Database Analysis Workflow', 
            'description': 'Query database and analyze results',
            'parameters': [
                TemplateParameter('database_id', 'Database service identifier', required=True),
                TemplateParameter('sql_query', 'SQL query to execute', required=True),
                TemplateParameter('analysis_focus', 'Analysis focus area', default='general trends'),
                TemplateParameter('output_chart', 'Generate chart visualization', type='boolean', default=False)
            ],
            'template': {
                'name': 'Database Analysis Workflow',
                'description': 'Query database and perform data analysis',
                'steps': [
                    {
                        'id': 'validate_query',
                        'name': 'Validate SQL Query',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'not_empty',
                            'target': 'sql_query'
                        }
                    },
                    {
                        'id': 'execute_query',
                        'name': 'Execute Database Query',
                        'type': 'external_service',
                        'action': 'database_query',
                        'parameters': {
                            'service_id': '{database_id}',
                            'query': '{sql_query}',
                            'timeout': 60
                        },
                        'dependencies': ['validate_query'],
                        'retry_count': 2
                    },
                    {
                        'id': 'validate_results',
                        'name': 'Validate Query Results',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'not_empty',
                            'target': 'execute_query.rows'
                        },
                        'dependencies': ['execute_query']
                    },
                    {
                        'id': 'analyze_data',
                        'name': 'Analyze Database Results',
                        'type': 'llm_query',
                        'action': 'Analyze this database query result focusing on {analysis_focus}. Query: {sql_query}. Results: {execute_query.rows}',
                        'parameters': {
                            'model_type': 'primary'
                        },
                        'dependencies': ['validate_results']
                    },
                    {
                        'id': 'generate_summary',
                        'name': 'Generate Analysis Summary',
                        'type': 'transformation',
                        'action': '',
                        'parameters': {
                            'type': 'format',
                            'template': 'Database Analysis Report\n\nQuery: {sql_query}\nRows Returned: {execute_query.row_count}\n\nAnalysis:\n{analyze_data.response}',
                            'target': 'analysis_report'
                        },
                        'dependencies': ['analyze_data']
                    }
                ]
            }
        }
        
        # Multi-Service Data Pipeline
        templates['multi_service_pipeline'] = {
            'name': 'Multi-Service Data Pipeline',
            'description': 'Complex data pipeline using multiple external services',
            'parameters': [
                TemplateParameter('input_source', 'Initial data source (api, file, database)', required=True),
                TemplateParameter('source_params', 'Source parameters (JSON)', required=True),
                TemplateParameter('enrichment_apis', 'APIs for data enrichment (comma-separated)', default=''),
                TemplateParameter('output_destination', 'Output destination', default='file')
            ],
            'template': {
                'name': 'Multi-Service Data Pipeline',
                'description': 'Comprehensive data processing pipeline',
                'steps': [
                    {
                        'id': 'fetch_initial_data',
                        'name': 'Fetch Initial Data',
                        'type': 'external_service',
                        'action': 'data_fetch',
                        'parameters': {
                            'source': '{input_source}',
                            'params': '{source_params}'
                        }
                    },
                    {
                        'id': 'validate_data',
                        'name': 'Validate Initial Data',
                        'type': 'validation',
                        'action': '',
                        'parameters': {
                            'type': 'not_empty',
                            'target': 'fetch_initial_data.data'
                        },
                        'dependencies': ['fetch_initial_data']
                    },
                    {
                        'id': 'enrich_data',
                        'name': 'Enrich Data with External APIs',
                        'type': 'loop',
                        'action': 'external_service_call',
                        'parameters': {
                            'type': 'foreach',
                            'items': '{enrichment_apis}',
                            'action': 'api_enrich',
                            'data_source': 'fetch_initial_data.data'
                        },
                        'dependencies': ['validate_data'],
                        'conditions': ['not_empty(enrichment_apis)']
                    },
                    {
                        'id': 'process_enriched_data',
                        'name': 'Process Enriched Data',
                        'type': 'llm_query',
                        'action': 'Process and analyze this enriched dataset: {enrich_data.results}. Original data: {fetch_initial_data.data}',
                        'parameters': {
                            'model_type': 'primary'
                        },
                        'dependencies': ['enrich_data']
                    },
                    {
                        'id': 'generate_insights',
                        'name': 'Generate Data Insights',
                        'type': 'llm_query',
                        'action': 'Generate key insights and recommendations from this processed data: {process_enriched_data.response}',
                        'parameters': {
                            'model_type': 'primary'
                        },
                        'dependencies': ['process_enriched_data']
                    },
                    {
                        'id': 'output_results',
                        'name': 'Output Final Results',
                        'type': 'file_operation',
                        'action': 'write_file',
                        'parameters': {
                            'path': '/tmp/pipeline_results_{timestamp}.json',
                            'content': '{"source": "{input_source}", "processed_data": {process_enriched_data.response}, "insights": "{generate_insights.response}", "metadata": {"timestamp": "{timestamp}", "enrichment_apis": "{enrichment_apis}"}}'
                        },
                        'dependencies': ['generate_insights']
                    }
                ]
            }
        }
        
        return templates
    
    def get_template_list(self) -> List[Dict[str, str]]:
        """Get list of available templates"""
        return [
            {
                'name': template_id,
                'title': template['name'],
                'description': template['description']
            }
            for template_id, template in self.templates.items()
        ]
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a template"""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        return {
            'id': template_id,
            'name': template['name'],
            'description': template['description'],
            'parameters': [
                {
                    'name': param.name,
                    'description': param.description,
                    'type': param.type,
                    'required': param.required,
                    'default': param.default
                }
                for param in template['parameters']
            ]
        }
    
    def create_workflow_from_template(self, template_id: str, parameters: Dict[str, Any]) -> WorkflowDefinition:
        """
        Create a workflow instance from a template.
        
        Args:
            template_id: Template identifier
            parameters: Template parameters
            
        Returns:
            WorkflowDefinition instance
        """
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        
        # Validate required parameters
        template_params = {param.name: param for param in template['parameters']}
        for param_name, param_def in template_params.items():
            if param_def.required and param_name not in parameters:
                raise ValueError(f"Required parameter missing: {param_name}")
            
            # Set default values
            if param_name not in parameters and param_def.default is not None:
                parameters[param_name] = param_def.default
        
        # Substitute parameters in template
        workflow_dict = self._substitute_parameters(template['template'], parameters)
        
        # Add unique ID
        workflow_dict['id'] = str(uuid.uuid4())
        
        # Parse to workflow definition
        workflow = self.parser.parse_from_dict(workflow_dict)
        
        return workflow
    
    def _substitute_parameters(self, template_dict: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively substitute parameters in template"""
        if isinstance(template_dict, dict):
            result = {}
            for key, value in template_dict.items():
                result[key] = self._substitute_parameters(value, parameters)
            return result
        elif isinstance(template_dict, list):
            return [self._substitute_parameters(item, parameters) for item in template_dict]
        elif isinstance(template_dict, str):
            # Substitute {parameter} placeholders
            result = template_dict
            for param_name, param_value in parameters.items():
                placeholder = f'{{{param_name}}}'
                if placeholder in result:
                    result = result.replace(placeholder, str(param_value))
            return result
        else:
            return template_dict
    
    def add_custom_template(self, template_id: str, name: str, description: str,
                           parameters: List[TemplateParameter], template_dict: Dict[str, Any]):
        """Add a custom template"""
        self.templates[template_id] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'template': template_dict
        }
    
    def export_template(self, template_id: str, format: str = 'json') -> str:
        """Export template definition"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        
        if format == 'json':
            import json
            return json.dumps(template, indent=2, default=str)
        elif format == 'yaml':
            import yaml
            return yaml.dump(template, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def create_simple_workflow(self, name: str, steps: List[Dict[str, Any]]) -> WorkflowDefinition:
        """Create a simple workflow without templates"""
        workflow_dict = {
            'name': name,
            'description': f'Simple workflow: {name}',
            'steps': steps
        }
        
        return self.parser.parse_from_dict(workflow_dict)