# Autonomous Scam Detection (India-first)

This repo contains a Next.js frontend and a Python (FastAPI) backend for AI-assisted scam detection.

## Structure

- `frontend/` — Next.js UI + API route that proxies to backend
- `backend/` — FastAPI API-only backend (`POST /analyze`, `POST /feedback`)

## Quick start (Windows PowerShell)

### 1) Backend (FastAPI)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run backend (pick a free port)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --app-dir "$PWD"
```

Backend docs:
- http://127.0.0.1:8010/docs

### 2) Frontend (Next.js)

```powershell
cd frontend
npm install

# Point the frontend API route to the backend
$env:BACKEND_URL="http://127.0.0.1:8010"

npm run dev
```

Open:
- http://localhost:3000

## Environment variables

Backend (create `backend/.env` from `backend/.env.example`):
- `GEMINI_API_KEY` — Gemini API key (Gemini 1.5 recommended)
- `GEMINI_MODEL` — e.g. `gemini-1.5-flash`
- `BACKEND_API_KEY` — optional API key for backend auth

Frontend (optional):
- `BACKEND_URL` — where the backend is running (default: `http://127.0.0.1:8000`)
- `BACKEND_API_KEY` — forwarded as `X-API-Key` when set

## API

- `POST /analyze` — unified scam analysis endpoint
- `POST /feedback` — store user feedback (scam/safe)
