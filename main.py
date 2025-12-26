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
    phone: str
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

        # Print users as JSON in terminal
        users_json = [dict(zip(colnames, row)) for row in rows]
        print("\n--- Users data (JSON) ---")
        import json
        print(json.dumps(users_json, indent=4))
        print("------------------------\n")

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


# --- Helper to get user data by phone ---
def get_user_by_phone(phone):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name, phone_number FROM users WHERE phone_number = %s;", (phone,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {"name": row[0], "phone_number": row[1]}
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

@app.post("/chat")
async def chat(req: ChatRequest):
    user_data = get_user_by_phone(req.phone)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        # Pass both message and user data to the AI
        reply = generate_response({
            "message": req.message,
            "user": user_data
        })
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generation error: {e}")
