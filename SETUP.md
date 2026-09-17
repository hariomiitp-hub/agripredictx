# SETUP & INSTALLATION GUIDE

## Prerequisites
- Python 3.8+ 
- Git
- Windows/Linux/Mac with 4GB+ RAM
- Optional: Docker for containerized deployment

## Local Installation

### Step 1: Clone/Download the Project
```bash
cd c:\Users\ems\Documents\New project
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3.1: Configure API Keys
Add these values to `.env` before using automatic indicator fill in the dashboard:
- `OPENWEATHER_API_KEY` for automatic location resolution and 3-month forecast windows
- `EARTH_ENGINE_PROJECT` plus `GOOGLE_APPLICATION_CREDENTIALS`, or `GEE_PROJECT` plus `GEE_SERVICE_ACCOUNT` and `GEE_CREDENTIALS_FILE`, for live NDVI from Google Earth Engine

### Step 4: Run Quick Start
```bash
python quickstart.py
```

This will:
1. Initialize the system
2. Train the model (first run)
3. Run 3 example predictions

## Usage Options

### Option 1: Interactive CLI
```bash
python main.py
```

Then select options for:
- Interactive mode (manual input)
- Batch predictions (JSON file)
- Feature importance view
- Model retraining

### Option 2: REST API Server
```bash
python api_server.py
```

Server runs at: http://localhost:5000

**API Endpoints:**
```
GET  /health          - System health check
POST /predict         - Single prediction
POST /predict-batch   - Batch predictions
GET  /model-info      - Model details
```

### Option 3: Jupyter Notebook
```bash
jupyter notebook Crop_Prediction_Demo.ipynb
```

Comprehensive walkthrough of:
- Data exploration
- Model training
- Predictions
- Evaluations
- Visualizations

### Option 4: Web Dashboard
```bash
python api_server_enhanced.py
```

Access dashboard at: http://localhost:5000

**Dashboard Features:**
- Interactive crop prediction interface
- Model health monitoring
- Batch processing capabilities
- Real-time recommendations

**Key Indicators:**
The dashboard factors in advanced agricultural indicators including:
- **Growing Degree Days (GDD)**: Auto-filled from current weather plus the OpenWeather outlook
- **Cumulative Rainfall**: Auto-filled from rainfall and forecast precipitation windows
- **Soil Fertility Index (SFI)**: Auto-filled from N, P, K, pH, moisture, soil type, fertilizers, and micronutrients
- **NDVI-based Vegetation Indicators**: Auto-filled from Google Earth Engine when configured, with a local fallback estimate otherwise

## Docker Deployment

### Option 1: Build & Run Manually
```bash
# Build image
docker build -t crop-prediction:latest .

# Run container
docker run -p 5000:5000 crop-prediction:latest
```

### Option 2: Docker Compose
```bash
docker-compose up -d
```

Access API at: http://localhost:5000

## Testing

### Test Input Format (JSON)
```json
{
  "soil": {
    "nitrogen": 150,
    "phosphorus": 70,
    "potassium": 80,
    "ph": 6.5,
    "moisture": 35,
    "soil_type": "loamy"
  },
  "weather": {
    "temperature": 25,
    "humidity": 70,
    "rainfall": 120
  },
  "region": "north_india"
}
```

### Test with cURL
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d @sample_farms.json
```

### Test with Python
```python
import requests
import json

url = "http://localhost:5000/predict"
data = {
    "soil": {
        "nitrogen": 150,
        "phosphorus": 70,
        "potassium": 80,
        "ph": 6.5,
        "moisture": 35,
        "soil_type": "loamy"
    },
    "weather": {
        "temperature": 25,
        "humidity": 70,
        "rainfall": 120
    }
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2))
```

## Troubleshooting

### Issue: Module import errors
**Solution:**
```bash
pip install --upgrade -r requirements.txt
```

### Issue: Model file not found
**Solution:**
```bash
python main.py
# Select option to train model
```

### Issue: Port 5000 already in use
**Solution:**
```bash
# Use different port
python api_server.py  # Edit to change port
# Or kill process on port 5000
```

### Issue: Out of memory
**Solution:**
- Reduce batch size in config.py
- Use smaller training dataset
- Run API server (more memory efficient)

## Configuration

Edit `config.py` to customize:

```python
# Model parameters
MODEL_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'xgb_max_depth': 6,
    'xgb_learning_rate': 0.1,
    'xgb_n_estimators': 200,
}

# Crop requirements
CROP_REQUIREMENTS = {
    'rice': {
        'N': (100, 180),
        'P': (40, 80),
        # ...
    }
}

# Add new crops to extend system
```

## Performance Optimization

### For Production:
1. Use Gunicorn instead of Flask dev server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
   ```

2. Use Nginx as reverse proxy

3. Add Redis for caching predictions

4. Use CloudFlare for CDN

### For Mobile/Web:
- Deploy API on cloud (AWS, GCP, Azure)
- Add authentication (JWT tokens)
- Implement rate limiting
- Add logging and monitoring

## File Structure Overview

```
crop-prediction-system/
├── config.py                 # Configuration
├── data_models.py           # Data classes
├── data_preparation.py      # Data handling
├── model.py                 # ML model
├── recommender.py           # Recommendations
├── utils.py                 # Utilities
├── main.py                  # CLI interface
├── api_server.py            # REST API
├── quickstart.py            # Quick start
├── Crop_Prediction_Demo.ipynb  # Jupyter notebook
├── sample_farms.json        # Sample data
├── requirements.txt         # Dependencies
├── Dockerfile              # Docker config
├── docker-compose.yml      # Docker compose
├── README.md               # Full documentation
└── SETUP.md               # This file
```

## Next Steps

1. **Test the system:** Run quickstart.py
2. **Explore data:** Open Crop_Prediction_Demo.ipynb
3. **Try API:** Start api_server.py and test endpoints
4. **Customize:** Edit config.py for your needs
5. **Deploy:** Use Docker for production

## Support Resources

- Check README.md for detailed documentation
- Review sample_farms.json for input format
- Examine data_models.py for class definitions
- See config.py for crop requirements

## Contact & Contributing

For issues or improvements:
1. Review the code structure
2. Check error messages in logs
3. Refer to README for detailed docs
4. Test with sample_farms.json

---

**Version**: 1.0  
**Status**: Production Ready  
**Last Updated**: April 2026
