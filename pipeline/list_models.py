import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load your API key from the .env file
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

print("Fetching available models that support text generation...\n")

# Loop through all models and print the ones we can use for the chatbot
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")