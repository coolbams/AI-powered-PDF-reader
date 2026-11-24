from dotenv import load_dotenv
from groq import Groq
import tiktoken
import os

load_dotenv()

MAX_HISTORY_TOKENS = 4000

LLM_MODEL_NAME = os.getenv("LLM") or "openai/gpt-oss-20b"

enc = tiktoken.get_encoding("o200k_base")

_client = None


def get_client() -> Groq:
    """Creates the Groq client on first use and reuses it."""
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def _trim_history(history: list[dict]) -> list[dict]:
    """Keeps the most recent messages that fit within MAX_HISTORY_TOKENS."""
    trimmed = []
    total = 0
    for msg in reversed(history):
        msg_tokens = len(enc.encode(msg["content"]))
        if total + msg_tokens > MAX_HISTORY_TOKENS:
            break
        trimmed.append(msg)
        total += msg_tokens
    return list(reversed(trimmed))


def generate_response(prompt: str, history: list[dict] | None = None) -> str:
    """Sends the prompt (with optional conversation history) to the Groq LLM."""

    messages = []
    if history:
        messages.extend(_trim_history(history))
    messages.append({"role": "user", "content": prompt})

    model_name = os.getenv("LLM") or LLM_MODEL_NAME or "openai/gpt-oss-20b"
    response = get_client().chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=4000,
        temperature=0.3,
    )
    return response.choices[0].message.content


def stream_response(prompt: str, history: list[dict] | None = None):
    """Streams tokens from Groq LLM one-by-one as they are generated."""

    messages = []
    if history:
        messages.extend(_trim_history(history))
    messages.append({"role": "user", "content": prompt})

    model_name = os.getenv("LLM") or LLM_MODEL_NAME or "openai/gpt-oss-20b"
    stream = get_client().chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=4000,
        temperature=0.3,
        stream=True,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token