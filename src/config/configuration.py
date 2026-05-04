"""Configuration management for the Growatt Weather Based Charger."""

import os
import re
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from ..utils.exceptions import GrowattConfigError


@dataclass
class GrowattConfig:
    """Growatt configuration settings."""

    username: str
    password: str
    plant_id: Optional[str]
    device_sn: Optional[str]
    statement_of_charge_pct: int
    minimum_charge_pct: int
    maximum_charge_pct: int
    battery_capacity_wh: int
    maximum_charge_rate_w: int
    average_load_w: int

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_percentage("statement_of_charge_pct")
        self._validate_percentage("minimum_charge_pct")
        self._validate_percentage("maximum_charge_pct")
        self._validate_positive("battery_capacity_wh")
        self._validate_positive("maximum_charge_rate_w")
        self._validate_positive("average_load_w")

        # Validate charge percentages are in correct order
        if self.minimum_charge_pct > self.maximum_charge_pct:
            raise GrowattConfigError(
                f"minimum_charge_pct ({self.minimum_charge_pct}) cannot be greater than "
                f"maximum_charge_pct ({self.maximum_charge_pct})"
            )

    def _validate_percentage(self, field_name: str):
        """Validate that a field contains a valid percentage (0-100)."""
        value = getattr(self, field_name)
        if not 0 <= value <= 100:
            raise GrowattConfigError(f"{field_name} must be between 0 and 100, got {value}")

    def _validate_positive(self, field_name: str):
        """Validate that a field contains a positive number."""
        value = getattr(self, field_name)
        if value <= 0:
            raise GrowattConfigError(f"{field_name} must be positive, got {value}")


@dataclass
class TariffConfig:
    """Tariff configuration settings."""

    off_peak_start_time: str
    off_peak_end_time: str

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_time_format("off_peak_start_time")
        self._validate_time_format("off_peak_end_time")
        self._validate_time_order()

    def _validate_time_format(self, field_name: str):
        """Validate time format (HH:MM)."""
        value = getattr(self, field_name)
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", value):
            raise GrowattConfigError(f"{field_name} must be in HH:MM format, got {value}")

    def _validate_time_order(self):
        """Validate that start time is before end time."""
        start = datetime.strptime(self.off_peak_start_time, "%H:%M")
        end = datetime.strptime(self.off_peak_end_time, "%H:%M")
        if start >= end:
            raise GrowattConfigError(
                f"off_peak_start_time ({self.off_peak_start_time}) must be before "
                f"off_peak_end_time ({self.off_peak_end_time})"
            )


@dataclass
class PeakWindowConfig:
    """Peak window configuration for afternoon boost checking."""

    peak_start_time: str
    peak_end_time: str
    check_time: str
    forecast_reliability: float = 0.4
    forecast_uncertainty_buffer_pct: float = 10.0

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_time_format("peak_start_time")
        self._validate_time_format("peak_end_time")
        self._validate_time_format("check_time")
        self._validate_time_order()
        self._validate_float_range("forecast_reliability", 0.0, 1.0)
        self._validate_float_range("forecast_uncertainty_buffer_pct", 0.0, 100.0)

    def _validate_time_format(self, field_name: str):
        """Validate time format (HH:MM)."""
        value = getattr(self, field_name)
        if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", value):
            raise GrowattConfigError(f"{field_name} must be in HH:MM format, got {value}")

    def _validate_time_order(self):
        """Validate that check time is before peak window."""
        check = datetime.strptime(self.check_time, "%H:%M")
        peak_start = datetime.strptime(self.peak_start_time, "%H:%M")
        peak_end = datetime.strptime(self.peak_end_time, "%H:%M")

        if peak_start >= peak_end:
            raise GrowattConfigError(
                f"peak_start_time ({self.peak_start_time}) must be before "
                f"peak_end_time ({self.peak_end_time})"
            )

        if check >= peak_start:
            raise GrowattConfigError(
                f"check_time ({self.check_time}) must be before "
                f"peak_start_time ({self.peak_start_time})"
            )

    def _validate_float_range(self, field_name: str, min_val: float, max_val: float):
        """Validate that a float is within a specified range."""
        value = float(getattr(self, field_name))
        if not min_val <= value <= max_val:
            raise GrowattConfigError(
                f"{field_name} must be between {min_val} and {max_val}, got {value}"
            )

    def get_peak_window_duration_hours(self) -> float:
        """Calculate the duration of the peak window in hours."""
        start = datetime.strptime(self.peak_start_time, "%H:%M")
        end = datetime.strptime(self.peak_end_time, "%H:%M")
        duration_seconds = (end - start).seconds
        return duration_seconds / 3600


@dataclass
class ForecastArrayConfig:
    """Single solar array configuration for multi-array setups."""

    declination: float  # Panel tilt angle in degrees
    azimuth: float  # Panel orientation/direction in degrees
    kwp: float  # Array capacity in kW peak


@dataclass
class ForecastConfig:
    """Solar forecast configuration settings."""

    location: str
    declination: float
    azimuth: float
    kw_power: float
    damping: float
    confidence: float
    arrays: Optional[List[ForecastArrayConfig]] = None  # Multi-array configuration

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_float_range("declination", -90, 90)
        self._validate_float_range("azimuth", 0, 360)
        self._validate_positive_float("kw_power")
        self._validate_float_range("damping", 0, 1)
        self._validate_float_range("confidence", 0, 1)

    def _validate_float_range(self, field_name: str, min_val: float, max_val: float):
        """Validate that a float is within a specified range."""
        value = float(getattr(self, field_name))
        if not min_val <= value <= max_val:
            raise GrowattConfigError(
                f"{field_name} must be between {min_val} and {max_val}, got {value}"
            )

    def _validate_positive_float(self, field_name: str):
        """Validate that a float is positive."""
        value = float(getattr(self, field_name))
        if value <= 0:
            raise GrowattConfigError(f"{field_name} must be positive, got {value}")


@dataclass
class ForecastProvidersConfig:
    """Multi-provider forecast configuration."""

    providers: List[str]  # e.g. ['solcast', 'forecast.solar']
    primary_provider: str  # Which provider to use for charging decisions
    fallback_enabled: bool = True  # Auto-fallback if primary fails
    log_all_providers: bool = True  # Log all providers for comparison


@dataclass
class SolcastConfig:
    """Solcast-specific configuration."""

    api_key: str
    resource_id: Optional[str] = None  # Optional - uses lat/lon if not provided

    def __post_init__(self):
        """Validate Solcast configuration."""
        if not self.api_key:
            raise GrowattConfigError("Solcast API key is required")


@dataclass
class EmailConfig:
    """Email notification configuration."""

    enabled: bool
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    sender_name: str
    recipient_email: str

    def __post_init__(self):
        if not self.enabled:
            return
        missing = [
            f
            for f in ("smtp_server", "sender_email", "sender_password", "recipient_email")
            if not getattr(self, f)
        ]
        if missing:
            raise GrowattConfigError(
                "Email notifications are enabled but the following settings are missing: "
                f"{', '.join(missing)}. "
                "Set them in [email] section of the config file or via environment variables."
            )
        if not 1 <= self.smtp_port <= 65535:
            raise GrowattConfigError(f"smtp_port must be between 1 and 65535, got {self.smtp_port}")


@dataclass
class APIResponseCacheConfig:
    enabled: bool
    cache_dir: str
    ttl_hours: float

    @classmethod
    def from_section(cls, section):
        return cls(
            enabled=section.getboolean("enabled", fallback=True),
            cache_dir=section.get("cache_dir", fallback="output/cache"),
            ttl_hours=section.getfloat("ttl_hours", fallback=4.0),
        )


class ConfigManager:
    """Configuration manager for the application."""

    def __init__(self, config_path: str):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = ConfigParser()

        self._load_config()

        if "cache" in self.config:
            self.cache = APIResponseCacheConfig.from_section(self.config["cache"])
        else:
            self.cache = APIResponseCacheConfig(True, "output/cache", 4.0)

    def _load_config(self) -> None:
        """Load and validate configuration file."""
        if not os.path.exists(self.config_path):
            raise GrowattConfigError(f"Config file not found: {self.config_path}")

        self.config.read(self.config_path)
        self._validate_sections()

    def _validate_sections(self) -> None:
        """Validate that all required sections are present."""
        required_sections = {"growatt", "tariff", "forecast.solar", "peak_window"}
        missing_sections = required_sections - set(self.config.sections())

        if missing_sections:
            raise GrowattConfigError(
                f"Missing required config sections: {', '.join(missing_sections)}"
            )

    def _get_env_or_config(self, section: str, key: str, env_var: str) -> str:
        """
        Get value from environment variable or config file.

        Args:
            section: Config section name
            key: Config key name
            env_var: Environment variable name

        Returns:
            Configuration value
        """
        value = os.getenv(env_var)
        if not value:
            value = self.config.get(section, key, fallback="")
        return value

    def _parse_providers_list(self, value: str) -> List[str]:
        """Parse comma-separated list of providers."""
        if not value:
            return ["forecast.solar"]  # Default
        return [p.strip() for p in value.split(",")]

    @property
    def forecast_providers(self) -> ForecastProvidersConfig:
        """Get forecast providers configuration."""
        # Get the section - might be 'forecast' or 'forecast.solar'
        if "forecast" in self.config:
            section = self.config["forecast"]
        elif "forecast.solar" in self.config:
            section = self.config["forecast.solar"]
        else:
            # Return defaults
            return ForecastProvidersConfig(
                providers=["forecast.solar"],
                primary_provider="forecast.solar",
                fallback_enabled=True,
                log_all_providers=True,
            )

        providers_str = section.get("providers", "forecast.solar")
        providers = self._parse_providers_list(providers_str)

        primary = section.get("primary_provider", providers[0] if providers else "forecast.solar")

        # Handle boolean values properly
        fallback_str = section.get("fallback_enabled", "true").lower()
        fallback = fallback_str in ("true", "yes", "1", "on")

        log_all_str = section.get("log_all_providers", "true").lower()
        log_all = log_all_str in ("true", "yes", "1", "on")

        return ForecastProvidersConfig(
            providers=providers,
            primary_provider=primary,
            fallback_enabled=fallback,
            log_all_providers=log_all,
        )

    @property
    def solcast(self) -> Optional[SolcastConfig]:
        """Get Solcast configuration if available."""
        # Try environment variable first
        api_key = os.getenv("SOLCAST_API_KEY")

        # Fall back to config file
        if not api_key and "solcast" in self.config:
            api_key = self.config["solcast"].get("api_key", "")

        if not api_key:
            return None  # Solcast not configured

        resource_id = None
        if "solcast" in self.config:
            resource_id = self.config["solcast"].get("resource_id", "")

        return SolcastConfig(api_key=api_key, resource_id=resource_id if resource_id else None)

    @property
    def growatt(self) -> GrowattConfig:
        """Get validated Growatt configuration."""
        section = self.config["growatt"]

        return GrowattConfig(
            username=self._get_env_or_config("growatt", "username", "GROWATT_USERNAME"),
            password=self._get_env_or_config("growatt", "password", "GROWATT_PASSWORD"),
            plant_id=section.get("plant_id", ""),
            device_sn=section.get("device_sn", ""),
            statement_of_charge_pct=section.getint("statement_of_charge_pct"),
            minimum_charge_pct=section.getint("minimum_charge_pct"),
            maximum_charge_pct=section.getint("maximum_charge_pct"),
            battery_capacity_wh=section.getint("battery_capacity_wh"),
            maximum_charge_rate_w=section.getint("maximum_charge_rate_w"),
            average_load_w=section.getint("average_load_w"),
        )

    @property
    def tariff(self) -> TariffConfig:
        """Get validated tariff configuration."""
        section = self.config["tariff"]

        return TariffConfig(
            off_peak_start_time=section.get("off_peak_start_time"),
            off_peak_end_time=section.get("off_peak_end_time"),
        )

    @property
    def peak_window(self) -> PeakWindowConfig:
        """Get validated peak window configuration."""
        section = self.config["peak_window"]

        return PeakWindowConfig(
            peak_start_time=section.get("peak_start_time"),
            peak_end_time=section.get("peak_end_time"),
            check_time=section.get("check_time"),
            forecast_reliability=section.getfloat("forecast_reliability", fallback=0.4),
            forecast_uncertainty_buffer_pct=section.getfloat(
                "forecast_uncertainty_buffer_pct", fallback=10.0
            ),
        )

    @property
    def email(self) -> EmailConfig:
        """Get email notification configuration."""
        section = self.config["email"] if "email" in self.config else {}

        def get(key, env_var, fallback=""):
            return os.getenv(env_var) or (section.get(key, fallback) if section else fallback)

        enabled_raw = (section.get("enabled", "false") if section else "false").lower()
        enabled = enabled_raw in ("true", "yes", "1", "on")

        sender_email = get("sender_email", "SENDER_EMAIL")
        sender_name = get("sender_name", "SENDER_NAME", fallback="Solar Tracker")
        if not sender_name and sender_email:
            sender_name = sender_email

        smtp_port_raw = get("smtp_port", "SMTP_PORT", fallback="587")
        try:
            smtp_port = int(smtp_port_raw)
        except (ValueError, TypeError):
            smtp_port = 587

        return EmailConfig(
            enabled=enabled,
            smtp_server=get("smtp_server", "SMTP_SERVER"),
            smtp_port=smtp_port,
            sender_email=sender_email,
            sender_password=get("sender_password", "SENDER_PASSWORD"),
            sender_name=sender_name,
            recipient_email=get("recipient_email", "RECIPIENT_EMAIL"),
        )

    @property
    def forecast(self) -> ForecastConfig:
        """Get validated forecast configuration."""
        section = self.config["forecast.solar"]

        # Parse multi-array configuration if present
        arrays = None
        arrays_str = section.get("arrays", "").strip()
        if arrays_str:
            arrays = self._parse_array_config(arrays_str)

        return ForecastConfig(
            location=section.get("location"),
            declination=section.getfloat("declination"),
            azimuth=section.getfloat("azimuth"),
            kw_power=section.getfloat("kw_power"),
            damping=section.getfloat("damping"),
            confidence=section.getfloat("confidence"),
            arrays=arrays,
        )

    def _parse_array_config(self, arrays_str: str) -> Optional[List[ForecastArrayConfig]]:
        """
        Parse multi-array configuration from INI format.

        Format: [decl1, az1, kwp1]; [decl2, az2, kwp2]; ...
        Example: [35, -90, 2.0]; [35, 0, 2.0]; [35, 90, 2.0]

        Args:
            arrays_str: Configuration string with array specifications

        Returns:
            List of ForecastArrayConfig objects or None if parsing fails
        """
        if not arrays_str:
            return None

        arrays = []
        # Split by semicolon to get each array definition
        array_specs = arrays_str.split(";")

        for spec in array_specs:
            spec = spec.strip()
            if not spec:
                continue

            # Remove square brackets if present
            spec = spec.strip("[]").strip()

            # Split by comma to get individual values
            try:
                parts = [p.strip() for p in spec.split(",")]
                if len(parts) != 3:
                    raise ValueError(
                        "Array spec must have 3 values (declination, azimuth, kwp), "
                        f"got {len(parts)}"
                    )

                declination = float(parts[0])
                azimuth = float(parts[1])
                kwp = float(parts[2])

                arrays.append(
                    ForecastArrayConfig(declination=declination, azimuth=azimuth, kwp=kwp)
                )
            except (ValueError, IndexError) as e:
                raise GrowattConfigError(f"Invalid array configuration '{spec}': {str(e)}")

        return arrays if arrays else None
