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
        # Print a single user by phone number (example: '0783857284')
        phone = os.getenv("PRINT_USER_PHONE", "0783857284")
        cur.execute("SELECT name, phone_number FROM users WHERE phone_number = %s;", (phone,))
        user_row = cur.fetchone()
        balance = None
        if user_row:
            # Try to get balance from formairtime_balance
            try:
                conn2 = get_db_connection()
                cur2 = conn2.cursor()
                cur2.execute("SELECT balance FROM airtime_balance WHERE phone_number = %s;", (phone,))
                balance_row = cur2.fetchone()
                if balance_row:
                    balance = balance_row[0]
                cur2.close()
                conn2.close()
            except Exception as e:
                print(f"Error fetching balance: {e}")
        cur.close()
        conn.close()
        print("\n--- User data (JSON) ---")
        import json
        if user_row:
            # Convert Decimal to float for JSON serialization
            if balance is not None:
                try:
                    balance_json = float(balance)
                except Exception:
                    balance_json = str(balance)
            else:
                balance_json = None
            print(json.dumps({"name": user_row[0], "phone_number": user_row[1], "balance": balance_json}, indent=4))
        else:
            print(json.dumps({"error": "User not found", "phone_number": phone}, indent=4))
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
        user_row = cur.fetchone()
        # Get balance from airtime_balance
        cur.execute("SELECT balance FROM airtime_balance WHERE phone_number = %s;", (phone,))
        balance_row = cur.fetchone()
        cur.close()
        conn.close()
        if user_row:
            return {
                "name": user_row[0],
                "phone_number": user_row[1],
                "balance": balance_row[0] if balance_row else None
            }
        return None
    except Exception as e:
        print(f"Error fetching user or balance: {e}")
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
