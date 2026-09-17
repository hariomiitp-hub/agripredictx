"""OpenWeather helpers for fetching the next 3 months of forecast data."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from data_models import WeatherData, WeatherForecast


logger = logging.getLogger(__name__)


class OpenWeatherError(RuntimeError):
    """Raised when OpenWeather forecast data cannot be fetched or parsed."""


@dataclass
class ForecastWindowSummary:
    """Summarized weather conditions for one 30-day outlook window."""

    start_date: str
    end_date: str
    temperature: float
    humidity: float
    rainfall: float

    def to_weather_data(self) -> WeatherData:
        return WeatherData(
            temperature=self.temperature,
            humidity=self.humidity,
            rainfall=self.rainfall,
        )

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "rainfall": self.rainfall,
        }


@dataclass
class LocationResolution:
    """Resolved location details used to fetch weather forecasts."""

    location_name: str
    district: str
    state: str
    country_code: str
    latitude: float
    longitude: float
    query: Optional[str] = None
    resolution_method: str = "openweather_geocoding"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OpenWeatherForecastClient:
    """Fetch three 30-day forecast windows from OpenWeather One Call 3.0."""

    DAY_SUMMARY_URL = "https://api.openweathermap.org/data/3.0/onecall/day_summary"
    GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/direct"
    REVERSE_GEOCODING_URL = "https://api.openweathermap.org/geo/1.0/reverse"

    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        self.session = session or requests.Session()
        self._daily_cache: Dict[Tuple[float, float, str], Dict] = {}

    def resolve_location(
        self,
        location_name: Optional[str] = None,
        district: Optional[str] = None,
        state: Optional[str] = None,
        country_code: str = "IN",
    ) -> LocationResolution:
        """Resolve a user-entered place, district, and state into coordinates."""
        self._ensure_api_key()

        query_parts = []
        for part in (location_name, district, state):
            cleaned = self._clean_location_part(part)
            if cleaned and cleaned.lower() not in [item.lower() for item in query_parts]:
                query_parts.append(cleaned)

        country = (country_code or "IN").strip().upper()
        query_parts.append(country)
        query = ",".join(query_parts)
        if not query_parts[:-1]:
            raise OpenWeatherError(
                "Please provide a location name, district, or state so OpenWeather can find the forecast area."
            )

        response = self.session.get(
            self.GEOCODING_URL,
            params={
                "q": query,
                "limit": 5,
                "appid": self.api_key,
            },
            timeout=20,
        )
        payload = self._parse_json_response(response, "OpenWeather geocoding")
        if not payload:
            raise OpenWeatherError(
                f"OpenWeather could not find a location for '{query}'. Please refine the district or state."
            )

        best_match = self._select_best_location_match(
            payload,
            expected_location=location_name,
            expected_district=district,
            expected_state=state,
            expected_country=country,
        )

        resolved_name = best_match.get("name") or district or state or location_name or "Unknown"
        resolved_state = best_match.get("state") or state or ""
        return LocationResolution(
            location_name=resolved_name,
            district=district or resolved_name,
            state=resolved_state,
            country_code=best_match.get("country") or country,
            latitude=round(float(best_match["lat"]), 6),
            longitude=round(float(best_match["lon"]), 6),
            query=query,
        )

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> LocationResolution:
        """Resolve coordinates into the nearest location name, district, and state."""
        self._ensure_api_key()

        response = self.session.get(
            self.REVERSE_GEOCODING_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "limit": 1,
                "appid": self.api_key,
            },
            timeout=20,
        )
        payload = self._parse_json_response(response, "OpenWeather reverse geocoding")
        if not payload:
            raise OpenWeatherError("OpenWeather could not reverse geocode the provided coordinates.")

        best_match = payload[0]
        resolved_name = best_match.get("name") or "Unknown"
        return LocationResolution(
            location_name=resolved_name,
            district=resolved_name,
            state=best_match.get("state") or "",
            country_code=best_match.get("country") or "IN",
            latitude=round(float(best_match["lat"]), 6),
            longitude=round(float(best_match["lon"]), 6),
            query=f"{latitude},{longitude}",
            resolution_method="reverse_geocoding",
        )

    def build_three_month_forecast(
        self,
        latitude: float,
        longitude: float,
        analysis_date: Optional[date] = None,
    ) -> tuple[WeatherForecast, Dict[str, object]]:
        """
        Build a 90-day forecast split into three 30-day windows.

        OpenWeather's One Call 3.0 `day_summary` endpoint supports forward dates,
        so we aggregate 90 daily summaries starting from the analysis date.
        """
        self._ensure_api_key()

        start_date = analysis_date or date.today()
        daily_summaries = [
            self._fetch_day_summary(latitude, longitude, start_date + timedelta(days=offset))
            for offset in range(90)
        ]

        windows: List[ForecastWindowSummary] = []
        for window_index in range(3):
            start_offset = window_index * 30
            end_offset = start_offset + 30
            window_days = daily_summaries[start_offset:end_offset]
            windows.append(self._summarize_window(window_days))

        forecast = WeatherForecast(*(window.to_weather_data() for window in windows))
        metadata = {
            "source": "OpenWeather One Call 3.0 day_summary",
            "analysis_date": start_date.isoformat(),
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "windows": [window.to_dict() for window in windows],
        }
        return forecast, metadata

    def _fetch_day_summary(self, latitude: float, longitude: float, target_date: date) -> Dict:
        cache_key = (round(float(latitude), 4), round(float(longitude), 4), target_date.isoformat())
        if cache_key in self._daily_cache:
            return self._daily_cache[cache_key]

        response = self.session.get(
            self.DAY_SUMMARY_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "date": target_date.isoformat(),
                "appid": self.api_key,
                "units": "metric",
            },
            timeout=20,
        )

        if response.status_code == 401:
            raise OpenWeatherError("OpenWeather rejected the API key. Check OPENWEATHER_API_KEY.")
        if response.status_code == 429:
            raise OpenWeatherError("OpenWeather rate limit reached. Please retry later.")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise OpenWeatherError(f"OpenWeather request failed for {target_date.isoformat()}: {exc}") from exc

        payload = response.json()
        self._daily_cache[cache_key] = payload
        return payload

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise OpenWeatherError(
                "OPENWEATHER_API_KEY is not configured. Add it to your environment or .env file."
            )

    def _parse_json_response(self, response: requests.Response, source_name: str) -> Any:
        if response.status_code == 401:
            raise OpenWeatherError("OpenWeather rejected the API key. Check OPENWEATHER_API_KEY.")
        if response.status_code == 429:
            raise OpenWeatherError("OpenWeather rate limit reached. Please retry later.")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise OpenWeatherError(f"{source_name} request failed: {exc}") from exc

        return response.json()

    def _select_best_location_match(
        self,
        candidates: List[Dict[str, Any]],
        expected_location: Optional[str],
        expected_district: Optional[str],
        expected_state: Optional[str],
        expected_country: Optional[str],
    ) -> Dict[str, Any]:
        best_candidate = candidates[0]
        best_score = float("-inf")

        for candidate in candidates:
            score = 0
            candidate_name = self._normalize_text(candidate.get("name"))
            candidate_state = self._normalize_text(candidate.get("state"))
            candidate_country = self._normalize_text(candidate.get("country"))

            for preferred_name in (expected_location, expected_district):
                normalized_preferred = self._normalize_text(preferred_name)
                if normalized_preferred and candidate_name == normalized_preferred:
                    score += 4
                elif normalized_preferred and normalized_preferred in candidate_name:
                    score += 2

            normalized_state = self._normalize_text(expected_state)
            if normalized_state and candidate_state == normalized_state:
                score += 3
            elif normalized_state and normalized_state in candidate_state:
                score += 1

            normalized_country = self._normalize_text(expected_country)
            if normalized_country and candidate_country == normalized_country:
                score += 2

            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate

    def _clean_location_part(self, value: Optional[str]) -> str:
        return (value or "").strip()

    def _normalize_text(self, value: Optional[str]) -> str:
        return self._clean_location_part(value).lower()

    def _summarize_window(self, summaries: List[Dict]) -> ForecastWindowSummary:
        if not summaries:
            raise OpenWeatherError("OpenWeather returned an empty forecast window.")

        daily_temperatures = [self._extract_daily_temperature(item) for item in summaries]
        daily_humidities = [self._extract_daily_humidity(item) for item in summaries]
        daily_rainfall = [self._extract_daily_rainfall(item) for item in summaries]

        return ForecastWindowSummary(
            start_date=summaries[0]["date"],
            end_date=summaries[-1]["date"],
            temperature=round(sum(daily_temperatures) / len(daily_temperatures), 1),
            humidity=round(sum(daily_humidities) / len(daily_humidities), 1),
            rainfall=round(sum(daily_rainfall), 1),
        )

    def _extract_daily_temperature(self, summary: Dict) -> float:
        temperature = summary.get("temperature", {})
        ordered_keys = ("afternoon", "morning", "evening", "night")
        values = [temperature[key] for key in ordered_keys if key in temperature]
        if values:
            return float(sum(values) / len(values))

        if "min" in temperature and "max" in temperature:
            return float((temperature["min"] + temperature["max"]) / 2)

        raise OpenWeatherError(f"OpenWeather response is missing temperature fields for {summary.get('date')}.")

    def _extract_daily_humidity(self, summary: Dict) -> float:
        humidity = summary.get("humidity", {})
        for key in ("afternoon", "morning", "evening", "night"):
            if key in humidity:
                return float(humidity[key])
        raise OpenWeatherError(f"OpenWeather response is missing humidity fields for {summary.get('date')}.")

    def _extract_daily_rainfall(self, summary: Dict) -> float:
        precipitation = summary.get("precipitation", {})
        return float(precipitation.get("total", 0.0))
