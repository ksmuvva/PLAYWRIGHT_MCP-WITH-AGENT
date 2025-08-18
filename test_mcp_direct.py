#!/usr/bin/env python3
"""
Direct MCP Tool Execution Test
Tests the MCP transport layer without LLM dependency
"""
import asyncio
import sys
import os
from mcp_client import MCPToolClient

async def test_mcp_tools():
    """Test MCP tool execution directly"""
    print("🧪 Testing MCP Tool Execution")
    print("=" * 50)
    
    # Set headless for testing
    os.environ.setdefault("BROWSER_HEADLESS", "true")
    
    client = MCPToolClient()
    try:
        print("1. Starting MCP server...")
        await client.start_server()
        print("   ✅ Server started")
        
        print("2. Listing available tools...")
        tools = await client.list_tools()
        print(f"   ✅ Found {len(tools)} tools")
        
        # Show first few tool names
        tool_names = [t.get("name", "unknown") for t in tools[:10]]
        print(f"   Sample tools: {', '.join(tool_names)}")
        
        print("3. Testing playwright_navigate...")
        nav_result = await client.call_tool("playwright_navigate", {
            "url": "https://example.com",
            "wait_for_load": True,
            "capture_screenshot": False
        })
        print(f"   ✅ Navigation result: {nav_result}")
        
        print("4. Testing playwright_get_page_info (if available)...")
        try:
            # Check if this tool exists
            has_page_info = any(t.get("name") == "playwright_get_page_info" for t in tools)
            if has_page_info:
                page_info = await client.call_tool("playwright_get_page_info", {})
                print(f"   ✅ Page info: {page_info}")
            else:
                print("   ℹ️  playwright_get_page_info not available")
        except Exception as e:
            print(f"   ⚠️  Page info failed: {e}")
        
        print("\n🎉 MCP Tool Execution Test PASSED!")
        print("✅ JSON-RPC communication working")
        print("✅ Tool discovery working") 
        print("✅ Tool execution working")
        
    except Exception as e:
        print(f"\n❌ MCP Test FAILED: {e}")
        return False
    finally:
        await client.stop_server()
        print("🔄 Server stopped")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)
