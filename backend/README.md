# Backend (FastAPI)

## Setup (Windows PowerShell)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Config

- Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
- System prompt is stored in `./prompts/gemini_1_5_system.txt` (override with `GEMINI_SYSTEM_PROMPT` if needed).

## Endpoints

- `POST /analyze`
- `POST /feedback`

OpenAPI docs:
- http://localhost:8000/docs
