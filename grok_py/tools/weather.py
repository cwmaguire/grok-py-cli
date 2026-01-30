"""Weather API tool for current conditions and forecasts."""

import os
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx

from .base import SyncTool, ToolCategory, ToolResult


class WeatherProvider(Enum):
    """Supported weather API providers."""
    OPENWEATHERMAP = "openweathermap"
    WEATHERAPI = "weatherapi"


class WeatherTool(SyncTool):
    """Tool for weather information from multiple providers."""

    def __init__(self):
        super().__init__(
            name="weather",
            description="Get current weather conditions and forecasts from multiple providers",
            category=ToolCategory.WEB
        )

        # API keys
        self.openweather_api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        self.weatherapi_key = os.getenv("WEATHERAPI_KEY")

        # HTTP client
        self.client = httpx.Client(timeout=30.0)

    def execute_sync(
        self,
        location: str,
        provider: Optional[str] = None,
        forecast_type: Optional[str] = None,
        days: Optional[int] = None
    ) -> ToolResult:
        """Get weather information.

        Args:
            location: City name, zip code, or coordinates (lat,lon)
            provider: Weather provider ('openweathermap' or 'weatherapi')
            forecast_type: 'current', 'hourly', or 'daily'
            days: Number of days for forecast (1-7)

        Returns:
            ToolResult with weather data
        """
        try:
            # Determine provider
            if not provider:
                if self.openweather_api_key:
                    provider = WeatherProvider.OPENWEATHERMAP.value
                elif self.weatherapi_key:
                    provider = WeatherProvider.WEATHERAPI.value
                else:
                    return ToolResult(
                        success=False,
                        error="No API keys configured. Set OPENWEATHERMAP_API_KEY or WEATHERAPI_KEY"
                    )

            provider_enum = WeatherProvider(provider)

            # Validate forecast_type
            if forecast_type and forecast_type not in ['current', 'hourly', 'daily']:
                return ToolResult(
                    success=False,
                    error="forecast_type must be 'current', 'hourly', or 'daily'"
                )

            # Default to current weather
            forecast_type = forecast_type or 'current'

            # Validate days
            if days and not (1 <= days <= 7):
                return ToolResult(
                    success=False,
                    error="days must be between 1 and 7"
                )

            # Get coordinates if location is coordinates, otherwise use location string
            coords = self._parse_coordinates(location)
            if coords:
                lat, lon = coords
                # Get weather data
                if provider_enum == WeatherProvider.OPENWEATHERMAP:
                    return self._get_openweather_data(lat, lon, forecast_type, days)
                elif provider_enum == WeatherProvider.WEATHERAPI:
                    return self._get_weatherapi_data(lat, lon, forecast_type, days)
            else:
                # Location is a city name, pass to APIs directly
                if provider_enum == WeatherProvider.OPENWEATHERMAP:
                    return self._get_openweather_data_by_city(location, forecast_type, days)
                elif provider_enum == WeatherProvider.WEATHERAPI:
                    return self._get_weatherapi_data_by_city(location, forecast_type, days)
                else:
                    return ToolResult(
                        success=False,
                        error=f"Unsupported provider: {provider}"
                    )

        except Exception as e:
            return ToolResult(success=False, error=f"Weather API error: {str(e)}")

    def _parse_coordinates(self, location: str) -> Optional[tuple]:
        """Parse location string as coordinates (lat,lon) if possible."""
        try:
            if ',' in location:
                parts = location.split(',')
                if len(parts) == 2:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    # Basic validation
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return lat, lon
        except ValueError:
            pass
        return None

    def _get_openweather_data_by_city(self, city: str, forecast_type: str, days: Optional[int]) -> ToolResult:
        """Get weather data from OpenWeatherMap by city name."""
        if not self.openweather_api_key:
            return ToolResult(success=False, error="OpenWeatherMap API key not configured")

        try:
            if forecast_type == 'current':
                url = "https://api.openweathermap.org/data/2.5/weather"
                params = {
                    'q': city,
                    'appid': self.openweather_api_key,
                    'units': 'metric'
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                formatted = self._format_openweather_current(data)
                return ToolResult(success=True, data=formatted)

            elif forecast_type in ['daily', 'hourly']:
                url = "https://api.openweathermap.org/data/2.5/forecast"
                params = {
                    'q': city,
                    'appid': self.openweather_api_key,
                    'units': 'metric'
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if forecast_type == 'daily':
                    formatted = self._format_openweather_daily(data, days or 5)
                else:  # hourly
                    formatted = self._format_openweather_hourly(data, days or 1)

                return ToolResult(success=True, data=formatted)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ToolResult(success=False, error="Invalid OpenWeatherMap API key")
            elif e.response.status_code == 429:
                return ToolResult(success=False, error="OpenWeatherMap API rate limit exceeded")
            elif e.response.status_code == 404:
                return ToolResult(success=False, error=f"City '{city}' not found")
            else:
                return ToolResult(success=False, error=f"OpenWeatherMap API error: {e.response.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=f"OpenWeatherMap request failed: {str(e)}")

    def _get_weatherapi_data_by_city(self, city: str, forecast_type: str, days: Optional[int]) -> ToolResult:
        """Get weather data from WeatherAPI by city name."""
        if not self.weatherapi_key:
            return ToolResult(success=False, error="WeatherAPI key not configured")

        try:
            url = "http://api.weatherapi.com/v1/forecast.json"
            params = {
                'key': self.weatherapi_key,
                'q': city,
                'days': days or 1,
                'aqi': 'no',
                'alerts': 'no'
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if forecast_type == 'current':
                formatted = self._format_weatherapi_current(data)
                return ToolResult(success=True, data=formatted)
            elif forecast_type == 'daily':
                formatted = self._format_weatherapi_daily(data, days or 5)
                return ToolResult(success=True, data=formatted)
            elif forecast_type == 'hourly':
                formatted = self._format_weatherapi_hourly(data, days or 1)
                return ToolResult(success=True, data=formatted)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ToolResult(success=False, error="Invalid WeatherAPI key")
            elif e.response.status_code == 403:
                return ToolResult(success=False, error="WeatherAPI access forbidden - check your plan")
            elif e.response.status_code == 400:
                return ToolResult(success=False, error=f"City '{city}' not found")
            else:
                return ToolResult(success=False, error=f"WeatherAPI error: {e.response.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=f"WeatherAPI request failed: {str(e)}")

    def _get_openweather_data(self, lat: float, lon: float, forecast_type: str, days: Optional[int]) -> ToolResult:
        """Get weather data from OpenWeatherMap."""
        if not self.openweather_api_key:
            return ToolResult(success=False, error="OpenWeatherMap API key not configured")

        try:
            if forecast_type == 'current':
                url = "https://api.openweathermap.org/data/2.5/weather"
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.openweather_api_key,
                    'units': 'metric'
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                formatted = self._format_openweather_current(data)
                return ToolResult(success=True, data=formatted)

            elif forecast_type in ['daily', 'hourly']:
                url = "https://api.openweathermap.org/data/2.5/forecast"
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.openweather_api_key,
                    'units': 'metric'
                }
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if forecast_type == 'daily':
                    formatted = self._format_openweather_daily(data, days or 5)
                else:  # hourly
                    formatted = self._format_openweather_hourly(data, days or 1)

                return ToolResult(success=True, data=formatted)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ToolResult(success=False, error="Invalid OpenWeatherMap API key")
            elif e.response.status_code == 429:
                return ToolResult(success=False, error="OpenWeatherMap API rate limit exceeded")
            else:
                return ToolResult(success=False, error=f"OpenWeatherMap API error: {e.response.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=f"OpenWeatherMap request failed: {str(e)}")

    def _get_weatherapi_data(self, lat: float, lon: float, forecast_type: str, days: Optional[int]) -> ToolResult:
        """Get weather data from WeatherAPI."""
        if not self.weatherapi_key:
            return ToolResult(success=False, error="WeatherAPI key not configured")

        try:
            url = "http://api.weatherapi.com/v1/forecast.json"
            params = {
                'key': self.weatherapi_key,
                'q': f"{lat},{lon}",
                'days': days or 1,
                'aqi': 'no',
                'alerts': 'no'
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if forecast_type == 'current':
                formatted = self._format_weatherapi_current(data)
                return ToolResult(success=True, data=formatted)
            elif forecast_type == 'daily':
                formatted = self._format_weatherapi_daily(data, days or 5)
                return ToolResult(success=True, data=formatted)
            elif forecast_type == 'hourly':
                formatted = self._format_weatherapi_hourly(data, days or 1)
                return ToolResult(success=True, data=formatted)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ToolResult(success=False, error="Invalid WeatherAPI key")
            elif e.response.status_code == 403:
                return ToolResult(success=False, error="WeatherAPI access forbidden - check your plan")
            else:
                return ToolResult(success=False, error=f"WeatherAPI error: {e.response.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=f"WeatherAPI request failed: {str(e)}")

    def _format_openweather_current(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format current weather from OpenWeatherMap."""
        return {
            'location': {
                'name': data['name'],
                'country': data.get('sys', {}).get('country'),
                'coordinates': [data['coord']['lat'], data['coord']['lon']]
            },
            'current': {
                'temperature_c': data['main']['temp'],
                'temperature_f': (data['main']['temp'] * 9/5) + 32,
                'feels_like_c': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_direction': data['wind'].get('deg'),
                'visibility': data.get('visibility'),
                'cloud_cover': data.get('clouds', {}).get('all'),
            },
            'provider': 'OpenWeatherMap'
        }

    def _format_openweather_daily(self, data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Format daily forecast from OpenWeatherMap."""
        # Group by date
        daily_data = {}
        for item in data['list']:
            date = item['dt_txt'].split(' ')[0]
            if date not in daily_data:
                daily_data[date] = []
            daily_data[date].append(item)

        forecast = []
        for date, items in list(daily_data.items())[:days]:
            # Calculate daily aggregates
            temps = [item['main']['temp'] for item in items]
            min_temp = min(temps)
            max_temp = max(temps)
            avg_temp = sum(temps) / len(temps)
            description = items[0]['weather'][0]['description']

            forecast.append({
                'date': date,
                'min_temp_c': min_temp,
                'max_temp_c': max_temp,
                'avg_temp_c': avg_temp,
                'description': description,
                'icon': items[0]['weather'][0]['icon']
            })

        return {
            'location': {
                'coordinates': [data['city']['coord']['lat'], data['city']['coord']['lon']]
            },
            'forecast': forecast,
            'provider': 'OpenWeatherMap'
        }

    def _format_openweather_hourly(self, data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Format hourly forecast from OpenWeatherMap."""
        hours_per_day = 24
        total_hours = days * hours_per_day

        forecast = []
        for item in data['list'][:total_hours]:
            forecast.append({
                'datetime': item['dt_txt'],
                'temperature_c': item['main']['temp'],
                'description': item['weather'][0]['description'],
                'icon': item['weather'][0]['icon'],
                'humidity': item['main']['humidity'],
                'wind_speed': item['wind']['speed']
            })

        return {
            'location': {
                'coordinates': [data['city']['coord']['lat'], data['city']['coord']['lon']]
            },
            'forecast': forecast,
            'provider': 'OpenWeatherMap'
        }

    def _format_weatherapi_current(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format current weather from WeatherAPI."""
        current = data['current']
        return {
            'location': {
                'name': data['location']['name'],
                'region': data['location']['region'],
                'country': data['location']['country'],
                'coordinates': [data['location']['lat'], data['location']['lon']]
            },
            'current': {
                'temperature_c': current['temp_c'],
                'temperature_f': current['temp_f'],
                'feels_like_c': current['feelslike_c'],
                'humidity': current['humidity'],
                'pressure': current['pressure_mb'],
                'description': current['condition']['text'],
                'icon': current['condition']['icon'],
                'wind_speed': current['wind_kph'],
                'wind_direction': current['wind_dir'],
                'visibility': current['vis_km'],
                'cloud_cover': current['cloud'],
            },
            'provider': 'WeatherAPI'
        }

    def _format_weatherapi_daily(self, data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Format daily forecast from WeatherAPI."""
        forecast_data = data['forecast']['forecastday'][:days]
        forecast = []

        for day in forecast_data:
            forecast.append({
                'date': day['date'],
                'min_temp_c': day['day']['mintemp_c'],
                'max_temp_c': day['day']['maxtemp_c'],
                'avg_temp_c': day['day']['avgtemp_c'],
                'description': day['day']['condition']['text'],
                'icon': day['day']['condition']['icon'],
                'chance_of_rain': day['day']['daily_chance_of_rain'],
                'chance_of_snow': day['day']['daily_chance_of_snow']
            })

        return {
            'location': {
                'name': data['location']['name'],
                'coordinates': [data['location']['lat'], data['location']['lon']]
            },
            'forecast': forecast,
            'provider': 'WeatherAPI'
        }

    def _format_weatherapi_hourly(self, data: Dict[str, Any], days: int) -> Dict[str, Any]:
        """Format hourly forecast from WeatherAPI."""
        forecast_data = data['forecast']['forecastday'][:days]
        forecast = []

        for day in forecast_data:
            for hour in day['hour']:
                forecast.append({
                    'datetime': hour['time'],
                    'temperature_c': hour['temp_c'],
                    'description': hour['condition']['text'],
                    'icon': hour['condition']['icon'],
                    'humidity': hour['humidity'],
                    'wind_speed': hour['wind_kph'],
                    'chance_of_rain': hour['chance_of_rain'],
                    'chance_of_snow': hour['chance_of_snow']
                })

        return {
            'location': {
                'name': data['location']['name'],
                'coordinates': [data['location']['lat'], data['location']['lon']]
            },
            'forecast': forecast,
            'provider': 'WeatherAPI'
        }