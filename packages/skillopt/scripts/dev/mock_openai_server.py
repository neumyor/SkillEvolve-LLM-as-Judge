#!/usr/bin/env python3
"""A deterministic mock OpenAI-compatible server for offline smoke tests.

Serves ``POST /v1/chat/completions`` (and ``GET /v1/models``) on localhost.
Responses are chosen by inspecting the request's system prompt, so the real
SkillOpt pipeline — rollout target, Evolution Controller, analysts, merge,
rank — runs end-to-end with zero external dependencies.

Usage:
    python scripts/dev/mock_openai_server.py [--port 8765]

The server prints one line per request to stdout for traceability.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "mock-model"

# ── Canned responses by prompt kind ─────────────────────────────────────────

CONTROLLER_UPDATE_EVERY = 2  # consult number that flips WAIT → UPDATE


def _controller_response(user: str) -> str:
    """A deterministic 'controller' for smoke tests.

    The semantic view renders the previous evidence state; a fresh cycle
    shows "(none yet — this is the first observation of this cycle)". This
    mock WAITs on the first consult of each cycle and UPDATEs once the
    state already carries an isolated hypothesis — i.e. windows of two
    observations, mirroring an evidence-triggered (not per-batch) cadence.
    """
    first_of_cycle = "none yet" in user
    if first_of_cycle:
        return json.dumps({
            "decision": "WAIT",
            "evidence_state": {
                "hypotheses": [
                    {
                        "defect": "Answers are not grounded in the provided context.",
                        "supporting_cases": ["ex_1"],
                        "counter_cases": [],
                        "assessment": "Evidence is still isolated; may be execution noise.",
                    }
                ],
                "unresolved": "Need another independent failure.",
            },
            "reason": "Evidence is isolated and may be execution noise.",
        })
    return json.dumps({
        "decision": "UPDATE",
        "evidence_state": {
            "hypotheses": [
                {
                    "defect": "Answers are not grounded in the provided context.",
                    "supporting_cases": ["ex_1", "ex_2"],
                    "counter_cases": [],
                    "assessment": "Recurring across independent tasks and fixable at the skill level.",
                }
            ],
            "unresolved": "",
        },
        "reason": "Multiple independent failures point to the same skill deficiency.",
    })


def _analyst_response(user: str, success: bool) -> str:
    if success:
        return json.dumps({
            "source_type": "success",
            "patch": {
                "reasoning": "mock",
                "edits": [
                    {
                        "op": "append",
                        "target": "",
                        "content": "- Successful pattern: ground every answer in the cited context passage.",
                    }
                ],
            },
        })
    return json.dumps({
        "source_type": "failure",
        "patch": {
            "reasoning": "mock",
            "edits": [
                {
                    "op": "append",
                    "target": "",
                    "content": "- Before answering, locate the exact passage that supports the answer and quote it mentally; if no passage supports it, answer from the most relevant passage.",
                }
            ],
        },
        "failure_summary": [
            {"failure_type": "ungrounded_answer", "count": 1, "description": "answer not grounded in context"}
        ],
    })


def _merge_response(user: str) -> str:
    # Concatenate every edit content that appears in the prompt.
    contents = re.findall(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', user)
    edits = [
        {"op": "append", "target": "", "content": c} for c in dict.fromkeys(contents)
    ]
    return json.dumps({"reasoning": "mock merge", "edits": edits})


def _rank_response(user: str) -> str:
    return json.dumps({"indices": [0, 1, 2], "reasoning": "mock ranking"})


def _rollout_response() -> str:
    return "Let me check the context.\n<answer>mock answer</answer>"


def choose_response(system: str, user: str) -> str:
    sys_l = (system or "").lower()
    if "evolution timing controller" in sys_l:
        return _controller_response(user)
    if "failure-analysis" in sys_l or "analyst" in sys_l and "fail" in sys_l:
        return _analyst_response(user, success=False)
    if "success" in sys_l and ("analyst" in sys_l or "analysis" in sys_l):
        return _analyst_response(user, success=True)
    if "merge" in sys_l:
        return _merge_response(user)
    if "rank" in sys_l or "select" in sys_l:
        return _rank_response(user)
    return _rollout_response()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet default access log
        pass

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/v1/models"):
            self._send_json({
                "object": "list",
                "data": [{"id": MODEL, "object": "model", "owned_by": "mock"}],
            })
        else:
            self._send_json({"error": {"message": f"not found: {self.path}"}}, status=404)

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/v1/chat/completions"):
            self._send_json({"error": {"message": f"not found: {self.path}"}}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            request = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send_json({"error": {"message": "bad json"}}, status=400)
            return
        messages = request.get("messages", [])
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        content = choose_response(system, user)
        print(
            f"[mock] {time.strftime('%H:%M:%S')} sys={_kind(system)} -> "
            f"{len(content)} chars",
            flush=True,
        )
        self._send_json({
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.get("model", MODEL),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": max(len(system) + len(user), 1) // 4,
                "completion_tokens": max(len(content), 1) // 4,
                "total_tokens": (len(system) + len(user) + len(content)) // 4,
            },
        })


def _kind(system: str) -> str:
    s = (system or "").lower()
    if "evolution timing controller" in s:
        return "controller"
    if "failure-analysis" in s or ("analyst" in s and "fail" in s):
        return "analyst-fail"
    if "success" in s and ("analyst" in s or "analysis" in s):
        return "analyst-success"
    if "merge" in s:
        return "merge"
    if "rank" in s or "select" in s:
        return "rank"
    return "rollout/other"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[mock] OpenAI-compatible mock listening on http://{args.host}:{args.port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
