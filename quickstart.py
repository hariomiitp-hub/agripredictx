#!/usr/bin/env python
"""
Quick start script for AgriPredictX.
Run this to set up and make your first prediction.
"""

import sys

from data_models import SoilParameters, WeatherData, FarmInput
from main import CropPredictionApp


def quick_start():
    """Run a quick demonstration."""
    print("\n" + "=" * 70)
    print("AGRIPREDICTX - Quick Start")
    print("=" * 70)

    print("\n1. Initializing application...")
    app = CropPredictionApp()
    app.initialize_model(force_retrain=False)

    print("\n2. Running example predictions...")
    print("-" * 70)

    examples = [
        {
            "name": "Rice Farm (North India)",
            "soil": SoilParameters(
                nitrogen=150,
                phosphorus=70,
                potassium=80,
                ph=6.5,
                moisture=35,
                soil_type="loamy",
            ),
            "weather": WeatherData(temperature=25, humidity=70, rainfall=120),
            "region": "north_india",
        },
        {
            "name": "Cotton Farm (Western)",
            "soil": SoilParameters(
                nitrogen=120,
                phosphorus=55,
                potassium=100,
                ph=6.8,
                moisture=20,
                soil_type="sandy",
            ),
            "weather": WeatherData(temperature=28, humidity=55, rainfall=65),
            "region": "western",
        },
        {
            "name": "Vegetable Farm (Eastern)",
            "soil": SoilParameters(
                nitrogen=140,
                phosphorus=65,
                potassium=95,
                ph=6.5,
                moisture=38,
                soil_type="loamy",
            ),
            "weather": WeatherData(temperature=24, humidity=75, rainfall=140),
            "region": "eastern",
        },
    ]

    for example in examples:
        print(f"\n[Example] {example['name']}:")
        farm_input = FarmInput(
            soil=example["soil"],
            weather=example["weather"],
            region=example["region"],
        )
        result = app.engine.get_recommendations(farm_input, top_n=3)

        primary = result.primary_recommendation
        print(f"   -> Recommended: {primary.crop_name.upper()}")
        print(f"   -> Suitability: {primary.suitability_score:.1f}/100")
        print(f"   -> Risk Level: {primary.risk_level}")
        if result.alternatives:
            alt1 = result.alternatives[0]
            print(f"   -> Alternative: {alt1.crop_name.title()} ({alt1.suitability_score:.1f}/100)")

    print("\n" + "=" * 70)
    print("Quick start completed successfully!")
    print("\nNext steps:")
    print("  1. Run 'python main.py' for interactive mode")
    print("  2. Run 'python api_server.py' to start the API server")
    print("  3. Check README.md for detailed documentation")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        quick_start()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
