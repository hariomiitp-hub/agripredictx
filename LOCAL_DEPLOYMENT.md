# Local Deployment Guide - AgriPredictX

Deploy the complete AgriPredictX system locally on your computer in minutes!

## ✅ Prerequisites

Before starting, ensure you have:

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 12+** - [Download](https://www.postgresql.org/download/)
- **Git** (optional) - For version control
- **Internet connection** - For initial setup and API calls

### Verify Prerequisites

```bash
# Check Python
python --version

# Check PostgreSQL
psql --version
```

---

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd "C:\Users\ems\Documents\New project"

# Install Python packages
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed flask, sqlalchemy, shap, xgboost, pandas, ...
```

### Step 2: Start PostgreSQL Service

**Windows:**
1. Open Services (services.msc)
2. Find "PostgreSQL Server XX"
3. Right-click → Start

OR in Command Prompt:
```bash
net start postgresql-x64-14
```

**Mac:**
```bash
brew services start postgresql
```

**Linux:**
```bash
sudo systemctl start postgresql
```

### Step 3: Deploy and Start Server

```bash
# Run deployment script
python deploy_local.py
```

The script will:
- ✓ Check prerequisites
- ✓ Create PostgreSQL user and database
- ✓ Create .env configuration file
- ✓ Initialize database schema
- ✓ Start the API server

**Expected output:**
```
============================================================
✓ AgriPredictX API Server Started!
============================================================

Local deployment ready:
  Dashboard:   http://localhost:5000/
  API Docs:    http://localhost:5000/api-docs
  Health:      http://localhost:5000/health

============================================================
```

---

## 📡 Verify Deployment

Open a new terminal and run:

```bash
python test_api.py
```

This will run 6 tests and verify the system is working:
1. ✓ Health Check
2. ✓ API Documentation
3. ✓ Yield Prediction with SHAP
4. ✓ Soil Data Ingestion
5. ✓ Prediction History
6. ✓ Ingestion Logs

**Expected output:**
```
============================================================
AgriPredictX API Test Suite
============================================================

Checking if API server is running at http://localhost:5000...
✓ API server is running!

... test results ...

Total: 6/6 tests passed

✓ All tests passed! API is working correctly.
```

---

## 🌐 Access the System

Once the server is running, open your browser and go to:

### Dashboard
```
http://localhost:5000/
```
Web interface for making predictions and viewing results

### API Documentation
```
http://localhost:5000/api-docs
```
Complete API endpoint reference

### Health Check
```
http://localhost:5000/health
```
System status and component information

---

## 📋 API Endpoints Reference

### 1. Predict Crop Yield

**Endpoint:** `POST /predict`

**Request:**
```json
{
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
  "crop": "wheat",
  "baseline_yield": 3.5
}
```

**Response:**
```json
{
  "success": true,
  "prediction_id": "uuid",
  "predicted_yield": "3.7 t/ha",
  "baseline_yield": "3.5 t/ha",
  "difference": "+0.2 t/ha",
  "top_positive_factors": ["gdd_cumulative", "ndvi_peak"],
  "top_negative_factors": ["soil_fertility_index"],
  "shap_values": {
    "feature1": 0.15,
    "feature2": -0.08
  },
  "explanation": { ... },
  "timestamp": "2026-05-01T10:30:00"
}
```

### 2. Ingest Soil Data

**Endpoint:** `POST /ingestion/soil`

```json
{
  "state": "Punjab",
  "district": "Ludhiana",
  "nitrogen": 150,
  "phosphorus": 80,
  "potassium": 120
}
```

### 3. Ingest Weather Data

**Endpoint:** `POST /ingestion/weather`

```json
{
  "latitude": 31.6295,
  "longitude": 74.8765,
  "state": "Punjab",
  "district": "Ludhiana"
}
```

### 4. View Prediction History

**Endpoint:** `GET /prediction-history`

Returns recent 10 predictions with SHAP explanations

### 5. View Ingestion Logs

**Endpoint:** `GET /ingestion-logs`

Returns operation logs from data ingestion

---

## 🔧 Configuration

### Environment Variables

The `.env` file contains all configuration. Edit to customize:

```env
# Database
DATABASE_URL=postgresql://agripredictx:agripredict123@localhost:5432/agripredictx

# OpenWeatherMap API (optional - for weather ingestion)
OPENWEATHER_API_KEY=your_api_key_here

# Sentinel-2 Credentials (optional - for satellite NDVI)
SENTINEL_USERNAME=your_username
SENTINEL_PASSWORD=your_password

# Flask Settings
FLASK_DEBUG=False
FLASK_ENV=production

# Model Path
MODEL_PATH=crop_model.pkl
```

### Getting API Keys

**OpenWeatherMap:**
1. Go to https://openweathermap.org/api
2. Sign up for free account
3. Get API key from Account → My API Keys
4. Add to .env: `OPENWEATHER_API_KEY=your_key`

**Sentinel-2 (Copernicus):**
1. Register at https://dataspace.copernicus.eu/
2. Get credentials
3. Add to .env file

---

## 📊 Using the API

### Example: Python Script

```python
import requests
import json

# Prediction request
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
print(f"Top Factors: {result['top_positive_factors']}")
```

### Example: cURL Command

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "soil": {"nitrogen": 150, "phosphorus": 80, "potassium": 120},
    "weather": {"temperature": 28.5, "humidity": 65, "rainfall": 50},
    "state": "Punjab",
    "district": "Ludhiana",
    "crop": "wheat"
  }'
```

### Example: JavaScript/Web

```javascript
fetch('http://localhost:5000/predict', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    soil: {
      nitrogen: 150,
      phosphorus: 80,
      potassium: 120,
      ph: 7.0,
      moisture: 25,
      soil_type: 'loamy',
      organic_carbon: 1.5,
      electrical_conductivity: 0.8
    },
    weather: {
      temperature: 28.5,
      humidity: 65,
      rainfall: 50
    },
    state: 'Punjab',
    district: 'Ludhiana',
    crop: 'wheat'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Predicted Yield:', data.predicted_yield);
  console.log('Top Factors:', data.top_positive_factors);
})
```

---

## 🐛 Troubleshooting

### Issue: "PostgreSQL service not running"

**Solution:**
```bash
# Windows
net start postgresql-x64-14

# Mac
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

### Issue: "FATAL: password authentication failed"

**Solution:** Check .env file has correct credentials. Default is:
```
DATABASE_URL=postgresql://agripredictx:agripredict123@localhost:5432/agripredictx
```

### Issue: "Connection refused - 127.0.0.1:5432"

**Solution:** PostgreSQL is not running. Start the service (see above).

### Issue: "ModuleNotFoundError: No module named 'flask'"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "SHAP not available" warning

**Solution:** Install SHAP
```bash
pip install shap>=0.43.0
```

### Issue: Port 5000 already in use

**Solution:** Stop the other service or use different port
```bash
# Find what's using port 5000 and stop it
# Or modify api_server_enhanced.py:
# app.run(port=5001)  # Use different port
```

---

## 📈 System Architecture

```
┌─────────────────────────────────────────┐
│   AgriPredictX Local Deployment         │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │Flask   │ │Model   │ │SHAP    │
   │API     │ │ML      │ │Explain │
   │Server  │ │Engine  │ │ability │
   └────────┘ └────────┘ └────────┘
        │          │          │
        └──────────┼──────────┘
                   │
        ┌──────────▼──────────┐
        │  PostgreSQL         │
        │  Database           │
        │  (6 Tables)         │
        └─────────────────────┘
```

---

## 📚 Complete Documentation

For detailed technical documentation, see:

1. **ARCHITECTURE.md** - Complete system design
2. **IMPLEMENTATION_SUMMARY.md** - What was built
3. **QUICKSTART.md** - Quick reference
4. **FILE_INDEX.md** - File directory and purposes
5. **system_config.py** - Configuration reference

---

## 🎯 Next Steps

1. ✓ **Deployment Complete** - System is running locally
2. → **Load Data** - Use ingestion endpoints to load weather/soil data
3. → **Make Predictions** - Call `/predict` endpoint with farm data
4. → **View Results** - Check prediction dashboard
5. → **Integrate** - Connect frontend or mobile app to API
6. → **Monitor** - Check logs and audit trail in database
7. → **Improve** - Collect feedback and retrain model

---

## 💡 Pro Tips

1. **Save Predictions** - Every prediction is saved to database with full explanation
2. **Audit Trail** - Complete operation logs for debugging
3. **SHAP Values** - Every prediction includes feature importance via Shapley values
4. **Waterfall Plots** - Visualization of feature contributions
5. **Farmer Reports** - Explanations formatted for non-technical users

---

## 📞 Support Resources

- **GitHub Issues** - Report bugs or request features
- **Documentation** - See markdown files in project directory
- **API Tests** - Run `python test_api.py` to verify system
- **Database GUI** - Use pgAdmin or DBeaver to inspect PostgreSQL

---

## 🎉 You're Ready!

Your local AgriPredictX deployment is complete and running!

**Quick commands:**
```bash
# Start server
python deploy_local.py

# Or directly
python api_server_enhanced.py

# Test the system
python test_api.py

# View logs
tail -f logs/agripredictx.log
```

**Access points:**
- Dashboard: http://localhost:5000/
- API: http://localhost:5000/predict
- Docs: http://localhost:5000/api-docs
- Health: http://localhost:5000/health

---

**Happy Farming! 🌾**
