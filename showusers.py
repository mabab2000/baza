import os
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

cur = conn.cursor()

import json

import json

# Query users table
cur.execute("SELECT * FROM users;")
rows = cur.fetchall()

# Get column names
colnames = [desc[0] for desc in cur.description]

# Convert rows to list of dictionaries for JSON
users_json = [dict(zip(colnames, row)) for row in rows]

# Print JSON in terminal
print(json.dumps(users_json, indent=4))

# Close connection
cur.close()
conn.close()

# Close connection
cur.close()
conn.close()

cur.close()
conn.close()
