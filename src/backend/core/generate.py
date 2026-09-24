from dotenv import load_dotenv
from groq import Groq
import tiktoken
import os

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key)

MAX_HISTORY_TOKENS = 4000
enc = tiktoken.get_encoding("o200k_base")


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

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        max_tokens=4000,
        temperature=0.3,
    )
    return response.choices[0].message.content