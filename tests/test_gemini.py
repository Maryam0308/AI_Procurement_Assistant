
import os
from dotenv import load_dotenv
from google import genai

# Load API key from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Connect to Gemini
client = genai.Client(api_key=api_key)

# Ask Gemini a test question
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Explain government procurement in 3 simple sentences."
)

print("Gemini Response:")
print(response.text)
