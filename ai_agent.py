#!/usr/bin/env python3

import asyncio
import json
import logging
import sys
import argparse
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all tool classes
from Tools.AdvancedBrowser.advanced import AdvancedBrowserTools
from Tools.BrowserControl.navigation import BrowserControlTools
from Tools.ContentExtraction.extraction import ContentExtractionTools
from Tools.ElementInteraction.interaction import ElementInteractionTools
from Tools.ElementLocation.location import ElementLocationTools
from Tools.Network.network import NetworkTools
from Tools.Debug.debug import DebugTools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMProvider:
    """Abstract base class for LLM providers"""
    
    def __init__(self):
        self.provider_name = "base"
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "openai"
        try:
            import openai
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = os.getenv("LLM_MODEL", "gpt-4")
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "anthropic"
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages format for Claude
            system_msg = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=system_msg if system_msg else "You are a helpful assistant.",
                messages=user_messages
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "gemini"
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages to Gemini format
            conversation_text = "\\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in messages
            ])
            
            response = self.model.generate_content(conversation_text)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

class DirectBrowserTools(
    AdvancedBrowserTools,
    BrowserControlTools,
    ContentExtractionTools,
    ElementInteractionTools,
    ElementLocationTools,
    NetworkTools,
    DebugTools
):
    """Combined browser tools class"""
    
    def __init__(self):
        super().__init__()
        self.available_methods = []
        self._scan_available_methods()
    
    def _scan_available_methods(self):
        """Scan for available methods from all parent classes"""
        import inspect
        
        seen_methods = set()  # Track method names to avoid duplicates
        
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if (not name.startswith('_') and 
                name not in ['initialize', 'cleanup', 'cleanup_all'] and
                name not in seen_methods and  # Avoid duplicates
                callable(method)):
                
                doc = method.__doc__ or "No description available"
                self.available_methods.append({
                    'name': name,
                    'description': doc.split('\\n')[0].strip() if doc else "No description",
                    'method': method
                })
                seen_methods.add(name)  # Mark as seen

class AIBrowserAgent:
    """Direct AI Browser Agent without MCP server"""
    
    def __init__(self, llm_provider_name: str = None):
        self.llm_provider = self._initialize_llm_provider(llm_provider_name)
        self.browser_tools = DirectBrowserTools()
        self.conversation_history = []
        self.initialized = False
    
    def _initialize_llm_provider(self, provider_name: str = None) -> LLMProvider:
        """Initialize the appropriate LLM provider"""
        if not provider_name:
            provider_name = os.getenv("LLM_PROVIDER", "openai").lower()
        
        provider_name = provider_name.lower()
        
        try:
            if provider_name == "openai":
                return OpenAIProvider()
            elif provider_name == "anthropic":
                return AnthropicProvider()
            elif provider_name == "gemini":
                return GeminiProvider()
            else:
                logger.warning(f"Unknown LLM provider '{provider_name}', defaulting to OpenAI")
                return OpenAIProvider()
        except ImportError as e:
            logger.error(f"Failed to initialize {provider_name}: {e}")
            raise Exception(f"LLM provider '{provider_name}' not available: {e}")
    
    async def initialize(self):
        """Initialize the browser tools"""
        try:
            logger.info(f"Initializing AI Browser Agent with {self.llm_provider.provider_name.upper()}...")
            await self.browser_tools.initialize()
            self.initialized = True
            logger.info(f"AI Browser Agent initialized successfully with {len(self.browser_tools.available_methods)} tools!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def create_system_message(self) -> str:
        """Create system message with available tools"""
        tools_description = "\\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.browser_tools.available_methods[:25]  # Show first 25 tools
        ])
        
        return f"""You are an AI Browser Automation Agent. You can control a browser using these tools:

{tools_description}
... and {len(self.browser_tools.available_methods) - 25} more tools.

When a user gives you a task, analyze it and respond with tool calls in this JSON format:

{{
  "reasoning": "Brief explanation of your approach",
  "tool_calls": [
    {{
      "tool": "tool_name",
      "arguments": {{
        "arg1": "value1",
        "arg2": "value2"
      }}
    }}
  ]
}}

IMPORTANT RULES:
1. Always respond with valid JSON in the format above
2. Include a "reasoning" field explaining your approach  
3. The "tool_calls" array should contain the sequence of tools to execute
4. The browser state is automatically managed - if the browser is closed, it will be reinitialized
5. CRITICAL JSON FORMAT RULES:
   - Use double quotes for ALL strings in JSON (NOT backticks or template literals)
   - Escape special characters in strings with backslashes
   - For multi-line JavaScript code in script fields, use \\n for line breaks
   - Example script parameter: "const data = {{title: 'Test', id: 123}}; return data;"
   - NO backticks allowed in JSON - use proper string escaping instead
5. Common patterns:
   - For navigation: use "playwright_navigate" with url parameter (NO timeout parameter!)
   - For page refresh: use "playwright_reload" 
   - For screenshots: use "playwright_screenshot" with filename, selector, page_index, path, full_page, or output_path
   - For clicking: use "playwright_click" with selector
   - For form filling: use "playwright_fill" with selector and text (NOT value!)
   - For getting text: use "playwright_get_visible_text"
   - For finding elements: use "playwright_find_element" with description or "playwright_multi_strategy_locate"
   - For checkboxes: use proper CSS selectors like "input[type='checkbox']" (not nth-child)
   - For dropdown selection: use "playwright_select" with selector and value
   - For verification: use "playwright_check_element" with selector, property, and expected_value
   - For assertions: use "playwright_assert_element_state" with selector and expected_state (a dictionary of properties)
   - For waiting for responses: use "playwright_expect_response" with url_pattern (NOT url!) and timeout_ms (NOT timeout!)
   - For waiting for elements: use "playwright_wait_for_element" with selector, state, timeout
   - For element info: use "playwright_element_info" with selector (NO attributes parameter!)
   - For file uploads: use "playwright_upload_file" with selector and file_path
   - For dialog handling: use "playwright_handle_dialog" with action and text
   - For performance: use "playwright_performance_metrics" 
   - For network info: use "playwright_network_info" with optional include_request_body and include_response_body
   - For tab switching: use "playwright_switch_tab" with target_page_index
   - For waiting: use "playwright_evaluate" with a delay script like "await new Promise(resolve => setTimeout(resolve, 2000))"
   - For page refresh: use "playwright_reload"

Example for "go to google.com":
{{
  "reasoning": "User wants to navigate to Google's homepage",
  "tool_calls": [
    {{
      "tool": "playwright_navigate",
      "arguments": {{
        "url": "https://google.com"
      }}
    }}
  ]
}}

Example for "refresh page 3 times and document changes":
{{
  "reasoning": "Take initial screenshot, then refresh and screenshot multiple times to document changes",
  "tool_calls": [
    {{
      "tool": "playwright_navigate",
      "arguments": {{
        "url": "https://example.com/dynamic"
      }}
    }},
    {{
      "tool": "playwright_screenshot",
      "arguments": {{}}
    }},
    {{
      "tool": "playwright_reload",
      "arguments": {{}}
    }},
    {{
      "tool": "playwright_screenshot",
      "arguments": {{}}
    }},
    {{
      "tool": "playwright_reload",
      "arguments": {{}}
    }},
    {{
      "tool": "playwright_screenshot",
      "arguments": {{}}
    }}
  ]
}}

Example for "click remove button, wait for element to disappear, then add it back":
{{
  "reasoning": "Need to click remove button, wait for element to disappear, then click add to restore it",
  "tool_calls": [
    {{
      "tool": "playwright_click",
      "arguments": {{
        "selector": "button[onclick='swapCheckbox()']"
      }}
    }},
    {{
      "tool": "playwright_evaluate",
      "arguments": {{
        "script": "await new Promise(resolve => setTimeout(resolve, 2000)); return 'waited 2 seconds';"
      }}
    }},
    {{
      "tool": "playwright_check_element",
      "arguments": {{
        "selector": "#checkbox",
        "property": "visible"
      }}
    }},
    {{
      "tool": "playwright_screenshot",
      "arguments": {{}}
    }}
  ]
}}

Example for "type Hello in the input field":
{{
  "reasoning": "Fill an input field with text using the correct parameter name",
  "tool_calls": [
    {{
      "tool": "playwright_fill",
      "arguments": {{
        "selector": "input[type='text']",
        "text": "Hello"
      }}
    }},
    {{
      "tool": "playwright_screenshot",
      "arguments": {{}}
    }}
  ]
}}

Example for "make API call and verify data":
{{
  "reasoning": "Use playwright_evaluate to make API call, then navigate and verify",
  "tool_calls": [
    {{
      "tool": "playwright_evaluate",
      "arguments": {{
        "script": "const response = await fetch('https://api.example.com/data', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ title: 'Test Data' }}) }}); return await response.json();"
      }}
    }},
    {{
      "tool": "playwright_navigate",
      "arguments": {{
        "url": "https://example.com/data-view"
      }}
    }},
    {{
      "tool": "playwright_wait_for_element",
      "arguments": {{
        "selector": ".data-item",
        "state": "visible",
        "timeout": 5000
      }}
    }}
  ]
}}

Example for "assert element properties":
{{
  "reasoning": "Check if an element has specific properties using assert_element_state",
  "tool_calls": [
    {{
      "tool": "playwright_assert_element_state",
      "arguments": {{
        "selector": "#submit-button",
        "expected_state": {{
          "visible": true,
          "enabled": true,
          "text": "Submit"
        }}
      }}
    }}
  ]
}}
"""
    
    async def process_prompt(self, user_prompt: str) -> str:
        """Process a user prompt and execute browser automation tasks"""
        logger.info(f"Processing: {user_prompt}")
        
        # Add user prompt to conversation history
        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        # Create messages for LLM
        messages = [
            {"role": "system", "content": self.create_system_message()},
            *self.conversation_history[-3:]  # Keep last 3 exchanges
        ]
        
        try:
            # Get response from LLM
            ai_response = await self.llm_provider.generate_response(messages)
            logger.info(f"LLM Response received")
            
            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Parse and execute tool calls
            execution_results = await self.execute_tool_calls_from_json(ai_response)
            
            if execution_results:
                return f"🤖 Analysis: {ai_response}\\n\\n📋 Execution Results:\\n{execution_results}"
            else:
                return f"🤖 {ai_response}"
            
        except Exception as e:
            error_msg = f"Error processing prompt: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def execute_tool_calls_from_json(self, ai_response: str) -> str:
        """Parse JSON response and execute tool calls directly"""
        try:
            # Extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in AI response")
                return ""
            
            json_str = ai_response[json_start:json_end]
            response_data = json.loads(json_str)
            
            if "tool_calls" not in response_data:
                logger.warning("No tool_calls found in JSON response")
                return ""
            
            results = []
            reasoning = response_data.get("reasoning", "No reasoning provided")
            results.append(f"💭 Reasoning: {reasoning}")
            
            for i, tool_call in enumerate(response_data["tool_calls"], 1):
                tool_name = tool_call.get("tool")
                arguments = tool_call.get("arguments", {})
                
                if not tool_name:
                    results.append(f"❌ Tool call {i}: Missing tool name")
                    continue
                
                # Find the tool method
                tool_method = None
                for tool_info in self.browser_tools.available_methods:
                    if tool_info['name'] == tool_name:
                        tool_method = tool_info['method']
                        break
                
                if not tool_method:
                    results.append(f"❌ Tool call {i}: Tool '{tool_name}' not found")
                    continue
                
                try:
                    logger.info(f"Executing tool {i}: {tool_name}")
                    
                    # Check browser state before tool execution
                    await self._ensure_browser_ready()
                    
                    # Execute the tool method directly
                    if asyncio.iscoroutinefunction(tool_method):
                        result = await tool_method(**arguments)
                    else:
                        result = tool_method(**arguments)
                    
                    results.append(f"✅ Tool {i} ({tool_name}): {result}")
                    
                except Exception as e:
                    # Check if error is related to browser being closed
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in [
                        "target page, context or browser has been closed",
                        "browser has been closed",
                        "context has been closed",
                        "page has been closed",
                        "browser connection lost",
                        "browser disconnected"
                    ]):
                        logger.warning(f"Browser closed error detected: {str(e)}")
                        logger.info(f"Attempting to reinitialize browser and retry tool {i}: {tool_name}")
                        
                        # Force complete browser reinitialization
                        try:
                            # Reset browser state completely
                            self.browser_tools.browser = None
                            self.browser_tools.context = None
                            self.browser_tools.pages = []
                            self.browser_tools.browser_initialized = False
                            
                            # Reinitialize browser
                            await self.browser_tools._ensure_browser_initialized()
                            logger.info(f"Browser reinitialized successfully, retrying tool {i}: {tool_name}")
                            
                            # Retry the tool method
                            if asyncio.iscoroutinefunction(tool_method):
                                result = await tool_method(**arguments)
                            else:
                                result = tool_method(**arguments)
                            
                            results.append(f"✅ Tool {i} ({tool_name}) [Retried after browser recovery]: {result}")
                            
                        except Exception as retry_e:
                            error_result = f"❌ Tool {i} ({tool_name}): Failed after browser reinit - {str(retry_e)}"
                            results.append(error_result)
                            logger.error(error_result)
                    else:
                        error_result = f"❌ Tool {i} ({tool_name}): Error - {str(e)}"
                        results.append(error_result)
                        logger.error(error_result)
            
            return "\\n".join(results)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return f"❌ Failed to parse tool calls: {e}"
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            return f"❌ Error executing tool calls: {e}"
    
    async def _ensure_browser_ready(self):
        """Ensure browser is ready for use by checking its state"""
        try:
            # First, try to check if browser is alive using the base class method
            if hasattr(self.browser_tools, 'is_browser_alive'):
                method = getattr(self.browser_tools, 'is_browser_alive')
                if callable(method):
                    is_alive = await method()
                    if not is_alive:
                        logger.info("Browser not alive according to is_browser_alive, reinitializing...")
                        await self.browser_tools._ensure_browser_initialized()
                        return
                else:
                    logger.debug("is_browser_alive is not callable, using alternative check")
            
            # Alternative check: verify browser and context exist and are not closed
            browser_ok = (
                hasattr(self.browser_tools, 'browser') and self.browser_tools.browser and
                hasattr(self.browser_tools, 'context') and self.browser_tools.context
            )
            
            if browser_ok:
                try:
                    # Try a simple browser operation to verify it's alive
                    if hasattr(self.browser_tools.browser, 'version'):
                        await self.browser_tools.browser.version()
                        logger.debug("Browser alive check passed")
                        return
                except Exception as e:
                    logger.warning(f"Browser version check failed: {e}")
                    browser_ok = False
            
            if not browser_ok:
                logger.info("Browser not ready, ensuring initialization...")
                await self.browser_tools._ensure_browser_initialized()
                
        except Exception as e:
            logger.warning(f"Error in _ensure_browser_ready: {e}")
            # If we can't check, try to ensure initialization anyway
            try:
                await self.browser_tools._ensure_browser_initialized()
            except Exception as init_e:
                logger.error(f"Failed to initialize browser: {init_e}")
    
    async def run_interactive(self):
        """Run the agent in interactive mode"""
        print(f"\\n🤖 AI Browser Automation Agent ({self.llm_provider.provider_name.upper()})")
        print("=" * 60)
        print("Available commands:")
        print("  - Type your browser automation task")
        print("  - 'switch <provider>' to change LLM (openai/anthropic/gemini)")
        print("  - 'quit' to exit\\n")
        
        while True:
            try:
                user_input = input("👤 Your task: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if user_input.lower().startswith('switch '):
                    new_provider = user_input[7:].strip().lower()
                    try:
                        self.llm_provider = self._initialize_llm_provider(new_provider)
                        print(f"✅ Switched to {self.llm_provider.provider_name.upper()}")
                        continue
                    except Exception as e:
                        print(f"❌ Failed to switch to {new_provider}: {e}")
                        continue
                
                if not user_input:
                    continue
                
                print("\\n🤖 Processing your request...\\n")
                response = await self.process_prompt(user_input)
                print(f"{response}\\n")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.initialized:
            await self.browser_tools.cleanup_all()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI Browser Automation Agent (Direct)")
    parser.add_argument('--llm', choices=['openai', 'anthropic', 'gemini'], 
                       help='LLM provider to use')
    parser.add_argument('--list-providers', action='store_true', 
                       help='List available providers')
    return parser.parse_args()

async def main():
    """Main function"""
    args = parse_arguments()
    
    if args.list_providers:
        print("\\n🔍 Available LLM Providers:")
        print("=" * 40)
        for provider in ['openai', 'anthropic', 'gemini']:
            status = "✅ Ready" if os.getenv(f"{provider.upper()}_API_KEY") else "❌ No API key"
            print(f"{provider.ljust(12)}: {status}")
        return
    
    agent = AIBrowserAgent(args.llm)
    
    try:
        success = await agent.initialize()
        if success:
            await agent.run_interactive()
        else:
            print("❌ Failed to initialize agent")
    except KeyboardInterrupt:
        print("\\nShutting down...")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
