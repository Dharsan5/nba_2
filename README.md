# Campus Energy Orchestrator

A smart campus energy monitoring dashboard for solar generation, demand forecasting, battery flow, and AI-powered energy recommendations. The app is designed for deployment across a static frontend and a Flask backend API.

## Features

- Real-time solar, grid, and load visualization
- Battery state-of-charge monitoring
- Department-wise solar generation breakdown
- Demand forecasting and energy source analysis
- AI recommendations for balancing solar and grid usage
- Forecast views for tomorrow's solar generation and campus demand
- Excel report generation for energy insights

## Project Structure

```text
campus-energy-orchestrator/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── Procfile
│   ├── *.pkl
│   ├── *.csv
│   └── *.xlsx
├── frontend/
│   ├── index.html
│   ├── solar.html
│   ├── solar-forecast.html
│   ├── demand.html
│   ├── recommendations.html
│   ├── api-config.js
│   └── requirements.txt
├── DEPLOYMENT.md
├── README.md
└── .gitignore
```

## Local Development

### 1) Start the backend

```powershell
cd backend
python app.py
```

The backend runs on:
```text
http://127.0.0.1:5000
```

### 2) Open the frontend

Open any HTML file in the `frontend` folder in your browser, such as:
```text
frontend/index.html
```

## Production Deployment

### Backend on Render

1. Create a new Web Service on Render.
2. Connect this repository.
3. Set the root directory to:
   ```text
   campus-energy-orchestrator/backend
   ```
4. Use Python 3.10.
5. Set build command:
   ```bash
   pip install -r requirements.txt
   ```
6. Set start command:
   ```bash
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
7. Deploy.

### Frontend on Vercel

1. Import the repository into Vercel.
2. Set the root directory to:
   ```text
   campus-energy-orchestrator/frontend
   ```
3. Use static hosting / Other project type.
4. Deploy.
5. Update the backend URL inside `frontend/api-config.js` if needed.

## Default Live API URL

```js
https://campus-energy-orchestrator-api.onrender.com
```

## Tech Stack

- Python
- Flask
- Pandas
- NumPy
- scikit-learn
- LightGBM
- Joblib
- HTML/CSS/JavaScript

## Notes

This project is intended for educational and demonstration use and simulates smart-grid intelligence using forecasting and renewable optimization logic.
