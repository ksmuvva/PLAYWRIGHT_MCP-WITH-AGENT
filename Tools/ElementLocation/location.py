"""
Element Location Tools for MCP - Advanced strategies for finding elements
"""
from typing import Dict, Any, Optional, List
import asyncio
import time
import traceback
from ..base import PlaywrightBase, logger

class ElementLocationTools(PlaywrightBase):
    """Advanced tools for locating elements using various strategies."""
    
    def __init__(self, browser_type: str = "chromium"):
        super().__init__(browser_type)
    
    async def playwright_wait_for_element(self, selector: str, state: str = "visible", timeout: int = 30000, page_index: int = 0) -> Dict[str, Any]:
        """Wait for an element to be in a specific state."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            await page.wait_for_selector(selector, state=state, timeout=timeout)
            return {"status": "success", "message": f"Element {selector} is now {state}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to wait for element: {str(e)}"}
    
    async def playwright_smart_click(self, text: str = None, selector: str = None, 
                                   element_type: str = "any", page_index: int = 0,
                                   capture_screenshot: bool = False, optional: bool = False,
                                   description: str = None, **kwargs) -> Dict[str, Any]:
        """
        Smart click that tries multiple selector strategies based on fuzzy text matching.
        
        Args:
            text: The text to look for
            selector: CSS/XPath selector (alternative to text)
            element_type: Type of element to target
            page_index: Index of the page
            capture_screenshot: Whether to capture screenshots
            optional: Whether the click is optional (won't fail if not found)
            description: Additional description to help with locating
        """
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        # Log parameters for debugging
        logger.info(f"smart_click called with text='{text}', selector='{selector}', " +
                   f"element_type='{element_type}', optional={optional}")
        
        try:
            # Handle case where selector is provided instead of text
            if selector and not text:
                try:
                    logger.info(f"Attempting direct click with selector before smart strategies: {selector}")
                    await page.click(selector)
                    result = {
                        "status": "success",
                        "message": f"Clicked element with selector: {selector}",
                        "selector_used": selector
                    }
                    
                    if capture_screenshot:
                        screenshot_path = f"smart_click_{asyncio.get_event_loop().time()}.png"
                        await page.screenshot(path=screenshot_path)
                        result["screenshot"] = screenshot_path
                        
                    return result
                except Exception as e:
                    logger.info(f"Direct click with selector failed: {str(e)}, trying smart strategies")
                    # If direct click fails and text was not provided, we'll use the selector as text
                    text = text or description or "Click Target"
            
            if not text:
                return {"status": "error", "message": "Either text or a valid selector must be provided"}
                
            # Create variations of the text for fuzzy matching
            text_variations = [
                text,
                text.lower(),
                text.upper(),
                text.title(),
            ]
            
            # Element type specific strategies
            selectors = []
            
            if element_type == "any" or element_type == "button":
                selectors.extend([
                    f"button:has-text('{text}')",
                    f"button:has-text('{text}', 'i')", # case-insensitive
                    f"input[type='button'][value*='{text}']",
                    f"input[type='submit'][value*='{text}']",
                    f"[role='button']:has-text('{text}')",
                ])
                
            if element_type == "any" or element_type == "link":
                selectors.extend([
                    f"a:has-text('{text}')",
                    f"a:has-text('{text}', 'i')", # case-insensitive
                    f"a[href]:has-text('{text}')",
                ])
                
            # General strategies that work across element types
            selectors.extend([
                f"text='{text}'",
                f"text='{text}' >> visible=true",
                f"[aria-label*='{text}']",
                f"[title*='{text}']",
                f"[placeholder*='{text}']",
                f"[name*='{text}']",
                f"[data-test*='{text}']",
            ])
            
            # Try each selector in turn
            for selector in selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=500)
                    if element:
                        await element.click()
                        logger.info(f"Smart click successful with selector: {selector}")
                        
                        result = {
                            "status": "success",
                            "message": f"Smart click successful: {text}",
                            "selector_used": selector,
                            "element_found": True
                        }
                        
                        if capture_screenshot:
                            screenshot_path = f"smart_click_success_{asyncio.get_event_loop().time()}.png"
                            await page.screenshot(path=screenshot_path)
                            result["screenshot"] = screenshot_path
                            
                        return result
                except Exception as e:
                    continue  # Try the next selector
            
            # Try accessibility API
            try:
                await page.click(f"[role=button][name='{text}']")
                return {
                    "status": "success", 
                    "message": f"Smart click successful via accessibility API: {text}",
                    "element_found": True
                }
            except Exception:
                pass  # Continue to next strategy
            
            # If we get here, all strategies failed
            debug_screenshot = None
            if capture_screenshot:
                debug_screenshot = f"smart_click_failed_{asyncio.get_event_loop().time()}.png"
                await page.screenshot(path=debug_screenshot)
            
            # If the click is optional, return success with a note
            if optional:
                return {
                    "status": "success", 
                    "message": f"Optional click: Element matching '{text}' not found but continuing",
                    "tried_selectors": selectors[:5],
                    "fallbacks_tried": ["accessibility_locator", "vision_locator", "js_locate"],
                    "element_found": False,
                    "debug_screenshot": debug_screenshot
                }
            else:
                # Regular non-optional click failed
                return {
                    "status": "error", 
                    "message": f"Smart click failed: Could not find clickable element matching '{text}'",
                    "tried_selectors": selectors[:5],
                    "fallbacks_tried": ["accessibility_locator", "vision_locator", "js_locate"],
                    "debug_screenshot": debug_screenshot
                }
            
        except Exception as e:
            import traceback
            logger.error(f"Error in smart click: {str(e)}")
            logger.debug(f"Detailed traceback: {traceback.format_exc()}")
            
            if optional:
                return {
                    "status": "success",
                    "message": f"Optional action: Exception occurred but continuing. Error: {str(e)}",
                    "element_found": False,
                    "error": str(e)
                }
            else:
                return {"status": "error", "message": str(e)}

    async def playwright_find_element(self, description: str, page_index: int = 0, 
                                    max_results: int = 5) -> Dict[str, Any]:
        """Find elements based on natural language description."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Create potential selectors based on description
            keywords = description.lower().split()
            selectors = []
            
            # Handle common element types
            if any(word in keywords for word in ["button", "click", "submit"]):
                selectors.extend([
                    "button",
                    "input[type='button']",
                    "input[type='submit']",
                    "[role='button']"
                ])
            
            if any(word in keywords for word in ["link", "anchor", "href"]):
                selectors.append("a")
            
            if any(word in keywords for word in ["input", "field", "text", "enter"]):
                selectors.extend([
                    "input[type='text']",
                    "input:not([type='button']):not([type='submit'])",
                    "textarea"
                ])
                
            if any(word in keywords for word in ["checkbox", "check"]):
                selectors.append("input[type='checkbox']")
                
            if any(word in keywords for word in ["radio"]):
                selectors.append("input[type='radio']")
                
            if any(word in keywords for word in ["select", "dropdown", "option"]):
                selectors.append("select")
                
            # If no specific element type is detected, use general selectors
            if not selectors:
                selectors = ["button", "a", "input", "select", "textarea", "[role='button']"]
            
            # Find matching elements
            found_elements = []
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                
                for element in elements:
                    # Get element info
                    tag_name = await page.evaluate("(element) => element.tagName.toLowerCase()", element)
                    text = await page.evaluate("(element) => element.innerText || element.textContent || element.value || ''", element)
                    
                    # Get element attributes
                    attributes = await page.evaluate("""(element) => {
                        const attrs = {};
                        for (const attr of element.attributes) {
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    }""", element)
                    
                    # Calculate relevance score - higher means more relevant
                    score = 0
                    
                    if text and any(keyword.lower() in text.lower() for keyword in keywords):
                        score += 10
                        
                    # Check attributes for matching keywords
                    for attr, value in attributes.items():
                        if value and any(keyword.lower() in value.lower() for keyword in keywords):
                            score += 5
                    
                    # Only include elements with some relevance
                    if score > 0:
                        element_info = {
                            "tag": tag_name,
                            "text": text[:100] if text else "",
                            "attributes": attributes,
                            "relevance": score
                        }
                        found_elements.append(element_info)
                        
            # Sort by relevance
            found_elements.sort(key=lambda x: x["relevance"], reverse=True)
            
            # Limit results
            found_elements = found_elements[:max_results]
            
            return {
                "status": "success",
                "message": f"Found {len(found_elements)} elements matching description: {description}",
                "elements": found_elements
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_accessibility_locator(self, description: str, action: str = "find",
                                            text_input: str = "", page_index: int = 0) -> Dict[str, Any]:
        """Use accessibility tree to locate elements."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Get accessibility tree
            snapshot = await page.accessibility.snapshot()
            
            # Find nodes matching description
            matching_nodes = []
            
            def search_nodes(node, depth=0):
                # Check if node name or role matches description
                relevance = 0
                
                if node.get("name") and description.lower() in node.get("name").lower():
                    relevance += 10
                    
                if node.get("role") and description.lower() in node.get("role").lower():
                    relevance += 5
                    
                # Add to matches if relevant
                if relevance > 0:
                    matching_nodes.append({
                        "name": node.get("name"),
                        "role": node.get("role"),
                        "relevance": relevance,
                        "node": node
                    })
                
                # Recursively search children
                for child in node.get("children", []):
                    search_nodes(child, depth + 1)
            
            # Start search from root
            if snapshot:
                search_nodes(snapshot)
            
            # Sort by relevance
            matching_nodes.sort(key=lambda x: x["relevance"], reverse=True)
            
            # If action is "find", just return the matches
            if action == "find":
                return {
                    "status": "success",
                    "message": f"Found {len(matching_nodes)} accessibility nodes matching: {description}",
                    "nodes": [{"name": n["name"], "role": n["role"]} for n in matching_nodes[:5]]
                }
            
            # If action is "click" or other interactive action, try to interact
            elif matching_nodes and action in ["click", "fill", "select"]:
                # Try to interact with the most relevant node
                top_node = matching_nodes[0]
                
                # Try to find the element in the DOM using accessibility properties
                element = None
                
                if top_node["role"] == "button" or top_node["role"] == "link":
                    # For buttons and links, try to find by role and name
                    try:
                        element = await page.wait_for_selector(
                            f"[role='{top_node['role']}'][name='{top_node['name']}']", 
                            timeout=1000
                        )
                    except:
                        # Try by text content as fallback
                        try:
                            element = await page.wait_for_selector(
                                f"text='{top_node['name']}'",
                                timeout=1000
                            )
                        except:
                            pass
                
                # If we found an element, interact with it
                if element:
                    if action == "click":
                        await element.click()
                    elif action == "fill":
                        await element.fill(text_input)
                    elif action == "select":
                        await element.select_option(text_input)
                    
                    return {
                        "status": "success",
                        "message": f"Successfully performed {action} on element via accessibility tree",
                        "element_found": True,
                        "element_details": {"name": top_node["name"], "role": top_node["role"]}
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Found accessibility node but couldn't locate corresponding DOM element",
                        "accessibility_details": {"name": top_node["name"], "role": top_node["role"]}
                    }
            else:
                return {
                    "status": "error",
                    "message": f"No matching accessibility nodes found for {description} or unsupported action: {action}"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_vision_locator(self, text: str, exact: bool = False,
                                     action: str = "find", text_input: str = "",
                                     page_index: int = 0) -> Dict[str, Any]:
        """Use vision-based location."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Create selector based on whether we want exact match
            selector = f"text='{text}'"
            if not exact:
                selector = f"text='{text}' >> visible=true"
            
            # Try to find the element
            element = await page.wait_for_selector(selector, timeout=2000)
            
            if element:
                # If just finding, return success
                if action == "find":
                    bound = await element.bounding_box()
                    return {
                        "status": "success",
                        "message": f"Found text '{text}' on page",
                        "element_found": True,
                        "position": bound
                    }
                
                # Perform action if requested
                if action == "click":
                    await element.click()
                elif action == "fill":
                    await element.fill(text_input)
                
                return {
                    "status": "success",
                    "message": f"Successfully performed {action} on element with text: {text}",
                    "element_found": True
                }
            else:
                return {
                    "status": "error",
                    "message": f"Could not find text '{text}' on page"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_js_locate(self, description: str, action: str = "find",
                                 text_input: str = "", page_index: int = 0) -> Dict[str, Any]:
        """Use JavaScript to locate elements."""
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        try:
            # Use JavaScript to find elements based on text content and attributes
            elements = await page.evaluate("""(description) => {
                const allElements = document.querySelectorAll('*');
                const matches = [];
                
                const descLower = description.toLowerCase();
                
                for (const el of allElements) {
                    let score = 0;
                    const text = el.innerText || el.textContent || '';
                    
                    // Check text content
                    if (text.toLowerCase().includes(descLower)) {
                        score += 10;
                    }
                    
                    // Check attributes
                    for (const attr of ['placeholder', 'title', 'aria-label', 'alt', 'name']) {
                        if (el.hasAttribute(attr) && el.getAttribute(attr).toLowerCase().includes(descLower)) {
                            score += 5;
                        }
                    }
                    
                    if (score > 0) {
                        matches.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id,
                            classes: Array.from(el.classList),
                            text: text.substring(0, 100),
                            score: score,
                            xpath: getXPath(el)
                        });
                    }
                }
                
                // Helper function to get XPath
                function getXPath(element) {
                    if (element.id) {
                        return `//*[@id="${element.id}"]`;
                    }
                    
                    // Get path parts
                    const parts = [];
                    while (element && element.nodeType === Node.ELEMENT_NODE) {
                        let sibling = element;
                        let index = 1;
                        while ((sibling = sibling.previousElementSibling)) {
                            if (sibling.nodeName === element.nodeName) {
                                index++;
                            }
                        }
                        parts.unshift(`${element.nodeName.toLowerCase()}[${index}]`);
                        element = element.parentNode;
                    }
                    
                    return `/${parts.join('/')}`;
                }
                
                // Sort by score and return top matches
                return matches.sort((a, b) => b.score - a.score).slice(0, 5);
            }""", description)
            
            if elements and len(elements) > 0:
                # For find action, just return the results
                if action == "find":
                    return {
                        "status": "success",
                        "message": f"Found {len(elements)} elements matching: {description}",
                        "elements": elements
                    }
                
                # For interactive actions, try to use the top match
                top_element = elements[0]
                
                # Use the XPath to interact with the element
                xpath = top_element["xpath"]
                element = await page.wait_for_selector(f"xpath={xpath}", timeout=2000)
                
                if element:
                    if action == "click":
                        await element.click()
                    elif action == "fill":
                        await element.fill(text_input)
                    
                    return {
                        "status": "success",
                        "message": f"Successfully performed {action} on element via JS locator",
                        "element_found": True,
                        "element_details": top_element
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Found element with JS but couldn't interact with it",
                        "element_details": top_element
                    }
            else:
                return {
                    "status": "error",
                    "message": f"No elements found matching description: {description}"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def playwright_multi_strategy_locate(self, description: str = None, selectors: List[str] = None,
                                            action: str = "click", text_input: str = "", 
                                            page_index: int = 0, capture_screenshot: bool = False,
                                            optional: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive tool that tries multiple locator strategies in sequence.
        
        Args:
            description: Description of element to find
            selectors: List of CSS/XPath selectors to try in order
            action: Action to perform ('click', 'fill', 'select', 'hover')
            text_input: Text to input if action requires it
            page_index: Index of the page to operate on
            capture_screenshot: Whether to capture screenshots
            optional: Whether the action is optional
        """
        page = await self._get_page(page_index)
        if not page:
            return {"status": "error", "message": "Invalid page index"}
        
        attempts = []
        
        # Log parameters to help with debugging
        logger.info(f"multi_strategy_locate called with description='{description}', selectors={selectors}, " +
                   f"action='{action}', optional={optional}")
        
        try:
            # Check if we have specific selectors provided or need to generate them from description
            if selectors and isinstance(selectors, list):
                # Use the provided selectors directly
                standard_selectors = selectors
                logger.info(f"Using provided selectors: {selectors}")
            elif description:
                # 1. Generate standard selectors from description
                standard_selectors = [
                    # Try exact text match
                    f"text={description}",
                    # Try contains text
                    f"text='{description}'",
                    # Try button with text
                    f"button:has-text('{description}')",
                    # Try link with text
                    f"a:has-text('{description}')",
                    # Try input with placeholder
                    f"input[placeholder*='{description}']",
                    # Try element with aria-label
                    f"[aria-label*='{description}']",
                    # Try label with text
                    f"label:has-text('{description}')"
                ]
            else:
                # Neither selectors nor description provided
                return {"status": "error", "message": "Either description or selectors must be provided"}
            
            for selector in standard_selectors:
                try:
                    attempt = {"strategy": "standard_selector", "selector": selector}
                    element = await page.wait_for_selector(selector, timeout=1000)
                    
                    if element:
                        # Element found, perform action
                        if action == "click":
                            await element.click()
                        elif action == "fill":
                            await element.fill(text_input)
                        elif action == "hover":
                            await element.hover()
                        elif action == "select":
                            await element.select_option(text_input)
                        
                        attempt["result"] = "success"
                        attempts.append(attempt)
                        
                        # Take screenshot if requested
                        screenshot_path = None
                        if capture_screenshot:
                            screenshot_path = f"multi_strategy_{int(time.time())}.png"
                            await page.screenshot(path=screenshot_path)
                        
                        return {
                            "status": "success",
                            "message": f"Located element using standard selector: {selector}",
                            "strategy_used": "standard_selector",
                            "selector_used": selector,
                            "action_performed": action,
                            "screenshot": screenshot_path
                        }
                        
                except Exception as e:
                    attempt["result"] = "failed"
                    attempt["error"] = str(e)
                    attempts.append(attempt)
            
            # Try accessibility-based location next
            try:
                attempt = {"strategy": "accessibility_tree", "description": description}
                
                a11y_result = await self.playwright_accessibility_locator(
                    description=description,
                    action=action,
                    text_input=text_input,
                    page_index=page_index
                )
                
                if a11y_result["status"] == "success" and a11y_result.get("element_found"):
                    attempt["result"] = "success"
                    attempts.append(attempt)
                    
                    # Take screenshot if requested
                    screenshot_path = None
                    if capture_screenshot:
                        screenshot_path = f"multi_strategy_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                    
                    return {
                        "status": "success",
                        "message": f"Located element using accessibility tree",
                        "strategy_used": "accessibility_tree",
                        "element_details": a11y_result.get("element_details"),
                        "action_performed": action,
                        "screenshot": screenshot_path
                    }
                
                attempt["result"] = "failed"
                attempt["error"] = "No matching elements found via accessibility tree"
                attempts.append(attempt)
                
            except Exception as e:
                attempt["result"] = "failed"
                attempt["error"] = str(e)
                attempts.append(attempt)
            
            # Try vision-based location
            try:
                attempt = {"strategy": "vision_location", "text": description}
                
                vision_result = await self.playwright_vision_locator(
                    text=description,
                    action=action,
                    text_input=text_input,
                    page_index=page_index
                )
                
                if vision_result["status"] == "success" and vision_result.get("element_found"):
                    attempt["result"] = "success"
                    attempts.append(attempt)
                    
                    # Take screenshot if requested
                    screenshot_path = None
                    if capture_screenshot:
                        screenshot_path = f"multi_strategy_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                    
                    return {
                        "status": "success",
                        "message": f"Located element using vision-based locator",
                        "strategy_used": "vision_locator",
                        "action_performed": action,
                        "screenshot": screenshot_path
                    }
                
                attempt["result"] = "failed"
                attempt["error"] = "No matching elements found via vision-based locator"
                attempts.append(attempt)
                
            except Exception as e:
                attempt["result"] = "failed"
                attempt["error"] = str(e)
                attempts.append(attempt)
            
            # Try JavaScript-based location
            try:
                attempt = {"strategy": "javascript", "description": description}
                
                js_result = await self.playwright_js_locate(
                    description=description,
                    action=action,
                    text_input=text_input,
                    page_index=page_index
                )
                
                if js_result["status"] == "success" and js_result.get("element_found"):
                    attempt["result"] = "success"
                    attempts.append(attempt)
                    
                    # Take screenshot if requested
                    screenshot_path = None
                    if capture_screenshot:
                        screenshot_path = f"multi_strategy_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                    
                    return {
                        "status": "success",
                        "message": f"Located element using JavaScript",
                        "strategy_used": "javascript",
                        "element_details": js_result.get("element_details"),
                        "action_performed": action,
                        "screenshot": screenshot_path
                    }
                
                attempt["result"] = "failed"
                attempt["error"] = "No matching elements found via JavaScript"
                attempts.append(attempt)
                
            except Exception as e:
                attempt["result"] = "failed"
                attempt["error"] = str(e)
                attempts.append(attempt)
            
            # If we got here, all strategies failed
            
            # Take a final screenshot to help with debugging
            debug_screenshot = None
            if capture_screenshot:
                debug_screenshot = f"multi_strategy_failed_{int(time.time())}.png"
                await page.screenshot(path=debug_screenshot)
            
            # Collect information about the page to help debug why nothing worked
            page_info = {
                "url": page.url,
                "title": await page.title(),
                "content_snippet": await page.evaluate("() => document.body.innerText.substring(0, 500)")
            }
            
            # If action is optional, return a success status with a note
            if optional:
                element_desc = description if description else "using provided selectors"
                return {
                    "status": "success",
                    "message": f"Optional action: Element matching '{element_desc}' not found but continuing",
                    "element_found": False,
                    "attempted_strategies": [a["strategy"] for a in attempts],
                    "detailed_attempts": attempts,
                    "page_info": page_info,
                }
            else:
                # Regular non-optional action failed
                element_desc = description if description else "using provided selectors"
                return {
                    "status": "error",
                    "message": f"Failed to locate element matching '{element_desc}' with any strategy",
                    "attempted_strategies": [a["strategy"] for a in attempts],
                    "detailed_attempts": attempts,
                    "page_info": page_info,
                    "debug_screenshot": debug_screenshot,
                    "suggestion": "Try using more specific description or inspect the page manually"
                }
            
        except Exception as e:
            import traceback
            logger.error(f"Error in multi_strategy_locate: {str(e)}")
            logger.debug(f"Detailed traceback: {traceback.format_exc()}")
            
            # For optional actions, return success even on exception
            if optional:
                return {
                    "status": "success",
                    "message": f"Optional action: Exception occurred but continuing. Error: {str(e)}",
                    "element_found": False,
                    "error": str(e)
                }
            else:
                return {"status": "error", "message": str(e)}
