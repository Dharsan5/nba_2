import os
import random
import joblib
import pandas as pd
import numpy as np
import requests
from math import sin, pi
from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask import send_file

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ===== REAL TIME TREND STORAGE =====
trend_history = {
    "solar": [],
    "demand": [],
    "grid": []
}
# ===== SMART GRID SYSTEM STATE =====
system_state = {
    "last_analysis_time": None,
    "alerts": {
        "battery_low": 30,
        "grid_peak": 400,
        "solar_low": 120
    },
    "grid_risk": "NORMAL",
    "ai_confidence": 92
}

# ===== DAILY SOLAR TRACKING =====
def ai_recommendations(solar_kw, demand_kw, battery_soc):

    recs = []

    solar_surplus = solar_kw - demand_kw
    demand_gap = demand_kw - solar_kw

    # ⭐ Priority 1 – Energy balance decision
    if solar_surplus > 50:
        recs.append(["HIGH",
                    "Store Excess Solar Energy",
                    "Solar generation exceeds demand. Charge battery to use energy during evening peak."])
    else:
        recs.append(["HIGH",
                    "Use Battery to Reduce Grid Usage",
                    "Solar generation is lower than demand. Discharge battery strategically to reduce electricity cost."])

    # ⭐ Priority 2 – Load optimization
    if solar_kw > 200:
        recs.append(["MEDIUM",
                    "Shift Flexible Loads to Daytime",
                    "Run heavy equipment during solar peak hours to maximize renewable usage."])
    else:
        recs.append(["MEDIUM",
                    "Limit Non-Essential Loads",
                    "Reduce optional loads to maintain energy balance and improve efficiency."])

    # ⭐ Priority 3 – Battery health intelligence
    if battery_soc > 85:
        recs.append(["LOW",
                    "Avoid Overcharging Battery",
                    "Battery SOC is high. Allow slight discharge to improve battery lifespan."])
    elif battery_soc < 30:
        recs.append(["HIGH",
                    "Activate Battery Protection Mode",
                    "Battery level is low. Prevent deep discharge to avoid long-term damage."])
    else:
        recs.append(["LOW",
                    "Battery Operating Normally",
                    "Battery level is in optimal range for efficient operation."])

    # ⭐ Priority 4 – System performance insight
    if solar_kw < 120:
        recs.append(["MEDIUM",
                    "Check Solar Panel Efficiency",
                    "Solar output is below expected level. Cleaning or inspection may improve performance."])
    else:
        recs.append(["LOW",
                    "Solar System Performing Efficiently",
                    "Solar generation is stable and supporting sustainable energy utilization."])

    return recs[:4]   # ⭐ ensures only 4 recommendations
solar_history = []
last_reset_day = datetime.now().day

API_KEY = "f3c1255b2e07d84a291e81f285ee4b01"
CITY = "Perundurai"

DEPT_SOLAR_SHARE = {
    "CTUG": 0.16,
    "IT_PARK": 0.14,
    "S&H": 0.12,
    "EEE": 0.11,
    "FT": 0.10,
    "MTS": 0.09,
    "CIVIL": 0.07,
    "MBA": 0.06,
    "ADMIN": 0.05,
    "ECE": 0.05,
    "AM": 0.03,
    "NATUROPATHY": 0.02
}

SOLAR_CAPACITY = 1500
GRID_TARIFF = 8
CO2_FACTOR = 0.82
BATTERY_MAX_DISCHARGE = 500

# ===== LOAD MODELS =====
solar_model = joblib.load("final_solar_model.pkl")
demand_model = joblib.load("demand_forecast_lgb_model.pkl")

# ===== LOAD DATA FOR LAG FEATURES =====
solar_df = pd.read_csv("solar_cleaned_hourly.csv")
solar_df["DATE_TIME"] = pd.to_datetime(solar_df["DATE_TIME"])
solar_df = solar_df.sort_values("DATE_TIME")

demand_df = pd.read_csv("consumption_2025_processed (1).csv")

weekday_map = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

demand_df["day_of_week_num"] = demand_df["day_of_week"].map(weekday_map)
demand_df["consumption_lag1"] = demand_df["consumption"].shift(1)
demand_df["consumption_lag2"] = demand_df["consumption"].shift(2)
demand_df["consumption_lag24"] = demand_df["consumption"].shift(24)
demand_df = demand_df.dropna()

daily_energy_total = 0
daily_hourly_log = []
last_reset_day = datetime.now().day
last_logged_hour = -1

@app.route("/api/data")
def get_data():
    
    global daily_energy_total, daily_hourly_log, last_reset_day, solar_history, last_logged_hour
    
    # ===== WEATHER API =====
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    weather = requests.get(url).json()

    temp = weather["main"]["temp"]
    cloud = weather["clouds"]["all"]
    humidity = weather["main"]["humidity"]
    wind_speed = weather["wind"]["speed"]
    weather_condition = weather["weather"][0]["main"]

    now = datetime.now()
    hour = now.hour
    
    # ===== STORE REAL TREND VALUES =====
    
    
    # ===== SOLAR IRRADIATION PHYSICS =====
    if 6 <= hour <= 18:
        base_irr = sin(pi * (hour - 6) / 12)
    else:
        base_irr = 0

    irradiation = base_irr * (1 - cloud / 100)
    irradiation = max(0, irradiation)

    last_solar = solar_df.iloc[-1]

    # ===== NEW ML FEATURES (MATCH TRAINING) =====
    irr_sq = irradiation ** 2
    irr_lag1 = last_solar["IRRADIATION"]
    irr_lag2 = solar_df.iloc[-2]["IRRADIATION"]
    irr_roll3 = solar_df["IRRADIATION"].tail(3).mean()

    temp_diff = (temp + 3) - temp
    irr_hour = irradiation * hour
    energy_lag1 = last_solar["ENERGY_KWH_HOUR"]

    solar_features = [[
        irradiation,
        irr_sq,
        irr_lag1,
        irr_lag2,
        temp_diff,
        hour,
        now.month,
        energy_lag1
    ]]


    predicted_log = solar_model.predict(solar_features)[0]
    predicted_norm = np.expm1(predicted_log)

    NORMALIZED_PEAK = 20
    ml_ratio = predicted_norm / NORMALIZED_PEAK

    ml_ratio = max(0.2, min(ml_ratio, 1))

    EFFICIENCY = 0.75
    solar_kw = SOLAR_CAPACITY * irradiation * EFFICIENCY * ml_ratio
    
    if solar_kw < 50 and irradiation > 0:
        solar_kw = solar_kw + 40

    solar_kw = max(0, solar_kw)
    solar_kw = min(solar_kw, SOLAR_CAPACITY)
    solar_kw = round(solar_kw, 1)
    
    
    current_day = datetime.now().day

# reset at midnight
    if current_day != last_reset_day:
        daily_energy_total = 0
        daily_hourly_log = []
        last_logged_hour = -1
        last_reset_day = current_day

    # ⭐ ADD ONLY ONCE PER HOUR
    if hour != last_logged_hour:
        daily_energy_total += solar_kw

        daily_hourly_log.append({
            "hour": hour,
            "solar_kw": solar_kw
        })

    last_logged_hour = hour
    
    dept_solar = {}

    for dept, share in DEPT_SOLAR_SHARE.items():
        dept_solar[dept] = round(solar_kw * share, 1)
    
    

    current_day = datetime.now().day

# reset history at midnight
    if current_day != last_reset_day:
        solar_history = []
        last_reset_day = current_day

    solar_history.append(solar_kw)

    # ===== DEMAND SIMULATION =====
    # ===== NEW ADVANCED DEMAND FEATURES =====

    df = demand_df.copy()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    df["day_of_week_num"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week_num"].isin([5,6]).astype(int)

    # cyclic
    df["month_sin"] = np.sin(2*np.pi*df["month"]/12)
    df["month_cos"] = np.cos(2*np.pi*df["month"]/12)

    df["week_sin"] = np.sin(2*np.pi*df["day_of_week_num"]/7)
    df["week_cos"] = np.cos(2*np.pi*df["day_of_week_num"]/7)

    # trend index
    df["time_index"] = np.arange(len(df))

    # lag features
    df["consumption_lag1"] = df["consumption"].shift(1)
    df["consumption_lag2"] = df["consumption"].shift(2)
    df["consumption_lag3"] = df["consumption"].shift(3)
    df["consumption_lag7"] = df["consumption"].shift(7)
    df["consumption_lag14"] = df["consumption"].shift(14)
    df["consumption_lag21"] = df["consumption"].shift(21)
    df["consumption_lag24"] = df["consumption"].shift(24)
    df["consumption_lag28"] = df["consumption"].shift(28)

    # rolling
    df["rolling_mean_3"] = df["consumption"].rolling(3).mean()
    df["rolling_mean_7"] = df["consumption"].rolling(7).mean()
    df["rolling_mean_14"] = df["consumption"].rolling(14).mean()
    df["rolling_mean_30"] = df["consumption"].rolling(30).mean()

    df["rolling_std_7"] = df["consumption"].rolling(7).std()

    # ema
    df["ema_7"] = df["consumption"].ewm(span=7).mean()
    df["ema_14"] = df["consumption"].ewm(span=14).mean()

    # trend
    df["trend"] = df["consumption"].shift(1) - df["consumption"].shift(2)

    df = df.dropna().reset_index(drop=True)

    last = df.iloc[-1]

    FEATURE_COLS = [
        "day","month","year",
        "month_sin","month_cos",
        "week_sin","week_cos",
        "is_weekend",
        "time_index",

        "consumption_lag1",
        "consumption_lag2",
        "consumption_lag3",
        "consumption_lag7",
        "consumption_lag14",
        "consumption_lag21",
        "consumption_lag24",
        "consumption_lag28",

        "rolling_mean_3",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_30",
        "rolling_std_7",
        "ema_7",
        "ema_14",
        "trend"
    ]
    

    demand_features = last[FEATURE_COLS].values.reshape(1,-1)

    predicted_demand = demand_model.predict(demand_features)[0]

    # smoothing (important for dashboard stability)
    predicted_demand = 0.7 * predicted_demand + 0.3 * last["rolling_mean_7"]

    demand_kw = round(max(0, predicted_demand), 1)

    # ===== BATTERY + GRID LOGIC =====
    if solar_kw >= demand_kw:
        battery_flow = (solar_kw - demand_kw) * 0.4
        battery_flow = min(battery_flow, BATTERY_MAX_DISCHARGE)
        grid_import = 0
        source = "Solar + Battery"
    else:
        battery_flow = min((demand_kw - solar_kw) * 0.3, BATTERY_MAX_DISCHARGE)
        grid_import = demand_kw - solar_kw - battery_flow
        source = "Grid + Battery + Solar"

    battery_flow = round(battery_flow, 1)
    grid_import = round(max(grid_import, 0), 1)

    battery_soc = random.randint(70, 95)
    
    

    # ===== COST + CO2 =====
    solar_used = max(0, min(solar_kw, demand_kw))
    cost_saving = round(solar_used * GRID_TARIFF, 1)
    co2_saved = round((solar_used * CO2_FACTOR) / 1000, 3)
    recommendations = ai_recommendations(solar_kw, demand_kw, battery_soc)
    
    # ===== STORE REAL TREND VALUES =====
    # ===== STORE REAL TREND VALUES =====
    trend_history["solar"].append(solar_kw)
    trend_history["demand"].append(demand_kw)
    trend_history["grid"].append(grid_import)

    trend_history["solar"] = trend_history["solar"][-12:]
    trend_history["demand"] = trend_history["demand"][-12:]
    trend_history["grid"] = trend_history["grid"][-12:]

    return jsonify({
        "solar_kw": solar_kw,
        "department_solar_generation": dept_solar,
        "irradiation": round(irradiation, 3),
        "cloud": cloud,
        "temperature": temp,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "weather_condition": weather_condition,
        "demand_kw": demand_kw,
        "battery_flow": battery_flow,
        "battery_soc": battery_soc,
        "grid_import": grid_import,
        "source": source,
        "cost_saving": cost_saving,
        "co2_saved": co2_saved,
        "recommendations": recommendations
    })
    
@app.route("/api/trend-data")
def real_trend_data():

    return jsonify({
        "solar": trend_history["solar"],
        "demand": trend_history["demand"],
        "grid": trend_history["grid"]
    })
    
@app.route("/api/refresh-analysis", methods=["POST"])
def refresh_analysis():

    global system_state

    # simulate fresh ML inference
    now = datetime.now()

    solar_kw = random.randint(80, 900)
    demand_kw = random.randint(200, 600)

    grid_risk = "LOW"
    if demand_kw > system_state["alerts"]["grid_peak"]:
        grid_risk = "HIGH"
    elif demand_kw > 0.8 * system_state["alerts"]["grid_peak"]:
        grid_risk = "MEDIUM"

    system_state["grid_risk"] = grid_risk
    system_state["last_analysis_time"] = now.strftime("%H:%M:%S")
    system_state["ai_confidence"] = random.randint(88, 97)

    return jsonify({
        "status": "updated",
        "analysis_time": system_state["last_analysis_time"],
        "grid_risk": grid_risk,
        "ai_confidence": system_state["ai_confidence"],
        "solar_sample": solar_kw,
        "demand_sample": demand_kw
    })

@app.route("/api/set-alerts", methods=["POST"])
def set_alerts():

    global system_state

    system_state["alerts"]["battery_low"] = random.randint(25, 35)
    system_state["alerts"]["grid_peak"] = random.randint(380, 450)
    system_state["alerts"]["solar_low"] = random.randint(100, 150)

    return jsonify({
        "status": "configured",
        "battery_low": system_state["alerts"]["battery_low"],
        "grid_peak": system_state["alerts"]["grid_peak"],
        "solar_low": system_state["alerts"]["solar_low"]
    })

@app.route("/api/report")
def generate_advanced_energy_report():

    data = get_data().json

    solar = data["solar_kw"]
    demand = data["demand_kw"]
    soc = data["battery_soc"]
    grid = data["grid_import"]
    cost = data["cost_saving"]
    co2 = data["co2_saved"]
    recs = data["recommendations"]

    now = datetime.now()

    # ===== SYSTEM KPI SHEET =====
    kpi_df = pd.DataFrame({
        "Metric":[
            "Solar Generation (kW)",
            "Load Demand (kW)",
            "Battery SOC (%)",
            "Grid Import (kW)",
            "Cost Saving Today (₹)",
            "Carbon Reduction (tons)"
        ],
        "Value":[solar,demand,soc,grid,cost,co2]
    })

    # ===== AI RECOMMENDATION SHEET =====
    rec_df = pd.DataFrame(recs,columns=["Priority","Recommendation","Reason"])

    # ===== PERFORMANCE ANALYTICS =====
    utilization = round((solar/(demand+1))*100,1)
    grid_dependency = round((grid/(demand+1))*100,1)

    perf_df = pd.DataFrame({
        "Indicator":[
            "Renewable Utilization %",
            "Grid Dependency %",
            "Battery Support %",
            "System Efficiency Score"
        ],
        "Value":[
            utilization,
            grid_dependency,
            round((soc/100)*50,1),
            round(80 + utilization*0.1,1)
        ]
    })

    # ===== RISK ANALYSIS =====
    risk = "LOW"
    if demand > 420:
        risk = "HIGH"
    elif demand > 350:
        risk = "MEDIUM"

    risk_df = pd.DataFrame({
        "Parameter":[
            "Peak Load Risk",
            "Battery Health Status",
            "Solar Stability",
            "AI Confidence"
        ],
        "Status":[
            risk,
            "GOOD" if soc>40 else "CRITICAL",
            "STABLE" if solar>150 else "VARIABLE",
            str(random.randint(88,97)) + "%"
        ]
    })

    # ===== DAILY TREND (Simulated intelligent trend) =====
    trend = np.random.randint(100,600,24)

    trend_df = pd.DataFrame({
        "Hour": list(range(24)),
        "Solar_kW": trend
    })

    # ===== MONTHLY PROJECTION =====
    monthly_energy = sum(trend) * 30
    monthly_df = pd.DataFrame({
        "Metric":[
            "Projected Monthly Solar Energy (kWh)",
            "Projected Monthly Cost Saving (₹)",
            "Projected CO2 Reduction (tons)"
        ],
        "Value":[
            monthly_energy,
            monthly_energy * 8,
            round(monthly_energy * 0.82 / 1000,2)
        ]
    })

    file = "AI_Smart_Grid_Energy_Report.xlsx"

    with pd.ExcelWriter(file) as writer:
        kpi_df.to_excel(writer, sheet_name="System KPI", index=False)
        rec_df.to_excel(writer, sheet_name="AI Recommendations", index=False)
        perf_df.to_excel(writer, sheet_name="Performance Analytics", index=False)
        risk_df.to_excel(writer, sheet_name="Risk Evaluation", index=False)
        trend_df.to_excel(writer, sheet_name="Daily Solar Trend", index=False)
        monthly_df.to_excel(writer, sheet_name="Monthly Projection", index=False)

    return send_file(file, as_attachment=True)

@app.route("/api/solar-tomorrow-forecast")
def solar_tomorrow():

    # ===== WEATHER FORECAST API =====
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()

    forecast_list = data["list"]

    solar_forecast = []

    last_solar = solar_df.iloc[-1]
    irr_lag1 = last_solar["IRRADIATION"]
    irr_lag2 = solar_df.iloc[-2]["IRRADIATION"]
    energy_lag1 = last_solar["ENERGY_KWH_HOUR"]

    total_energy = 0

    for item in forecast_list[:24]:   # next 24 hours

        cloud = item["clouds"]["all"]
        temp = item["main"]["temp"]

        dt = datetime.fromtimestamp(item["dt"])
        hour = dt.hour
        month = dt.month

        # ===== PHYSICS IRRADIATION =====
        if 6 <= hour <= 18:
            base_irr = sin(pi * (hour - 6) / 12)
        else:
            base_irr = 0

        irradiation = base_irr * (1 - cloud / 100)
        irradiation = max(0, irradiation)

        irr_sq = irradiation ** 2

        solar_features = [[
            irradiation,
            irr_sq,
            irr_lag1,
            irr_lag2,
            3,
            hour,
            month,
            energy_lag1
        ]]

        predicted_log = solar_model.predict(solar_features)[0]
        predicted_norm = np.expm1(predicted_log)

        NORMALIZED_PEAK = 20
        ml_ratio = predicted_norm / NORMALIZED_PEAK
        ml_ratio = max(0.2, min(ml_ratio, 1))

        EFFICIENCY = 0.75
        solar_kw = SOLAR_CAPACITY * irradiation * EFFICIENCY * ml_ratio
        solar_kw = round(max(0, min(solar_kw, SOLAR_CAPACITY)), 1)

        total_energy += solar_kw

        solar_forecast.append({
            "hour": hour,
            "cloud": cloud,
            "irradiation": round(irradiation,3),
            "solar_kw": solar_kw
        })

    return jsonify({
        "tomorrow_total_solar_energy_kwh": round(total_energy,1),
        "hourly_forecast": solar_forecast
    })

@app.route("/api/demand-tomorrow-total")
def demand_tomorrow_total():

    df = demand_df.copy()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # ===== SAME FEATURE ENGINEERING AS TRAINING =====
    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    df["day_of_week_num"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week_num"].isin([5,6]).astype(int)

    df["month_sin"] = np.sin(2*np.pi*df["month"]/12)
    df["month_cos"] = np.cos(2*np.pi*df["month"]/12)

    df["week_sin"] = np.sin(2*np.pi*df["day_of_week_num"]/7)
    df["week_cos"] = np.cos(2*np.pi*df["day_of_week_num"]/7)

    df["time_index"] = np.arange(len(df))

    df["consumption_lag1"] = df["consumption"].shift(1)
    df["consumption_lag2"] = df["consumption"].shift(2)
    df["consumption_lag3"] = df["consumption"].shift(3)
    df["consumption_lag7"] = df["consumption"].shift(7)
    df["consumption_lag14"] = df["consumption"].shift(14)
    df["consumption_lag21"] = df["consumption"].shift(21)
    df["consumption_lag24"] = df["consumption"].shift(24)
    df["consumption_lag28"] = df["consumption"].shift(28)

    df["rolling_mean_3"] = df["consumption"].rolling(3).mean()
    df["rolling_mean_7"] = df["consumption"].rolling(7).mean()
    df["rolling_mean_14"] = df["consumption"].rolling(14).mean()
    df["rolling_mean_30"] = df["consumption"].rolling(30).mean()

    df["rolling_std_7"] = df["consumption"].rolling(7).std()

    df["ema_7"] = df["consumption"].ewm(span=7).mean()
    df["ema_14"] = df["consumption"].ewm(span=14).mean()

    df["trend"] = df["consumption"].shift(1) - df["consumption"].shift(2)

    df = df.dropna().reset_index(drop=True)

    last = df.iloc[-1]

    FEATURE_COLS = [
        "day","month","year",
        "month_sin","month_cos",
        "week_sin","week_cos",
        "is_weekend",
        "time_index",

        "consumption_lag1",
        "consumption_lag2",
        "consumption_lag3",
        "consumption_lag7",
        "consumption_lag14",
        "consumption_lag21",
        "consumption_lag24",
        "consumption_lag28",

        "rolling_mean_3",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_30",
        "rolling_std_7",
        "ema_7",
        "ema_14",
        "trend"
    ]

    features = last[FEATURE_COLS].values.reshape(1,-1)

    predicted_daily_demand = demand_model.predict(features)[0]

    return {
        "tomorrow_total_demand_kwh": round(float(predicted_daily_demand),1)
    }
    
from flask import send_file

@app.route("/api/report")
def generate_full_energy_report():

    data = get_data().json

    solar = data["solar_kw"]
    demand = data["demand_kw"]
    soc = data["battery_soc"]
    cost = data["cost_saving"]
    co2 = data["co2_saved"]
    recs = data["recommendations"]

    # ===== Solar Summary Sheet =====
    solar_df_report = pd.DataFrame({
        "Metric":[
            "Current Solar Generation (kW)",
            "Current Demand (kW)",
            "Battery SOC (%)",
            "Grid Import (kW)",
            "Cost Saving (₹)",
            "CO2 Saved (tons)"
        ],
        "Value":[
            solar,
            demand,
            soc,
            data["grid_import"],
            cost,
            co2
        ]
    })

    # ===== Recommendation Sheet =====
    rec_df = pd.DataFrame(recs,columns=["Priority","Recommendation","Reason"])

    # ===== Department Solar Sheet =====
    dept_df = pd.DataFrame(
        list(data["department_solar_generation"].items()),
        columns=["Department","Solar Generation kW"]
    )

    # ===== Daily History Sheet =====
    global solar_history
    daily_df = pd.DataFrame({
        "Hourly Solar kW": solar_history
    })

    # ===== Monthly Simulation Sheet =====
    monthly_energy = sum(solar_history) * 30
    monthly_df = pd.DataFrame({
        "Metric":["Estimated Monthly Solar Energy kWh"],
        "Value":[round(monthly_energy,1)]
    })

    file = "Hybrid_Solar_Energy_Report.xlsx"

    with pd.ExcelWriter(file) as writer:
        solar_df_report.to_excel(writer, sheet_name="System Summary", index=False)
        rec_df.to_excel(writer, sheet_name="AI Recommendations", index=False)
        dept_df.to_excel(writer, sheet_name="Department Solar", index=False)
        daily_df.to_excel(writer, sheet_name="Daily Solar Trend", index=False)
        monthly_df.to_excel(writer, sheet_name="Monthly Projection", index=False)

    return send_file(file, as_attachment=True)

@app.route("/api/solar-full-day")
def solar_full_day():

    global daily_energy_total, daily_hourly_log

    return jsonify({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "plant_capacity": SOLAR_CAPACITY,
        "total_solar_generation_kwh": round(float(daily_energy_total),1),
        "hourly_breakdown": daily_hourly_log
    })
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)