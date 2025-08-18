import asyncio
import os
import sys

# Ensure repository root is on sys.path to import Tools package
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(CURRENT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from Tools.base import PlaywrightBase

async def main():
    base = PlaywrightBase("msedge")
    print("Initializing Playwright...")
    ok = await base.initialize()
    if not ok:
        print("Init failed")
        return

    print("Ensuring browser is initialized (msedge channel)...")
    await base._ensure_browser_initialized()

    print(f"Browser initialized: {bool(base.browser)} | Context: {bool(base.context)} | Pages: {len(base.pages)}")

    page = await base._get_active_page()
    if not page:
        print("Failed to get active page")
        await base.cleanup_all()
        return

    print("Navigating to https://example.com ...")
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        print(f"Page title: {title}")
    except Exception as e:
        print(f"Navigation error: {e}")

    print("Cleaning up...")
    await base.cleanup_all()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
