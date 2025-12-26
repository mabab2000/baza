import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
	base_url="https://router.huggingface.co/v1",
	api_key=os.environ["DEEPSEEK_API_KEY"],
)
def generate_response(metadata):
	# metadata should have 'message' and 'user' keys
	message = metadata.get("message", "Hello!")
	user = metadata.get("user", {})
	system_prompt = """
	You are an AI assistant. Always respond in English. You have access to the following user data:
	Name: {name}
	Phone: {phone_number}
	Balance: {balance}
	If the user asks 'who am I', reply with 'you are {name}' based on the user data. If the user asks about their balance, reply with the actual balance from the user data. For other questions, use the user data to provide relevant information if possible.
	""".format(
		name=user.get("name", "Unknown"),
		phone_number=user.get("phone_number", "Unknown"),
		balance=user.get("balance", "Unknown")
	)
	completion = client.chat.completions.create(
		model="deepseek-ai/DeepSeek-V3.2:novita",
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": message}
		],
	)
	return completion.choices[0].message.content
