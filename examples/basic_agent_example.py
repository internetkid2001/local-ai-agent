#!/usr/bin/env python3
"""
Basic AI Agent Implementation
A simple local AI agent that demonstrates core functionality
"""

import asyncio
import json
import logging
import requests
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    """Represents a function call to be executed"""
    tool_name: str
    arguments: Dict[str, Any]
    
@dataclass
class AgentResponse:
    """Response from the agent"""
    content: str
    tool_calls: List[ToolCall] = None
    error: str = None

class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, base_url="http://localhost:11434", model="llama3.1:8b"):
        self.base_url = base_url
        self.model = model
        self.conversation_history = []
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def chat(self, message: str, tools: List[Dict] = None) -> AgentResponse:
        """Send a chat message with optional function calling"""
        try:
            self.add_message("user", message)
            
            payload = {
                "model": self.model,
                "messages": self.conversation_history,
                "stream": False
            }
            
            if tools:
                payload["tools"] = tools
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "message" in result:
                assistant_message = result["message"]
                content = assistant_message.get("content", "")
                
                self.add_message("assistant", content)
                
                # Check for tool calls
                tool_calls = []
                if "tool_calls" in assistant_message:
                    for call in assistant_message["tool_calls"]:
                        tool_calls.append(ToolCall(
                            tool_name=call["function"]["name"],
                            arguments=call["function"]["arguments"]
                        ))
                
                return AgentResponse(
                    content=content,
                    tool_calls=tool_calls if tool_calls else None
                )
            
            return AgentResponse(
                content="",
                error="No message in response"
            )
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return AgentResponse(
                content="",
                error=str(e)
            )
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

class FileSystemTools:
    """Basic file system operations"""
    
    def __init__(self, allowed_paths: List[str] = None):
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
    
    def _validate_path(self, path: str) -> bool:
        """Check if path is within allowed directories"""
        if not self.allowed_paths:
            return True  # No restrictions if not specified
            
        resolved_path = Path(path).resolve()
        return any(
            str(resolved_path).startswith(str(allowed))
            for allowed in self.allowed_paths
        )
    
    def read_file(self, path: str) -> str:
        """Read contents of a file"""
        try:
            if not self._validate_path(path):
                return f"Error: Path '{path}' is not allowed"
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"File contents of {path}:\n{content}"
            
        except FileNotFoundError:
            return f"Error: File '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied for '{path}'"
        except Exception as e:
            return f"Error reading file: {e}"
    
    def list_directory(self, directory: str = ".") -> str:
        """List files in a directory"""
        try:
            if not self._validate_path(directory):
                return f"Error: Directory '{directory}' is not allowed"
            
            path = Path(directory)
            if not path.exists():
                return f"Error: Directory '{directory}' does not exist"
            
            if not path.is_dir():
                return f"Error: '{directory}' is not a directory"
            
            files = []
            for item in sorted(path.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else 0
                files.append(f"{item_type:4} {size:>8} {item.name}")
            
            return f"Contents of {directory}:\n" + "\n".join(files)
            
        except PermissionError:
            return f"Error: Permission denied for '{directory}'"
        except Exception as e:
            return f"Error listing directory: {e}"
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to a file"""
        try:
            if not self._validate_path(path):
                return f"Error: Path '{path}' is not allowed"
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully wrote to {path}"
            
        except PermissionError:
            return f"Error: Permission denied for '{path}'"
        except Exception as e:
            return f"Error writing file: {e}"

class BasicAIAgent:
    """A simple AI agent with file system capabilities"""
    
    def __init__(self, model="llama3.1:8b", allowed_paths=None):
        self.ollama = OllamaClient(model=model)
        self.fs_tools = FileSystemTools(allowed_paths)
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict]:
        """Define available tools for the agent"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files and directories in a given path",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory path to list (default: current directory)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to write"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call and return the result"""
        try:
            if tool_call.tool_name == "read_file":
                return self.fs_tools.read_file(tool_call.arguments["path"])
            
            elif tool_call.tool_name == "list_directory":
                directory = tool_call.arguments.get("directory", ".")
                return self.fs_tools.list_directory(directory)
            
            elif tool_call.tool_name == "write_file":
                return self.fs_tools.write_file(
                    tool_call.arguments["path"],
                    tool_call.arguments["content"]
                )
            
            else:
                return f"Unknown tool: {tool_call.tool_name}"
                
        except Exception as e:
            return f"Error executing {tool_call.tool_name}: {e}"
    
    def chat(self, message: str) -> str:
        """Main chat interface"""
        logger.info(f"User: {message}")
        
        # Get response from LLM
        response = self.ollama.chat(message, self.tools)
        
        if response.error:
            return f"Error: {response.error}"
        
        # Execute any tool calls
        if response.tool_calls:
            results = []
            for tool_call in response.tool_calls:
                logger.info(f"Executing tool: {tool_call.tool_name}")
                result = self.execute_tool(tool_call)
                results.append(f"Tool '{tool_call.tool_name}' result:\n{result}")
            
            # Add tool results to conversation
            tool_results = "\n\n".join(results)
            self.ollama.add_message("user", f"Tool execution results:\n{tool_results}")
            
            # Get final response incorporating tool results
            final_response = self.ollama.chat(
                "Based on the tool results above, provide a helpful summary or response to the user."
            )
            
            return final_response.content if not final_response.error else f"Error: {final_response.error}"
        
        return response.content

def main():
    """Main function to run the basic agent"""
    print("=== Basic AI Agent ===")
    print("A simple local AI agent with file system capabilities")
    print("Allowed operations: read_file, list_directory, write_file")
    print("Type 'quit' to exit\n")
    
    # Initialize agent with safe paths
    allowed_paths = [
        "/home/vic/Documents",
        "/home/vic/Downloads",
        "/tmp"
    ]
    
    agent = BasicAIAgent(allowed_paths=allowed_paths)
    
    # Check if Ollama is available
    try:
        test_response = agent.ollama.chat("Hello")
        if test_response.error:
            print(f"Error connecting to Ollama: {test_response.error}")
            print("Make sure Ollama is running: ollama serve")
            return
    except Exception as e:
        print(f"Failed to connect to Ollama: {e}")
        print("Make sure Ollama is installed and running")
        return
    
    print("Agent ready! You can ask me to:")
    print("- Read files: 'read the file /home/vic/Documents/test.txt'")
    print("- List directories: 'show me files in /home/vic/Downloads'")
    print("- Write files: 'create a file called hello.txt with the content Hello World'")
    print()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            response = agent.chat(user_input)
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()