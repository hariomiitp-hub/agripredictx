"""
Test Script for AgriPredictX API
Run: python test_api.py
"""
import requests
import json
import time
from datetime import datetime

# API Configuration
API_URL = 'http://localhost:5000'

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_health():
    """Test health check endpoint"""
    print_header("Test 1: Health Check")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {data['status']}")
            print(f"✓ Service: {data['service']}")
            print(f"✓ Version: {data['version']}")
            print(f"✓ Components ready:")
            for component, status in data['components'].items():
                status_str = "✓" if status else "✗"
                print(f"  {status_str} {component}")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_api_docs():
    """Test API documentation endpoint"""
    print_header("Test 2: API Documentation")
    
    try:
        response = requests.get(f"{API_URL}/api-docs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Service: {data['service']}")
            print(f"✓ Available endpoints:")
            for endpoint, description in data['endpoints'].items():
                print(f"  • {endpoint}: {description}")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_predict():
    """Test prediction endpoint"""
    print_header("Test 3: Yield Prediction with SHAP Explanation")
    
    payload = {
        "soil": {
            "nitrogen": 150,
            "phosphorus": 80,
            "potassium": 120,
            "ph": 7.0,
            "moisture": 25,
            "soil_type": "loamy",
            "organic_carbon": 1.5,
            "electrical_conductivity": 0.8,
            "dap": 40,
            "urea": 80,
            "ssp": 25,
            "mop": 25,
            "zinc": 2.0,
            "iron": 15.0,
            "copper": 1.0,
            "boron": 0.8,
            "manganese": 6.0
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
    
    try:
        response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✓ Prediction ID: {data['prediction_id']}")
                print(f"✓ Location: {data['location']}")
                print(f"✓ Crop: {data['crop']}")
                print(f"✓ Predicted Yield: {data['predicted_yield']}")
                print(f"✓ Baseline Yield: {data['baseline_yield']}")
                print(f"✓ Difference: {data['difference']}")
                print(f"✓ Top Positive Factors: {', '.join(data['top_positive_factors'])}")
                print(f"✓ Top Negative Factors: {', '.join(data['top_negative_factors'])}")
                print(f"✓ SHAP Values Available: {bool(data['shap_values'])}")
                print(f"✓ Timestamp: {data['timestamp']}")
                return True
            else:
                print(f"✗ Prediction failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_soil_ingestion():
    """Test soil data ingestion"""
    print_header("Test 4: Soil Fertility Data Ingestion")
    
    payload = {
        "state": "Punjab",
        "district": "Ludhiana",
        "nitrogen": 150,
        "phosphorus": 80,
        "potassium": 120
    }
    
    try:
        response = requests.post(f"{API_URL}/ingestion/soil", json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✓ {data['message']}")
                print(f"✓ Soil Fertility Index: {data['soil_fertility_index']:.3f}")
                return True
            else:
                print(f"✗ {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_prediction_history():
    """Test prediction history endpoint"""
    print_header("Test 5: Prediction History")
    
    try:
        response = requests.get(f"{API_URL}/prediction-history", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✓ Retrieved {len(data['predictions'])} recent predictions")
                if data['predictions']:
                    for i, pred in enumerate(data['predictions'][:3], 1):
                        print(f"\n  Prediction {i}:")
                        print(f"    ID: {pred['prediction_id']}")
                        print(f"    Location: {pred['state']}, {pred['district']}")
                        print(f"    Crop: {pred['crop']}")
                        print(f"    Yield: {pred['predicted_yield']:.2f} t/ha")
                return True
            else:
                print(f"✗ {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_ingestion_logs():
    """Test ingestion logs endpoint"""
    print_header("Test 6: Ingestion Operation Logs")
    
    try:
        response = requests.get(f"{API_URL}/ingestion-logs", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✓ Retrieved {len(data['logs'])} ingestion logs")
                if data['logs']:
                    for i, log in enumerate(data['logs'][:3], 1):
                        print(f"\n  Log {i}:")
                        print(f"    Source: {log['source_type']}")
                        print(f"    Operation: {log['operation']}")
                        print(f"    Status: {log['status']}")
                        print(f"    Records: {log['records_processed']}")
                return True
            else:
                print(f"✗ {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print_header("AgriPredictX API Test Suite")
    
    # Check if server is running
    print("Checking if API server is running at http://localhost:5000...")
    try:
        requests.get(f"{API_URL}/health", timeout=2)
    except:
        print("✗ API server is not running!")
        print("\nStart the server with:")
        print("  python deploy_local.py")
        print("\nOr directly:")
        print("  python api_server_enhanced.py")
        return
    
    print("✓ API server is running!\n")
    
    # Run tests
    results = {}
    results['Health Check'] = test_health()
    results['API Documentation'] = test_api_docs()
    results['Yield Prediction'] = test_predict()
    results['Soil Ingestion'] = test_soil_ingestion()
    results['Prediction History'] = test_prediction_history()
    results['Ingestion Logs'] = test_ingestion_logs()
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! API is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check the output above.")
    
    print("\n" + "="*60)
    print("Available Endpoints:")
    print("="*60)
    print("  GET    /health                 - Health check")
    print("  GET    /api-docs               - API documentation")
    print("  POST   /predict                - Make yield prediction")
    print("  POST   /ingestion/soil         - Ingest soil data")
    print("  POST   /ingestion/weather      - Ingest weather data")
    print("  GET    /prediction-history     - Recent predictions")
    print("  GET    /ingestion-logs         - Operation logs")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
