import asyncio
import os
from mcp_client import MCPToolClient

async def main():
    # Ensure headless for CI/silent run
    os.environ.setdefault("BROWSER_HEADLESS", "true")
    client = MCPToolClient()
    try:
        await client.start_server()
        tools = await client.list_tools()
        print(f"TOOLS_COUNT={len(tools)}")
        # Pick a tool that should exist
        target = "playwright_navigate"
        exists = any(t.get("name") == target for t in tools)
        print(f"HAS_{target}={exists}")
        if not exists:
            # Print first few tool names for debugging
            print("TOOLS_SAMPLE=", [t.get("name") for t in tools[:10]])
            return
        # Call navigate to a fast site
        res = await client.call_tool(target, {"url": "https://example.com", "wait_for_load": True, "capture_screenshot": False})
        print("CALL_RESULT=", res)
    finally:
        await client.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
