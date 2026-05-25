# EE427 — Voice Robot (Group G-19)

**React (Vercel)** → **FastAPI + ngrok** → **ESP32 on LAN**

```
Computer Networks/
├── backend/            FastAPI bridge (Python)
├── frontend/           Vite + React UI
├── esp32_controller.py Local keyboard controller
├── requirements.txt    Python deps for keyboard controller
└── README.md
```

---

## Local testing

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env
```

Set in `backend/.env`:

| Variable | Example |
|----------|---------|
| `BRIDGE_API_KEY` | any long random string |
| `ESP32_BASE_URL` | `http://192.168.1.192` |
| `CORS_ORIGINS` | `http://localhost:5173` |

Start the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check it works: `curl http://localhost:8000/health` → `{"status":"ok"}`

---

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local      # then edit
npm install
npm run dev
```

Set in `frontend/.env.local`:

| Variable | Value for local testing |
|----------|------------------------|
| `VITE_API_URL` | `http://localhost:8000` |
| `VITE_API_KEY` | same value as `BRIDGE_API_KEY` |

Open the printed URL in **Chrome** (speech recognition requires Chrome/Edge).

---

### 3. Keyboard controller (local LAN only)

```bash
pip install -r requirements.txt
python esp32_controller.py --url http://192.168.1.192
```

| Key | Action |
|-----|--------|
| W/S/A/D | Forward / Back / Left / Right |
| E | Stop |
| 1/2/3 | Speed Low / Med / High |
| Q | Quit (sends stop) |

---

## Vercel + ngrok (remote access)

### ngrok

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL (e.g. `https://xxxx.ngrok-free.app`).

### Frontend on Vercel

1. Push the repo to GitHub.
2. Import in Vercel → set **Root Directory** to `frontend`.
3. Add environment variables:
   - `VITE_API_URL` = your ngrok HTTPS URL
   - `VITE_API_KEY` = your `BRIDGE_API_KEY` value
4. Deploy.

### Backend CORS

Add your Vercel URL to `CORS_ORIGINS` in `backend/.env`:

```
CORS_ORIGINS=http://localhost:5173,https://your-app.vercel.app
```

Restart uvicorn after editing .env.

---

## ESP32 API contract

| Route | Action |
|-------|--------|
| `GET /F` | Forward |
| `GET /B` | Backward |
| `GET /L` | Left |
| `GET /R` | Right |
| `GET /S` | Stop |
| `GET /SPD/LOW` | Speed low |
| `GET /SPD/MED` | Speed medium |
| `GET /SPD/HIGH` | Speed high |
