from openai import OpenAI

from src.settings import settings

client = OpenAI(api_key=settings.openai.apikey)

response = client.responses.create(
  model="gpt-5-nano",
  input="Привет, до какого момента ограничены твои знания?",
  store=True,
)

print(response.output_text)
