#!/usr/bin/env python3

"""
Manual test for SauceDemo to demonstrate the correct tool usage
This bypasses the LLM parameter issues and shows the proper working flow.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPToolClient

async def test_saucedemo_workflow():
    """Test the complete SauceDemo workflow with correct parameters."""
    
    print("🚀 Starting SauceDemo test with Microsoft Edge...")
    
    # Initialize MCP client with Edge browser
    client = MCPToolClient(browser_type="msedge")
    
    try:
        # Start the MCP server
        await client.start_server()
        print("✅ MCP Server started")
        
        # List available tools
        tools = await client.list_tools()
        print(f"📋 Available tools: {len(tools)} tools")
        
        # Step 1: Navigate to SauceDemo
        print("\n📍 Step 1: Navigating to SauceDemo...")
        result = await client.call_tool("playwright_navigate", {"url": "https://www.saucedemo.com"})
        print(f"Navigate result: {result}")
        
        # Step 2: Wait for username field
        print("\n⏳ Step 2: Waiting for username field...")
        result = await client.call_tool("playwright_wait_for_element", {
            "selector": "#user-name", 
            "state": "visible", 
            "timeout": 10000
        })
        print(f"Wait result: {result}")
        
        # Step 3: Fill username (using correct 'text' parameter)
        print("\n👤 Step 3: Filling username...")
        result = await client.call_tool("playwright_fill", {
            "selector": "#user-name", 
            "text": "standard_user"  # ✅ Correct parameter name
        })
        print(f"Username fill result: {result}")
        
        # Step 4: Fill password (using correct 'text' parameter)
        print("\n🔒 Step 4: Filling password...")
        result = await client.call_tool("playwright_fill", {
            "selector": "#password", 
            "text": "secret_sauce"  # ✅ Correct parameter name
        })
        print(f"Password fill result: {result}")
        
        # Step 5: Click login button
        print("\n🔑 Step 5: Clicking login button...")
        result = await client.call_tool("playwright_click", {"selector": "#login-button"})
        print(f"Login click result: {result}")
        
        # Step 6: Wait for inventory to load
        print("\n📦 Step 6: Waiting for inventory...")
        result = await client.call_tool("playwright_wait_for_element", {
            "selector": ".inventory_list", 
            "state": "visible", 
            "timeout": 10000
        })
        print(f"Inventory wait result: {result}")
        
        # Step 7: Add first item to cart
        print("\n🛒 Step 7: Adding Sauce Labs Backpack to cart...")
        result = await client.call_tool("playwright_click", {
            "selector": "button[data-test='add-to-cart-sauce-labs-backpack']"
        })
        print(f"Add backpack result: {result}")
        
        # Step 8: Add second item to cart
        print("\n🚲 Step 8: Adding Sauce Labs Bike Light to cart...")
        result = await client.call_tool("playwright_click", {
            "selector": "button[data-test='add-to-cart-sauce-labs-bike-light']"
        })
        print(f"Add bike light result: {result}")
        
        # Step 9: Go to cart
        print("\n🛍️ Step 9: Going to cart...")
        result = await client.call_tool("playwright_click", {"selector": ".shopping_cart_link"})
        print(f"Cart navigation result: {result}")
        
        # Step 10: Proceed to checkout
        print("\n💳 Step 10: Proceeding to checkout...")
        result = await client.call_tool("playwright_click", {
            "selector": "button[data-test='checkout']"
        })
        print(f"Checkout click result: {result}")
        
        # Step 11: Fill checkout information
        print("\n📝 Step 11: Filling checkout information...")
        
        await client.call_tool("playwright_fill", {
            "selector": "input[data-test='firstName']", 
            "text": "John"  # ✅ Correct parameter
        })
        
        await client.call_tool("playwright_fill", {
            "selector": "input[data-test='lastName']", 
            "text": "Doe"  # ✅ Correct parameter
        })
        
        await client.call_tool("playwright_fill", {
            "selector": "input[data-test='postalCode']", 
            "text": "12345"  # ✅ Correct parameter
        })
        
        # Step 12: Continue to overview
        print("\n➡️ Step 12: Continuing to overview...")
        result = await client.call_tool("playwright_click", {
            "selector": "input[data-test='continue']"
        })
        print(f"Continue result: {result}")
        
        # Step 13: Get total price
        print("\n💰 Step 13: Getting total price...")
        result = await client.call_tool("playwright_check_element", {
            "selector": ".summary_total_label", 
            "property": "text"
        })
        print(f"Total price result: {result}")
        
        # Extract and display the total
        if result and result.get("status") == "success":
            total_text = result.get("actual_value", "")
            print(f"\n🎯 FINAL RESULT: {total_text}")
        else:
            print(f"\n❌ Failed to get total price: {result}")
            
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await client.close()
        print("🧹 Cleaned up MCP client")

if __name__ == "__main__":
    asyncio.run(test_saucedemo_workflow())
