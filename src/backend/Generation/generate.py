from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY= os.getenv("GORQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def generate_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.3,
    )
    return response.choices[0].message.content