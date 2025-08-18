"""
Debug Tools for MCP - Tools for debugging and testing browser automation
"""
from typing import Dict, Any, Optional, List
import time
import os
import json
import asyncio

from ..base import PlaywrightBase, logger

class DebugTools(PlaywrightBase):
    """Tools for debugging and testing."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_debug_info(self, page_index: int = 0) -> Dict[str, Any]:
        """Get debugging information about the current page and browser state."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get basic page information
            url = page.url
            title = await page.title()
            
            # Get viewport size
            viewport_size = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
            
            # Get DOM stats
            dom_stats = await page.evaluate("""() => {
                return {
                    elements: document.querySelectorAll('*').length,
                    images: document.querySelectorAll('img').length,
                    links: document.querySelectorAll('a').length,
                    forms: document.querySelectorAll('form').length,
                    iframes: document.querySelectorAll('iframe').length,
                    scripts: document.querySelectorAll('script').length
                };
            }""")
            
            # Get performance metrics
            perf_metrics = await page.evaluate("""() => {
                const perfData = window.performance.timing;
                const navStart = perfData.navigationStart;
                
                return {
                    loadTime: perfData.loadEventEnd - navStart,
                    domContentLoaded: perfData.domContentLoadedEventEnd - navStart,
                    firstPaint: perfData.responseStart - navStart,
                    ttfb: perfData.responseStart - perfData.requestStart,
                    domInteractive: perfData.domInteractive - navStart
                };
            }""")
            
            # Check if there are any console errors
            console_errors = [log for log in self.console_logs if log["type"] == "error"]
            
            return {
                "status": "success",
                "page_info": {
                    "url": url,
                    "title": title,
                    "viewport": viewport_size
                },
                "dom_stats": dom_stats,
                "performance": perf_metrics,
                "errors_count": len(console_errors),
                "recent_errors": console_errors[-5:] if console_errors else []
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_element_info(self, selector: str, page_index: int = 0) -> Dict[str, Any]:
        """Get detailed information about a specific element."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Find the element
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "message": f"Element not found: {selector}"}
                
            # Get element properties
            element_info = await page.evaluate("""(element) => {
                const rect = element.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(element);
                
                // Get all attributes
                const attributes = {};
                for (const attr of element.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                // Get key CSS properties
                const cssProps = {};
                for (const prop of ['color', 'backgroundColor', 'fontSize', 'fontFamily', 
                                   'visibility', 'display', 'position', 'zIndex']) {
                    cssProps[prop] = computedStyle[prop];
                }
                
                // Check visibility
                const isVisible = !(
                    element.offsetWidth === 0 || 
                    element.offsetHeight === 0 || 
                    computedStyle.visibility === 'hidden' || 
                    computedStyle.display === 'none'
                );
                
                // Check if element is in viewport
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const inViewport = (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= viewportHeight &&
                    rect.right <= viewportWidth
                );
                
                return {
                    tagName: element.tagName.toLowerCase(),
                    id: element.id,
                    className: element.className,
                    textContent: element.textContent?.trim().substring(0, 100),
                    attributes: attributes,
                    size: {
                        width: rect.width,
                        height: rect.height
                    },
                    position: {
                        top: rect.top,
                        left: rect.left,
                        bottom: rect.bottom,
                        right: rect.right
                    },
                    isVisible: isVisible,
                    inViewport: inViewport,
                    cssProperties: cssProps
                };
            }""", element)
            
            # Take screenshot of element
            screenshot_path = f"element_debug_{int(time.time())}.png"
            await element.screenshot(path=screenshot_path)
            
            return {
                "status": "success",
                "element_info": element_info,
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_log_state(self, description: str, details: Optional[Dict[str, Any]] = None,
                                 page_index: int = 0, capture_screenshot: bool = True) -> Dict[str, Any]:
        """Log the current state for debugging purposes."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            timestamp = int(time.time())
            log_entry = {
                "timestamp": timestamp,
                "description": description,
                "url": page.url,
                "title": await page.title()
            }
            
            # Add custom details if provided
            if details:
                log_entry["details"] = details
                
            # Save screenshot if requested
            if capture_screenshot:
                screenshot_path = f"debug_log_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                log_entry["screenshot"] = screenshot_path
                
            # Write log entry to a file
            debug_dir = os.path.join(os.getcwd(), "debug_logs")
            os.makedirs(debug_dir, exist_ok=True)
            
            log_file = os.path.join(debug_dir, f"debug_log_{timestamp}.json")
            with open(log_file, "w") as f:
                json.dump(log_entry, f, indent=2)
                
            return {
                "status": "success",
                "message": f"Logged state: {description}",
                "log_file": log_file,
                "screenshot": log_entry.get("screenshot")
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_highlight_element(self, selector: str, color: str = "red",
                                       duration_ms: int = 1000, page_index: int = 0) -> Dict[str, Any]:
        """Highlight an element on the page for debugging."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Check if element exists
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "message": f"Element not found: {selector}"}
                
            # Add highlight
            original_style = await page.evaluate("""(selector, color) => {
                const element = document.querySelector(selector);
                if (!element) return null;
                
                const originalOutline = element.style.outline;
                const originalZIndex = element.style.zIndex;
                const originalPosition = element.style.position;
                
                element.style.outline = `3px solid ${color}`;
                element.style.zIndex = '9999';
                
                if (element.style.position === 'static') {
                    element.style.position = 'relative';
                }
                
                return {
                    outline: originalOutline,
                    zIndex: originalZIndex,
                    position: originalPosition
                };
            }""", selector, color)
            
            # Take screenshot with highlight
            screenshot_path = f"highlight_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            
            # Wait for specified duration
            await asyncio.sleep(duration_ms / 1000)  # Convert ms to seconds
            
            # Remove highlight
            await page.evaluate("""(selector, originalStyle) => {
                const element = document.querySelector(selector);
                if (!element) return;
                
                element.style.outline = originalStyle.outline;
                element.style.zIndex = originalStyle.zIndex;
                element.style.position = originalStyle.position;
            }""", selector, original_style)
            
            return {
                "status": "success",
                "message": f"Highlighted element {selector} for {duration_ms}ms",
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_assert_element_state(self, selector: str, expected_state: Dict[str, Any],
                                          page_index: int = 0) -> Dict[str, Any]:
        """Assert the state of an element for testing."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Find the element
            element = await page.query_selector(selector)
            if not element:
                return {
                    "status": "failed",
                    "message": f"Element not found: {selector}",
                    "assertion": "exists",
                    "expected": True,
                    "actual": False
                }
                
            # Get actual state
            actual_state = await page.evaluate("""(element) => {
                const isVisible = element.offsetWidth > 0 && element.offsetHeight > 0;
                const computedStyle = window.getComputedStyle(element);
                
                return {
                    visible: isVisible && 
                             computedStyle.visibility !== 'hidden' && 
                             computedStyle.display !== 'none',
                    text: element.textContent?.trim(),
                    value: element.value,
                    disabled: element.disabled,
                    checked: element.checked,
                    attributes: Object.fromEntries(
                        Array.from(element.attributes)
                            .map(attr => [attr.name, attr.value])
                    ),
                    cssProperties: {
                        display: computedStyle.display,
                        visibility: computedStyle.visibility,
                        backgroundColor: computedStyle.backgroundColor,
                        color: computedStyle.color
                    }
                };
            }""", element)
            
            # Check assertions
            failures = []
            
            # Check visibility
            if "visible" in expected_state and expected_state["visible"] != actual_state["visible"]:
                failures.append({
                    "assertion": "visible",
                    "expected": expected_state["visible"],
                    "actual": actual_state["visible"]
                })
                
            # Check text content
            if "text" in expected_state:
                expected_text = expected_state["text"]
                actual_text = actual_state["text"]
                
                # Check if it's a contains check or exact match
                if expected_text.startswith("*") and expected_text.endswith("*"):
                    expected_substring = expected_text[1:-1]
                    if expected_substring not in actual_text:
                        failures.append({
                            "assertion": "text_contains",
                            "expected": expected_substring,
                            "actual": actual_text
                        })
                else:
                    # Exact match
                    if expected_text != actual_text:
                        failures.append({
                            "assertion": "text_exact",
                            "expected": expected_text,
                            "actual": actual_text
                        })
            
            # Check value
            if "value" in expected_state and expected_state["value"] != actual_state["value"]:
                failures.append({
                    "assertion": "value",
                    "expected": expected_state["value"],
                    "actual": actual_state["value"]
                })
                
            # Check disabled state
            if "disabled" in expected_state and expected_state["disabled"] != actual_state["disabled"]:
                failures.append({
                    "assertion": "disabled",
                    "expected": expected_state["disabled"],
                    "actual": actual_state["disabled"]
                })
                
            # Check checked state
            if "checked" in expected_state and expected_state["checked"] != actual_state["checked"]:
                failures.append({
                    "assertion": "checked",
                    "expected": expected_state["checked"],
                    "actual": actual_state["checked"]
                })
                
            # Check attributes
            if "attributes" in expected_state:
                for attr_name, expected_value in expected_state["attributes"].items():
                    actual_value = actual_state["attributes"].get(attr_name)
                    
                    if expected_value != actual_value:
                        failures.append({
                            "assertion": f"attribute_{attr_name}",
                            "expected": expected_value,
                            "actual": actual_value
                        })
            
            # Check CSS properties
            if "cssProperties" in expected_state:
                for prop_name, expected_value in expected_state["cssProperties"].items():
                    actual_value = actual_state["cssProperties"].get(prop_name)
                    
                    if expected_value != actual_value:
                        failures.append({
                            "assertion": f"css_{prop_name}",
                            "expected": expected_value,
                            "actual": actual_value
                        })
            
            # Generate a screenshot on failure
            screenshot_path = None
            if failures:
                screenshot_path = f"assertion_failure_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                
                return {
                    "status": "failed",
                    "message": f"Element state assertion failed for {selector}",
                    "failures": failures,
                    "screenshot": screenshot_path
                }
            else:
                return {
                    "status": "success",
                    "message": f"Element state assertions passed for {selector}"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def playwright_auto_execute(self, action: str, target: str, value: str = "", 
                                   page_index: int = 0, max_attempts: int = 3, 
                                   capture_screenshot: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Automatically execute an action with intelligent tool selection and fallbacks.
        
        Args:
            action: The action to perform ('click', 'fill', 'select', etc.)
            target: The target element description or selector
            value: Any value to input (for fill, select actions)
            page_index: The index of the page to use
            max_attempts: Maximum number of attempts to try different strategies
            capture_screenshot: Whether to capture screenshots
            **kwargs: Additional arguments to pass to the tools
            
        This tool automatically determines the best approach to interact with elements.
        """
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        attempts = []
        
        try:
            # Map common actions to tool names
            action_tool_map = {
                "click": ["playwright_smart_click", "playwright_multi_strategy_locate", "playwright_js_locate"],
                "fill": ["playwright_fill", "playwright_multi_strategy_locate", "playwright_js_locate"],
                "navigate": ["playwright_navigate"],
                "select": ["playwright_select", "playwright_multi_strategy_locate"],
                "hover": ["playwright_hover", "playwright_multi_strategy_locate"]
            }
            
            # Get the appropriate tools for this action
            tool_names = action_tool_map.get(action.lower(), ["playwright_multi_strategy_locate"])
            
            # First attempt: Try the primary tool for this action
            primary_tool_name = tool_names[0]
            attempt = {"strategy": primary_tool_name, "target": target}
            
            try:
                # Make sure the tool exists
                if not hasattr(self, primary_tool_name):
                    logger.error(f"Tool {primary_tool_name} does not exist")
                    attempt["result"] = "error"
                    attempt["error"] = f"Tool {primary_tool_name} does not exist"
                    attempts.append(attempt)
                    raise AttributeError(f"Tool {primary_tool_name} does not exist")
                
                # Get the method and verify it's callable
                method = getattr(self, primary_tool_name)
                if not callable(method):
                    logger.error(f"Tool {primary_tool_name} is not callable")
                    attempt["result"] = "error"
                    attempt["error"] = f"Tool {primary_tool_name} is not callable"
                    attempts.append(attempt)
                    raise TypeError(f"Tool {primary_tool_name} is not callable")
                
                # Prepare arguments based on the action
                tool_args = kwargs.copy()
                
                # Common arguments
                tool_args["page_index"] = page_index
                tool_args["capture_screenshot"] = capture_screenshot
                
                # Action-specific arguments
                if primary_tool_name == "playwright_navigate":
                    tool_args["url"] = target
                elif primary_tool_name == "playwright_smart_click":
                    tool_args["text"] = target
                elif primary_tool_name == "playwright_fill":
                    tool_args["selector"] = target
                    tool_args["text"] = value
                elif primary_tool_name == "playwright_select":
                    tool_args["selector"] = target
                    tool_args["value"] = value
                elif primary_tool_name == "playwright_hover":
                    tool_args["selector"] = target
                elif primary_tool_name == "playwright_multi_strategy_locate":
                    tool_args["description"] = target
                    tool_args["action"] = action
                    tool_args["text_input"] = value
                    
                # Execute the method with the prepared arguments
                result = await method(**tool_args)
                
                if result.get("status") == "success":
                    logger.info(f"Direct {action} with {primary_tool_name} successful")
                    attempt["result"] = "success"
                    attempts.append(attempt)
                    return {
                        "status": "success",
                        "message": f"Action '{action}' completed successfully with direct tool",
                        "tool_used": primary_tool_name,
                        "details": result
                    }
                else:
                    logger.info(f"Direct {action} with {primary_tool_name} failed: {result.get('message')}")
                    attempt["result"] = "failed"
                    attempt["error"] = result.get("message", "Unknown error")
                    attempts.append(attempt)
                    
            except Exception as e:
                attempt["result"] = "error"
                attempt["error"] = str(e)
                attempts.append(attempt)
            
            # If we reach here, the primary tool failed
            
            # Fallback attempts: Try alternate tools
            for i, tool_name in enumerate(tool_names[1:], 1):
                if i >= max_attempts:
                    break
                
                logger.info(f"Trying fallback #{i}: {tool_name}")
                attempt = {"strategy": tool_name, "target": target}
                
                try:
                    # Make sure the tool exists
                    if not hasattr(self, tool_name):
                        attempt["result"] = "error"
                        attempt["error"] = f"Tool {tool_name} does not exist"
                        attempts.append(attempt)
                        continue
                    
                    # Get the method
                    method = getattr(self, tool_name)
                    
                    # Prepare arguments based on the tool
                    tool_args = kwargs.copy()
                    tool_args["page_index"] = page_index
                    tool_args["capture_screenshot"] = capture_screenshot
                    
                    if tool_name == "playwright_multi_strategy_locate":
                        tool_args["description"] = target
                        tool_args["action"] = action
                        tool_args["text_input"] = value
                    elif tool_name == "playwright_js_locate":
                        tool_args["description"] = target
                        tool_args["action"] = action
                        tool_args["text_input"] = value
                    elif tool_name == "playwright_vision_locator":
                        tool_args["text"] = target
                        tool_args["action"] = action
                        tool_args["text_input"] = value
                    
                    # Execute the method
                    result = await method(**tool_args)
                    
                    if result.get("status") == "success":
                        logger.info(f"Fallback {action} with {tool_name} successful")
                        attempt["result"] = "success"
                        attempts.append(attempt)
                        return {
                            "status": "success",
                            "message": f"Action '{action}' completed successfully with fallback tool",
                            "tool_used": tool_name,
                            "fallback_attempt": i,
                            "details": result
                        }
                    else:
                        logger.info(f"Fallback {action} with {tool_name} failed: {result.get('message')}")
                        attempt["result"] = "failed"
                        attempt["error"] = result.get("message", "Unknown error")
                        attempts.append(attempt)
                        
                except Exception as e:
                    attempt["result"] = "error"
                    attempt["error"] = str(e)
                    attempts.append(attempt)
            
            # Final fallback: Special handling for certain actions
            logger.info("Trying final specialized fallbacks")
            
            # For click actions, try a generic JavaScript click as last resort
            if action.lower() == "click":
                attempt = {"strategy": "js_direct_click", "target": target}
                
                try:
                    # Try to find element with generic selector or containing text
                    script = f"""
                    (target) => {{
                        // Try by ID
                        let element = document.getElementById(target);
                        
                        // Try by any selector
                        if (!element) {{
                            try {{
                                element = document.querySelector(target);
                            }} catch (e) {{
                                // Invalid selector, continue to other methods
                            }}
                        }}
                        
                        // Try by text content
                        if (!element) {{
                            const elements = Array.from(document.querySelectorAll('*'));
                            element = elements.find(el => 
                                (el.innerText && el.innerText.includes(target)) || 
                                (el.textContent && el.textContent.includes(target))
                            );
                        }}
                        
                        // If element found, click it
                        if (element) {{
                            element.click();
                            return {{
                                success: true,
                                elementInfo: {{
                                    tagName: element.tagName,
                                    id: element.id,
                                    className: element.className
                                }}
                            }};
                        }}
                        
                        return {{ success: false, message: "Element not found" }};
                    }}
                    """
                    
                    result = await page.evaluate(script, target)
                    
                    if result.get("success"):
                        attempt["result"] = "success"
                        attempts.append(attempt)
                        
                        screenshot_path = None
                        if capture_screenshot:
                            screenshot_path = f"js_direct_click_{int(time.time())}.png"
                            await page.screenshot(path=screenshot_path)
                            
                        return {
                            "status": "success",
                            "message": f"Clicked element via direct JavaScript as last resort",
                            "tool_used": "js_direct_click",
                            "element_info": result.get("elementInfo"),
                            "screenshot": screenshot_path
                        }
                    else:
                        attempt["result"] = "failed"
                        attempt["error"] = result.get("message", "Unknown error")
                        attempts.append(attempt)
                        
                except Exception as e:
                    attempt["result"] = "error"
                    attempt["error"] = str(e)
                    attempts.append(attempt)
            
            # All attempts failed
            logger.error(f"All attempts to perform {action} on {target} failed")
            
            # Take a final screenshot to help debug
            debug_screenshot = None
            if capture_screenshot:
                debug_screenshot = f"auto_execute_failed_{int(time.time())}.png"
                await page.screenshot(path=debug_screenshot)
                
            return {
                "status": "error",
                "message": f"Failed to perform {action} on {target} after {len(attempts)} attempts",
                "attempts": attempts,
                "debug_screenshot": debug_screenshot,
                "suggestion": "Try a more specific target or a different approach"
            }
            
        except Exception as e:
            logger.error(f"Error in auto_execute: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def playwright_check_element(self, selector: str, property: str, expected_value: str = None, 
                                     page_index: int = 0) -> Dict[str, Any]:
        """
        Check element property/state - simplified version for LLM usage.
        
        Args:
            selector: CSS selector for the element
            property: Property to check (text, value, checked, visible, disabled, etc.)
            expected_value: Expected value (optional, for comparison)
            page_index: Page index (default 0)
            
        Returns:
            Dictionary with status and property value
        """
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Find the element
            element = await page.query_selector(selector)
            if not element:
                return {
                    "status": "error", 
                    "message": f"Element not found: {selector}"
                }
            
            # Get the property value based on type
            if property == "text":
                actual_value = await element.text_content()
                actual_value = actual_value.strip() if actual_value else ""
            elif property == "value":
                actual_value = await element.get_attribute("value") or ""
            elif property == "checked":
                actual_value = await element.is_checked()
            elif property == "visible":
                actual_value = await element.is_visible()
            elif property == "disabled":
                actual_value = await element.is_disabled()
            elif property == "enabled":
                actual_value = await element.is_enabled()
            else:
                # Try to get as attribute
                actual_value = await element.get_attribute(property)
            
            result = {
                "status": "success",
                "selector": selector,
                "property": property,
                "actual_value": actual_value
            }
            
            # If expected value provided, compare
            if expected_value is not None:
                if isinstance(actual_value, bool):
                    expected_bool = expected_value.lower() in ('true', '1', 'yes', 'on')
                    matches = actual_value == expected_bool
                else:
                    matches = str(actual_value) == str(expected_value)
                
                result.update({
                    "expected_value": expected_value,
                    "matches": matches,
                    "assertion": "pass" if matches else "fail"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking element {selector}: {e}")
            return {
                "status": "error",
                "message": f"Error checking element: {str(e)}"
            }
    
    async def playwright_is_browser_alive(self, page_index: int = 0) -> Dict[str, Any]:
        """Check if the browser is still alive and responsive."""
        try:
            # Use the base class method to check browser status
            is_alive = await self.is_browser_alive()
            return {
                "status": "success",
                "alive": is_alive,
                "message": f"Browser is {'alive' if is_alive else 'not alive'}"
            }
        except Exception as e:
            return {
                "status": "error",
                "alive": False,
                "message": f"Error checking browser: {str(e)}"
            }
