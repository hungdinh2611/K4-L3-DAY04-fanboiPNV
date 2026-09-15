"""
Flask backend for IT Helpdesk Agent Web UI.
Run: python server.py --provider openrouter --version v0
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
UI_DIR = ROOT / "ui"
load_lab_env(ROOT)

app = Flask(__name__, static_folder=str(UI_DIR))
CORS(app)

# ── Global session state ──────────────────────────────────────────────────────
session: dict[str, Any] = {}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def trim_history(history: list[dict], window: int) -> list[dict]:
    if window <= 0:
        return []
    return history[-window * 2:]


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def tool_results_message(events: list[dict]) -> dict:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for an incident report and the findings are ready, "
            "call the reporting tool. Otherwise answer directly, state uncertainty, and give the safest next step."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict:
    call_summary = [{"name": c.name, "args": c.args} for c in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


def run_model_tool_loop(
    *,
    provider: Any,
    messages: list[dict],
    tools: list[dict],
    model: str | None,
    max_tool_rounds: int,
) -> dict[str, Any]:
    working_messages = list(messages)
    rounds: list[dict] = []
    all_tool_events: list[dict] = []

    for round_index in range(1, max_tool_rounds + 1):
        response = provider.complete(working_messages, tools, model=model, temperature=0.0)
        calls = response.tool_calls
        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": c.name, "args": c.args} for c in calls],
            "tool_results": [],
        }

        if not calls:
            rounds.append(round_record)
            return {
                "status": "answered",
                "assistant_text": response.text or "",
                "rounds": rounds,
                "tool_events": all_tool_events,
            }

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict] = []

        for call in calls:
            event = execute_tool_call(call)
            round_record["tool_results"].append(event)
            all_tool_events.append(event)

            result = event.get("result", {})
            if isinstance(result, dict) and result.get("awaiting_user"):
                question = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                rounds.append(round_record)
                return {
                    "status": "waiting_for_user",
                    "assistant_text": question,
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }
            non_clarification_events.append(event)

        rounds.append(round_record)
        working_messages.append(tool_results_message(non_clarification_events))

    return {
        "status": "max_tool_rounds",
        "assistant_text": f"Stopped after {max_tool_rounds} tool rounds.",
        "rounds": rounds,
        "tool_events": all_tool_events,
    }


def write_transcript(path: Path, transcript: dict) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(UI_DIR), "index.html")


@app.route("/api/info", methods=["GET"])
def api_info():
    return jsonify({
        "version": session.get("version", "v0"),
        "provider": session.get("provider", "openrouter"),
        "model": session.get("model", ""),
        "artifact_version": session.get("artifact_version", ""),
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_text = (data or {}).get("message", "").strip()
    if not user_text:
        return jsonify({"error": "empty message"}), 400

    provider = session["provider_obj"]
    tools = session["tools"]
    system_prompt = session["system_prompt"]
    history = session.setdefault("history", [])

    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(history, 5),
        {"role": "user", "content": user_text},
    ]

    try:
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=tools,
            model=session.get("model_override"),
            max_tool_rounds=4,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    assistant_text = result["assistant_text"]
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})

    # Save transcript
    transcript = session.setdefault("transcript", {})
    transcript.setdefault("turns", []).append({
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        **result,
        "ended_at": now_iso(),
    })
    write_transcript(session["transcript_path"], transcript)

    return jsonify({
        "reply": assistant_text,
        "tool_events": result.get("tool_events", []),
        "status": result.get("status", "answered"),
        "transcript_path": str(session["transcript_path"]),
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    session["history"] = []
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"{safe_slug(session['version'])}_{safe_slug(session['provider'])}_{timestamp}"
    session["transcript_path"] = ROOT / "transcripts" / f"{transcript_id}.transcript.json"
    artifact_version = build_artifact_version(session["version"], ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")
    session["artifact_version"] = artifact_version.artifact_version
    session["transcript"] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": session["provider"],
        "model": session["model"],
        "created_at": now_iso(),
        "turns": [],
    }
    return jsonify({"ok": True, "artifact_version": session["artifact_version"]})


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Web UI server for IT Helpdesk Agent.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], default="openrouter")
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", default="v0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    provider_obj = make_provider(args.provider)
    model = args.model or getattr(provider_obj, "default_model", None)
    tool_declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    openai_tools = to_openai_tools(tool_declarations)
    system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    artifact_version = build_artifact_version(args.version, ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"{safe_slug(args.version)}_{safe_slug(args.provider)}_{timestamp}"
    transcript_path = ROOT / "transcripts" / f"{transcript_id}.transcript.json"

    session.update({
        "version": args.version,
        "provider": args.provider,
        "provider_obj": provider_obj,
        "model": model,
        "model_override": args.model,
        "tools": openai_tools,
        "system_prompt": system_prompt,
        "artifact_version": artifact_version.artifact_version,
        "history": [],
        "transcript_path": transcript_path,
        "transcript": {
            "transcript_id": transcript_id,
            **artifact_version_dict(artifact_version),
            "provider": args.provider,
            "model": model,
            "created_at": now_iso(),
            "turns": [],
        },
    })

    print(f"IT Helpdesk Agent UI -> http://localhost:{args.port}")
    print(f"   version={args.version}  provider={args.provider}  model={model}")
    app.run(debug=False, port=args.port)


if __name__ == "__main__":
    main()
