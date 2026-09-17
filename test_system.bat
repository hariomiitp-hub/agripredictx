@echo off
REM Quick test script for AgriPredictX

echo Testing AgriPredictX...
echo.

REM Check Python
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    exit /b 1
)
echo [OK] Python available

REM Check imports
python -c "import config, data_models, recommender_engine; print('[OK] Core modules import successfully')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Module imports failed
    exit /b 1
)

REM Check Flask
python -c "import flask; print('[OK] Flask available')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Flask not available
    exit /b 1
)

REM Check OpenWeather-backed prediction path with a mocked forecast client
python -c "import api_server; from data_models import WeatherData, WeatherForecast; FakeLocation = type('FakeLocation', (), {'__init__': lambda self, location_name, district, state, country_code, latitude, longitude, resolution_method='openweather_geocoding': setattr(self, '__dict__', {'location_name': location_name, 'district': district, 'state': state, 'country_code': country_code, 'latitude': latitude, 'longitude': longitude, 'query': f'{district},{state},{country_code}', 'resolution_method': resolution_method}), 'to_dict': lambda self: self.__dict__}); api_server.forecast_client = type('FakeForecastClient', (), {'resolve_location': lambda self, location_name=None, district=None, state=None, country_code='IN': FakeLocation(location_name or district or 'Ludhiana', district or 'Ludhiana', state or 'Punjab', country_code, 30.9009, 75.8573), 'reverse_geocode': lambda self, latitude, longitude: FakeLocation('Ludhiana', 'Ludhiana', 'Punjab', 'IN', latitude, longitude, 'reverse_geocoding'), 'build_three_month_forecast': lambda self, latitude, longitude: (WeatherForecast(WeatherData(27,70,115), WeatherData(29,74,120), WeatherData(28,69,105)), {'source':'mock-openweather','analysis_date':'2026-05-01','latitude':latitude,'longitude':longitude,'windows':[{'start_date':'2026-05-01','end_date':'2026-05-30','temperature':27.0,'humidity':70.0,'rainfall':115.0},{'start_date':'2026-05-31','end_date':'2026-06-29','temperature':29.0,'humidity':74.0,'rainfall':120.0},{'start_date':'2026-06-30','end_date':'2026-07-29','temperature':28.0,'humidity':69.0,'rainfall':105.0}]})})(); api_server.initialize_app(); client=api_server.app.test_client(); response=client.post('/predict', json={'soil': {'nitrogen':130,'phosphorus':55,'potassium':75,'ph':6.6,'moisture':32,'soil_type':'loamy','organic_carbon':1.3,'electrical_conductivity':0.7,'dap':35,'urea':90,'ssp':28,'mop':30,'zinc':2.5,'iron':18,'copper':0.9,'boron':0.8,'manganese':8}, 'weather': {'temperature':26,'humidity':68,'rainfall':110}, 'location_name':'Ludhiana', 'district':'Ludhiana', 'state':'Punjab', 'country_code':'IN', 'land_area':5.5, 'land_area_unit':'hectares', 'region':'north_india'}); payload=response.get_json(); assert response.status_code == 200 and payload['weather_context']['source']=='mock-openweather' and payload['farm_context']['district']=='Ludhiana' and payload['farm_context']['farm_size']==5.5 and payload['primary_recommendation']['crop_name']; print('[OK] OpenWeather-backed location prediction works')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] OpenWeather-backed prediction failed
    exit /b 1
)

echo.
echo All checks passed! The system is ready for deployment.
echo.
echo To deploy locally: .\deploy.bat local
echo To deploy with Docker: .\deploy.bat dev (requires Docker)
echo.
echo API will be available at: http://localhost:5000
