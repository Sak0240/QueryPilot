from openai import OpenAI

from app.config import settings

client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
reply = client.chat.completions.create(
    model=settings.llm_model,
    messages=[{"role": "user", "content": "Say hi in one short sentence"}],
)
print(reply.choices[0].message.content)