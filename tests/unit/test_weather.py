"""Unit tests for WeatherTool."""

import pytest
from unittest.mock import patch, MagicMock
from grok_py.tools.weather import WeatherTool, WeatherProvider
from grok_py.tools.base import ToolResult


class TestWeatherProvider:
    """Test WeatherProvider enum."""

    def test_enum_values(self):
        """Test WeatherProvider enum values."""
        assert WeatherProvider.OPENWEATHERMAP == "openweathermap"
        assert WeatherProvider.WEATHERAPI == "weatherapi"


class TestWeatherTool:
    """Test WeatherTool class."""

    def setup_method(self):
        """Set up test method."""
        with patch('grok_py.tools.weather.os.getenv', return_value="fake_key"), \
             patch('grok_py.tools.weather.httpx.Client'):
            self.tool = WeatherTool()

    @patch('grok_py.tools.weather.os.getenv')
    @patch('grok_py.tools.weather.httpx.Client')
    def test_init_with_keys(self, mock_client_class, mock_getenv):
        """Test WeatherTool initialization with API keys."""
        mock_getenv.side_effect = lambda key: "openweather_key" if key == "OPENWEATHERMAP_API_KEY" else "weatherapi_key"

        tool = WeatherTool()

        assert tool.openweather_api_key == "openweather_key"
        assert tool.weatherapi_key == "weatherapi_key"

    @patch('grok_py.tools.weather.os.getenv')
    @patch('grok_py.tools.weather.httpx.Client')
    def test_init_without_keys(self, mock_client_class, mock_getenv):
        """Test WeatherTool initialization without API keys."""
        mock_getenv.return_value = None

        tool = WeatherTool()

        assert tool.openweather_api_key is None
        assert tool.weatherapi_key is None

    def test_execute_sync_no_provider_no_keys(self):
        """Test execute_sync with no provider specified and no keys."""
        tool = WeatherTool()
        tool.openweather_api_key = None
        tool.weatherapi_key = None

        result = tool.execute_sync("London")

        assert result.success is False
        assert "No API keys configured" in result.error

    def test_execute_sync_invalid_provider(self):
        """Test execute_sync with invalid provider."""
        result = self.tool.execute_sync("London", provider="invalid")

        assert result.success is False
        assert "Unsupported provider" in result.error

    def test_execute_sync_invalid_forecast_type(self):
        """Test execute_sync with invalid forecast type."""
        result = self.tool.execute_sync("London", forecast_type="invalid")

        assert result.success is False
        assert "forecast_type must be" in result.error

    def test_execute_sync_invalid_days(self):
        """Test execute_sync with invalid days."""
        result = self.tool.execute_sync("London", days=10)

        assert result.success is False
        assert "days must be between 1 and 7" in result.error

    def test_parse_coordinates_valid(self):
        """Test _parse_coordinates with valid coordinates."""
        result = self.tool._parse_coordinates("40.7128,-74.0060")
        assert result == (40.7128, -74.0060)

    def test_parse_coordinates_invalid(self):
        """Test _parse_coordinates with invalid coordinates."""
        result = self.tool._parse_coordinates("London")
        assert result is None

    def test_parse_coordinates_out_of_range(self):
        """Test _parse_coordinates with out of range coordinates."""
        result = self.tool._parse_coordinates("100.0,200.0")
        assert result is None

    @patch.object(WeatherTool, '_get_openweather_data_by_city')
    def test_execute_sync_openweather_city(self, mock_get_data):
        """Test execute_sync with OpenWeatherMap by city."""
        mock_result = ToolResult(success=True, data={"weather": "sunny"})
        mock_get_data.return_value = mock_result

        result = self.tool.execute_sync("London", provider="openweathermap")

        mock_get_data.assert_called_once_with("London", "current", None)
        assert result == mock_result

    @patch.object(WeatherTool, '_get_weatherapi_data')
    def test_execute_sync_weatherapi_coords(self, mock_get_data):
        """Test execute_sync with WeatherAPI by coordinates."""
        mock_result = ToolResult(success=True, data={"weather": "rainy"})
        mock_get_data.return_value = mock_result

        result = self.tool.execute_sync("40.7128,-74.0060", provider="weatherapi", forecast_type="daily", days=3)

        mock_get_data.assert_called_once_with(40.7128, -74.0060, "daily", 3)
        assert result == mock_result

    def test_get_openweather_data_by_city_no_key(self):
        """Test _get_openweather_data_by_city without API key."""
        tool = WeatherTool()
        tool.openweather_api_key = None

        result = tool._get_openweather_data_by_city("London", "current", None)

        assert result.success is False
        assert "OpenWeatherMap API key not configured" in result.error

    @patch.object(WeatherTool, 'client')
    def test_get_openweather_data_by_city_current(self, mock_client):
        """Test _get_openweather_data_by_city current weather."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "London",
            "sys": {"country": "GB"},
            "coord": {"lat": 51.5074, "lon": -0.1278},
            "main": {"temp": 15.0, "feels_like": 14.0, "humidity": 70, "pressure": 1013},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 5.0, "deg": 180},
            "visibility": 10000,
            "clouds": {"all": 10}
        }
        mock_client.get.return_value = mock_response

        result = self.tool._get_openweather_data_by_city("London", "current", None)

        assert result.success is True
        assert result.data["location"]["name"] == "London"
        assert result.data["current"]["temperature_c"] == 15.0
        assert result.data["provider"] == "OpenWeatherMap"

    @patch.object(WeatherTool, 'client')
    def test_get_openweather_data_by_city_401_error(self, mock_client):
        """Test _get_openweather_data_by_city with 401 error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.get.side_effect = Exception("401")

        # Mock the HTTPStatusError
        import httpx
        mock_client.get.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

        result = self.tool._get_openweather_data_by_city("London", "current", None)

        assert result.success is False
        assert "Invalid OpenWeatherMap API key" in result.error

    def test_get_weatherapi_data_by_city_no_key(self):
        """Test _get_weatherapi_data_by_city without API key."""
        tool = WeatherTool()
        tool.weatherapi_key = None

        result = tool._get_weatherapi_data_by_city("London", "current", None)

        assert result.success is False
        assert "WeatherAPI key not configured" in result.error

    @patch.object(WeatherTool, 'client')
    def test_get_weatherapi_data_by_city_current(self, mock_client):
        """Test _get_weatherapi_data_by_city current weather."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "location": {
                "name": "London",
                "region": "England",
                "country": "UK",
                "lat": 51.5074,
                "lon": -0.1278
            },
            "current": {
                "temp_c": 15.0,
                "temp_f": 59.0,
                "feelslike_c": 14.0,
                "humidity": 70,
                "pressure_mb": 1013,
                "condition": {"text": "Sunny", "icon": "//icon.png"},
                "wind_kph": 10.0,
                "wind_dir": "SW",
                "vis_km": 10.0,
                "cloud": 20
            }
        }
        mock_client.get.return_value = mock_response

        result = self.tool._get_weatherapi_data_by_city("London", "current", None)

        assert result.success is True
        assert result.data["location"]["name"] == "London"
        assert result.data["current"]["temperature_c"] == 15.0
        assert result.data["provider"] == "WeatherAPI"

    @patch.object(WeatherTool, 'client')
    def test_get_weatherapi_data_by_city_daily(self, mock_client):
        """Test _get_weatherapi_data_by_city daily forecast."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "location": {
                "name": "London",
                "lat": 51.5074,
                "lon": -0.1278
            },
            "forecast": {
                "forecastday": [
                    {
                        "date": "2024-01-01",
                        "day": {
                            "mintemp_c": 10.0,
                            "maxtemp_c": 15.0,
                            "avgtemp_c": 12.5,
                            "condition": {"text": "Cloudy", "icon": "//icon.png"},
                            "daily_chance_of_rain": 20,
                            "daily_chance_of_snow": 0
                        }
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response

        result = self.tool._get_weatherapi_data_by_city("London", "daily", 1)

        assert result.success is True
        assert len(result.data["forecast"]) == 1
        assert result.data["forecast"][0]["date"] == "2024-01-01"
        assert result.data["provider"] == "WeatherAPI"

    def test_format_openweather_current(self):
        """Test _format_openweather_current."""
        data = {
            "name": "London",
            "sys": {"country": "GB"},
            "coord": {"lat": 51.5074, "lon": -0.1278},
            "main": {"temp": 15.0, "feels_like": 14.0, "humidity": 70, "pressure": 1013},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 5.0, "deg": 180},
            "visibility": 10000,
            "clouds": {"all": 10}
        }

        result = self.tool._format_openweather_current(data)

        assert result["location"]["name"] == "London"
        assert result["current"]["temperature_c"] == 15.0
        assert result["current"]["description"] == "clear sky"
        assert result["provider"] == "OpenWeatherMap"

    def test_format_weatherapi_current(self):
        """Test _format_weatherapi_current."""
        data = {
            "location": {
                "name": "London",
                "region": "England",
                "country": "UK",
                "lat": 51.5074,
                "lon": -0.1278
            },
            "current": {
                "temp_c": 15.0,
                "temp_f": 59.0,
                "feelslike_c": 14.0,
                "humidity": 70,
                "pressure_mb": 1013,
                "condition": {"text": "Sunny", "icon": "//icon.png"},
                "wind_kph": 10.0,
                "wind_dir": "SW",
                "vis_km": 10.0,
                "cloud": 20
            }
        }

        result = self.tool._format_weatherapi_current(data)

        assert result["location"]["name"] == "London"
        assert result["current"]["temperature_c"] == 15.0
        assert result["current"]["description"] == "Sunny"
        assert result["provider"] == "WeatherAPI"