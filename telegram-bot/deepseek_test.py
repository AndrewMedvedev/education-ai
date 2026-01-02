# Please install OpenAI SDK first: `pip3 install openai`
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.settings import ENV_PATH

load_dotenv(ENV_PATH)

client = OpenAI(api_key=os.getenv("DEEPSEEK_APIKEY"), base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)
