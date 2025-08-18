import asyncio
import os
import sys

# Ensure repo root on path
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(CURRENT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from Tools.BrowserControl.navigation import BrowserControlTools

async def main():
    os.environ.setdefault("BROWSER_HEADLESS", "true")
    tools = BrowserControlTools(browser_type="msedge")
    print("Initializing Playwright (msedge)...")
    ok = await tools.initialize()
    if not ok:
        print("Init failed")
        return
    print("Navigating to https://example.com ...")
    res = await tools.playwright_navigate("https://example.com", wait_for_load=False, capture_screenshot=False)
    print(res)
    await tools.cleanup_all()

if __name__ == "__main__":
    asyncio.run(main())
