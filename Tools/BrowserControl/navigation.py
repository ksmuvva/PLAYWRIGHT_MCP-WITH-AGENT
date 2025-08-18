"""
Browser Control Tools for MCP - Basic browser navigation and control
"""
import asyncio
from typing import Dict, Any, Optional

from ..base import PlaywrightBase, logger

class BrowserControlTools(PlaywrightBase):
    """Browser control and navigation tools."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_navigate(self, url: str, wait_for_load: bool = True, 
                               capture_screenshot: bool = False, page_index: int = 0) -> Dict[str, Any]:
        """Navigate to a URL."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            logger.info(f"Navigating to URL: {url}")
            
            # Determine wait_until conditions based on wait_for_load parameter
            wait_until = "domcontentloaded"
            if wait_for_load:
                wait_until = "load"  # Wait for window.load event
            
            # Navigate with appropriate timeout
            await page.goto(url, wait_until=wait_until, timeout=60000)  # 60 seconds timeout
            
            result = {
                "status": "success",
                "message": f"Navigated to {url}",
                "title": await page.title(),
                "url": page.url
            }
            
            # Take a screenshot if requested
            if capture_screenshot:
                screenshot_path = f"navigation_{int(page_index)}_{int(asyncio.get_event_loop().time())}.png"
                await page.screenshot(path=screenshot_path)
                result["screenshot"] = screenshot_path
                
            return result
            
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def playwright_go_back(self, page_index: int = 0) -> Dict[str, Any]:
        """Navigate back in browser history."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.go_back()
            return {
                "status": "success",
                "message": "Navigated back in history",
                "title": await page.title(),
                "url": page.url
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def playwright_go_forward(self, page_index: int = 0) -> Dict[str, Any]:
        """Navigate forward in browser history."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.go_forward()
            return {
                "status": "success",
                "message": "Navigated forward in history",
                "title": await page.title(),
                "url": page.url
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def playwright_reload(self, page_index: int = 0) -> Dict[str, Any]:
        """Reload/refresh the current page."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.reload()
            return {
                "status": "success",
                "message": "Page reloaded successfully",
                "title": await page.title(),
                "url": page.url
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def playwright_close(self, page_index: int = 0) -> Dict[str, Any]:
        """Close a page."""
        if page_index < 0 or page_index >= len(self.pages):
            return {"status": "error", "message": "Invalid page index"}
            
        try:
            await self.pages[page_index].close()
            self.pages.pop(page_index)
            return {
                "status": "success",
                "message": f"Closed page at index {page_index}",
                "pages_count": len(self.pages)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
