
import argparse
import asyncio
import logging
import inspect
import os
import sys
import json
from contextlib import asynccontextmanager
try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None  # Optional; stdio mode does not require FastMCP
from Tools.AdvancedBrowser.advanced import AdvancedBrowserTools
from Tools.BrowserControl.navigation import BrowserControlTools
from Tools.CodeGeneration.codegen import CodeGenerationTools
from Tools.ContentExtraction.extraction import ContentExtractionTools
from Tools.Debug.debug import DebugTools
from Tools.ElementInteraction.interaction import ElementInteractionTools
from Tools.ElementLocation.location import ElementLocationTools
from Tools.Network.network import NetworkTools
import uvicorn

# Configure logging (stderr only to avoid corrupting stdio protocol)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Global browser type - set by command line arguments
DEFAULT_BROWSER_TYPE = "chromium"

class PlaywrightMCPServer(
    AdvancedBrowserTools,
    BrowserControlTools,
    CodeGenerationTools,
    ContentExtractionTools,
    DebugTools,
    ElementInteractionTools,
    ElementLocationTools,
    NetworkTools,
):
    def __init__(self, browser_type: str = None):
        # Use cooperative multiple inheritance init
        # Use provided browser_type, then env var, then global default
        selected_browser = browser_type or os.getenv("BROWSER_TYPE") or DEFAULT_BROWSER_TYPE
        super().__init__(browser_type=selected_browser)

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()

@asynccontextmanager
async def lifespan(app):
    tool_provider = PlaywrightMCPServer()
    await tool_provider.__aenter__()
    # Register tools from the tool_provider
    for name, method in inspect.getmembers(tool_provider, predicate=inspect.ismethod):
        if not name.startswith('_') and hasattr(app, 'tool'):
            app.tool()(method)
    yield
    await tool_provider.__aexit__(None, None, None)

# Create an MCP server
mcp = None
if FastMCP is not None:
    mcp = FastMCP(
        "Playwright Server",
        lifespan=lifespan
    )

if __name__ == "__main__":
    async def _run_stdio(browser_type: str = DEFAULT_BROWSER_TYPE):
        """Run a minimal JSON-RPC 2.0 stdio server exposing tools/list and tools/call."""
        # Ensure logs go to stderr to avoid corrupting stdio protocol
        try:
            tool_provider = PlaywrightMCPServer(browser_type=browser_type)
            await tool_provider.__aenter__()
        except Exception as e:
            # Log to stderr; client will see early exit
            print(f"MCP stdio server failed to initialize: {e}", file=sys.stderr)
            return

        # Build tool registry
        def _collect_tools():
            tools = {}
            for name, method in inspect.getmembers(tool_provider, predicate=inspect.ismethod):
                if name.startswith('_'):
                    continue
                tools[name] = method
            return tools

        tools = _collect_tools()

        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer

        async def read_line() -> bytes:
            return await asyncio.to_thread(stdin.readline)

        async def read_exactly(n: int) -> bytes:
            return await asyncio.to_thread(stdin.read, n)

        async def write_bytes(data: bytes) -> None:
            def _write():
                stdout.write(data)
                stdout.flush()
            await asyncio.to_thread(_write)

        async def send_response(resp_id, result=None, error=None):
            body = {"jsonrpc": "2.0", "id": resp_id}
            if error is not None:
                body["error"] = error
            else:
                body["result"] = result
            data = json.dumps(body).encode('utf-8')
            header = f"Content-Length: {len(data)}\r\n\r\n".encode('ascii')
            await write_bytes(header + data)

        async def handle_request(req: dict):
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params") or {}
            try:
                if method == "tools/list":
                    # Return list of tools with simple description
                    tool_list = []
                    for name, m in tools.items():
                        doc = m.__doc__ or ""
                        desc = doc.strip().split('\n')[0] if doc else ""
                        tool_list.append({"name": name, "description": desc})
                    await send_response(req_id, result={"tools": tool_list})
                    return
                elif method == "tools/call":
                    name = params.get("name")
                    arguments = params.get("arguments", {})
                    if not isinstance(name, str) or not isinstance(arguments, dict):
                        await send_response(req_id, error={"code": -32602, "message": "Invalid params"})
                        return
                    fn = tools.get(name)
                    if not fn:
                        await send_response(req_id, error={"code": -32601, "message": f"Tool '{name}' not found"})
                        return
                    try:
                        res = fn(**arguments)
                        if inspect.iscoroutine(res):
                            res = await res
                        # Ensure JSON-serializable result
                        try:
                            json.dumps(res)
                            out = res
                        except Exception:
                            out = str(res)
                        await send_response(req_id, result=out)
                        return
                    except Exception as e:
                        await send_response(req_id, error={"code": -32000, "message": str(e)})
                        return
                else:
                    await send_response(req_id, error={"code": -32601, "message": "Method not found"})
            except Exception as e:
                await send_response(req_id, error={"code": -32000, "message": str(e)})

        try:
            while True:
                # Read headers
                content_length = None
                while True:
                    line = await read_line()
                    if not line:
                        # EOF
                        raise EOFError()
                    s = line.decode('ascii', errors='ignore').strip()
                    if s == "":
                        break
                    if s.lower().startswith('content-length:'):
                        try:
                            content_length = int(s.split(':', 1)[1].strip())
                        except Exception:
                            content_length = None
                if content_length is None:
                    # Skip until next message
                    continue
                body = await read_exactly(content_length)
                try:
                    msg = json.loads(body.decode('utf-8'))
                except Exception:
                    continue
                if isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and "method" in msg:
                    await handle_request(msg)
                # Notifications are ignored
        except EOFError:
            pass
        finally:
            try:
                await tool_provider.__aexit__(None, None, None)
            except Exception:
                pass

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Playwright MCP Server")
    parser.add_argument("--browser-type", default="chromium", 
                        choices=["chromium", "firefox", "webkit", "chrome", "msedge"],
                        help="Browser type to use (default: chromium)")
    args = parser.parse_args()
    
    # Set global browser type
    DEFAULT_BROWSER_TYPE = args.browser_type
    
    if os.getenv("MCP_TRANSPORT", "").lower() == "stdio":
        asyncio.run(_run_stdio(browser_type=args.browser_type))
    else:
        # Default to FastMCP ASGI app
        if mcp is None:
            print("FastMCP not installed; cannot run ASGI server. Set MCP_TRANSPORT=stdio to use stdio.", file=sys.stderr)
            sys.exit(1)
        mcp.run()
