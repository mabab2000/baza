from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import psycopg2
import json
from decimal import Decimal
from generator import generate_response

load_dotenv()

app = FastAPI()

# --- Request model ---
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

# --- Startup: print all users and balances ---
def print_users_and_balances():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.phone_number, u.name, COALESCE(a.balance, 0) AS airtime_balance
            FROM users u
            LEFT JOIN airtime_balance a ON u.phone_number = a.phone_number;
        """)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        # Convert Decimal → float
        users_json = []
        for row in rows:
            row_dict = dict(zip(colnames, row))
            if isinstance(row_dict.get("airtime_balance"), Decimal):
                row_dict["airtime_balance"] = float(row_dict["airtime_balance"])
            users_json.append(row_dict)

        print("\n--- Users with Airtime Balances ---")
        print(json.dumps(users_json, indent=4))
        print("------------------------\n")

    except Exception as e:
        print(f"Error fetching users and balances: {e}")

@app.on_event("startup")
async def startup_event():
    print_users_and_balances()

# --- Root endpoint ---
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Send POST /chat with JSON {\"phone\": ..., \"message\": ...}"
    }

# --- Helper: get user info and balance by phone ---
def get_user_by_phone_with_balance(phone: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.name, u.phone_number, COALESCE(a.balance, 0) AS airtime_balance
            FROM users u
            LEFT JOIN airtime_balance a ON u.phone_number = a.phone_number
            WHERE u.phone_number = %s;
        """, (phone,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {"name": row[0], "phone_number": row[1], "airtime_balance": float(row[2])}
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

# --- Chat endpoint ---
@app.post("/chat")
async def chat(req: ChatRequest):
    user_data = get_user_by_phone_with_balance(req.phone)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        # Build prompt including actual balance
        prompt_message = (
            f"You are an assistant. Answer the user's question using ONLY the information below.\n\n"
            f"User Info:\n"
            f"- Name: {user_data['name']}\n"
            f"- Phone: {user_data['phone_number']}\n"
            f"- Airtime Balance: {user_data['airtime_balance']}\n\n"
            f"Question: {req.message}\n\n"
            f"Respond concisely using the values above directly."
        )

        # Only return AI-generated reply
        reply = generate_response({"message": prompt_message})

        return {"reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generation error: {e}")
