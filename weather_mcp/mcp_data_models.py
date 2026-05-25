"""Pydantic models for weather MCP request validation."""

from datetime import date

from pydantic import BaseModel, field_validator, model_validator


class WeatherRequest(BaseModel):
    """Validated request parameters for the get_weather tool.

    Attributes:
        location: Non-empty location name.
        start_date: Optional start date in YYYY-MM-DD format.
        end_date: Optional end date in YYYY-MM-DD format; must be >= start_date.
    """

    location: str
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("location")
    @classmethod
    def location_must_not_be_empty(cls, v: str) -> str:
        """Validate that location is non-empty after stripping whitespace.

        Args:
            v: The raw location string.

        Returns:
            The stripped location string.

        Raises:
            ValueError: If the stripped location is empty.
        """
        if not v.strip():
            raise ValueError("location must not be empty")
        return v.strip()

    @field_validator("start_date", "end_date")
    @classmethod
    def date_must_be_valid(cls, v: str | None) -> str | None:
        """Validate that date strings are in YYYY-MM-DD format.

        Args:
            v: The raw date string or None.

        Returns:
            The original date string if valid, or None.

        Raises:
            ValueError: If the string is not a valid ISO date.
        """
        if v is not None:
            date.fromisoformat(v)
        return v

    @model_validator(mode="after")
    def start_before_end(self) -> "WeatherRequest":
        """Validate that start_date is not after end_date.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If start_date is after end_date.
        """
        if self.start_date and self.end_date:
            if date.fromisoformat(self.start_date) > date.fromisoformat(self.end_date):
                raise ValueError("start_date must be before end_date")
        return self
