"""
Base utilities and common classes for MCP Tools
"""
import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, CDPSession, TimeoutError as PlaywrightTimeoutError

# Configure logging
logger = logging.getLogger("mcp_tools")

class PlaywrightBase:
    """Base class for Playwright automation."""
    def __init__(self, browser_type: str = "chromium"):
        self.playwright = None
        self.browser = None
        self.context = None
        self.pages = []
        self.console_logs = []
        self.browser_initialized = False  # Track if browser is initialized
        self.active_page_index = 0  # Track the currently active page index
        self.browser_type = browser_type.lower()  # Store browser type preference
        
    async def initialize(self):
        """Initialize Playwright without launching a browser."""
        try:
            # Launch Playwright but don't create a browser yet
            if not self.playwright:
                self.playwright = await async_playwright().start()
                logger.info("Playwright initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def _init_browser(self):
        """
        Internal method to initialize the browser and context.
        This is a shared implementation used by both verify_browser_page and _ensure_browser_initialized.
        """
        try:
            # Initialize Playwright if not already initialized
            if not self.playwright:
                logger.info("Starting Playwright...")
                self.playwright = await async_playwright().start()

            # Get browser type from instance variable with fallback to environment
            browser_type = self.browser_type or os.getenv("BROWSER_TYPE", "chromium").lower()
            logger.info(f"Initializing browser with type: {browser_type}")

            # Get headless mode from environment or default to False
            headless = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"

            # Prepare launch options before using them anywhere
            launch_options: Dict[str, Any] = {"headless": headless}
            
            # Select the appropriate browser engine
            if browser_type == "firefox":
                browser_engine = self.playwright.firefox
                logger.info("Using Firefox browser engine")
            elif browser_type == "webkit":
                browser_engine = self.playwright.webkit
                logger.info("Using WebKit browser engine")
            elif browser_type == "chrome":
                # Use Chromium engine but prefer the Chrome channel
                browser_engine = self.playwright.chromium
                launch_options["channel"] = "chrome"
                logger.info("Using Google Chrome channel via Chromium engine")
            elif browser_type == "msedge" or browser_type == "edge":
                # Use Chromium engine with Microsoft Edge channel when available
                browser_engine = self.playwright.chromium
                launch_options["channel"] = "msedge"
                logger.info("Using Microsoft Edge channel via Chromium engine")
            else:
                # Default to chromium
                browser_engine = self.playwright.chromium
                logger.info("Using Chromium browser engine")
            
            # Note: We now prefer the official channels for Chrome/Edge instead of manual paths.
            
            # Launch the selected browser with a fallback if channel is invalid
            try:
                self.browser = await browser_engine.launch(**launch_options)
            except Exception as launch_err:
                # Fallback: remove channel and try plain Chromium
                if launch_options.get("channel"):
                    logger.warning(f"Channel launch failed ({launch_options['channel']}): {launch_err}; falling back to Chromium without channel")
                    launch_options.pop("channel", None)
                    self.browser = await browser_engine.launch(**launch_options)
                else:
                    raise
            
            # Get viewport size from environment variables with defaults
            viewport_width = int(os.getenv("VIEWPORT_WIDTH", 1280))
            viewport_height = int(os.getenv("VIEWPORT_HEIGHT", 720))
            viewport_size = {"width": viewport_width, "height": viewport_height}
            
            # Create a browser context with the configured viewport
            self.context = await self.browser.new_context(
                viewport=viewport_size,
                accept_downloads=True
            )
            
            # Setup event listeners for console logs
            self.context.on("console", lambda msg: self._handle_console_log(msg))
            
            self.browser_initialized = True
            logger.info("Browser initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            self.browser = None
            self.context = None
            self.browser_initialized = False
            return False
    
    async def is_browser_alive(self):
        """
        Check if the browser is still responsive and available.
        Returns True if the browser is alive, False otherwise.
        """
        if not self.browser:
            logger.info("Browser validation failed: Browser object doesn't exist")
            self.browser_initialized = False
            return False
        
        try:
            # Prefer the built-in connection check when available
            if hasattr(self.browser, "is_connected"):
                if self.browser.is_connected():
                    logger.info("Browser check succeeded: connection is active")
                    return True
                else:
                    logger.warning("Browser connection check failed: not connected")
                    self.browser_initialized = False
                    return False
            
            # Fallback: try accessing contexts list
            _ = self.browser.contexts
            logger.info("Browser check succeeded via contexts access")
            return True
        except Exception as e:
            logger.error(f"Browser check failed with exception: {e}")
            # Reset state since browser is no longer valid
            self.browser_initialized = False
            self.browser = None  # Clear the reference to release memory
            return False
            
    async def verify_browser_page(self, page_index=0):
        """
        Verify browser and page are alive, and recover if needed.
        Returns tuple (browser_ok, page) where:
        - browser_ok: True if browser is ready to use
        - page: The page object if available, None otherwise
        """
        logger.info(f"Verifying browser and page state...")
        
        # First check browser existence and initialization state
        if not self.browser_initialized or not self.browser:
            logger.info("Browser not initialized or doesn't exist - initializing now")
            browser_alive = False
        else:
            # Check if the existing browser is still alive
            logger.info("Checking if existing browser is still responsive...")
            browser_alive = await self.is_browser_alive()
            
            if not browser_alive:
                logger.info("Browser is not responsive - will reinitialize")
            else:
                logger.info("Browser is responsive - proceeding with checks")
          # Initialize/reinitialize browser if needed
        if not browser_alive:
            # Browser needs initialization or recovery
            success = await self._init_browser()
            if not success:
                return False, None
        
        # Create or get page
        page = None
        try:
            # Use _get_active_page to handle cases where page index is 0
            if page_index == 0:
                page = await self._get_active_page()
            else:
                if len(self.pages) > page_index and self.pages[page_index]:
                    page = self.pages[page_index]
                else:
                    # Create new page
                    page = await self.context.new_page()
                    # Make sure pages list is long enough
                    while len(self.pages) <= page_index:
                        self.pages.append(None)
                    self.pages[page_index] = page
        except Exception as e:
            logger.error(f"Failed to get/create page: {e}")
            return True, None  # Browser ok but page failed
        
        return True, page
            
    async def _ensure_browser_initialized(self):
        """
        Ensure browser is initialized before using it.
        This method preserves existing browser sessions if they're still valid.
        """        # Check if browser or context is closed or missing in a version-compatible way
        needs_initialization = False
        
        # Check if browser is missing
        if not self.browser or not self.context:
            logger.info("Browser or context is missing - initialization needed")
            needs_initialization = True
        else:
            # Check if browser is closed
            try:
                if hasattr(self.browser, 'is_closed') and self.browser.is_closed():
                    logger.info("Browser is closed - initialization needed")
                    needs_initialization = True
            except Exception as e:
                logger.warning(f"Error checking browser state: {e}")
                # Be conservative - assume initialization is needed if we can't check
                needs_initialization = True
        
        # If browser is still alive, just update the initialization flag
        if self.browser and self.context and not needs_initialization:
            logger.info("Browser is still alive - using existing session")
            self.browser_initialized = True
            
            # Instead of resetting pages array, check if we need to sync with actual browser pages
            if not self.pages:
                # If our pages array is empty but browser is alive, get existing pages from context
                try:
                    existing_pages = self.context.pages
                    if existing_pages:
                        self.pages = existing_pages
                        logger.info(f"Synchronized with {len(existing_pages)} existing browser pages")
                except Exception as e:
                    logger.warning(f"Error synchronizing with existing pages: {e}")
                    # If we can't get pages, we'll create a new one when needed
            return
            
        # Only reinitialize if needed
        if needs_initialization:
            try:
                # Clean up any existing resources that might be in an inconsistent state
                try:
                    if self.context:
                        # Check if context has closed method before trying to use it
                        if hasattr(self.context, 'is_closed') and not self.context.is_closed():
                            await self.context.close()
                        else:
                            # Fallback: try to close without checking
                            try:
                                await self.context.close()
                            except:
                                pass
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                
                try:
                    if self.browser:
                        # Check if browser has closed method before trying to use it
                        if hasattr(self.browser, 'is_closed') and not self.browser.is_closed():
                            await self.browser.close()
                        else:
                            # Fallback: try to close without checking
                            try:
                                await self.browser.close()
                            except:
                                pass
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                    
                # Reset state before creating new resources
                self.pages = []
                self.browser_initialized = False
                self.active_page_index = 0
                
                # Use the shared browser initialization method
                await self._init_browser()
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                raise

    async def _get_active_page(self) -> Optional[Page]:
        """Get the currently active page, creating one if necessary."""
        try:
            # Ensure browser is initialized
            await self._ensure_browser_initialized()
            
            # If we don't have any pages yet or the active page is invalid, create one
            if not self.pages or self.active_page_index >= len(self.pages):
                logger.info(f"No active page, creating new one")
                new_page = await self.context.new_page()
                self.pages.append(new_page)
                self.active_page_index = len(self.pages) - 1
                logger.info(f"Created new page at index {self.active_page_index}")
            
            # Return the active page
            return self.pages[self.active_page_index]
        except Exception as e:
            logger.error(f"Error getting active page: {e}")
            return None

    async def _get_page(self, page_index: int) -> Optional[Page]:
        """Get a page by index, creating one if necessary."""
        if page_index < 0:
            logger.error(f"Invalid page index: {page_index}")
            return None
        
        # Default to active page if index is 0
        if page_index == 0:
            return await self._get_active_page()
            
        # Ensure browser is initialized
        await self._ensure_browser_initialized()
        
        # Create new pages if needed
        while len(self.pages) <= page_index:
            new_page = await self.context.new_page()
            self.pages.append(new_page)
            logger.info(f"Created new page at index {len(self.pages) - 1}")
        
        # Update active page index to the requested page
        self.active_page_index = page_index
        return self.pages[page_index]
    
    async def set_active_page(self, page_index: int):
        """Set the active page by index."""
        if page_index < 0 or page_index >= len(self.pages):
            logger.error(f"Invalid page index for setting active page: {page_index}")
            return False
        
        self.active_page_index = page_index
        logger.info(f"Set active page to index {page_index}")
        return True
    
    async def cleanup(self):
        """Cleanup resources but maintain browser persistence."""
        try:
            # Close all pages but keep the browser running
            for page in self.pages:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                
            self.pages = []
            self.active_page_index = 0
            logger.info("Closed all pages")
            
            # Don't close the browser to enable persistent sessions
            return {"status": "success", "message": "Cleaned up browser resources"}
            
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")
            return {"status": "error", "message": str(e)}
    
    async def reset_pages(self):
        """
        Reset pages array without closing any actual browser resources.
        This is the safest option for between-command cleanup to ensure browser persistence.
        """
        try:
            # Instead of just emptying the array, synchronize with context
            old_pages_count = len(self.pages)
            
            # Clear the list but don't close the pages (browser will manage them)
            self.pages = []
            self.active_page_index = 0
            
            # Synchronize with browser context if possible
            if self.context and hasattr(self.context, 'pages'):
                try:
                    # Keep the first page from context if it exists
                    context_pages = self.context.pages
                    if context_pages:
                        self.pages = [context_pages[0]]
                        logger.info("Kept the first browser page active")
                except Exception as e:
                    logger.warning(f"Error syncing with context pages: {e}")
            
            logger.info(f"Reset pages array from {old_pages_count} to {len(self.pages)} pages while preserving browser session")
            
            # Ensure browser state is marked as still initialized
            self.browser_initialized = True if self.browser else False
            
            return {"status": "success", "message": "Reset pages array while preserving browser session"}
            
        except Exception as e:
            logger.error(f"Failed to reset pages: {e}")
            return {"status": "error", "message": str(e)}
            
    async def cleanup_all(self):
        """Clean up all resources including browser and playwright."""
        try:
            # Close all pages
            for page in self.pages:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page during cleanup_all: {e}")
                
            self.pages = []
            self.active_page_index = 0
            
            # Close browser context
            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    logger.warning(f"Error closing context during cleanup_all: {e}")
            
            # Close browser
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser during cleanup_all: {e}")
            
            # Close playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright during cleanup_all: {e}")
            
            self.context = None
            self.browser = None
            self.playwright = None
            self.browser_initialized = False
            logger.info("Fully cleaned up all browser resources")
            
            return {"status": "success", "message": "Fully cleaned up all browser resources"}
            
        except Exception as e:
            logger.error(f"Error in cleanup_all: {e}")
            return {"status": "error", "message": str(e)}
            
    def _handle_console_log(self, msg):
        """Handle console log message from browser."""
        self.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "time": asyncio.get_event_loop().time()
        })
        logger.info(f"Browser console {msg.type}: {msg.text}")
