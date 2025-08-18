"""
MCP Tools Package - Collection of browser automation tools for the MCP protocol
"""

import asyncio
from typing import Dict, Any, Optional, List, Union

from .BrowserControl.navigation import BrowserControlTools
from .ContentExtraction.extraction import ContentExtractionTools
from .ElementInteraction.interaction import ElementInteractionTools
from .Network.network import NetworkTools
from .AdvancedBrowser.advanced import AdvancedBrowserTools
from .ElementLocation.location import ElementLocationTools
from .Debug.debug import DebugTools
from .CodeGeneration.codegen import CodeGenerationTools
from .base import logger

class PlaywrightTools(
    BrowserControlTools,
    ContentExtractionTools, 
    ElementInteractionTools,
    NetworkTools,
    AdvancedBrowserTools,
    ElementLocationTools,
    DebugTools,
    CodeGenerationTools
):
    """
    Integration class that brings together all Playwright tool categories.
    
    This class provides a unified interface to all tools organized by functionality:
    - BrowserControl: Basic navigation (navigate, back, forward, close)
    - ContentExtraction: Screenshots, PDFs, text extraction
    - ElementInteraction: Clicks, fills, drag operations
    - Network: Response handling, user agent customization
    - AdvancedBrowser: JavaScript execution, DevTools integration
    - ElementLocation: Smart element location strategies
    - Debug: Debugging and testing
    - CodeGeneration: Code generation and session management
    """
    
    def __init__(self):
        """Initialize all parent classes."""
        BrowserControlTools.__init__(self)
        ContentExtractionTools.__init__(self)
        ElementInteractionTools.__init__(self)
        NetworkTools.__init__(self)
        AdvancedBrowserTools.__init__(self)
        ElementLocationTools.__init__(self)
        DebugTools.__init__(self)
        CodeGenerationTools.__init__(self)
        logger.info("PlaywrightTools initialized")

    # Smart method mapping dictionary for backward compatibility
    METHOD_MAP = {
        # Map old method names to new ones if names changed
        "playwright_navigate": "playwright_navigate",
        "playwright_go_back": "playwright_go_back",
        "playwright_go_forward": "playwright_go_forward",
        "playwright_close": "playwright_close",
        "playwright_screenshot": "playwright_screenshot",
        "playwright_save_as_pdf": "playwright_save_as_pdf",
        "playwright_get_visible_text": "playwright_get_visible_text",
        "playwright_get_visible_html": "playwright_get_visible_html",
        "playwright_click": "playwright_click",
        "playwright_iframe_click": "playwright_iframe_click",
        "playwright_hover": "playwright_hover",
        "playwright_fill": "playwright_fill",
        "playwright_select": "playwright_select",
        "playwright_drag": "playwright_drag",
        "playwright_press_key": "playwright_press_key",
        "playwright_expect_response": "playwright_expect_response",
        "playwright_assert_response": "playwright_assert_response",
        "playwright_custom_user_agent": "playwright_custom_user_agent",
        "playwright_evaluate": "playwright_evaluate",
        "playwright_console_logs": "playwright_console_logs",
        "playwright_smart_click": "playwright_smart_click",
        "playwright_multi_strategy_locate": "playwright_multi_strategy_locate",
        "playwright_debug_info": "playwright_debug_info",
        "start_codegen_session": "start_codegen_session",
        "end_codegen_session": "end_codegen_session",
        "get_codegen_session": "get_codegen_session",
        "clear_codegen_session": "clear_codegen_session"
    }
    
    async def dispatch_method(self, method_name: str, **kwargs) -> Dict[str, Any]:
        """
        Dynamic method dispatch for backward compatibility.
        
        Args:
            method_name: The name of the method to call
            **kwargs: Arguments to pass to the method
            
        Returns:
            The result of the method call
        """
        # Look up the actual method name if it's in the map
        actual_method_name = self.METHOD_MAP.get(method_name, method_name)
        
        # Get the method from self
        method = getattr(self, actual_method_name, None)
        
        if method and callable(method):
            try:
                logger.info(f"Dispatching method: {actual_method_name}")
                result = await method(**kwargs)
                return result
            except Exception as e:
                import traceback
                logger.error(f"Error executing {actual_method_name}: {str(e)}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                return {"status": "error", "message": f"Error in {method_name}: {str(e)}"}
        else:
            return {"status": "error", "message": f"Method not found: {method_name}"}
            
    async def cleanup_all(self):
        """Clean up all resources."""
        try:
            # Close all pages
            for page in self.pages:
                await page.close()
                
            self.pages = []
            
            # Close browser context
            if self.context:
                await self.context.close()
                
            # Close browser
            if self.browser:
                await self.browser.close()
                
            # Close playwright
            if self.playwright:
                await self.playwright.stop()
                
            logger.info("All resources cleaned up")
            return {"status": "success", "message": "All resources cleaned up"}
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    # Make sure we explicitly override the base class cleanup method
    async def cleanup(self):
        """
        Clean up pages but maintain browser persistence between command sequences.
        This method ensures the browser isn't closed after a command sequence completes.
        """
        try:
            # Close all pages but keep the browser running
            for page in self.pages:
                await page.close()
                
            self.pages = []
            logger.info("Cleaned up pages while preserving browser session")
            
            # Don't close the browser or context to enable persistent sessions
            return {"status": "success", "message": "Cleaned up pages while preserving browser session"}
            
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")
            return {"status": "error", "message": str(e)}
