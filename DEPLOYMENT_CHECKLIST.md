# 🚀 AgriPredictX Deployment Checklist

Your complete agricultural yield prediction system is ready for local deployment! Follow this checklist to get started.

---

## ✅ Pre-Deployment Checklist

### System Requirements
- [ ] Python 3.8+ installed (`python --version`)
- [ ] PostgreSQL 12+ installed (`psql --version`)
- [ ] PostgreSQL service running (Windows: Services panel, Mac: `brew services`, Linux: systemctl)
- [ ] At least 2GB free disk space
- [ ] At least 1GB free RAM

### Project Setup
- [ ] Project folder: `C:\Users\ems\Documents\New project`
- [ ] All files present (check for .py, .ipynb, config files)
- [ ] `requirements.txt` file exists
- [ ] Internet connection available (for initial setup)

---

## 🎯 Deployment Steps

### Step 1: Install Dependencies (2 minutes)

**Windows - Double-click this:**
```
deploy_local.bat
```

**Or manually:**
```bash
# Open terminal in project folder
pip install -r requirements.txt
```

✅ **Success criteria:** All packages installed without errors

---

### Step 2: Start Database (1 minute)

**Windows:**
1. Open Services (services.msc)
2. Find "PostgreSQL Server XX"
3. Right-click → Start

**Mac:**
```bash
brew services start postgresql
```

**Linux:**
```bash
sudo systemctl start postgresql
```

✅ **Success criteria:** Database service is running

---

### Step 3: Run Deployment Script (2 minutes)

**Windows - Double-click:**
```
deploy_local.bat
```

**Or run Python directly:**
```bash
python deploy_local.py
```

This will:
- ✓ Create PostgreSQL user: `agripredictx`
- ✓ Create database: `agripredictx`
- ✓ Generate `.env` file with configuration
- ✓ Initialize database schema (6 tables)
- ✓ Start Flask API server on port 5000

✅ **Success criteria:** You see "✓ AgriPredictX API Server Started!"

---

### Step 4: Verify Installation (3 minutes)

**Open a new terminal and run:**

```bash
python test_api.py
```

This runs 6 tests:
1. Health Check
2. API Documentation
3. Yield Prediction with SHAP
4. Soil Ingestion
5. Prediction History
6. Ingestion Logs

✅ **Success criteria:** All 6 tests show "✓ PASS"

---

## 🌐 Access Your System

Once deployment is complete, open your browser and visit:

| URL | Purpose |
|-----|---------|
| http://localhost:5000/ | **Dashboard** - Web interface for predictions |
| http://localhost:5000/api-docs | **API Documentation** - Complete endpoint reference |
| http://localhost:5000/health | **Health Check** - System status |

---

## 📊 Your First Prediction

### Option 1: Web Dashboard

1. Open http://localhost:5000/
2. Enter farm data:
   - **Soil:** Nitrogen (150), Phosphorus (80), Potassium (120)
   - **Weather:** Temperature (28.5°C), Humidity (65%), Rainfall (50mm)
   - **Location:** Punjab, Ludhiana
   - **Crop:** Wheat
3. Click "Predict"
4. View results with SHAP explanations!

### Option 2: Python Script

```python
import requests

url = "http://localhost:5000/predict"
payload = {
    "soil": {
        "nitrogen": 150,
        "phosphorus": 80,
        "potassium": 120,
        "ph": 7.0,
        "moisture": 25,
        "soil_type": "loamy",
        "organic_carbon": 1.5,
        "electrical_conductivity": 0.8
    },
    "weather": {
        "temperature": 28.5,
        "humidity": 65,
        "rainfall": 50
    },
    "state": "Punjab",
    "district": "Ludhiana",
    "crop": "wheat"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Predicted Yield: {result['predicted_yield']}")
print(f"Top Positive Factors: {result['top_positive_factors']}")
```

### Option 3: cURL Command

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "soil": {"nitrogen": 150, "phosphorus": 80, "potassium": 120, "ph": 7.0, "moisture": 25},
    "weather": {"temperature": 28.5, "humidity": 65, "rainfall": 50},
    "state": "Punjab",
    "district": "Ludhiana",
    "crop": "wheat"
  }'
```

---

## 📋 API Quick Reference

### Endpoints Available

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System status |
| `GET` | `/api-docs` | API documentation |
| `POST` | `/predict` | Make yield prediction with SHAP |
| `POST` | `/ingestion/soil` | Load soil fertility data |
| `POST` | `/ingestion/weather` | Load weather data |
| `GET` | `/prediction-history` | View recent predictions |
| `GET` | `/ingestion-logs` | View operation logs |

---

## 🔧 Configuration

### Environment File (.env)

Located in project folder. Default settings:

```env
DATABASE_URL=postgresql://agripredictx:agripredict123@localhost:5432/agripredictx
OPENWEATHER_API_KEY=your_api_key_here
FLASK_DEBUG=False
FLASK_ENV=production
MODEL_PATH=crop_model.pkl
```

### Getting API Keys (Optional)

**OpenWeatherMap (for weather ingestion):**
1. Visit https://openweathermap.org/api
2. Sign up (free account)
3. Get API key from Account → My API Keys
4. Add to .env: `OPENWEATHER_API_KEY=your_key`

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **LOCAL_DEPLOYMENT.md** | Complete deployment guide |
| **ARCHITECTURE.md** | System design and data flow |
| **IMPLEMENTATION_SUMMARY.md** | What was built and how |
| **QUICKSTART.md** | Code examples and quick reference |
| **system_config.py** | Configuration reference |
| **FILE_INDEX.md** | File directory and purposes |
| **database_models.py** | Database schema (6 tables) |
| **ingestion_layer.py** | Data ingestion from 4 sources |
| **feature_engineering.py** | ML feature calculations |
| **explainability.py** | SHAP integration |

---

## ⚠️ Troubleshooting

### Issue: "PostgreSQL not running"
**Solution:**
```bash
# Windows
net start postgresql-x64-14

# Or use Services panel (services.msc)
```

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "Connection refused - 127.0.0.1:5432"
**Solution:** PostgreSQL service is not running. Start it from Services or command line above.

### Issue: "Port 5000 already in use"
**Solution:** Stop the other service or edit api_server_enhanced.py to use different port (e.g., 5001).

### Issue: "FATAL: password authentication failed"
**Solution:** Check .env file has correct credentials. Default is:
```
DATABASE_URL=postgresql://agripredictx:agripredict123@localhost:5432/agripredictx
```

**More help:** See LOCAL_DEPLOYMENT.md → Troubleshooting section

---

## 🎯 What You Can Now Do

✅ **Make Predictions**
- Predict crop yield based on soil, weather, and location
- Get SHAP explanations for every prediction
- View top positive/negative factors

✅ **Ingest Data**
- Load soil fertility measurements
- Ingest weather data from APIs
- Store satellite NDVI data
- Track historical crop yields

✅ **Monitor System**
- View prediction history with explanations
- Check ingestion operation logs
- Monitor system health and components
- Access complete audit trail

✅ **Integrate**
- Use REST API in your applications
- Connect to frontend dashboards
- Build farmer mobile apps
- Automate batch predictions

---

## 📈 Next Steps (Optional)

1. **Connect Frontend** - Update index.html and app.js to use the API
2. **Setup Monitoring** - Add Prometheus/Grafana for metrics
3. **Automate Ingestion** - Use APScheduler for continuous updates
4. **Add Authentication** - Implement user login and API keys
5. **Deploy to Cloud** - Docker → AWS/GCP/Azure
6. **Train Custom Model** - Retrain with your farm data

---

## ✨ System Architecture

```
┌────────────────────────────────┐
│   Local AgriPredictX System     │
└────────────┬───────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌─────┐ ┌──────┐ ┌──────┐
│Flask│ │Model │ │SHAP  │
│API  │ │ML    │ │Explain
└─────┘ └──────┘ └──────┘
    │        │        │
    └────────┼────────┘
             │
        ┌────▼────┐
        │PostgreSQL
        │Database
        └─────────┘
```

**Components:**
- **Flask API** - HTTP server on port 5000
- **ML Model** - XGBoost for yield prediction
- **SHAP Engine** - Feature importance explanations
- **PostgreSQL** - 6 tables for data storage
- **Feature Engineer** - 10+ agronomic features
- **Ingestion Layer** - Data from 4 sources

---

## 🎉 You're Ready to Go!

Your local AgriPredictX deployment is complete and running!

### Quick Commands Reference

```bash
# Start fresh deployment
python deploy_local.py

# Test the system
python test_api.py

# View dashboard
http://localhost:5000/

# See all endpoints
http://localhost:5000/api-docs

# Check system health
http://localhost:5000/health
```

---

**Happy Farming! 🌾**

For questions or issues, refer to LOCAL_DEPLOYMENT.md or check system_config.py for detailed configuration options.
