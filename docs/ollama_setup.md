# Ollama Setup and Usage Guide

## Installation

### Linux Installation (Your System)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version
```

### AMD GPU Support (RX 6600 XT)
Ollama supports AMD GPUs through ROCm. Your RX 6600 XT should work well.

```bash
# Check if ROCm is detected
ollama list
# If GPU acceleration isn't working, install ROCm:
# sudo apt install rocm-opencl-dev
```

## Model Selection for Your Hardware

### Recommended Models for 31GB RAM + RX 6600 XT

#### Primary Recommendation: Llama 3.1 8B
```bash
ollama pull llama3.1:8b
# Size: ~4.7GB
# RAM usage: ~8-10GB
# Performance: Excellent for general tasks
```

#### Alternative Options:
```bash
# Mistral 7B - Fast and efficient
ollama pull mistral:7b

# CodeLlama 7B - Best for coding tasks
ollama pull codellama:7b

# Llama 3.1 8B Instruct - Better for following instructions
ollama pull llama3.1:8b-instruct

# Phi-3 Medium - Microsoft's efficient model
ollama pull phi3:14b
```

#### Large Models (with quantization):
```bash
# Llama 3.1 70B with heavy quantization (if you want to try)
ollama pull llama3.1:70b-q4_0
# Warning: Will use 35-40GB RAM, slower inference
```

## Basic Usage

### Starting Ollama Service
```bash
# Ollama runs as a service, but you can start it manually:
ollama serve

# Run in background:
nohup ollama serve > ollama.log 2>&1 &
```

### Interactive Chat
```bash
# Start chatting with a model
ollama run llama3.1:8b

# Exit with /bye or Ctrl+D
```

### API Usage
```bash
# Generate text via API
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

# Chat format
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "stream": false
}'
```

## Python Integration

### Basic Client
```python
import requests
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
    
    def generate(self, model, prompt, **kwargs):
        """Generate text from a prompt"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
        )
        return response.json()
    
    def chat(self, model, messages, **kwargs):
        """Chat with conversation history"""
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
        )
        return response.json()

# Usage
client = OllamaClient()
result = client.generate("llama3.1:8b", "Explain quantum physics")
print(result["response"])
```

### Advanced Client with Function Calling
```python
import requests
import json
from typing import List, Dict, Any

class OllamaAgent:
    def __init__(self, model="llama3.1:8b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.conversation_history = []
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def chat(self, message: str, tools: List[Dict] = None, **kwargs):
        """Send a chat message with optional tools"""
        self.add_message("user", message)
        
        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "stream": False,
            **kwargs
        }
        
        if tools:
            payload["tools"] = tools
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        
        result = response.json()
        
        if "message" in result:
            self.add_message("assistant", result["message"]["content"])
            
            # Handle tool calls
            if "tool_calls" in result["message"]:
                return result["message"]["tool_calls"]
        
        return result
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

# Example with function calling
tools = [
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
    }
]

agent = OllamaAgent()
response = agent.chat("Read the file /home/vic/test.txt", tools=tools)
```

## Performance Optimization

### GPU Acceleration Settings
```python
# Check GPU usage
import subprocess
result = subprocess.run(["rocm-smi"], capture_output=True, text=True)
print(result.stdout)
```

### Memory Management
```bash
# Monitor Ollama memory usage
ollama ps

# Set memory limits (if needed)
OLLAMA_MAX_LOADED_MODELS=1 ollama serve
```

### Model Configuration
```bash
# Create custom model with specific parameters
cat > Modelfile << EOF
FROM llama3.1:8b

# Set parameters for your hardware
PARAMETER num_ctx 4096          # Context length
PARAMETER num_gpu 1             # Use GPU
PARAMETER num_thread 8          # Use 8 CPU cores
PARAMETER temperature 0.7       # Creativity level
PARAMETER top_p 0.9            # Nucleus sampling
PARAMETER repeat_penalty 1.1   # Avoid repetition

# Custom system prompt for agent tasks
SYSTEM """
You are a helpful AI assistant that can control the local computer through function calls.
You have access to file operations, system commands, and desktop automation.
Always confirm before performing destructive operations.
Be precise and efficient in your responses.
"""
EOF

# Create the custom model
ollama create local-agent -f Modelfile
```

### Performance Monitoring
```python
import time
import psutil
import subprocess

class OllamaMonitor:
    def __init__(self):
        self.start_time = None
        
    def start_monitoring(self):
        self.start_time = time.time()
        
    def get_stats(self):
        # Get system stats
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Get GPU stats (AMD)
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmemuse", "--csv"], 
                capture_output=True, text=True
            )
            gpu_info = result.stdout
        except:
            gpu_info = "GPU info unavailable"
            
        return {
            "cpu_percent": cpu_percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_percent": memory.percent,
            "gpu_info": gpu_info,
            "uptime": time.time() - self.start_time if self.start_time else 0
        }

# Usage
monitor = OllamaMonitor()
monitor.start_monitoring()

# ... run your agent ...

stats = monitor.get_stats()
print(f"CPU: {stats['cpu_percent']}%")
print(f"Memory: {stats['memory_used_gb']:.1f}GB ({stats['memory_percent']}%)")
```

## Troubleshooting

### Common Issues

#### 1. Model Won't Load
```bash
# Check available space
df -h
# Check Ollama logs
journalctl -u ollama -f
# Clear model cache if needed
ollama rm llama3.1:8b
ollama pull llama3.1:8b
```

#### 2. Slow Performance
```bash
# Check if using GPU
ollama ps
# Should show GPU usage

# If CPU-only, install ROCm drivers
sudo apt update
sudo apt install rocm-opencl-dev rocm-smi
```

#### 3. Out of Memory
```bash
# Use smaller model
ollama pull llama3.1:8b-q4_0  # Quantized version

# Or adjust context size
OLLAMA_NUM_CTX=2048 ollama run llama3.1:8b
```

#### 4. Connection Issues
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart service
sudo systemctl restart ollama

# Check port
netstat -tlnp | grep 11434
```

### Debug Mode
```bash
# Run with debug logging
OLLAMA_DEBUG=1 ollama serve

# Check logs
tail -f ~/.ollama/logs/server.log
```

## Integration Examples

### Simple Agent Loop
```python
import asyncio
from ollama_client import OllamaAgent

async def main():
    agent = OllamaAgent("llama3.1:8b")
    
    print("Local AI Agent started. Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
            
        response = agent.chat(user_input)
        print(f"Agent: {response.get('message', {}).get('content', 'Error')}")

if __name__ == "__main__":
    asyncio.run(main())
```

### With MCP Integration
```python
import asyncio
from ollama_client import OllamaAgent
from mcp_client import MCPClient

async def main():
    # Initialize components
    ollama = OllamaAgent("llama3.1:8b")
    mcp = MCPClient()
    
    # Connect to MCP servers
    await mcp.connect_server("filesystem", ["python", "mcp-servers/filesystem/server.py"])
    await mcp.connect_server("system", ["python", "mcp-servers/system/server.py"])
    
    # Define available tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file's contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "list_files",
                "description": "List files in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string"}
                    },
                    "required": ["directory"]
                }
            }
        }
    ]
    
    print("AI Agent with MCP ready!")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
            
        # Get response from Ollama
        response = ollama.chat(user_input, tools=tools)
        
        # Handle tool calls
        if isinstance(response, list):  # Tool calls
            for tool_call in response:
                tool_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                
                if tool_name == "read_file":
                    result = await mcp.call_tool("filesystem", "read_file", args)
                elif tool_name == "list_files":
                    result = await mcp.call_tool("filesystem", "list_directory", args)
                
                print(f"Tool result: {result}")
        else:
            print(f"Agent: {response.get('message', {}).get('content', 'Error')}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### 1. Model Selection
- **For speed**: Use 7B models (Mistral, Llama 3.1 7B)
- **For quality**: Use 8B models (Llama 3.1 8B, Code Llama 8B)
- **For coding**: Use CodeLlama or Llama 3.1 with code-specific prompts

### 2. Memory Management
- Keep only 1-2 models loaded at a time
- Use quantized models for larger sizes
- Monitor RAM usage with `htop` or `ollama ps`

### 3. Performance Tuning
- Set appropriate context length (2048-4096 for most tasks)
- Use GPU acceleration when available
- Adjust temperature based on task (0.1 for factual, 0.7 for creative)

### 4. Error Handling
```python
def safe_ollama_call(client, model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.generate(model, prompt)
            return response
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Useful Commands Reference

```bash
# List all models
ollama list

# Show model info
ollama show llama3.1:8b

# Remove a model
ollama rm modelname

# Copy a model
ollama cp source destination

# Update all models
ollama pull --all

# Check service status
systemctl status ollama

# View resource usage
ollama ps

# Test API connection
curl http://localhost:11434/api/tags
```