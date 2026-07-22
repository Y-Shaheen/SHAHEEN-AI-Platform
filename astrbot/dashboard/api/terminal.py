"""Interactive terminal WebSocket API for the AstrBot dashboard."""

from __future__ import annotations

import asyncio
import os
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from astrbot.core import logger
from astrbot.dashboard.responses import ApiError, ok

from .auth import AuthContext, require_scope

router = APIRouter(tags=["Terminal"])

# ──────────────────────────────────────────────────────────────────────────────
# Session registry
# ──────────────────────────────────────────────────────────────────────────────

_MAX_SESSIONS = 5
_MAX_OUTPUT_BYTES = 128 * 1024  # 128 KB per command
_COMMAND_TIMEOUT = 60.0  # seconds

# session_id → running subprocess (or None when idle)
_active_sessions: dict[str, asyncio.subprocess.Process] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Auth helper
# ──────────────────────────────────────────────────────────────────────────────


async def require_system_scope(request: Request) -> AuthContext:
    return await require_scope(request, "system")


def _authenticate_ws(websocket: WebSocket) -> bool:
    """Validate a JWT token passed as ?token= query param."""
    token = websocket.query_params.get("token")
    if not token:
        return False
    jwt_secret = websocket.app.state.jwt_secret
    try:
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        return bool(payload.get("username"))
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Request models
# ──────────────────────────────────────────────────────────────────────────────


class TerminalExecRequest(BaseModel):
    command: str
    cwd: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# REST endpoint – fire-and-collect (non-interactive)
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/terminal/exec")
async def terminal_exec(
    payload: TerminalExecRequest,
    _auth: AuthContext = Depends(require_system_scope),
):
    """Execute a shell command and return its combined stdout/stderr."""
    command = (payload.command or "").strip()
    if not command:
        raise ApiError("Empty command")

    cwd = payload.cwd or os.getcwd()
    if not os.path.isdir(cwd):
        raise ApiError(f"Working directory does not exist: {cwd}")

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=os.environ.copy(),
        )

        output_parts: list[str] = []
        total_bytes = 0
        truncated = False

        async def _collect() -> None:
            nonlocal total_bytes, truncated
            assert proc.stdout is not None
            async for chunk in proc.stdout:
                decoded = chunk.decode("utf-8", errors="replace")
                output_parts.append(decoded)
                total_bytes += len(decoded)
                if total_bytes > _MAX_OUTPUT_BYTES:
                    truncated = True
                    proc.kill()
                    break

        try:
            await asyncio.wait_for(_collect(), timeout=_COMMAND_TIMEOUT)
        except TimeoutError:
            proc.kill()
            output_parts.append(f"\n[Command timed out after {_COMMAND_TIMEOUT:.0f}s]")

        await proc.wait()
        output = "".join(output_parts)
        if truncated:
            output += "\n[Output truncated – exceeded 128 KB limit]"

        return ok(
            {
                "output": output,
                "exit_code": proc.returncode,
                "cwd": cwd,
                "truncated": truncated,
            }
        )
    except Exception as exc:
        raise ApiError(str(exc)) from exc


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint – interactive streaming terminal
# ──────────────────────────────────────────────────────────────────────────────

# Protocol (JSON messages):
#
# Client → Server:
#   { "type": "exec",  "command": "ls -la", "cwd": "/opt" }
#   { "type": "kill" }
#   { "type": "ping" }
#   { "type": "close" }
#
# Server → Client:
#   { "type": "ready",  "session_id": "...", "cwd": "..." }
#   { "type": "output", "data": "...", "stream": "stdout"|"stderr" }
#   { "type": "done",   "exit_code": 0, "cwd": "..." }
#   { "type": "cwd",    "cwd": "..." }
#   { "type": "killed" }
#   { "type": "pong" }
#   { "type": "error",  "data": "..." }


@router.websocket("/terminal/ws")
async def terminal_ws(websocket: WebSocket) -> None:
    """Interactive streaming terminal over WebSocket."""
    await websocket.accept()

    if not _authenticate_ws(websocket):
        await websocket.send_json(
            {"type": "error", "data": "Authentication required"}
        )
        await websocket.close(code=4001)
        return

    if len(_active_sessions) >= _MAX_SESSIONS:
        await websocket.send_json(
            {"type": "error", "data": "Too many active terminal sessions"}
        )
        await websocket.close(code=4002)
        return

    session_id = str(uuid.uuid4())
    cwd = os.getcwd()
    current_proc: asyncio.subprocess.Process | None = None

    await websocket.send_json(
        {"type": "ready", "session_id": session_id, "cwd": cwd}
    )

    try:
        while True:
            try:
                msg = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            msg_type = msg.get("type", "")

            # ── ping ──────────────────────────────────────────────────────────
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # ── close ─────────────────────────────────────────────────────────
            if msg_type == "close":
                break

            # ── kill ──────────────────────────────────────────────────────────
            if msg_type == "kill":
                if current_proc and current_proc.returncode is None:
                    current_proc.kill()
                    await websocket.send_json({"type": "killed"})
                continue

            # ── exec ──────────────────────────────────────────────────────────
            if msg_type == "exec":
                command = (msg.get("command") or "").strip()
                req_cwd = (msg.get("cwd") or cwd).strip()

                if not command:
                    continue

                # Built-in cd – handled locally so the session cwd persists
                if command.startswith("cd"):
                    parts = command.split(None, 1)
                    target_raw = parts[1] if len(parts) > 1 else "~"
                    target = os.path.expanduser(target_raw)
                    if not os.path.isabs(target):
                        target = os.path.join(req_cwd, target)
                    target = os.path.normpath(target)
                    try:
                        os.listdir(target)  # permission check
                        cwd = target
                        await websocket.send_json(
                            {"type": "done", "exit_code": 0, "cwd": cwd}
                        )
                    except OSError as exc:
                        await websocket.send_json(
                            {
                                "type": "output",
                                "data": f"cd: {exc.strerror}: {target}\n",
                                "stream": "stderr",
                            }
                        )
                        await websocket.send_json(
                            {"type": "done", "exit_code": 1, "cwd": cwd}
                        )
                    continue

                # General command execution
                exec_cwd = req_cwd if os.path.isdir(req_cwd) else cwd
                try:
                    current_proc = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=exec_cwd,
                        env=os.environ.copy(),
                    )
                    _active_sessions[session_id] = current_proc

                    total_bytes = 0
                    truncated = False

                    async def _stream_pipe(
                        pipe: asyncio.StreamReader, stream_name: str
                    ) -> None:
                        nonlocal total_bytes, truncated
                        async for chunk in pipe:
                            decoded = chunk.decode("utf-8", errors="replace")
                            total_bytes += len(decoded)
                            if total_bytes > _MAX_OUTPUT_BYTES:
                                truncated = True
                                if current_proc and current_proc.returncode is None:
                                    current_proc.kill()
                                break
                            try:
                                await websocket.send_json(
                                    {
                                        "type": "output",
                                        "data": decoded,
                                        "stream": stream_name,
                                    }
                                )
                            except Exception:
                                break

                    assert current_proc.stdout is not None
                    assert current_proc.stderr is not None

                    try:
                        await asyncio.wait_for(
                            asyncio.gather(
                                _stream_pipe(current_proc.stdout, "stdout"),
                                _stream_pipe(current_proc.stderr, "stderr"),
                            ),
                            timeout=_COMMAND_TIMEOUT,
                        )
                    except TimeoutError:
                        if current_proc.returncode is None:
                            current_proc.kill()
                        await websocket.send_json(
                            {
                                "type": "output",
                                "data": f"\n[Timed out after {_COMMAND_TIMEOUT:.0f}s]\n",
                                "stream": "stderr",
                            }
                        )

                    await current_proc.wait()

                    if truncated:
                        await websocket.send_json(
                            {
                                "type": "output",
                                "data": "\n[Output truncated – exceeded 128 KB]\n",
                                "stream": "stderr",
                            }
                        )

                    await websocket.send_json(
                        {
                            "type": "done",
                            "exit_code": current_proc.returncode,
                            "cwd": cwd,
                        }
                    )
                except Exception as exc:
                    await websocket.send_json(
                        {"type": "error", "data": str(exc)}
                    )
                finally:
                    _active_sessions.pop(session_id, None)
                    current_proc = None

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Terminal WS error [%s]: %s", session_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "data": str(exc)})
        except Exception:
            pass
    finally:
        if current_proc and current_proc.returncode is None:
            try:
                current_proc.kill()
            except Exception:
                pass
        _active_sessions.pop(session_id, None)
        try:
            await websocket.close()
        except Exception:
            pass
