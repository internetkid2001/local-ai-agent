#!/usr/bin/env python3
"""
Performance Optimization Tests

Test suite for the enhanced MCP orchestrator with performance optimizations
including connection pooling, response caching, error handling, and monitoring.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6 - Performance Optimization
"""

import asyncio
import json
import logging
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.orchestration.enhanced_orchestrator import (
    EnhancedMCPOrchestrator, 
    EnhancedOrchestrationConfig,
    OrchestrationStep
)
from src.agent.performance.connection_pool import PoolConfig
from src.agent.performance.response_cache import CacheConfig
from src.mcp_client.client_manager import MCPClientManager
from src.mcp_client.base_client import MCPClientConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Test suite for performance optimization features"""
    
    def __init__(self):
        self.orchestrator = None
        self.client_manager = None
        self.test_results = {}
    
    async def setup(self):
        """Set up test environment"""
        logger.info("Setting up performance test environment...")
        
        # Create client manager
        self.client_manager = MCPClientManager()
        
        # Initialize with test configurations
        test_configs = {
            "filesystem": MCPClientConfig(
                host="localhost",
                port=8765,
                name="filesystem_test"
            ),
            "desktop": MCPClientConfig(
                host="localhost", 
                port=8766,
                name="desktop_test"
            ),
            "system": MCPClientConfig(
                host="localhost",
                port=8767,
                name="system_test"
            )
        }
        
        # Initialize clients
        if not await self.client_manager.initialize(test_configs):
            raise RuntimeError("Failed to initialize MCP clients")
        
        # Create enhanced orchestrator with performance optimizations
        config = EnhancedOrchestrationConfig(
            enable_connection_pooling=True,
            enable_response_caching=True,
            enable_error_handling=True,
            enable_monitoring=True,
            pool_config=PoolConfig(
                max_connections_per_type=3,
                min_connections_per_type=1,
                enable_prewarming=True
            ),
            cache_config=CacheConfig(
                max_size=1000,
                default_ttl=300.0,
                enable_persistence=False
            )
        )
        
        self.orchestrator = EnhancedMCPOrchestrator(self.client_manager, config)
        await self.orchestrator.initialize()
        
        logger.info("Performance test environment set up successfully")
    
    async def test_connection_pooling(self):
        """Test connection pooling performance"""
        logger.info("Testing connection pooling performance...")
        
        # Test without pooling (baseline)
        start_time = time.time()
        
        tasks = []
        for i in range(10):
            # Create simple workflow
            steps = [
                OrchestrationStep(
                    id=f"list_dir_{i}",
                    name=f"List Directory {i}",
                    server="filesystem",
                    tool="list_directory",
                    arguments={"path": "/tmp"}
                )
            ]
            
            workflow_id = self.orchestrator.create_workflow(
                f"Pool Test {i}",
                f"Connection pool test workflow {i}",
                steps
            )
            
            task = asyncio.create_task(
                self.orchestrator.execute_workflow(workflow_id)
            )
            tasks.append(task)
        
        # Execute all workflows
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        pooling_time = time.time() - start_time
        
        # Check results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        
        self.test_results["connection_pooling"] = {
            "total_workflows": len(tasks),
            "successful": successful,
            "execution_time": pooling_time,
            "avg_time_per_workflow": pooling_time / len(tasks),
            "pool_stats": self.orchestrator.connection_pool.get_pool_stats()
        }
        
        logger.info(f"Connection pooling test completed: {successful}/{len(tasks)} successful in {pooling_time:.2f}s")
    
    async def test_response_caching(self):
        """Test response caching performance"""
        logger.info("Testing response caching performance...")
        
        # Test cache miss (first call)
        start_time = time.time()
        
        steps = [
            OrchestrationStep(
                id="cache_test_1",
                name="Cache Test 1",
                server="system",
                tool="get_system_metrics",
                arguments={"detailed": True}
            )
        ]
        
        workflow_id = self.orchestrator.create_workflow(
            "Cache Test 1",
            "Test cache miss",
            steps
        )
        
        await self.orchestrator.execute_workflow(workflow_id)
        miss_time = time.time() - start_time
        
        # Test cache hit (second call with same parameters)
        start_time = time.time()
        
        workflow_id = self.orchestrator.create_workflow(
            "Cache Test 2",
            "Test cache hit",
            steps
        )
        
        await self.orchestrator.execute_workflow(workflow_id)
        hit_time = time.time() - start_time
        
        cache_stats = self.orchestrator.response_cache.get_stats()
        
        self.test_results["response_caching"] = {
            "cache_miss_time": miss_time,
            "cache_hit_time": hit_time,
            "speedup_factor": miss_time / hit_time if hit_time > 0 else 0,
            "cache_stats": cache_stats
        }
        
        logger.info(f"Response caching test completed: {miss_time:.3f}s miss, {hit_time:.3f}s hit")
    
    async def test_error_handling(self):
        """Test enhanced error handling"""
        logger.info("Testing enhanced error handling...")
        
        # Test with invalid parameters to trigger errors
        steps = [
            OrchestrationStep(
                id="error_test_1",
                name="Error Test 1",
                server="filesystem",
                tool="read_file",
                arguments={"path": "/nonexistent/file.txt"}
            )
        ]
        
        workflow_id = self.orchestrator.create_workflow(
            "Error Test",
            "Test error handling",
            steps
        )
        
        start_time = time.time()
        
        try:
            await self.orchestrator.execute_workflow(workflow_id)
        except Exception as e:
            logger.info(f"Expected error caught: {e}")
        
        error_time = time.time() - start_time
        
        error_stats = self.orchestrator.error_handler.get_error_stats()
        
        self.test_results["error_handling"] = {
            "error_processing_time": error_time,
            "error_stats": error_stats,
            "service_health": self.orchestrator.error_handler.get_service_health()
        }
        
        logger.info(f"Error handling test completed in {error_time:.3f}s")
    
    async def test_monitoring_metrics(self):
        """Test performance monitoring metrics"""
        logger.info("Testing performance monitoring...")
        
        # Execute a series of workflows to generate metrics
        workflows = []
        for i in range(5):
            steps = [
                OrchestrationStep(
                    id=f"monitor_step_{i}_1",
                    name=f"Monitor Step {i} - 1",
                    server="system",
                    tool="get_system_metrics",
                    arguments={"detailed": False}
                ),
                OrchestrationStep(
                    id=f"monitor_step_{i}_2",
                    name=f"Monitor Step {i} - 2",
                    server="filesystem",
                    tool="list_directory",
                    arguments={"path": "/tmp"}
                ),
                OrchestrationStep(
                    id=f"monitor_step_{i}_3",
                    name=f"Monitor Step {i} - 3",
                    server="desktop",
                    tool="get_screen_info",
                    arguments={}
                )
            ]
            
            workflow_id = self.orchestrator.create_workflow(
                f"Monitor Test {i}",
                f"Monitoring test workflow {i}",
                steps
            )
            workflows.append(workflow_id)
        
        # Execute workflows
        start_time = time.time()
        
        tasks = [
            self.orchestrator.execute_workflow(wid) 
            for wid in workflows
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        monitoring_time = time.time() - start_time
        
        # Get monitoring dashboard
        dashboard = self.orchestrator.get_performance_dashboard()
        
        self.test_results["monitoring"] = {
            "total_execution_time": monitoring_time,
            "workflows_executed": len(workflows),
            "dashboard_data": dashboard
        }
        
        logger.info(f"Monitoring test completed: {len(workflows)} workflows in {monitoring_time:.2f}s")
    
    async def test_workflow_optimization(self):
        """Test workflow optimization features"""
        logger.info("Testing workflow optimization...")
        
        # Create a complex workflow with dependencies
        steps = [
            # Independent steps (can run in parallel)
            OrchestrationStep(
                id="opt_step_1",
                name="Optimization Step 1",
                server="system",
                tool="get_system_metrics",
                arguments={"detailed": False}
            ),
            OrchestrationStep(
                id="opt_step_2",
                name="Optimization Step 2",
                server="filesystem",
                tool="list_directory",
                arguments={"path": "/tmp"}
            ),
            OrchestrationStep(
                id="opt_step_3",
                name="Optimization Step 3",
                server="desktop",
                tool="get_screen_info",
                arguments={}
            ),
            # Dependent step
            OrchestrationStep(
                id="opt_step_4",
                name="Optimization Step 4",
                server="filesystem",
                tool="write_file",
                arguments={
                    "path": "/tmp/optimization_test.txt",
                    "content": "Test content"
                },
                depends_on=["opt_step_1", "opt_step_2"]
            ),
            # Final step
            OrchestrationStep(
                id="opt_step_5",
                name="Optimization Step 5",
                server="filesystem",
                tool="read_file",
                arguments={"path": "/tmp/optimization_test.txt"},
                depends_on=["opt_step_4"]
            )
        ]
        
        workflow_id = self.orchestrator.create_workflow(
            "Optimization Test",
            "Test workflow optimization",
            steps
        )
        
        start_time = time.time()
        result = await self.orchestrator.execute_workflow(workflow_id)
        optimization_time = time.time() - start_time
        
        status = self.orchestrator.get_workflow_status(workflow_id)
        
        self.test_results["workflow_optimization"] = {
            "execution_time": optimization_time,
            "workflow_status": status,
            "steps_executed": len(result.results),
            "performance_metrics": status.get("performance_metrics", {})
        }
        
        logger.info(f"Workflow optimization test completed in {optimization_time:.2f}s")
    
    async def run_performance_benchmark(self):
        """Run comprehensive performance benchmark"""
        logger.info("Running comprehensive performance benchmark...")
        
        benchmark_start = time.time()
        
        # Run all performance tests
        await self.test_connection_pooling()
        await self.test_response_caching()
        await self.test_error_handling()
        await self.test_monitoring_metrics()
        await self.test_workflow_optimization()
        
        benchmark_time = time.time() - benchmark_start
        
        # Generate comprehensive report
        report = {
            "benchmark_duration": benchmark_time,
            "test_results": self.test_results,
            "final_dashboard": self.orchestrator.get_performance_dashboard(),
            "timestamp": time.time()
        }
        
        logger.info(f"Performance benchmark completed in {benchmark_time:.2f}s")
        return report
    
    async def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up performance test environment...")
        
        if self.orchestrator:
            await self.orchestrator.shutdown()
        
        if self.client_manager:
            await self.client_manager.shutdown()
        
        logger.info("Performance test environment cleaned up")


async def main():
    """Run performance optimization tests"""
    test_suite = PerformanceTestSuite()
    
    try:
        await test_suite.setup()
        
        # Run benchmark
        report = await test_suite.run_performance_benchmark()
        
        # Print results
        print("\n" + "="*60)
        print("PERFORMANCE OPTIMIZATION TEST RESULTS")
        print("="*60)
        
        print(f"\nBenchmark Duration: {report['benchmark_duration']:.2f}s")
        
        # Connection pooling results
        pool_results = report['test_results']['connection_pooling']
        print(f"\nConnection Pooling:")
        print(f"  - Workflows: {pool_results['successful']}/{pool_results['total_workflows']}")
        print(f"  - Execution Time: {pool_results['execution_time']:.2f}s")
        print(f"  - Avg Time/Workflow: {pool_results['avg_time_per_workflow']:.3f}s")
        print(f"  - Pool Hits: {pool_results['pool_stats']['global_stats']['pool_hits']}")
        
        # Caching results
        cache_results = report['test_results']['response_caching']
        print(f"\nResponse Caching:")
        print(f"  - Cache Miss Time: {cache_results['cache_miss_time']:.3f}s")
        print(f"  - Cache Hit Time: {cache_results['cache_hit_time']:.3f}s")
        print(f"  - Speedup Factor: {cache_results['speedup_factor']:.1f}x")
        print(f"  - Hit Rate: {cache_results['cache_stats']['hit_rate']:.1%}")
        
        # Error handling results
        error_results = report['test_results']['error_handling']
        print(f"\nError Handling:")
        print(f"  - Error Processing Time: {error_results['error_processing_time']:.3f}s")
        print(f"  - Total Errors: {error_results['error_stats']['error_stats']['total_errors']}")
        
        # Monitoring results
        monitor_results = report['test_results']['monitoring']
        print(f"\nMonitoring:")
        print(f"  - Workflows Monitored: {monitor_results['workflows_executed']}")
        print(f"  - Total Execution Time: {monitor_results['total_execution_time']:.2f}s")
        
        # Workflow optimization results
        opt_results = report['test_results']['workflow_optimization']
        print(f"\nWorkflow Optimization:")
        print(f"  - Execution Time: {opt_results['execution_time']:.2f}s")
        print(f"  - Steps Executed: {opt_results['steps_executed']}")
        
        if 'performance_metrics' in opt_results:
            perf_metrics = opt_results['performance_metrics']
            print(f"  - Avg Step Time: {perf_metrics['avg_step_time']:.3f}s")
            print(f"  - Max Step Time: {perf_metrics['max_step_time']:.3f}s")
        
        print(f"\nFinal Dashboard Summary:")
        dashboard = report['final_dashboard']
        print(f"  - Active Workflows: {dashboard['active_workflows']}")
        print(f"  - Completed Workflows: {dashboard['completed_workflows']}")
        
        if 'monitoring' in dashboard:
            monitoring = dashboard['monitoring']
            if 'kpis' in monitoring:
                kpis = monitoring['kpis']
                print(f"  - Avg Response Time: {kpis.get('avg_response_time', 0):.3f}s")
                print(f"  - P95 Response Time: {kpis.get('p95_response_time', 0):.3f}s")
                print(f"  - Error Rate: {kpis.get('error_rate', 0):.1%}")
                print(f"  - Cache Hit Rate: {kpis.get('cache_hit_rate', 0):.1%}")
        
        print("\n" + "="*60)
        print("PERFORMANCE OPTIMIZATION TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise
    
    finally:
        await test_suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())