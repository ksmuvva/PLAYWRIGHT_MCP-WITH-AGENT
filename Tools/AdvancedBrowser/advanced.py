"""
Advanced Browser Tools for MCP - JavaScript execution and console logs
"""
from typing import Dict, Any, Optional, List
import time

from ..base import PlaywrightBase, logger

class AdvancedBrowserTools(PlaywrightBase):
    """Advanced browser capabilities like JavaScript execution and console logs."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_evaluate(self, script: str, page_index: int = 0, arg: Any = None) -> Dict[str, Any]:
        """Execute JavaScript in the page context."""
        # Ensure browser is initialized
        await self._ensure_browser_initialized()
        
        # Get page with extra validation
        try:
            page = await self._get_page(page_index)
            if not page:
                logger.error(f"Invalid page index or failed to create page: {page_index}")
                return {"status": "error", "message": f"Invalid page index or failed to create page: {page_index}"}
        except Exception as e:
            logger.error(f"Error getting page for evaluate: {e}")
            return {"status": "error", "message": f"Error getting page for evaluate: {str(e)}"}
        
        try:
            logger.info(f"Executing script: {script[:50]}..." if len(script) > 50 else f"Executing script: {script}")
            
            # Check if we need to wrap the script in a function
            if "return " in script and not ("() =>" in script or "function" in script):
                logger.info("Script contains return statement, wrapping in function")
                script = f"() => {{ {script} }}"
                
            # Execute the script in the page context
            if arg is not None:
                result = await page.evaluate(script, arg)
            else:
                result = await page.evaluate(script)
            
            logger.info(f"Script executed successfully, result type: {type(result).__name__}")
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error evaluating script: {e}")
            # Provide more helpful error messages
            error_msg = str(e)
            if "Illegal return statement" in error_msg:
                error_msg += " (Try wrapping your script in '() => { ... }' function syntax)"
                
            return {
                "status": "error", 
                "message": error_msg,
                "script": script  # Include the problematic script for debugging
            }
    
    async def playwright_console_logs(self, page_index: int = 0, count: int = 10) -> Dict[str, Any]:
        """Get console logs from the page."""
        await self._get_page(page_index)  # ensure page exists
        
        try:
            # Get last N console logs or all if fewer than N
            log_count = min(count, len(self.console_logs))
            filtered_logs = self.console_logs[-log_count:] if log_count > 0 else []
            
            return {
                "status": "success",
                "message": f"Retrieved {len(filtered_logs)} console logs",
                "logs": filtered_logs
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def playwright_cdp_evaluate(self, script: str, page_index: int = 0) -> Dict[str, Any]:
        """Execute Chrome DevTools Protocol commands."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get a CDP session (only works with Chromium-based browsers)
            client = await page.context.new_cdp_session(page)
            
            # Execute the CDP command
            result = await client.send("Runtime.evaluate", {
                "expression": script,
                "returnByValue": True
            })
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    async def playwright_devtools_info(self, page_index: int = 0) -> Dict[str, Any]:
        """Get debugging information from DevTools."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Use CDP to get debugging information
            client = await page.context.new_cdp_session(page)
            
            # Get JavaScript heap info
            memory = await client.send("Runtime.getHeapUsage")
            
            # Get performance metrics
            metrics = await client.send("Performance.getMetrics")
            
            # Get network info
            resources = await page.evaluate("""() => {
                return performance.getEntriesByType('resource').map(r => ({
                    name: r.name,
                    duration: r.duration,
                    transferSize: r.transferSize
                }));
            }""")
            
            return {
                "status": "success",
                "memoryInfo": memory,
                "metrics": metrics,
                "resources": resources
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_performance_metrics(self, page_index: int = 0) -> Dict[str, Any]:
        """Get performance metrics for the page."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get navigation timing
            navigation_timing = await page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        navigationStart: timing.navigationStart,
                        loadEventEnd: timing.loadEventEnd,
                        domContentLoadedEventEnd: timing.domContentLoadedEventEnd,
                        firstPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-paint')?.startTime,
                        firstContentfulPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-contentful-paint')?.startTime
                    };
                }
            """)
            
            return {"status": "success", "performanceMetrics": navigation_timing}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_switch_tab(self, target_page_index: int, page_index: int = 0) -> Dict[str, Any]:
        """Switch to a different tab/page."""
        try:
            if target_page_index >= len(self.pages):
                return {"status": "error", "message": f"Invalid page index: {target_page_index}"}
            
            # Bring the page to front
            await self.pages[target_page_index].bring_to_front()
            return {"status": "success", "message": f"Switched to page {target_page_index}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
