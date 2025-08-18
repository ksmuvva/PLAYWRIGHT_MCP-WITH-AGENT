"""
Network Tools for MCP - Network request/response handling and monitoring
"""
from typing import Dict, Any, Optional
import asyncio
import time

from ..base import PlaywrightBase, logger

class NetworkTools(PlaywrightBase):
    """Tools for monitoring and interacting with network activity."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_expect_response(self, url_pattern: str, timeout_ms: int = 30000,
                                       page_index: int = 0) -> Dict[str, Any]:
        """Wait for a specific HTTP response."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Wait for the response matching the given URL pattern
            async with page.expect_response(url_pattern, timeout=timeout_ms) as response_info:
                response = await response_info.value
                
            # Get basic response information
            status = response.status
            status_text = response.status_text
            
            # Try to get response body, with a fallback for binary responses
            try:
                body = await response.text()
            except:
                body = "(binary data or response already consumed)"
                
            # Get response headers
            headers = response.headers
                
            return {
                "status": "success",
                "message": f"Received response for {url_pattern}",
                "response_url": response.url,
                "response_status": status,
                "response_status_text": status_text,
                "response_headers": headers,
                "response_body_preview": body[:1000] if len(body) > 1000 else body
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_assert_response(self, url_pattern: str, status_code: int = 200,
                                       page_index: int = 0) -> Dict[str, Any]:
        """Assert properties of an HTTP response."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Wait for the response matching the given URL pattern
            async with page.expect_response(url_pattern) as response_info:
                response = await response_info.value
                
            actual_status = response.status
            
            if actual_status == status_code:
                return {
                    "status": "success",
                    "message": f"Response status code matched: {status_code}",
                    "url": response.url
                }
            else:
                return {
                    "status": "error",
                    "message": f"Response status code mismatch. Expected: {status_code}, Actual: {actual_status}",
                    "url": response.url
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_custom_user_agent(self, user_agent: str, page_index: int = 0) -> Dict[str, Any]:
        """Set a custom user agent."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.set_extra_http_headers({"User-Agent": user_agent})
            
            return {
                "status": "success",
                "message": f"Set custom user agent: {user_agent}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_network_info(self, page_index: int = 0, include_request_body: bool = False, 
                                      include_response_body: bool = False) -> Dict[str, Any]:
        """Get network information including cookies and headers."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get cookies
            cookies = await page.context.cookies()
            
            # Get current URL
            url = page.url
            
            # Get basic network info
            network_info = {
                "status": "success",
                "url": url,
                "cookies": cookies,
                "userAgent": await page.evaluate("navigator.userAgent")
            }
            
            # Add request/response body info if requested
            if include_request_body or include_response_body:
                network_info["note"] = "Request/response body capture requires setting up network listeners before navigation"
            
            return network_info
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
