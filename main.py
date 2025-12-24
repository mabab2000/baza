
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from generator import generate_response
import os
from dotenv import load_dotenv

app = FastAPI()

class MetadataRequest(BaseModel):
	message: str
	metadata: Dict[str, Any] | None = None




class ChatRequest(BaseModel):
	message: str


@app.get("/")
async def root():
	return {"status": "ok", "message": "Send POST /chat with JSON {\"message\": ..., \"metadata\": {...}}"}





@app.post("/chat")
async def chat(req: ChatRequest):
	try:
		reply = generate_response({"message": req.message})
		return {"reply": reply}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"generation error: {e}")
