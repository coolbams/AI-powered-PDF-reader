from dotenv import load_dotenv
from groq import Groq
import os

load_dotenv()

api_key= os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key)

def generate_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.3,
    )
    return response.choices[0].message.content