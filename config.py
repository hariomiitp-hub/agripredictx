# Configuration for AgriPredictX

# Soil parameter ranges (expanded)
SOIL_CONFIG = {
    'nitrogen': {'min': 0, 'max': 200, 'unit': 'kg/hectare'},
    'phosphorus': {'min': 0, 'max': 150, 'unit': 'kg/hectare'},
    'potassium': {'min': 0, 'max': 200, 'unit': 'kg/hectare'},
    'ph': {'min': 3.5, 'max': 9.0, 'unit': 'pH'},
    'moisture': {'min': 0, 'max': 50, 'unit': '%'},
    'organic_carbon': {'min': 0, 'max': 5.0, 'unit': '%'},
    'electrical_conductivity': {'min': 0, 'max': 10.0, 'unit': 'dS/m'},
    'dap': {'min': 0, 'max': 100, 'unit': 'kg/hectare'},
    'urea': {'min': 0, 'max': 200, 'unit': 'kg/hectare'},
    'ssp': {'min': 0, 'max': 100, 'unit': 'kg/hectare'},
    'mop': {'min': 0, 'max': 100, 'unit': 'kg/hectare'},
    'zinc': {'min': 0, 'max': 10, 'unit': 'ppm'},
    'iron': {'min': 0, 'max': 50, 'unit': 'ppm'},
    'copper': {'min': 0, 'max': 5, 'unit': 'ppm'},
    'boron': {'min': 0, 'max': 2, 'unit': 'ppm'},
    'manganese': {'min': 0, 'max': 20, 'unit': 'ppm'},
}

# Weather parameters (current + 3-month forecast)
WEATHER_CONFIG = {
    'temperature': {'min': -10, 'max': 50, 'unit': 'C'},
    'humidity': {'min': 0, 'max': 100, 'unit': '%'},
    'rainfall': {'min': 0, 'max': 500, 'unit': 'mm/month'},
    'wind_speed': {'min': 0, 'max': 100, 'unit': 'km/h'},
    'sunshine_hours': {'min': 0, 'max': 24, 'unit': 'hours/day'},
}

# Soil type categories
SOIL_TYPES = {
    'sandy': 0,
    'clay': 1,
    'loamy': 2,
    'silt': 3,
    'peat': 4,
}

# Comprehensive crop database with Kharif, Rabi, and Zaid crops
CROP_REQUIREMENTS = {
    # KHARIF CROPS (June-October)
    # Food Grains - Cereals
    'rice': {
        'season': 'kharif',
        'category': 'food_grain_cereal',
        'N': (100, 180), 'P': (40, 80), 'K': (40, 80), 'pH': (5.5, 7.5),
        'moisture': (30, 50), 'temp': (20, 30), 'rainfall': (150, 250),
        'soil_type': ['loamy', 'clay'], 'duration': 120, 'yield_range': (3.5, 6.0),
        'description': 'High nitrogen and moisture requirements, clay/loamy soil preferred',
        'fertilizer_advice': {'urea': 120, 'dap': 60, 'mop': 40, 'zinc': 25, 'iron': 50}
    },
    'maize': {
        'season': 'kharif',
        'category': 'food_grain_cereal',
        'N': (120, 150), 'P': (60, 90), 'K': (40, 60), 'pH': (6.0, 7.5),
        'moisture': (25, 40), 'temp': (21, 27), 'rainfall': (60, 120),
        'soil_type': ['loamy', 'clay'], 'duration': 90, 'yield_range': (2.5, 4.5),
        'description': 'Warm season crop, good for mixed farming',
        'fertilizer_advice': {'urea': 100, 'dap': 50, 'mop': 30, 'zinc': 20, 'manganese': 10}
    },
    'sorghum': {
        'season': 'kharif',
        'category': 'food_grain_cereal',
        'N': (80, 120), 'P': (40, 60), 'K': (30, 50), 'pH': (6.0, 8.5),
        'moisture': (20, 35), 'temp': (25, 35), 'rainfall': (40, 80),
        'soil_type': ['loamy', 'sandy'], 'duration': 100, 'yield_range': (1.5, 3.0),
        'description': 'Drought tolerant, suitable for dry areas',
        'fertilizer_advice': {'urea': 80, 'dap': 40, 'mop': 20, 'zinc': 15}
    },
    'pearl_millet': {
        'season': 'kharif',
        'category': 'food_grain_cereal',
        'N': (60, 100), 'P': (30, 50), 'K': (20, 40), 'pH': (6.5, 8.5),
        'moisture': (15, 30), 'temp': (25, 35), 'rainfall': (30, 60),
        'soil_type': ['sandy', 'loamy'], 'duration': 75, 'yield_range': (1.0, 2.5),
        'description': 'Very drought tolerant, suitable for arid regions',
        'fertilizer_advice': {'urea': 60, 'dap': 30, 'mop': 15, 'zinc': 12}
    },
    'finger_millet': {
        'season': 'kharif',
        'category': 'food_grain_cereal',
        'N': (40, 80), 'P': (20, 40), 'K': (20, 40), 'pH': (5.5, 7.5),
        'moisture': (20, 35), 'temp': (20, 30), 'rainfall': (50, 100),
        'soil_type': ['loamy', 'clay'], 'duration': 90, 'yield_range': (1.5, 3.0),
        'description': 'Nutritious millet, suitable for hilly areas',
        'fertilizer_advice': {'urea': 50, 'dap': 25, 'mop': 20, 'zinc': 15, 'iron': 30}
    },

    # Food Grains - Pulses
    'pigeon_pea': {
        'season': 'kharif',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (40, 60), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (20, 35), 'temp': (20, 35), 'rainfall': (60, 120),
        'soil_type': ['loamy', 'clay'], 'duration': 180, 'yield_range': (0.8, 1.5),
        'description': 'Long duration pulse, nitrogen fixer',
        'fertilizer_advice': {'urea': 20, 'dap': 50, 'mop': 20, 'molybdenum': 0.5}
    },
    'black_gram': {
        'season': 'kharif',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (30, 50), 'K': (20, 40), 'pH': (6.5, 8.0),
        'moisture': (25, 40), 'temp': (25, 32), 'rainfall': (60, 100),
        'soil_type': ['loamy', 'clay'], 'duration': 75, 'yield_range': (0.6, 1.2),
        'description': 'Short duration pulse, good for intercropping',
        'fertilizer_advice': {'urea': 20, 'dap': 40, 'mop': 20, 'zinc': 10}
    },
    'green_gram': {
        'season': 'kharif',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (30, 50), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (20, 35), 'temp': (25, 32), 'rainfall': (50, 90),
        'soil_type': ['loamy', 'sandy'], 'duration': 65, 'yield_range': (0.5, 1.0),
        'description': 'Very short duration, suitable for late sowing',
        'fertilizer_advice': {'urea': 15, 'dap': 35, 'mop': 15, 'zinc': 8}
    },

    # Oilseeds
    'groundnut': {
        'season': 'kharif',
        'category': 'oilseed',
        'N': (20, 40), 'P': (40, 60), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (25, 40), 'temp': (25, 32), 'rainfall': (50, 100),
        'soil_type': ['sandy', 'loamy'], 'duration': 120, 'yield_range': (1.2, 2.5),
        'description': 'Oilseed crop, requires well-drained soil',
        'fertilizer_advice': {'urea': 25, 'dap': 50, 'mop': 25, 'calcium': 100, 'zinc': 10}
    },
    'soybean': {
        'season': 'kharif',
        'category': 'oilseed',
        'N': (20, 40), 'P': (60, 80), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (25, 40), 'temp': (20, 30), 'rainfall': (60, 120),
        'soil_type': ['loamy', 'clay'], 'duration': 100, 'yield_range': (1.5, 3.0),
        'description': 'High protein oilseed, suitable for mixed farming',
        'fertilizer_advice': {'urea': 30, 'dap': 60, 'mop': 30, 'cobalt': 0.5, 'molybdenum': 0.5}
    },
    'sesame': {
        'season': 'kharif',
        'category': 'oilseed',
        'N': (30, 50), 'P': (20, 40), 'K': (20, 40), 'pH': (6.0, 8.0),
        'moisture': (15, 30), 'temp': (25, 35), 'rainfall': (40, 80),
        'soil_type': ['sandy', 'loamy'], 'duration': 90, 'yield_range': (0.3, 0.8),
        'description': 'Drought tolerant oilseed, suitable for dry areas',
        'fertilizer_advice': {'urea': 25, 'dap': 30, 'mop': 20, 'zinc': 5}
    },

    # Cash Crops
    'cotton': {
        'season': 'kharif',
        'category': 'cash_crop',
        'N': (100, 150), 'P': (40, 80), 'K': (80, 120), 'pH': (6.0, 7.0),
        'moisture': (15, 30), 'temp': (22, 32), 'rainfall': (50, 80),
        'soil_type': ['loamy', 'sandy'], 'duration': 180, 'yield_range': (2.0, 4.0),
        'description': 'Fiber crop, requires hot climate',
        'fertilizer_advice': {'urea': 100, 'dap': 60, 'mop': 40, 'zinc': 25, 'iron': 50, 'boron': 1}
    },
    'sugarcane': {
        'season': 'kharif',
        'category': 'cash_crop',
        'N': (150, 200), 'P': (60, 100), 'K': (100, 150), 'pH': (6.0, 7.5),
        'moisture': (30, 50), 'temp': (20, 30), 'rainfall': (100, 250),
        'soil_type': ['loamy', 'clay'], 'duration': 300, 'yield_range': (60, 100),
        'description': 'High moisture requirement, long duration crop',
        'fertilizer_advice': {'urea': 150, 'dap': 80, 'mop': 60, 'zinc': 37.5, 'iron': 50}
    },
    'jute': {
        'season': 'kharif',
        'category': 'cash_crop',
        'N': (60, 100), 'P': (30, 50), 'K': (40, 60), 'pH': (5.5, 7.0),
        'moisture': (30, 45), 'temp': (24, 32), 'rainfall': (150, 200),
        'soil_type': ['loamy', 'clay'], 'duration': 120, 'yield_range': (2.5, 4.0),
        'description': 'Fiber crop, requires high rainfall',
        'fertilizer_advice': {'urea': 60, 'dap': 40, 'mop': 30, 'zinc': 12.5}
    },

    # RABI CROPS (October-March)
    # Food Grains - Cereals
    'wheat': {
        'season': 'rabi',
        'category': 'food_grain_cereal',
        'N': (120, 150), 'P': (50, 70), 'K': (40, 60), 'pH': (6.0, 7.5),
        'moisture': (15, 35), 'temp': (15, 25), 'rainfall': (40, 100),
        'soil_type': ['loamy', 'clay'], 'duration': 120, 'yield_range': (3.0, 5.0),
        'description': 'Winter cereal, staple food crop',
        'fertilizer_advice': {'urea': 100, 'dap': 50, 'mop': 25, 'zinc': 25, 'iron': 50}
    },
    'barley': {
        'season': 'rabi',
        'category': 'food_grain_cereal',
        'N': (80, 120), 'P': (40, 60), 'K': (30, 50), 'pH': (6.0, 8.0),
        'moisture': (15, 30), 'temp': (12, 25), 'rainfall': (30, 70),
        'soil_type': ['loamy', 'sandy'], 'duration': 110, 'yield_range': (2.0, 4.0),
        'description': 'Cold tolerant cereal, suitable for marginal lands',
        'fertilizer_advice': {'urea': 80, 'dap': 40, 'mop': 20, 'zinc': 20}
    },
    'oats': {
        'season': 'rabi',
        'category': 'food_grain_cereal',
        'N': (60, 100), 'P': (30, 50), 'K': (30, 50), 'pH': (6.0, 7.5),
        'moisture': (20, 35), 'temp': (10, 20), 'rainfall': (50, 100),
        'soil_type': ['loamy', 'clay'], 'duration': 100, 'yield_range': (1.5, 3.0),
        'description': 'Fodder crop, suitable for hilly areas',
        'fertilizer_advice': {'urea': 60, 'dap': 35, 'mop': 25, 'zinc': 15}
    },

    # Food Grains - Pulses
    'chickpea': {
        'season': 'rabi',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (40, 60), 'K': (20, 40), 'pH': (6.0, 8.0),
        'moisture': (15, 30), 'temp': (15, 25), 'rainfall': (30, 70),
        'soil_type': ['loamy', 'sandy'], 'duration': 100, 'yield_range': (1.0, 2.0),
        'description': 'Winter pulse, drought tolerant',
        'fertilizer_advice': {'urea': 20, 'dap': 50, 'mop': 20, 'zinc': 12.5, 'boron': 1}
    },
    'lentil': {
        'season': 'rabi',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (30, 50), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (15, 30), 'temp': (15, 25), 'rainfall': (30, 70),
        'soil_type': ['loamy', 'sandy'], 'duration': 110, 'yield_range': (0.8, 1.5),
        'description': 'Cold tolerant pulse, suitable for light soils',
        'fertilizer_advice': {'urea': 15, 'dap': 40, 'mop': 15, 'zinc': 10}
    },
    'field_pea': {
        'season': 'rabi',
        'category': 'food_grain_pulse',
        'N': (20, 40), 'P': (40, 60), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (20, 35), 'temp': (10, 20), 'rainfall': (40, 80),
        'soil_type': ['loamy', 'clay'], 'duration': 100, 'yield_range': (1.2, 2.5),
        'description': 'Fodder and grain pulse, cold tolerant',
        'fertilizer_advice': {'urea': 20, 'dap': 50, 'mop': 20, 'zinc': 12.5}
    },

    # Oilseeds
    'mustard': {
        'season': 'rabi',
        'category': 'oilseed',
        'N': (60, 100), 'P': (30, 50), 'K': (20, 40), 'pH': (6.0, 8.0),
        'moisture': (15, 30), 'temp': (10, 25), 'rainfall': (30, 60),
        'soil_type': ['loamy', 'sandy'], 'duration': 120, 'yield_range': (1.0, 2.0),
        'description': 'Oilseed for temperate regions',
        'fertilizer_advice': {'urea': 60, 'dap': 40, 'mop': 20, 'boron': 1, 'molybdenum': 0.5}
    },
    'linseed': {
        'season': 'rabi',
        'category': 'oilseed',
        'N': (40, 80), 'P': (30, 50), 'K': (20, 40), 'pH': (6.0, 7.5),
        'moisture': (15, 30), 'temp': (10, 20), 'rainfall': (40, 80),
        'soil_type': ['loamy', 'clay'], 'duration': 100, 'yield_range': (0.5, 1.2),
        'description': 'Industrial oilseed, suitable for light soils',
        'fertilizer_advice': {'urea': 40, 'dap': 35, 'mop': 15, 'zinc': 10}
    },

    # Cash Crops
    'potato': {
        'season': 'rabi',
        'category': 'cash_crop',
        'N': (80, 150), 'P': (50, 100), 'K': (150, 200), 'pH': (5.5, 7.5),
        'moisture': (25, 45), 'temp': (15, 25), 'rainfall': (50, 100),
        'soil_type': ['loamy', 'sandy'], 'duration': 90, 'yield_range': (20, 40),
        'description': 'Tuber crop, high potassium requirement',
        'fertilizer_advice': {'urea': 100, 'dap': 75, 'mop': 100, 'zinc': 25, 'iron': 50, 'boron': 1}
    },

    # ZAID CROPS (March-June)
    # Food Grains - Cereals
    'summer_rice': {
        'season': 'zaid',
        'category': 'food_grain_cereal',
        'N': (80, 120), 'P': (30, 60), 'K': (30, 60), 'pH': (5.5, 7.0),
        'moisture': (25, 40), 'temp': (25, 35), 'rainfall': (100, 150),
        'soil_type': ['loamy', 'clay'], 'duration': 90, 'yield_range': (2.5, 4.5),
        'description': 'Summer rice, requires irrigation',
        'fertilizer_advice': {'urea': 80, 'dap': 40, 'mop': 30, 'zinc': 20}
    },

    # Food Grains - Pulses
    'summer_moong': {
        'season': 'zaid',
        'category': 'food_grain_pulse',
        'N': (15, 30), 'P': (25, 40), 'K': (15, 30), 'pH': (6.5, 8.0),
        'moisture': (20, 35), 'temp': (25, 35), 'rainfall': (50, 80),
        'soil_type': ['loamy', 'sandy'], 'duration': 60, 'yield_range': (0.4, 0.8),
        'description': 'Very short duration summer pulse',
        'fertilizer_advice': {'urea': 15, 'dap': 30, 'mop': 15, 'zinc': 7.5}
    },

    # Oilseeds
    'summer_groundnut': {
        'season': 'zaid',
        'category': 'oilseed',
        'N': (15, 30), 'P': (30, 50), 'K': (15, 30), 'pH': (6.0, 7.5),
        'moisture': (20, 35), 'temp': (25, 35), 'rainfall': (40, 70),
        'soil_type': ['sandy', 'loamy'], 'duration': 90, 'yield_range': (0.8, 1.5),
        'description': 'Summer oilseed, requires irrigation',
        'fertilizer_advice': {'urea': 20, 'dap': 40, 'mop': 20, 'calcium': 75, 'zinc': 7.5}
    },

    # Horticultural Crops
    'tomato': {
        'season': 'kharif',
        'category': 'horticultural',
        'N': (100, 150), 'P': (40, 80), 'K': (100, 150), 'pH': (6.0, 7.0),
        'moisture': (20, 35), 'temp': (18, 28), 'rainfall': (50, 75),
        'soil_type': ['loamy'], 'duration': 120, 'yield_range': (20, 40),
        'description': 'Vegetable crop, versatile growing conditions',
        'fertilizer_advice': {'urea': 80, 'dap': 60, 'mop': 80, 'calcium': 100, 'magnesium': 50, 'zinc': 25, 'boron': 1}
    },
    'onion': {
        'season': 'rabi',
        'category': 'horticultural',
        'N': (80, 120), 'P': (40, 60), 'K': (60, 100), 'pH': (6.0, 7.5),
        'moisture': (15, 30), 'temp': (15, 25), 'rainfall': (30, 60),
        'soil_type': ['loamy', 'sandy'], 'duration': 120, 'yield_range': (15, 30),
        'description': 'Bulb crop, requires well-drained soil',
        'fertilizer_advice': {'urea': 60, 'dap': 50, 'mop': 50, 'zinc': 20, 'iron': 30}
    },
    'cabbage': {
        'season': 'rabi',
        'category': 'horticultural',
        'N': (120, 180), 'P': (50, 80), 'K': (80, 120), 'pH': (6.0, 7.5),
        'moisture': (25, 40), 'temp': (15, 25), 'rainfall': (50, 100),
        'soil_type': ['loamy'], 'duration': 90, 'yield_range': (25, 50),
        'description': 'Cool season vegetable, high nitrogen requirement',
        'fertilizer_advice': {'urea': 100, 'dap': 60, 'mop': 60, 'calcium': 150, 'magnesium': 75, 'boron': 1.5}
    },

    # Plantation Crops
    'tea': {
        'season': 'perennial',
        'category': 'plantation',
        'N': (80, 120), 'P': (20, 40), 'K': (40, 80), 'pH': (4.5, 5.5),
        'moisture': (30, 50), 'temp': (20, 30), 'rainfall': (200, 300),
        'soil_type': ['loamy', 'clay'], 'duration': 365*50, 'yield_range': (2.0, 3.5),
        'description': 'Perennial crop, requires acidic soil and high rainfall',
        'fertilizer_advice': {'urea': 100, 'ssp': 40, 'mop': 60, 'zinc': 25, 'copper': 5, 'boron': 1}
    },
    'coffee': {
        'season': 'perennial',
        'category': 'plantation',
        'N': (60, 100), 'P': (20, 40), 'K': (60, 100), 'pH': (5.5, 6.5),
        'moisture': (25, 40), 'temp': (18, 28), 'rainfall': (150, 250),
        'soil_type': ['loamy', 'clay'], 'duration': 365*30, 'yield_range': (0.5, 1.5),
        'description': 'Perennial crop, requires shade and well-drained soil',
        'fertilizer_advice': {'urea': 80, 'ssp': 30, 'mop': 80, 'zinc': 20, 'iron': 40, 'copper': 5}
    },
    'rubber': {
        'season': 'perennial',
        'category': 'plantation',
        'N': (40, 80), 'P': (20, 40), 'K': (40, 60), 'pH': (5.0, 6.5),
        'moisture': (30, 50), 'temp': (25, 32), 'rainfall': (200, 300),
        'soil_type': ['loamy', 'clay'], 'duration': 365*25, 'yield_range': (1.5, 2.5),
        'description': 'Perennial crop, requires high rainfall and humidity',
        'fertilizer_advice': {'urea': 60, 'ssp': 30, 'mop': 50, 'zinc': 15, 'iron': 30, 'copper': 3}
    },
}

# Model hyperparameters
MODEL_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'xgb_max_depth': 6,
    'xgb_learning_rate': 0.1,
    'xgb_n_estimators': 200,
    'xgb_subsample': 0.8,
    'xgb_colsample_bytree': 0.8,
}

# Regions and their profiles
REGIONS = {
    'north_india': {'avg_temp': 20, 'avg_rainfall': 80, 'soil_type': 'loamy'},
    'south_india': {'avg_temp': 28, 'avg_rainfall': 120, 'soil_type': 'clay'},
    'eastern': {'avg_temp': 25, 'avg_rainfall': 150, 'soil_type': 'loamy'},
    'western': {'avg_temp': 26, 'avg_rainfall': 100, 'soil_type': 'sandy'},
}
