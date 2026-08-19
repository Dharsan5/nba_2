# Deployment Guide

This project is split into:
- Frontend: `frontend/` static files
- Backend: `backend/` Flask API

## 1) Backend on Render

1. Push the project to GitHub.
2. In Render, create a new Web Service.
3. Connect the GitHub repo.
4. Set the service configuration:
   - Name: `campus-energy-orchestrator-api`
   - Root directory: `campus-energy-orchestrator/backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Keep the default Python version or choose `3.10`.
6. Deploy.

After deployment, copy the Render URL, for example:
`https://campus-energy-orchestrator-api.onrender.com`

## 2) Frontend on Vercel

1. Push the project to GitHub.
2. In Vercel, import the repository.
3. Set the project root directory to `campus-energy-orchestrator/frontend`.
4. Framework: `Other` / static hosting.
5. No build command is needed for plain HTML/CSS/JS.
6. Output directory: `.`
7. Deploy.

## 3) Update frontend API URL

Open `frontend/api-config.js` and replace:
`https://YOUR_RENDER_BACKEND.onrender.com`
with your actual Render backend URL.

Example:
```js
window.__APP_CONFIG__.API_BASE = "https://campus-energy-orchestrator-api.onrender.com";
```

## 4) Local testing

Start the backend locally:
```powershell
cd backend
python app.py
```

Open the frontend locally in a browser from the `frontend` folder.

The app will automatically use `http://127.0.0.1:5000` when running locally.
