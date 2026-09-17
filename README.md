# 🌾 AgriPredictX

An advanced AI-powered crop recommendation system with yield prediction, fertilizer advice, and weather integration. Supports 32+ crops across Kharif, Rabi, and Zaid seasons with comprehensive soil analysis including micronutrients.

## 🚀 Features

### Core Features
- **32 Crop Types**: Comprehensive coverage of Indian agricultural crops
- **Advanced ML Models**: XGBoost and Random Forest algorithms
- **Real-time Recommendations**: Instant crop suitability analysis
- **Explainable AI**: Detailed reasoning for all recommendations

### Enhanced Features
- **Yield Prediction**: Tons per hectare with confidence intervals
- **Fertilizer Optimization**: NPK + micronutrient recommendations
- **Weather Integration**: OpenWeather-powered 3-month outlook analysis and risk assessment
- **Soil Health Analysis**: 16+ soil parameters including organic carbon and micronutrients
- **Seasonal Suitability**: Kharif, Rabi, and Zaid crop recommendations

### Technical Features
- **REST API**: Production-ready Flask API
- **Containerized**: Docker deployment with health checks
- **CLI Interface**: Command-line tools for batch processing
- **Batch Processing**: Handle multiple farm inputs simultaneously

### Insurance Assurance
- **Supporting evidence**: Loss Verification Scores, timestamped loss events, SHAP reports, and evidence packets
- **Claim workflows**: Claim timeline CRUD, escalation nudges, counterfactual loss comparison, and farmer-reported transcript fallback
- **B2B surfaces**: Authenticated insurer/state aggregation APIs and FPO member dashboard/export preparation
- **Legal boundary**: Outputs are independent supporting evidence and do not determine insurance eligibility or payout

#### Assurance API configuration

Set `DATABASE_URL` and, for B2B/FPO routes, `AGRIPREDICTX_B2B_API_KEY`. Send `X-API-Key` plus one of
`X-Role: insurer`, `state_department`, or `fpo_admin`. The batch detector can be invoked by cron or
Windows Task Scheduler through `insurance_jobs.scan_registered_farms`.

Satellite image export, SMS/push delivery, and ASR are integration points. When they are not configured,
the API returns structured availability warnings and preserves the raw farmer transcript or sensor data.

## 📋 Requirements

### For Local Development (Recommended)
- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 12+** - [Download](https://www.postgresql.org/download/)
- 2GB RAM minimum
- 1GB disk space

### For Docker Deployment
- Docker & Docker Compose
- 4GB RAM minimum
- 2GB disk space

## 🛠️ Quick Start

### Option 1: Local Development (⚡ 5 minutes)

**Windows:**
```bash
# Double-click to run
deploy_local.bat

# Or manually:
python deploy_local.py
```

**Mac/Linux:**
```bash
python deploy_local.py
```

This will:
- ✓ Install Python dependencies
- ✓ Create PostgreSQL database
- ✓ Initialize database schema
- ✓ Start the API server on http://localhost:5000

**Verify Installation:**
```bash
python test_api.py
```

**View Dashboard:**
- Dashboard: http://localhost:5000/
- API Docs: http://localhost:5000/api-docs
- Health: http://localhost:5000/health

### Option 2: Docker Deployment (Recommended for Production)

```bash
# Deploy in development mode
./deploy.bat dev

# Or for production with nginx
./deploy.bat prod
```

### Option 3: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file (see system_config.py for details)
# Start PostgreSQL service

# Initialize database
python -c "from ingestion_layer import DatabaseConnector; DatabaseConnector().create_tables()"

# Run the API server
python api_server_enhanced.py

# Or use the enhanced CLI
python main_system.py
```

## 📊 New Features (v2.0)

### Data Ingestion Layer
- ✓ OpenWeatherMap API integration (3-hour intervals)
- ✓ Historical crop yield data loading (data.gov.in)
- ✓ Sentinel-2 satellite NDVI data fetching
- ✓ Soil fertility measurement ingestion
- ✓ Robust error handling (KeyError: 'list' fix)

### Advanced Feature Engineering
- ✓ Cumulative Growing Degree Days (GDD)
- ✓ 7-day and 14-day rolling rainfall analysis
- ✓ Soil Fertility Index (SFI) calculation
- ✓ NDVI canopy health indicators
- ✓ Crop/State/District encoding

### SHAP Explainability
- ✓ Per-prediction Shapley values
- ✓ Waterfall plot visualization
- ✓ Top factor identification
- ✓ Farmer-friendly explanations
- ✓ Complete audit logging

### Database & Monitoring
- ✓ PostgreSQL with SQLAlchemy ORM
- ✓ 6 data tables with audit trail
- ✓ Operation logging and monitoring
- ✓ Prediction history tracking
- ✓ Performance metrics

## 📡 API Usage

### Health Check
```bash
curl http://localhost:5000/health
```

### Single Prediction
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "soil": {
      "nitrogen": 120, "phosphorus": 60, "potassium": 80,
      "ph": 6.5, "moisture": 25, "soil_type": "loamy",
      "organic_carbon": 1.2, "electrical_conductivity": 0.8,
      "dap": 40, "urea": 100, "ssp": 30, "mop": 40,
      "zinc": 3.0, "iron": 25, "copper": 1.5, "boron": 1.0, "manganese": 12
    },
    "weather": {
      "temperature": 28, "humidity": 65, "rainfall": 80
    },
    "latitude": 30.9009,
    "longitude": 75.8573,
    "region": "Punjab",
    "farm_size": 5.0,
    "irrigation_available": true
  }'
```

### Batch Prediction
```bash
curl -X POST http://localhost:5000/predict-batch \
  -H "Content-Type: application/json" \
  -d '[{
    "soil": {...},
    "weather": {...}
  }]'
```

## 🏗️ Architecture

```
crop-prediction-system/
├── api_server.py          # Flask REST API
├── main.py                 # CLI interface
├── model.py               # ML model training/inference
├── recommender.py         # Recommendation engine
├── data_models.py         # Data structures
├── config.py              # Configuration & crop database
├── data_preparation.py    # Data preprocessing
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Multi-container setup
├── nginx.conf           # Reverse proxy config
├── deploy.bat           # Windows deployment script
├── .env                 # Environment variables
└── README.md            # This file
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
FLASK_ENV=production
MODEL_PATH=/app/models/crop_model.pkl
HOST=0.0.0.0
PORT=5000
WORKERS=4
LOG_LEVEL=INFO
```

### Model Training
```bash
# Train a new model
python -c "from model import train_model_from_scratch; model = train_model_from_scratch()"

# Load existing model
python -c "from model import CropPredictionModel; model = CropPredictionModel.load_model('crop_model.pkl')"
```

## 📊 Supported Crops

### Kharif Crops (June-October)
- **Cereals**: Rice, Maize, Sorghum, Pearl Millet, Finger Millet
- **Pulses**: Pigeon Pea, Black Gram, Green Gram
- **Oilseeds**: Groundnut, Soybean, Sesame
- **Cash Crops**: Cotton, Sugarcane, Jute
- **Horticultural**: Tomato

### Rabi Crops (October-March)
- **Cereals**: Wheat, Barley, Oats
- **Pulses**: Chickpea, Lentil, Field Pea
- **Oilseeds**: Mustard, Linseed
- **Cash Crops**: Potato
- **Horticultural**: Onion, Cabbage

### Zaid Crops (March-June)
- **Cereals**: Summer Rice
- **Pulses**: Summer Moong
- **Oilseeds**: Summer Groundnut

### Plantation Crops
- **Perennial**: Tea, Coffee, Rubber

## 🌦️ Weather Integration

The system uses OpenWeather to build a 3-month outlook from the day of analysis for:
- **Temperature Analysis**: Heat/cold stress detection
- **Rainfall Prediction**: Drought/flood risk assessment
- **Humidity Monitoring**: Disease risk evaluation
- **Seasonal Planning**: Optimal sowing windows

## 🧪 Soil Analysis

### Macronutrients
- Nitrogen (N), Phosphorus (P), Potassium (K)

### Soil Properties
- pH Level, Moisture Content, Soil Type
- Organic Carbon, Electrical Conductivity

### Fertilizer Components
- DAP, Urea, SSP, MOP

### Micronutrients
- Zinc, Iron, Copper, Boron, Manganese

## 📈 Yield Prediction

- **Units**: Tons per hectare
- **Categories**: Low (<40%), Medium (40-80%), High (80-120%), Very High (>120%)
- **Factors**: Soil health, weather conditions, irrigation, historical trends
- **Confidence**: Statistical confidence intervals

## 🌱 Fertilizer Recommendations

### Macronutrients (kg/ha)
- Nitrogen, Phosphorus, Potassium requirements
- Application schedules (basal, 30 days, 60 days)

### Micronutrients (ppm)
- Deficiency detection and supplementation
- Foliar application recommendations

### Cost Estimation
- Approximate fertilizer costs
- Economic optimization suggestions

## 🚀 Deployment Options

### Development Mode
```bash
./deploy.bat dev
# Access at http://localhost:5000
```

### Production Mode
```bash
./deploy.bat prod
# Access at http://localhost (nginx proxy)
```

### Manual Docker Commands
```bash
# Build
docker-compose build

# Run development
docker-compose up -d

# Run production
docker-compose --profile production up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🔍 Monitoring & Maintenance

### Health Checks
- Automatic container health monitoring
- API endpoint health verification
- Resource usage monitoring

### Logging
- Application logs in `/app/logs/`
- Docker container logs
- Structured logging with levels

### Model Updates
```bash
# Retrain model
./deploy.bat stop
python -c "from model import train_model_from_scratch; model = train_model_from_scratch()"
./deploy.bat restart
```

## 🤝 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/predict` | Single prediction |
| POST | `/predict-batch` | Batch predictions |
| GET | `/model-info` | Model information |

### Response Format
```json
{
  "primary_recommendation": {
    "crop_name": "rice",
    "suitability_score": 85.5,
    "matching_factors": ["Nitrogen: 120 kg/ha [ok]", "pH Level: 6.5 [ok]"],
    "mismatched_factors": ["Potassium: too low (80 kg/ha)"],
    "recommendation_reason": "High nitrogen and moisture requirements..."
  },
  "yield_prediction": {
    "crop_name": "rice",
    "predicted_yield": 4.2,
    "yield_range": [3.5, 5.0],
    "confidence_level": 0.85,
    "yield_category": "high"
  },
  "fertilizer_recommendation": {
    "nitrogen_recommendation": 80,
    "phosphorus_recommendation": 40,
    "potassium_recommendation": 60,
    "micronutrient_recommendations": {"zinc": 5.0},
    "application_schedule": {"basal": "urea, dap, mop"}
  },
  "confidence": 0.88
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Port 5000 already in use**
   ```bash
   # Find process using port
   netstat -ano | findstr :5000
   # Kill process or change port in .env
   ```

2. **Model not found**
   ```bash
   # Train new model
   python -c "from model import train_model_from_scratch; model = train_model_from_scratch()"
   ```

3. **Docker build fails**
   ```bash
   # Clear Docker cache
   docker system prune -a
   ./deploy.bat build
   ```

### Logs
```bash
# View application logs
./deploy.bat logs

# View specific container logs
docker-compose logs crop-prediction-api
```

## � Documentation

### Quick Start
- **LOCAL_DEPLOYMENT.md** - Complete local deployment guide (5 minutes)
- **QUICKSTART.md** - Quick reference and code examples

### Technical Details
- **ARCHITECTURE.md** - Complete system architecture with diagrams
- **IMPLEMENTATION_SUMMARY.md** - What was implemented and how
- **FILE_INDEX.md** - Complete file reference and dependencies
- **system_config.py** - Configuration reference with all settings

### Setup & Configuration
- **.env file** - Environment variables (generated by deploy_local.py)
- **system_config.py** - All configurable parameters
- **requirements.txt** - Python dependencies

### API & Testing
- **api_server_enhanced.py** - Enhanced REST API with SHAP
- **test_api.py** - API test suite (6 tests)
- **API Docs** - http://localhost:5000/api-docs (when server running)

### Database
- **database_models.py** - SQLAlchemy ORM schema (6 tables)
- **ingestion_layer.py** - Data ingestion from 4 sources
- PostgreSQL tables with full audit trail

### ML & Explainability
- **feature_engineering.py** - Agronomic feature calculations
- **explainability.py** - SHAP integration and explanations
- **model.py** - XGBoost/RandomForest models
- Per-prediction Shapley values and waterfall plots

## 🔧 Troubleshooting

### Common Issues

**PostgreSQL not running:**
```bash
# Windows
net start postgresql-x64-14

# Mac
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

**Port 5000 already in use:**
Change port in api_server_enhanced.py:
```python
app.run(port=5001)  # Use different port
```

**Python packages not installed:**
```bash
pip install -r requirements.txt
```

**Database connection error:**
Check .env file has correct `DATABASE_URL`

**More issues:**
See LOCAL_DEPLOYMENT.md Troubleshooting section

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Check **LOCAL_DEPLOYMENT.md** for setup help
- Review **ARCHITECTURE.md** for technical details
- Run `python test_api.py` to verify installation
- Check the API documentation at http://localhost:5000/api-docs

---

**Built with ❤️ for Indian farmers**

```bash
# Run the interactive application
python main.py

# Select option 1 for interactive prediction
# Enter soil and weather parameters when prompted
```

### 3. Usage - API Server

```bash
# Start the Flask API server
python api_server.py

# Server will be available at http://localhost:5000
```

### 4. Usage - Batch Processing

```bash
# Use sample_farms.json as input
python main.py
# Select option 2 for batch prediction
# Enter: sample_farms.json
```

## 📊 Input Parameters

### Soil Parameters
| Parameter | Range | Unit |
|-----------|-------|------|
| Nitrogen (N) | 0-200 | kg/hectare |
| Phosphorus (P) | 0-150 | kg/hectare |
| Potassium (K) | 0-200 | kg/hectare |
| pH Level | 3.5-9.0 | pH |
| Soil Moisture | 0-50 | % |
| Soil Type | sandy, clay, loamy | categorical |

### Weather Parameters
| Parameter | Range | Unit |
|-----------|-------|------|
| Temperature | -10 to 50 | °C |
| Humidity | 0-100 | % |
| Rainfall | 0-500 | mm/month |

## 💻 API Endpoints

### Health Check
```
GET /health
```
Response: Model status and version

### Single Prediction
```
POST /predict
Content-Type: application/json

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

### Batch Prediction
```
POST /predict-batch
Content-Type: application/json

[
    { farm1_data },
    { farm2_data },
    ...
]
```

### Model Information
```
GET /model-info
```
Response: Feature importance, crops, features, etc.

## 🎯 Supported Crops

The system can recommend the following crops:
- **Rice** - High nitrogen and moisture requirements
- **Wheat** - Moderate nutrients, cooler weather
- **Corn** - High nitrogen requirement
- **Potato** - High potassium, well-drained soil
- **Sugarcane** - High moisture, warm climate
- **Cotton** - Hot, dry climate preference
- **Tomato** - Versatile vegetable crop
- **Cabbage** - Cool season crop

## 🔍 How It Works

### 1. Data Processing
- Input soil and weather parameters are validated
- Features are normalized using StandardScaler
- Missing weather parameters use defaults

### 2. ML Prediction
- XGBoost model predicts crop suitability with probability scores
- Top N crops are identified based on model confidence

### 3. Rule-Based Analysis
- Each recommended crop is analyzed against domain-specific requirements
- Matching and mismatched factors are identified
- Suitability scores combine ML probability with rule-based analysis (60-40 weight)

### 4. Recommendation Generation
- Crops are ranked by suitability score
- Risk levels are assessed
- Human-readable explanations are generated

## 📈 Model Performance

- **Accuracy**: ~85-90% on test set (varies with data distribution)
- **Model Type**: XGBoost (primary), Random Forest (alternative)
- **Training Data**: 1000 synthetic samples generated from crop requirements
- **Features**: 9 (8 continuous + 1 categorical)

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Crop requirements
CROP_REQUIREMENTS = {
    'rice': {
        'N': (100, 180),
        'P': (40, 80),
        # ... other parameters
    },
    # ... other crops
}

# Model hyperparameters
MODEL_CONFIG = {
    'xgb_max_depth': 6,
    'xgb_learning_rate': 0.1,
    'xgb_n_estimators': 200,
    # ...
}

# Regional profiles
REGIONS = {
    'north_india': {'avg_temp': 20, 'avg_rainfall': 80, ...},
    # ... other regions
}
```

## 📝 Example Usage

### CLI Example
```
Select option: 1
Nitrogen: 150
Phosphorus: 70
Potassium: 80
pH Level: 6.5
Soil Moisture: 35
Soil Type: loamy
Temperature: 25
Humidity: 70
Rainfall: 120
Region: north_india

=== CROP RECOMMENDATIONS ===
🌾 PRIMARY RECOMMENDATION: RICE
   Suitability Score: 82.3/100
   Risk Level: LOW
   Reason: High nitrogen and moisture requirements. Your farm has 
           nitrogen and moisture at suitable levels. 
           
✓ Matching Factors:
   • Nitrogen: High ✓
   • Potassium: 80 kg/ha ✓
   • Soil Type: loamy ✓
   ...
```

### API Example (Python)
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

## 🔄 Model Retraining

To retrain the model with new data:

```bash
python main.py
# Select option 4: Retrain Model
# Or use force_retrain=True in code
```

## 📦 Dependencies

- **pandas** >= 2.0.3 - Data manipulation
- **numpy** >= 1.24.3 - Numerical computing
- **scikit-learn** >= 1.3.0 - ML algorithms
- **xgboost** >= 2.0.0 - Gradient boosting
- **flask** >= 2.3.2 - Web API framework
- **matplotlib** >= 3.7.2 - Visualization
- **joblib** >= 1.3.1 - Model serialization

## 🎓 Training Data

The system uses synthetic training data generated from crop requirements. For production use:
1. Collect historical yield data for your region
2. Prepare data in the format shown in `sample_farms.json`
3. Update the `create_sample_dataset()` function to use real data
4. Retrain the model with new data

## 🌍 Scalability Considerations

### For Mobile/Web Applications
- Use the **REST API** for scalable deployment
- Deploy Flask app using **Gunicorn** or **uWSGI**
- Use **Docker** for containerization
- Frontend can be built with React/Flutter

### For Real-Time Processing
- Model predictions take < 100ms per farm
- Supports batch processing with thousands of farms
- Can be integrated with IoT sensors for automated updates

### Performance Optimization
- Model is pre-trained and cached
- Feature normalization happens in-memory
- Support for GPU acceleration with XGBoost

## 🔐 Production Deployment

### Docker Setup
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "api_server.py"]
```

### Environment Variables
```bash
export FLASK_ENV=production
export FLASK_DEBUG=0
export MODEL_PATH=/var/models/crop_model.pkl
```

## 📋 Future Enhancements

- [ ] Integration with real-time weather APIs
- [ ] Historical yield tracking and model improvement
- [ ] Mobile app with GPS location integration
- [ ] Multi-language support
- [ ] Advanced crop rotation recommendations
- [ ] Climate change impact analysis
- [ ] Precision agriculture features
- [ ] Integration with agricultural IoT devices

## 🐛 Troubleshooting

### Model Not Loading
```
Error: Model not found
Solution: Run main.py and select option to train model first
```

### Invalid Input Error
```
Error: Invalid soil parameters
Solution: Check that all values are within specified ranges
```

### API Connection Error
```
Error: Connection refused
Solution: Ensure Flask server is running (python api_server.py)
```

## 📞 Support

For issues or suggestions:
1. Check sample_farms.json for correct input format
2. Review crop requirements in config.py
3. Examine error messages and logs

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

Built with:
- XGBoost for efficient gradient boosting
- Scikit-learn for ML utilities
- Flask for REST API framework

---

**Version**: 1.0  
**Last Updated**: April 2026  
**Status**: Production Ready
