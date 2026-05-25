"""Tests for WeatherRequest Pydantic model validation."""

import pytest
from pydantic import ValidationError

from weather_mcp.mcp_data_models import WeatherRequest


def test_valid_location_only():
    """Model constructs successfully with only a location."""
    req = WeatherRequest(location="Tokyo")
    assert req.location == "Tokyo"
    assert req.start_date is None
    assert req.end_date is None


def test_location_whitespace_is_stripped():
    """Leading/trailing whitespace in location is stripped."""
    req = WeatherRequest(location="  Paris  ")
    assert req.location == "Paris"


def test_empty_location_raises():
    """Empty location string raises ValidationError."""
    with pytest.raises(ValidationError):
        WeatherRequest(location="")


def test_whitespace_only_location_raises():
    """Whitespace-only location raises ValidationError."""
    with pytest.raises(ValidationError):
        WeatherRequest(location="   ")


def test_valid_with_start_date_only():
    """Model constructs successfully with location and start_date."""
    req = WeatherRequest(location="London", start_date="2024-01-01")
    assert req.start_date == "2024-01-01"
    assert req.end_date is None


def test_valid_with_both_dates():
    """Model constructs successfully with location and both dates."""
    req = WeatherRequest(location="Berlin", start_date="2024-06-01", end_date="2024-06-07")
    assert req.start_date == "2024-06-01"
    assert req.end_date == "2024-06-07"


def test_invalid_start_date_format_raises():
    """Non-ISO start_date raises ValidationError."""
    with pytest.raises(ValidationError):
        WeatherRequest(location="NYC", start_date="not-a-date")


def test_invalid_month_in_date_raises():
    """Date with invalid month raises ValidationError."""
    with pytest.raises(ValidationError):
        WeatherRequest(location="NYC", start_date="2024-13-01")


def test_start_date_after_end_date_raises():
    """start_date after end_date raises ValidationError."""
    with pytest.raises(ValidationError):
        WeatherRequest(location="Rome", start_date="2024-06-10", end_date="2024-06-01")


def test_equal_start_and_end_date_is_valid():
    """start_date equal to end_date is valid."""
    req = WeatherRequest(location="Madrid", start_date="2024-06-05", end_date="2024-06-05")
    assert req.start_date == req.end_date
