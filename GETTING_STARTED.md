# ⚡ Get Started in 5 Minutes

## Step 1: Install Python packages
```bash
pip install -r requirements.txt
```

## Step 2: Start PostgreSQL
- **Windows:** Open Services (services.msc) → PostgreSQL → Right-click → Start
- **Mac:** `brew services start postgresql`
- **Linux:** `sudo systemctl start postgresql`

## Step 3: Deploy
```bash
python deploy_local.py
```

## Step 4: Test
```bash
python test_api.py
```

## 🎉 Done! Your API is running at:
- **Dashboard:** http://localhost:5000/
- **API Docs:** http://localhost:5000/api-docs
- **Health Check:** http://localhost:5000/health

---

## 📚 Need Help?

- **Full Setup Guide:** Read LOCAL_DEPLOYMENT.md
- **Deployment Issues:** See DEPLOYMENT_CHECKLIST.md → Troubleshooting
- **API Reference:** http://localhost:5000/api-docs (when server is running)
- **System Architecture:** Read ARCHITECTURE.md

---

## 🚀 Make Your First Prediction

**Option 1: Web Dashboard**
Open http://localhost:5000/ and use the form

**Option 2: Python**
```python
import requests

result = requests.post('http://localhost:5000/predict', json={
    "soil": {"nitrogen": 150, "phosphorus": 80, "potassium": 120, "ph": 7.0, "moisture": 25},
    "weather": {"temperature": 28.5, "humidity": 65, "rainfall": 50},
    "state": "Punjab",
    "district": "Ludhiana",
    "crop": "wheat"
}).json()

print(result['predicted_yield'])
```

**Option 3: cURL**
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"soil": {...}, "weather": {...}, "state": "Punjab", "district": "Ludhiana", "crop": "wheat"}'
```

---

**That's it! You now have a working AI-powered crop yield prediction system! 🌾**
