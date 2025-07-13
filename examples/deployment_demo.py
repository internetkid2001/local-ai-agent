#!/usr/bin/env python3

"""
Local AI Agent - Deployment Infrastructure Demo
Demonstrates the complete deployment pipeline and infrastructure capabilities.
"""

import os
import sys
import subprocess
import time
import requests
from typing import Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DeploymentDemo:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.admin_token = None
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                command.split(),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed."""
        print("🔍 Checking prerequisites...")
        
        tools = ["docker", "docker-compose", "curl"]
        missing_tools = []
        
        for tool in tools:
            result = self.run_command(f"which {tool}")
            if not result["success"]:
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"❌ Missing tools: {', '.join(missing_tools)}")
            print("Please install the missing tools and try again.")
            return False
        
        print("✅ All prerequisites satisfied")
        return True
    
    def deploy_local(self) -> bool:
        """Deploy the application locally using Docker Compose."""
        print("\n🚀 Deploying Local AI Agent locally...")
        
        # Check if deployment script exists
        deploy_script = "deployment/scripts/deploy.sh"
        if not os.path.exists(deploy_script):
            print(f"❌ Deployment script not found: {deploy_script}")
            return False
        
        # Run deployment script
        print("Running deployment script...")
        result = self.run_command(f"bash {deploy_script} local")
        
        if not result["success"]:
            print(f"❌ Deployment failed: {result['stderr']}")
            return False
        
        print("✅ Local deployment completed")
        return True
    
    def wait_for_service(self, url: str, timeout: int = 60) -> bool:
        """Wait for service to be ready."""
        print(f"⏳ Waiting for service at {url}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ Service is ready at {url}")
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(5)
        
        print(f"❌ Service not ready after {timeout} seconds")
        return False
    
    def authenticate(self) -> bool:
        """Authenticate with the API and get access token."""
        print("\n🔐 Authenticating with API...")
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test various API endpoints."""
        print("\n🧪 Testing API endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test endpoints
        endpoints = [
            ("GET", "/health", "Health check"),
            ("GET", "/", "Root endpoint"),
            ("GET", "/api/v1/agents", "Agents list"),
            ("GET", "/api/v1/workflows", "Workflows list"),
            ("GET", "/api/v1/mcp-servers", "MCP servers list"),
        ]
        
        for method, endpoint, description in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
                
                if response.status_code in [200, 401]:  # 401 is expected for some endpoints
                    print(f"✅ {description}: {response.status_code}")
                else:
                    print(f"❌ {description}: {response.status_code}")
                    return False
            
            except Exception as e:
                print(f"❌ {description}: {e}")
                return False
        
        return True
    
    def test_agent_creation(self) -> bool:
        """Test creating an agent."""
        print("\n🤖 Testing agent creation...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        agent_data = {
            "name": "Demo Agent",
            "description": "Test agent for deployment demo",
            "capabilities": ["text_processing", "data_analysis"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents",
                json=agent_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                agent_id = data["data"]["id"]
                print(f"✅ Agent created successfully: {agent_id}")
                return True
            else:
                print(f"❌ Agent creation failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Agent creation error: {e}")
            return False
    
    def test_workflow_creation(self) -> bool:
        """Test creating a workflow."""
        print("\n📋 Testing workflow creation...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        workflow_data = {
            "name": "Demo Workflow",
            "description": "Test workflow for deployment demo",
            "steps": [
                {"name": "Step 1", "action": "initialize"},
                {"name": "Step 2", "action": "process"},
                {"name": "Step 3", "action": "complete"}
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/workflows",
                json=workflow_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                workflow_id = data["data"]["id"]
                print(f"✅ Workflow created successfully: {workflow_id}")
                return True
            else:
                print(f"❌ Workflow creation failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Workflow creation error: {e}")
            return False
    
    def test_graphql_endpoint(self) -> bool:
        """Test GraphQL endpoint."""
        print("\n🔗 Testing GraphQL endpoint...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        query = """
        query {
            agents {
                id
                name
                status
            }
        }
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/graphql",
                json={"query": query},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "agents" in data["data"]:
                    print(f"✅ GraphQL query successful: {len(data['data']['agents'])} agents")
                    return True
                else:
                    print(f"❌ GraphQL query failed: Invalid response")
                    return False
            else:
                print(f"❌ GraphQL query failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ GraphQL query error: {e}")
            return False
    
    def check_monitoring(self) -> bool:
        """Check monitoring endpoints."""
        print("\n📊 Checking monitoring endpoints...")
        
        monitoring_endpoints = [
            ("http://localhost:9090", "Prometheus"),
            ("http://localhost:3000", "Grafana")
        ]
        
        for url, service in monitoring_endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service} is accessible")
                else:
                    print(f"⚠️ {service} returned status {response.status_code}")
            except Exception as e:
                print(f"⚠️ {service} is not accessible: {e}")
        
        return True
    
    def cleanup_deployment(self) -> bool:
        """Clean up the deployment."""
        print("\n🧹 Cleaning up deployment...")
        
        result = self.run_command("bash deployment/scripts/deploy.sh local --cleanup")
        
        if result["success"]:
            print("✅ Cleanup completed")
            return True
        else:
            print(f"❌ Cleanup failed: {result['stderr']}")
            return False
    
    def run_demo(self) -> bool:
        """Run the complete deployment demo."""
        print("🚀 Local AI Agent - Deployment Infrastructure Demo")
        print("=" * 60)
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Step 2: Deploy locally
        if not self.deploy_local():
            return False
        
        # Step 3: Wait for service to be ready
        if not self.wait_for_service(f"{self.base_url}/health"):
            return False
        
        # Step 4: Authenticate
        if not self.authenticate():
            return False
        
        # Step 5: Test API endpoints
        if not self.test_api_endpoints():
            return False
        
        # Step 6: Test agent creation
        if not self.test_agent_creation():
            return False
        
        # Step 7: Test workflow creation
        if not self.test_workflow_creation():
            return False
        
        # Step 8: Test GraphQL
        if not self.test_graphql_endpoint():
            return False
        
        # Step 9: Check monitoring
        self.check_monitoring()
        
        print("\n🎉 Deployment demo completed successfully!")
        print("\n📊 Access Points:")
        print(f"• API Gateway: {self.base_url}")
        print(f"• API Documentation: {self.base_url}/docs")
        print(f"• GraphQL Playground: {self.base_url}/graphql")
        print("• Prometheus: http://localhost:9090")
        print("• Grafana: http://localhost:3000 (admin/admin123)")
        
        print("\n🛠️ To cleanup deployment, run:")
        print("bash deployment/scripts/deploy.sh local --cleanup")
        
        return True


if __name__ == "__main__":
    demo = DeploymentDemo()
    
    try:
        success = demo.run_demo()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
        print("Run cleanup: bash deployment/scripts/deploy.sh local --cleanup")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1)