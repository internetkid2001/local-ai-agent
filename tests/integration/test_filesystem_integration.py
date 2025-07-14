
import pytest
import asyncio
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, "/home/vic/Documents/CODE/local-ai-agent")

from src.mcp_client.filesystem_client import FilesystemMCPClient

@pytest.fixture
def temp_directory():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.mark.asyncio
async def test_filesystem_client_integration(temp_directory):
    """Test filesystem MCP client integration with a running server."""
    client = FilesystemMCPClient()
    await asyncio.sleep(1)  # Give the server time to start
    initialized = await client.initialize()
    assert initialized, "Filesystem MCP client failed to initialize."

    try:
        # List initial files (should be empty)
        initial_files = await client.execute_tool("list_files", {"path": "."})
        assert initial_files["files"] == []

        # Create a file
        create_result = await client.execute_tool(
            "create_file",
            {"path": "test.txt", "content": "hello world"}
        )
        assert create_result["success"]

        # List files again
        updated_files = await client.execute_tool("list_files", {"path": "."})
        assert "test.txt" in [f["name"] for f in updated_files["files"]]

        # Read the file
        read_result = await client.execute_tool("read_file", {"path": "test.txt"})
        assert read_result["content"] == "hello world"

        # Delete the file
        delete_result = await client.execute_tool("delete_file", {"path": "test.txt"})
        assert delete_result["success"]

        # List files one last time
        final_files = await client.execute_tool("list_files", {"path": "."})
        assert "test.txt" not in [f["name"] for f in final_files["files"]]

    finally:
            await asyncio.sleep(1) # Wait for the server to process the request
            await client.shutdown()

