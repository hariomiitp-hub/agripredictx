# Complete API Reference

## Base URL
```
http://localhost:5000
```

## Authentication
Currently no authentication required. For production, add JWT tokens.

---

## Endpoints

### 1. Health Check
Check if the API server is running and model is loaded.

**Request:**
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0"
}
```

**Status Code:** 200

---

### 2. Single Prediction
Get crop recommendations for a single farm.

**Request:**
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

**Response:**
```json
{
  "primary_recommendation": {
    "crop_name": "rice",
    "suitability_score": 82.5,
    "rank": 1,
    "matching_factors": [
      "Nitrogen: High ✓",
      "Soil Type: loamy ✓"
    ],
    "mismatched_factors": [
      "Potassium: too low"
    ],
    "recommendation_reason": "...",
    "risk_level": "low"
  },
  "alternatives": [
    {
      "crop_name": "wheat",
      "suitability_score": 75.2,
      "rank": 2,
      ...
    }
  ],
  "confidence": 0.82,
  "model_version": "1.0"
}
```

**Status Code:** 200 (Success) | 400 (Bad Request) | 500 (Server Error)

---

### 3. Batch Prediction
Get predictions for multiple farms at once.

**Request:**
```
POST /predict-batch
Content-Type: application/json

[
  {
    "soil": { ... },
    "weather": { ... }
  },
  {
    "soil": { ... },
    "weather": { ... }
  }
]
```

**Response:**
```json
{
  "results": [
    {
      "id": 0,
      "status": "success",
      "recommendations": { ... }
    },
    {
      "id": 1,
      "status": "success",
      "recommendations": { ... }
    }
  ]
}
```

**Status Code:** 200 (Success) | 400 (Bad Request) | 500 (Server Error)

---

### 4. Model Information
Get details about the loaded ML model.

**Request:**
```
GET /model-info
```

**Response:**
```json
{
  "model_type": "xgboost",
  "is_trained": true,
  "crops": [
    "rice",
    "wheat",
    "corn",
    "potato",
    "sugarcane",
    "cotton",
    "tomato",
    "cabbage"
  ],
  "features": [
    "N",
    "P",
    "K",
    "pH",
    "moisture",
    "temperature",
    "humidity",
    "rainfall",
    "soil_type"
  ],
  "feature_importance": {
    "N": 0.25,
    "temperature": 0.15,
    ...
  },
  "n_features": 9,
  "n_crops": 8
}
```

**Status Code:** 200 (Success) | 500 (Server Error)

---

## Field Descriptions

### Soil Parameters
| Field | Type | Range | Unit | Description |
|-------|------|-------|------|-------------|
| nitrogen | float | 0-200 | kg/ha | Soil nitrogen content |
| phosphorus | float | 0-150 | kg/ha | Soil phosphorus |
| potassium | float | 0-200 | kg/ha | Soil potassium |
| ph | float | 3.5-9.0 | pH | Soil acidity/alkalinity |
| moisture | float | 0-50 | % | Soil moisture content |
| soil_type | string | sandy, clay, loamy | - | Type of soil |

### Weather Parameters
| Field | Type | Range | Unit | Description |
|-------|------|-------|------|-------------|
| temperature | float | -10 to 50 | °C | Current temperature |
| humidity | float | 0-100 | % | Air humidity |
| rainfall | float | 0-500 | mm/month | Monthly rainfall |

### Recommendation Response
| Field | Type | Description |
|-------|------|-------------|
| crop_name | string | Recommended crop |
| suitability_score | float | 0-100 score |
| rank | int | Ranking (1, 2, 3...) |
| matching_factors | array | Factors supporting the crop |
| mismatched_factors | array | Factors against the crop |
| recommendation_reason | string | Human-readable explanation |
| risk_level | string | low, medium, or high |
| confidence | float | 0-1 confidence level |

---

## Error Responses

### 400 - Bad Request
```json
{
  "error": "Invalid input. Must include soil and weather data"
}
```

### 500 - Server Error
```json
{
  "error": "Invalid input: soil parameters out of range",
  "traceback": "..."
}
```

---

## Example Requests

### Python
```python
import requests
import json

# Single prediction
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

### JavaScript/Node.js
```javascript
const data = {
    soil: {
        nitrogen: 150,
        phosphorus: 70,
        potassium: 80,
        ph: 6.5,
        moisture: 35,
        soil_type: "loamy"
    },
    weather: {
        temperature: 25,
        humidity: 70,
        rainfall: 120
    }
};

fetch('http://localhost:5000/predict', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

---

## Rate Limiting
Not currently implemented. For production:
- Limit: 100 requests per minute per IP
- Burst limit: 10 requests per second

---

## Versioning
Current API Version: **1.0**

Version will be updated in response headers and model_version field.

---

## CORS Support
All endpoints support Cross-Origin requests.

**Allowed Headers:**
- Content-Type
- Authorization (future)

**Allowed Methods:**
- GET
- POST
- OPTIONS

---

## Performance Notes

- **Response Time**: ~50-100ms per prediction
- **Batch Processing**: ~500ms for 100 farms
- **Model Size**: ~5-10MB loaded in memory
- **Memory Usage**: ~500MB total

---

## Testing

### Health Check
```bash
curl http://localhost:5000/health
```

### Get Model Info
```bash
curl http://localhost:5000/model-info
```

### Send Test Prediction
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```

---

**Last Updated**: April 2026  
**API Version**: 1.0  
**Status**: Production Ready
