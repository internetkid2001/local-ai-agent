"""
Start script for the AI Bridge MCP Server.
"""

import asyncio
from server import AiBridgeMCPServer

if __name__ == "__main__":
    server = AiBridgeMCPServer()
    host = "localhost"
    port = 8005

    async def start():
        async with websockets.serve(server._handle_websocket_client, host, port):
            print(f"AI Bridge MCP Server started on ws://{host}:{port}")
            await asyncio.Future()  # Run forever

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("AI Bridge Server stopped.")
