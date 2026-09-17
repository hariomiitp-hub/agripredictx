"""Utility functions for AgriPredictX."""
import json
from datetime import datetime
from typing import Dict, List

import numpy as np

from data_models import SoilParameters, RecommendationResult


def load_farm_data_from_json(filepath: str) -> List[Dict]:
    """Load farm data from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results_to_json(results: List[Dict], output_filepath: str):
    """Save prediction results to JSON file."""
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def create_report(result: RecommendationResult) -> str:
    """Create a detailed text report from a recommendation result."""
    report = []
    report.append("=" * 70)
    report.append("CROP RECOMMENDATION REPORT")
    report.append("=" * 70)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    soil = result.farm_input.soil
    report.append("SOIL PARAMETERS:")
    report.append("-" * 70)
    report.append(f"  Nitrogen:       {soil.nitrogen:.1f} kg/ha")
    report.append(f"  Phosphorus:     {soil.phosphorus:.1f} kg/ha")
    report.append(f"  Potassium:      {soil.potassium:.1f} kg/ha")
    report.append(f"  pH Level:       {soil.ph:.1f}")
    report.append(f"  Soil Moisture:  {soil.moisture:.1f}%")
    report.append(f"  Soil Type:      {soil.soil_type.title()}")
    report.append("")

    weather = result.farm_input.weather
    report.append("WEATHER CONDITIONS:")
    report.append("-" * 70)
    report.append(f"  Temperature:    {weather.temperature:.1f} C")
    report.append(f"  Humidity:       {weather.humidity:.1f}%")
    report.append(f"  Rainfall:       {weather.rainfall:.1f} mm/month")
    report.append("")

    report.append("CROP RECOMMENDATIONS:")
    report.append("=" * 70)

    primary = result.primary_recommendation
    report.append(f"\n1. {primary.crop_name.upper()} (Primary Recommendation)")
    report.append("-" * 70)
    report.append(f"   Suitability Score: {primary.suitability_score:.1f}/100")
    report.append(f"   Risk Level:        {primary.risk_level.upper()}")
    report.append(f"   Confidence:        {result.confidence:.1%}")
    report.append(f"   Reason:            {primary.recommendation_reason}")
    report.append("")
    report.append("   Matching Factors:")
    for factor in primary.matching_factors:
        report.append(f"     - {factor}")
    report.append("")

    if primary.mismatched_factors:
        report.append("   Factors to Monitor:")
        for factor in primary.mismatched_factors:
            report.append(f"     - {factor}")
        report.append("")

    if result.alternatives:
        report.append("ALTERNATIVE OPTIONS:")
        report.append("=" * 70)
        for alt in result.alternatives:
            report.append(f"\n{alt.rank}. {alt.crop_name.title()}")
            report.append(f"   Suitability Score: {alt.suitability_score:.1f}/100")
            report.append(f"   Risk Level:        {alt.risk_level.upper()}")

    report.append("\n" + "=" * 70)
    return "\n".join(report)


def export_report_to_file(result: RecommendationResult, output_filepath: str):
    """Export report to text file."""
    report = create_report(result)
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(report)


def validate_input_range(value: float, min_val: float, max_val: float, param_name: str) -> bool:
    """Validate that a parameter is within an acceptable range."""
    if not min_val <= value <= max_val:
        print(f"Warning: {param_name} = {value} is outside normal range ({min_val}-{max_val})")
        return False
    return True


def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to 0-1 range."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def denormalize_value(normalized: float, min_val: float, max_val: float) -> float:
    """Denormalize value from 0-1 range."""
    return normalized * (max_val - min_val) + min_val


def get_crop_summary_stats(results: List[Dict]) -> Dict:
    """Get summary statistics from batch prediction results."""
    crops_recommended = {}
    total_results = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")

    for result in results:
        if result["status"] == "success":
            crop = result["recommendations"]["primary_recommendation"]["crop_name"]
            crops_recommended[crop] = crops_recommended.get(crop, 0) + 1

    return {
        "total_processed": total_results,
        "successful": success_count,
        "failed": total_results - success_count,
        "crops_recommended": crops_recommended,
        "success_rate": success_count / total_results * 100 if total_results > 0 else 0,
    }


def create_comparison_chart(results: List[Dict]) -> str:
    """Create an ASCII chart comparing crop recommendations."""
    crops_recommended = {}

    for result in results:
        if result["status"] == "success":
            crop = result["recommendations"]["primary_recommendation"]["crop_name"]
            crops_recommended[crop] = crops_recommended.get(crop, 0) + 1

    if not crops_recommended:
        return "No successful results to chart"

    max_count = max(crops_recommended.values())
    chart = "\nCrop Recommendations Summary\n"
    chart += "=" * 40 + "\n"

    for crop, count in sorted(crops_recommended.items(), key=lambda x: x[1], reverse=True):
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "#" * bar_length
        percentage = (count / sum(crops_recommended.values())) * 100
        chart += f"{crop:15} {bar:30} {count} ({percentage:.1f}%)\n"

    return chart


def suggest_crop_rotation(current_crop: str, years_grown: int = 1) -> List[str]:
    """Suggest crop rotation options based on the current crop."""
    rotation_rules = {
        "rice": ["wheat", "corn", "potato"],
        "wheat": ["rice", "corn", "sugarcane"],
        "corn": ["wheat", "potato", "cotton"],
        "potato": ["tomato", "cabbage", "wheat"],
        "sugarcane": ["rice", "wheat"],
        "cotton": ["corn", "wheat", "potato"],
        "tomato": ["potato", "cabbage"],
        "cabbage": ["tomato", "potato"],
    }
    return rotation_rules.get(current_crop, [])


def analyze_soil_deficiency(soil: SoilParameters) -> Dict[str, str]:
    """Analyze soil deficiencies and provide recommendations."""
    deficiencies = {}

    if soil.nitrogen < 50:
        deficiencies["nitrogen"] = "Low - Consider nitrogen fertilizer application"
    elif soil.nitrogen > 180:
        deficiencies["nitrogen"] = "High - Monitor for over-fertilization"

    if soil.phosphorus < 20:
        deficiencies["phosphorus"] = "Low - Add phosphate fertilizer"
    elif soil.phosphorus > 120:
        deficiencies["phosphorus"] = "High - Limited additional application needed"

    if soil.potassium < 50:
        deficiencies["potassium"] = "Low - Add potassium fertilizer"
    elif soil.potassium > 150:
        deficiencies["potassium"] = "High - Avoid excess potassium"

    if soil.ph < 5.5:
        deficiencies["ph"] = "Acidic - Consider lime application"
    elif soil.ph > 8.0:
        deficiencies["ph"] = "Alkaline - Consider sulfur application"

    if soil.moisture < 15:
        deficiencies["moisture"] = "Low - Increase irrigation"
    elif soil.moisture > 45:
        deficiencies["moisture"] = "High - Improve drainage"

    return deficiencies


def print_summary_statistics(results: List[RecommendationResult]):
    """Print summary statistics from multiple recommendations."""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    crop_counts = {}
    avg_scores = {}

    for result in results:
        crop = result.primary_recommendation.crop_name
        score = result.primary_recommendation.suitability_score
        crop_counts[crop] = crop_counts.get(crop, 0) + 1
        avg_scores[crop] = avg_scores.get(crop, []) + [score]

    print(f"\nTotal Recommendations: {len(results)}")
    print("\nCrop Distribution:")
    for crop, count in sorted(crop_counts.items(), key=lambda x: x[1], reverse=True):
        avg_score = np.mean(avg_scores[crop])
        print(f"  {crop:15} : {count:3} farms (avg score: {avg_score:.1f}/100)")

    print("\n" + "=" * 60)
