import asyncio
import os
import sys
import json
import time
from typing import Any, Dict, List, Optional


class JSONRPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"JSON-RPC error {code}: {message}")
        self.code = code
        self.data = data


class JSONRPCStdioClient:
    """Minimal JSON-RPC 2.0 client over stdio using Content-Length framing."""

    def __init__(self, proc: asyncio.subprocess.Process, read_timeout: float = 30.0):
        self.proc = proc
        self._reader = proc.stdout
        self._writer = proc.stdin
        self._next_id = 1
        self._pending: Dict[int, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._read_timeout = read_timeout

    async def start(self):
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._read_loop())

    async def close(self):
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except Exception:
                pass
            self._read_task = None
        # Writer closed when proc terminates

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        req_id = self._next_id
        self._next_id += 1
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        body = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            body["params"] = params
        data = json.dumps(body).encode("utf-8")
        header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
        self._writer.write(header + data)
        await self._writer.drain()
        try:
            return await asyncio.wait_for(fut, timeout=self._read_timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise TimeoutError(f"Timeout waiting for response to {method}")

    async def _read_loop(self):
        try:
            while True:
                # Read headers
                content_length = None
                while True:
                    line = await self._reader.readline()
                    if not line:
                        # EOF: reject all pending requests with a clear error
                        for _, fut in list(self._pending.items()):
                            if not fut.done():
                                fut.set_exception(ConnectionError("Connection lost"))
                        self._pending.clear()
                        return
                    line_str = line.decode("ascii", errors="ignore").strip()
                    if line_str == "":
                        break
                    if line_str.lower().startswith("content-length:"):
                        try:
                            content_length = int(line_str.split(":", 1)[1].strip())
                        except Exception:
                            pass
                if content_length is None:
                    # Not a framed message; skip
                    continue
                # Read body
                body = await self._reader.readexactly(content_length)
                try:
                    msg = json.loads(body.decode("utf-8"))
                except Exception:
                    continue
                # Handle response
                if isinstance(msg, dict) and msg.get("jsonrpc") == "2.0" and "id" in msg:
                    req_id = msg["id"]
                    fut = self._pending.pop(req_id, None)
                    if fut is None:
                        continue
                    if "error" in msg and msg["error"] is not None:
                        err = msg["error"]
                        fut.set_exception(JSONRPCError(err.get("code", -32000), err.get("message", "error"), err.get("data")))
                    else:
                        fut.set_result(msg.get("result"))
                # Notifications are ignored
        except asyncio.CancelledError:
            return


class MCPToolClient:
    """
    JSON-RPC over stdio MCP client:
    - Starts/stops the MCP server process (playwright_server.py)
    - Implements tools.list and tools.call
    - Adds simple retry and error mapping for robust integration
    """

    def __init__(self, python_exe: Optional[str] = None, server_script: Optional[str] = None, browser_type: str = "chromium"):
        self.python_exe = python_exe or sys.executable
        self.server_script = server_script or os.path.join(os.path.dirname(__file__), "playwright_server.py")
        self.browser_type = browser_type
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._rpc: Optional[JSONRPCStdioClient] = None
        self._stderr_tail: list[str] = []
        self._stderr_task: Optional[asyncio.Task] = None

    async def _drain_stderr(self):
        if not self._proc or not self._proc.stderr:
            return
        try:
            while True:
                line = await self._proc.stderr.readline()
                if not line:
                    return
                try:
                    s = line.decode("utf-8", errors="ignore").rstrip()
                except Exception:
                    s = str(line)
                # Keep last ~20 lines
                self._stderr_tail.append(s)
                if len(self._stderr_tail) > 20:
                    self._stderr_tail.pop(0)
                # Also mirror to parent's stderr for visibility
                try:
                    sys.stderr.write(f"[MCP-STDIO] {s}\n")
                except Exception:
                    pass
        except asyncio.CancelledError:
            return

    async def start_server(self) -> None:
        if self._proc and self._proc.returncode is None and self._rpc:
            return
        env = os.environ.copy()
        env.setdefault("MCP_TRANSPORT", "stdio")
        self._proc = await asyncio.create_subprocess_exec(
            self.python_exe,
            self.server_script,
            "--browser-type", self.browser_type,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(self.server_script),
            env=env,
        )
        self._rpc = JSONRPCStdioClient(self._proc)
        await self._rpc.start()
        # Start draining stderr for diagnostics
        self._stderr_task = asyncio.create_task(self._drain_stderr())
        # Small grace period to catch immediate startup crashes
        await asyncio.sleep(0.05)
        if self._proc.returncode is not None:
            err = "\n".join(self._stderr_tail[-10:]) if self._stderr_tail else ""
            raise RuntimeError(f"MCP server exited early with code {self._proc.returncode}. Stderr tail:\n{err}")

    async def stop_server(self) -> None:
        try:
            if self._rpc:
                await self._rpc.close()
        finally:
            self._rpc = None
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except Exception:
                pass
            self._stderr_task = None
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()
        self._proc = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        await self._ensure_started()
        attempts = 0
        last_err: Optional[Exception] = None
        while attempts < 2:
            attempts += 1
            try:
                # Some servers require initialize first; try tools/list directly
                result = await self._rpc.request("tools/list")
                if isinstance(result, dict) and "tools" in result:
                    return result["tools"]
                if isinstance(result, list):
                    return result
                return []
            except JSONRPCError as e:
                last_err = e
                if e.code in (-32601,):
                    # method not found; no point retrying differently here
                    break
            except Exception as e:
                last_err = e
            await asyncio.sleep(0.2)
        err_tail = "\n".join(self._stderr_tail[-10:]) if self._stderr_tail else ""
        raise RuntimeError(f"tools.list failed: {last_err}\nServer stderr tail:\n{err_tail}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        await self._ensure_started()
        attempts = 0
        last_err: Optional[Exception] = None
        while attempts < 2:
            attempts += 1
            try:
                params = {"name": name, "arguments": arguments}
                result = await self._rpc.request("tools/call", params)
                return result
            except JSONRPCError as e:
                last_err = e
                # Map common JSON-RPC errors to clearer messages
                if e.code == -32601:
                    raise RuntimeError(f"Tool '{name}' not found")
                if e.code == -32602:
                    raise RuntimeError(f"Invalid parameters for tool '{name}': {e}")
                # Retry once on server error
            except (TimeoutError, asyncio.IncompleteReadError, ConnectionError) as e:
                last_err = e
                # Retry on transient IO issues
            await asyncio.sleep(0.2)
        err_tail = "\n".join(self._stderr_tail[-10:]) if self._stderr_tail else ""
        raise RuntimeError(f"tools.call '{name}' failed: {last_err}\nServer stderr tail:\n{err_tail}")

    async def _ensure_started(self):
        if not self._proc or self._proc.returncode is not None or not self._rpc:
            await self.start_server()
