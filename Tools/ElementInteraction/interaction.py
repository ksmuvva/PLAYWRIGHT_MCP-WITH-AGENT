"""
Element Interaction Tools for MCP - Click, fill, select, and other interactions
"""
from typing import Dict, Any, Optional
import time
import asyncio

from ..base import PlaywrightBase, logger

class ElementInteractionTools(PlaywrightBase):
    """Tools for interacting with page elements."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_click(self, selector: str, page_index: int = 0, 
                             capture_screenshot: bool = False, fallback: bool = True) -> Dict[str, Any]:
        """
        Click on an element with fallback strategies.
        
        Args:
            selector: CSS/XPath selector to locate the element
            page_index: Index of the page to operate on
            capture_screenshot: Whether to capture screenshots
            fallback: Whether to attempt fallback strategies if direct click fails
        """
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Try standard click first
            await page.click(selector)
            
            result = {
                "status": "success",
                "message": f"Clicked element: {selector}"
            }
            
            if capture_screenshot:
                screenshot_path = f"click_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                result["screenshot"] = screenshot_path
                
            return result
            
        except Exception as e:
            if not fallback:
                return {"status": "error", "message": str(e)}
            
            # Try alternative strategies if fallback is enabled
            try:
                logger.info(f"Direct click failed, trying force click for: {selector}")
                
                # Try force click with JavaScript
                element = await page.query_selector(selector)
                if not element:
                    return {"status": "error", "message": f"Element not found: {selector}"}
                    
                await page.evaluate("(element) => element.click()", element)
                
                result = {
                    "status": "success", 
                    "message": f"Clicked element with JavaScript fallback: {selector}",
                    "fallback_used": True
                }
                
                if capture_screenshot:
                    screenshot_path = f"click_fallback_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)
                    result["screenshot"] = screenshot_path
                    
                return result
                
            except Exception as fallback_error:
                return {"status": "error", "message": f"Click failed: {str(e)}. Fallback error: {str(fallback_error)}"}
    
    async def playwright_click_and_switch_tab(self, selector: str, page_index: int = 0,
                                           capture_screenshot: bool = False) -> Dict[str, Any]:
        """Click on an element that opens a new tab and switch to it."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Store current count of pages
            original_page_count = len(self.pages)
            
            # Set up a listener for new pages/tabs
            async with page.expect_popup() as popup_info:
                # Click the element that should open a new tab
                await page.click(selector)
            
            # Get the new page
            new_page = await popup_info.value
            
            # Add the new page to our page collection
            self.pages.append(new_page)
            new_page_index = len(self.pages) - 1
            
            # Wait for the new page to load
            await new_page.wait_for_load_state("domcontentloaded")
            
            result = {
                "status": "success",
                "message": f"Clicked element and switched to new tab: {selector}",
                "original_page_index": page_index,
                "new_page_index": new_page_index,
                "new_page_url": new_page.url,
                "new_page_title": await new_page.title()
            }
            
            if capture_screenshot:
                screenshot_path = f"new_tab_{int(time.time())}.png"
                await new_page.screenshot(path=screenshot_path)
                result["screenshot"] = screenshot_path
                
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_iframe_click(self, iframe_selector: str, element_selector: str,
                                    page_index: int = 0, capture_screenshot: bool = False) -> Dict[str, Any]:
        """Click on an element inside an iframe."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get the iframe
            iframe = await page.frame_locator(iframe_selector)
            if not iframe:
                return {"status": "error", "message": f"Iframe not found: {iframe_selector}"}
            
            # Click the element inside the iframe
            await iframe.locator(element_selector).click()
            
            result = {
                "status": "success",
                "message": f"Clicked element in iframe: {element_selector}"
            }
            
            if capture_screenshot:
                screenshot_path = f"iframe_click_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                result["screenshot"] = screenshot_path
                
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_hover(self, selector: str, page_index: int = 0,
                             capture_screenshot: bool = False) -> Dict[str, Any]:
        """Hover over an element."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.hover(selector)
            
            result = {
                "status": "success",
                "message": f"Hovered over element: {selector}"
            }
            
            if capture_screenshot:
                screenshot_path = f"hover_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                result["screenshot"] = screenshot_path
                
            return result
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_fill(self, selector: str, text: str, page_index: int = 0) -> Dict[str, Any]:
        """Fill a form field."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.fill(selector, text)
            
            return {
                "status": "success",
                "message": f"Filled element {selector} with text: {text}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_select(self, selector: str, value: str, page_index: int = 0) -> Dict[str, Any]:
        """Select an option from a dropdown."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.select_option(selector, value)
            
            return {
                "status": "success",
                "message": f"Selected option with value '{value}' from dropdown {selector}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_drag(self, source_selector: str, target_selector: str,
                            page_index: int = 0) -> Dict[str, Any]:
        """Drag and drop elements."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get source and target elements
            source = await page.query_selector(source_selector)
            target = await page.query_selector(target_selector)
            
            if not source:
                return {"status": "error", "message": f"Source element not found: {source_selector}"}
                
            if not target:
                return {"status": "error", "message": f"Target element not found: {target_selector}"}
            
            # Perform the drag and drop action
            await source.drag_to(target)
            
            return {
                "status": "success",
                "message": f"Dragged element {source_selector} to {target_selector}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_press_key(self, key: str, page_index: int = 0) -> Dict[str, Any]:
        """Press a keyboard key."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.keyboard.press(key)
            
            return {
                "status": "success",
                "message": f"Pressed key: {key}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_upload_file(self, selector: str, file_path: str, page_index: int = 0) -> Dict[str, Any]:
        """Upload a file to a file input element."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.set_input_files(selector, file_path)
            return {"status": "success", "message": f"File uploaded: {file_path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_handle_dialog(self, action: str = "accept", text: str = "", page_index: int = 0) -> Dict[str, Any]:
        """Handle browser dialogs (alert, confirm, prompt)."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Set up dialog handler
            if action == "accept":
                page.on("dialog", lambda dialog: dialog.accept(text if text else None))
            elif action == "dismiss":
                page.on("dialog", lambda dialog: dialog.dismiss())
            
            return {"status": "success", "message": f"Dialog handler set to {action}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
