from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from generator import generate_response
import os
from dotenv import load_dotenv
import psycopg2
from tabulate import tabulate  # optional for nice table display

load_dotenv()

app = FastAPI()

# --- Request models ---
class MetadataRequest(BaseModel):
    message: str
    metadata: Dict[str, Any] | None = None

class ChatRequest(BaseModel):
    message: str

# --- Database connection helper ---
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# --- Function to print users ---
def print_users_in_terminal():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users;")
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        # Print nicely in terminal
        print("\n--- Users table ---")
        print(tabulate(rows, headers=colnames, tablefmt="psql"))
        print("-------------------\n")

    except Exception as e:
        print(f"Error fetching users: {e}")

# --- Startup event to print users ---
@app.on_event("startup")
async def startup_event():
    print_users_in_terminal()

# --- Endpoints ---
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
