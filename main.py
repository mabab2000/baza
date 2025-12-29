"""
Telecom Bundle Chat Service (FastAPI)

Behavior:
- Users can query bundles and receive only relevant next-level categories when asking main categories.
- Users can ask for their name.
- Users can view profile, airtime balance, and bundle balances.
- Admin-controlled full users table access.
- Purchase bundles via 'purchase <id>'.
- Database-sourced responses only; no raw IDs returned.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import logging
import re
from datetime import datetime
from decimal import Decimal

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telecom-chat")

app = FastAPI(title="Telecom Bundle Chat Service", version="1.0.0")

# Request model
class ChatRequest(BaseModel):
    phone: str = Field(..., description="User phone number")
    message: str = Field(..., description="User message / query")

# Whitelisted tables
ALLOWED_TABLES = [
    "users", "airtime_balance", "purchased_bundles",
    "main_category", "sub_category", "period", "quantity_price"
]

ADMIN_PHONES = [p.strip() for p in os.getenv("ADMIN_PHONES", "").split(",") if p.strip()]

# ---------- Database helpers ----------
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
        )
    except Exception as e:
        logger.exception("Failed to connect to DB")
        raise

def fetch_one(query, params=()):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

def fetch_all(query, params=()):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

def to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value

# ---------- Startup: print allowed tables ----------
@app.on_event("startup")
def startup_event():
    for t in ALLOWED_TABLES:
        try:
            rows = fetch_all(f"SELECT * FROM {t};")
            print(f"\n--- {t.upper()} ({len(rows)} rows) ---")
        except Exception as e:
            logger.warning("Could not fetch table %s: %s", t, e)

# ---------- Domain helpers ----------
def fetch_user(phone):
    row = fetch_one("""
        SELECT u.*, COALESCE(a.balance, 0) AS airtime
        FROM users u
        LEFT JOIN airtime_balance a ON u.phone_number = a.phone_number
        WHERE u.phone_number = %s
    """, (phone,))
    if row:
        row["airtime"] = float(row.get("airtime", 0))
    return row

def fetch_airtime(phone):
    row = fetch_one("SELECT COALESCE(balance,0) AS balance FROM airtime_balance WHERE phone_number=%s", (phone,))
    return float(row["balance"]) if row else 0.0

def fetch_bundle_balances(phone):
    rows = fetch_all("""
        SELECT pb.phone_number, mc.name AS main_category, sc.name AS sub_category,
               pb.remaining, qp.quantity, qp.price, p.label AS period, pb.purchase_date
        FROM purchased_bundles pb
        JOIN quantity_price qp ON pb.quantity_price_id = qp.id
        JOIN period p ON qp.period_id = p.id
        JOIN sub_category sc ON p.sub_id = sc.id
        JOIN main_category mc ON sc.main_id = mc.id
        WHERE pb.phone_number=%s
        ORDER BY pb.purchase_date DESC
    """, (phone,))
    return rows

def list_main_categories():
    rows = fetch_all("SELECT name FROM main_category;")
    return [r["name"] for r in rows]

def list_subcategories(main_category=None):
    if main_category:
        rows = fetch_all("""
            SELECT sc.name FROM sub_category sc
            JOIN main_category mc ON sc.main_id = mc.id
            WHERE mc.name=%s
        """, (main_category,))
    else:
        rows = fetch_all("SELECT name FROM sub_category;")
    return [r["name"] for r in rows]

def fetch_bundles(main=None, sub=None, period=None):
    query = """
        SELECT mc.name AS main_category, sc.name AS sub_category,
               qp.quantity, qp.price, p.label AS period
        FROM quantity_price qp
        JOIN period p ON qp.period_id = p.id
        JOIN sub_category sc ON p.sub_id = sc.id
        JOIN main_category mc ON sc.main_id = mc.id
        WHERE 1=1
    """
    params = []
    if main: 
        query += " AND mc.name=%s"
        params.append(main)
    if sub:
        query += " AND sc.name=%s"
        params.append(sub)
    if period:
        query += " AND p.label=%s"
        params.append(period)
    return fetch_all(query, tuple(params))

# ---------- NLP helpers ----------
def normalize(text):
    return re.sub(r"[\-_/]+", " ", text.strip().lower())

PERIOD_MAP = {"daily":"day","weekly":"week","monthly":"month","day":"day","week":"week","month":"month"}
def parse_period(text):
    t = normalize(text)
    for k, v in PERIOD_MAP.items():
        if k in t:
            return v
    return None

def extract_category(message):
    msg = normalize(message)
    mains = list_main_categories()
    subs = list_subcategories()
    found_main, found_sub = None, None
    for m in mains:
        if m.lower() in msg:
            found_main = m
            break
    for s in subs:
        if s.lower() in msg:
            found_sub = s
            break
    return found_main, found_sub

def parse_quantity(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(gb|mb)?", text.lower())
    if m:
        return float(m.group(1)), m.group(2) or "unit"
    return None, None

def is_bundle_intent(text):
    t = text.lower()
    keywords = ["buy","purchase","bundle","subscribe","get","need","want","which","show"]
    return any(k in t for k in keywords)

# ---------- Chat endpoint ----------
@app.post("/chat")
def chat(req: ChatRequest):
    phone, message = req.phone.strip(), req.message.strip()
    user = fetch_user(phone)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    lower = message.lower()

    # 1. Ask name
    if re.search(r"\b(what('?s| is) my name|who am i|tell me my name)\b", lower):
        return {"reply": f"Your name is: {user.get('name')}"}

    # 2. Profile
    if re.match(r"^\s*show\s+(my\s+profile|profile|my info)\s*$", lower):
        return {"reply": f"{user.get('name')}, here is your profile.", "user": user}

    # 3. Airtime
    if re.search(r"\b(airtime|account balance)\b", lower) and "bundle" not in lower:
        return {"reply": f"{user.get('name')}, your airtime balance is: {fetch_airtime(phone)}"}

    # 4. Bundle balances
    if "bundle" in lower and "balance" in lower:
        bundles = fetch_bundle_balances(phone)
        if not bundles:
            return {"reply": f"{user.get('name')}, you have no active bundles."}
        lines = [f"{user.get('name')}, your active bundles:"]
        for i, b in enumerate(bundles, start=1):
            lines.append(f"{i}. {b['main_category']} / {b['sub_category']} — Remaining: {b['remaining']} — {b['period']} — Purchased: {b['purchase_date']}")
        return {"reply": "\n".join(lines)}

    # 5. Purchase command
    m = re.match(r"^\s*purchase\s+(\d+)\s*$", lower)
    if m:
        return {"reply": "Purchase logic not included here"}  # Placeholder

    # 6. Bundle intent
    if is_bundle_intent(message):
        main, sub = extract_category(message)
        if main and not sub:  # User asked main category only
            subcats = list_subcategories(main)
            if subcats:
                return {"reply": f"{user.get('name')}, under '{main}' you can choose: {', '.join(subcats)}"}
        # Else provide all bundles matching request
        bundles = fetch_bundles(main, sub, parse_period(message))
        if not bundles:
            return {"reply": f"{user.get('name')}, no bundles match your request."}
        lines = [f"{user.get('name')}, bundles matching your request:"]
        for b in bundles[:10]:
            lines.append(f"{b['main_category']} / {b['sub_category']} — {b['quantity']} units — {b['period']} — Price: {b['price']}")
        return {"reply": "\n".join(lines)}

    # 7. Fallback
    return {"reply": f"Hello {user.get('name')}, I can help you buy bundles, check airtime, or show your profile."}

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "service": "telecom-bundle-chat"}
