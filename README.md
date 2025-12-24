Quick FastAPI OpenAI example

Setup

1. Copy your OpenAI key into `.env` as:

```
OPENAI_API_KEY=sk-REPLACE_WITH_YOUR_KEY
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Test

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"Hello"}'
```
