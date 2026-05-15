"""
One-shot CLI for StudioFlow Agent.

Usage (from repo root):
  uv run --project services/agent python services/agent/run.py "what's broken?"

Loads .env from repo root, configures ADK to route Gemini through Vertex AI
with Application Default Credentials, then sends a single prompt and prints
the final agent response. Tool calls are echoed to stderr.
"""
import asyncio
import os
import sys
from pathlib import Path

# Make sibling `agent.py` importable without packaging the directory.
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv


def _bootstrap_env() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    # ADK -> Vertex AI via ADC.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID", ""))
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("REGION", "us-central1"))


async def run_once(prompt: str) -> int:
    # Imports happen after _bootstrap_env() so ADK sees Vertex env vars at init.
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types
    from agent import root_agent

    app_name = "studioflow-agent-cli"
    user_id = "local-dev"

    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id,
    )

    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=prompt)],
    )

    final_text: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if part.function_call:
                args_repr = dict(part.function_call.args or {})
                print(f"[tool] -> {part.function_call.name}({args_repr})", file=sys.stderr)
            if part.function_response:
                resp_preview = str(part.function_response.response)[:300]
                print(f"[tool] <- {part.function_response.name}: {resp_preview}", file=sys.stderr)
            if part.text and event.is_final_response():
                final_text.append(part.text)

    if not final_text:
        print("(agent produced no final text)", file=sys.stderr)
        return 1

    print("\n".join(final_text))
    return 0


def main() -> int:
    _bootstrap_env()

    if len(sys.argv) < 2:
        print('Usage: python run.py "<prompt>"', file=sys.stderr)
        return 2

    prompt = " ".join(sys.argv[1:])
    return asyncio.run(run_once(prompt))


if __name__ == "__main__":
    sys.exit(main())
