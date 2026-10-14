# Module: backend.app.tools.weather
"""
Weather Tool for Friday AI Assistant.
Retrieves real-time global weather and forecasts via Open-Meteo API.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


class WeatherInput(BaseModel):
    city: str = Field(..., description="The name of the city/region to look up weather for (e.g. 'London', 'Chennai', 'New York').")


class GetWeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "Get live current weather conditions, temperature in Celsius, feels-like, humidity, and wind speed for any city worldwide."
    permission_level: PermissionLevel = PermissionLevel.SAFE
    category: str = "general"
    args_schema = WeatherInput

    async def execute(self, city: str, **kwargs: Any) -> ToolResult:
        city = city.strip()
        if not city:
            return ToolResult(tool_name=self.name, success=False, error="City name cannot be empty.")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                geo_response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1, "language": "en", "format": "json"},
                )
                geo_response.raise_for_status()
                geo_data = geo_response.json()
                results = geo_data.get("results", [])

                if not results:
                    return ToolResult(tool_name=self.name, success=False, error=f"Could not find coordinates for city '{city}'.")

                location = results[0]
                latitude = location["latitude"]
                longitude = location["longitude"]
                city_name = location.get("name", city)
                country = location.get("country", "")

                from datetime import datetime
                weather_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                        "past_days": 2,
                        "timezone": "auto",
                    },
                )
                weather_response.raise_for_status()
                weather_data = weather_response.json()

            current = weather_data.get("current", {})
            daily = weather_data.get("daily", {})

            temperature = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            feels_like = current.get("apparent_temperature")
            wind_speed = current.get("wind_speed_10m")
            weather_code = current.get("weather_code")
            description = _weather_description(weather_code)

            times = daily.get("time", [])
            daily_rain_prob = daily.get("precipitation_probability_max", [])
            daily_rain_sum = daily.get("precipitation_sum", [])
            daily_codes = daily.get("weather_code", [])
            daily_max_temps = daily.get("temperature_2m_max", [])
            daily_min_temps = daily.get("temperature_2m_min", [])

            today_str = datetime.now().strftime("%Y-%m-%d")
            today_idx = times.index(today_str) if today_str in times else (len(times) // 2 if times else 0)
            yesterday_idx = max(0, today_idx - 1)
            tomorrow_idx = min(len(times) - 1, today_idx + 1) if times else 0

            # Yesterday's historical weather
            yesterday_rain_prob = daily_rain_prob[yesterday_idx] if len(daily_rain_prob) > yesterday_idx else 0
            yesterday_rain_sum = daily_rain_sum[yesterday_idx] if len(daily_rain_sum) > yesterday_idx else 0.0
            yesterday_code = daily_codes[yesterday_idx] if len(daily_codes) > yesterday_idx else None
            yesterday_desc = _weather_description(yesterday_code)
            yesterday_max = daily_max_temps[yesterday_idx] if len(daily_max_temps) > yesterday_idx else None
            yesterday_min = daily_min_temps[yesterday_idx] if len(daily_min_temps) > yesterday_idx else None

            # Today's weather
            today_rain_prob = daily_rain_prob[today_idx] if len(daily_rain_prob) > today_idx else 0
            today_rain_sum = daily_rain_sum[today_idx] if len(daily_rain_sum) > today_idx else 0.0

            # Tomorrow's forecast
            tomorrow_rain_prob = daily_rain_prob[tomorrow_idx] if len(daily_rain_prob) > tomorrow_idx else 0
            tomorrow_rain_sum = daily_rain_sum[tomorrow_idx] if len(daily_rain_sum) > tomorrow_idx else 0.0
            tomorrow_code = daily_codes[tomorrow_idx] if len(daily_codes) > tomorrow_idx else None
            tomorrow_desc = _weather_description(tomorrow_code)
            tomorrow_max = daily_max_temps[tomorrow_idx] if len(daily_max_temps) > tomorrow_idx else None
            tomorrow_min = daily_min_temps[tomorrow_idx] if len(daily_min_temps) > tomorrow_idx else None

            data_payload = {
                "city": city_name,
                "country": country,
                "condition": description,
                "temperature_celsius": temperature,
                "feels_like_celsius": feels_like,
                "humidity_percent": humidity,
                "wind_speed_kmh": wind_speed,
                "precipitation_mm": current.get("precipitation", 0),
                "yesterday_condition": yesterday_desc,
                "yesterday_rain_chance": yesterday_rain_prob,
                "yesterday_rain_sum_mm": yesterday_rain_sum,
                "yesterday_temp_max": yesterday_max,
                "yesterday_temp_min": yesterday_min,
                "today_rain_chance": today_rain_prob,
                "today_rain_sum_mm": today_rain_sum,
                "tomorrow_condition": tomorrow_desc,
                "tomorrow_rain_chance": tomorrow_rain_prob,
                "tomorrow_rain_sum_mm": tomorrow_rain_sum,
                "tomorrow_temp_max": tomorrow_max,
                "tomorrow_temp_min": tomorrow_min,
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=data_payload,
                metadata={
                    "summary": f"{description}, {temperature}°C (Feels like {feels_like}°C), {humidity}% humidity in {city_name}, {country}. Yesterday: {yesterday_desc}, rain: {yesterday_rain_sum}mm. Tomorrow: {tomorrow_desc}, {tomorrow_min}-{tomorrow_max}°C, {tomorrow_rain_prob}% rain."
                }
            )

        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=f"Weather retrieval failed: {str(exc)}")


async def get_weather_data(city: str) -> Optional[Dict[str, Any]]:
    """Helper wrapper to fetch raw structured weather and forecast data."""
    tool = GetWeatherTool()
    res = await tool.execute(city=city)
    if res.success and res.data:
        return res.data
    return None


async def get_weather(city: str) -> str:
    """Helper wrapper for direct callers."""
    tool = GetWeatherTool()
    res = await tool.execute(city=city)
    if res.success and res.data:
        d = res.data
        return (
            f"Weather in {d.get('city')}, {d.get('country')}:\n"
            f"Condition: {d.get('condition')}\n"
            f"Temperature: {d.get('temperature_celsius')}°C (Feels like {d.get('feels_like_celsius')}°C)\n"
            f"Humidity: {d.get('humidity_percent')}%\n"
            f"Wind: {d.get('wind_speed_kmh')} km/h\n"
            f"Today Rain Chance: {d.get('today_rain_chance')}%\n"
            f"Tomorrow: {d.get('tomorrow_condition')}, {d.get('tomorrow_temp_min')}°C to {d.get('tomorrow_temp_max')}°C (Rain chance: {d.get('tomorrow_rain_chance')}%)"
        )
    return res.error or "Weather service unavailable."


def _weather_description(code: int | None) -> str:
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, "Clear conditions")