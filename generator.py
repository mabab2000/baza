import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
	base_url="https://router.huggingface.co/v1",
	api_key=os.environ["DEEPSEEK_API_KEY"],
)
def generate_response(metadata):
	# Expecting metadata to have a 'message' key
	message = metadata.get("message", "Hello!")
	completion = client.chat.completions.create(
		model="deepseek-ai/DeepSeek-V3.2:novita",
		messages=[
			{"role": "system", "content": "You are an AI assistant. Always respond in English."},
			{"role": "user", "content": message}
		],
	)
	return completion.choices[0].message.content
