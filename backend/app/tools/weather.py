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

                weather_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                        "timezone": "auto",
                    },
                )
                weather_response.raise_for_status()
                weather_data = weather_response.json()

            current = weather_data.get("current", {})
            temperature = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            feels_like = current.get("apparent_temperature")
            wind_speed = current.get("wind_speed_10m")
            weather_code = current.get("weather_code")
            description = _weather_description(weather_code)

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "city": city_name,
                    "country": country,
                    "condition": description,
                    "temperature_celsius": temperature,
                    "feels_like_celsius": feels_like,
                    "humidity_percent": humidity,
                    "wind_speed_kmh": wind_speed
                },
                metadata={
                    "summary": f"{description}, {temperature}°C (Feels like {feels_like}°C), {humidity}% humidity in {city_name}, {country}"
                }
            )

        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=f"Weather retrieval failed: {str(exc)}")


async def get_weather(city: str) -> str:
    """Helper wrapper for direct callers."""
    tool = GetWeatherTool()
    res = await tool.execute(city=city)
    if res.success and res.data:
        d = res.data
        return (
            f"Weather in {d.get('city')}, {d.get('country')}:\n"
            f"Condition: {d.get('condition')}\n"
            f"Temperature: {d.get('temperature_celsius')}°C\n"
            f"Feels like: {d.get('feels_like_celsius')}°C\n"
            f"Humidity: {d.get('humidity_percent')}%\n"
            f"Wind: {d.get('wind_speed_kmh')} km/h"
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