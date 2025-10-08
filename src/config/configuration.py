"""Configuration management for the Growatt Weather Based Charger."""

import os
import re
from typing import Any, Dict, Optional
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime

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
        self._validate_percentage('statement_of_charge_pct')
        self._validate_percentage('minimum_charge_pct')
        self._validate_percentage('maximum_charge_pct')
        self._validate_positive('battery_capacity_wh')
        self._validate_positive('maximum_charge_rate_w')
        self._validate_positive('average_load_w')
        
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
            raise GrowattConfigError(
                f"{field_name} must be between 0 and 100, got {value}"
            )

    def _validate_positive(self, field_name: str):
        """Validate that a field contains a positive number."""
        value = getattr(self, field_name)
        if value <= 0:
            raise GrowattConfigError(
                f"{field_name} must be positive, got {value}"
            )

@dataclass
class TariffConfig:
    """Tariff configuration settings."""
    off_peak_start_time: str
    off_peak_end_time: str

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_time_format('off_peak_start_time')
        self._validate_time_format('off_peak_end_time')
        self._validate_time_order()

    def _validate_time_format(self, field_name: str):
        """Validate time format (HH:MM)."""
        value = getattr(self, field_name)
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', value):
            raise GrowattConfigError(
                f"{field_name} must be in HH:MM format, got {value}"
            )

    def _validate_time_order(self):
        """Validate that start time is before end time."""
        start = datetime.strptime(self.off_peak_start_time, '%H:%M')
        end = datetime.strptime(self.off_peak_end_time, '%H:%M')
        if start >= end:
            raise GrowattConfigError(
                f"off_peak_start_time ({self.off_peak_start_time}) must be before "
                f"off_peak_end_time ({self.off_peak_end_time})"
            )

@dataclass
class ForecastConfig:
    """Solar forecast configuration settings."""
    location: str
    declination: float
    azimuth: float
    kw_power: float
    damping: float
    confidence: float

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_float_range('declination', -90, 90)
        self._validate_float_range('azimuth', 0, 360)
        self._validate_positive_float('kw_power')
        self._validate_float_range('damping', 0, 1)
        self._validate_float_range('confidence', 0, 1)

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
            raise GrowattConfigError(
                f"{field_name} must be positive, got {value}"
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

    def _load_config(self) -> None:
        """Load and validate configuration file."""
        if not os.path.exists(self.config_path):
            raise GrowattConfigError(f"Config file not found: {self.config_path}")
            
        self.config.read(self.config_path)
        self._validate_sections()

    def _validate_sections(self) -> None:
        """Validate that all required sections are present."""
        required_sections = {'growatt', 'tariff', 'forecast.solar'}
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
            value = self.config.get(section, key, fallback='')
        return value

    @property
    def growatt(self) -> GrowattConfig:
        """Get validated Growatt configuration."""
        section = self.config['growatt']
        
        return GrowattConfig(
            username=self._get_env_or_config('growatt', 'username', 'GROWATT_USERNAME'),
            password=self._get_env_or_config('growatt', 'password', 'GROWATT_PASSWORD'),
            plant_id=section.get('plant_id', ''),
            device_sn=section.get('device_sn', ''),
            statement_of_charge_pct=section.getint('statement_of_charge_pct'),
            minimum_charge_pct=section.getint('minimum_charge_pct'),
            maximum_charge_pct=section.getint('maximum_charge_pct'),
            battery_capacity_wh=section.getint('battery_capacity_wh'),
            maximum_charge_rate_w=section.getint('maximum_charge_rate_w'),
            average_load_w=section.getint('average_load_w')
        )

    @property
    def tariff(self) -> TariffConfig:
        """Get validated tariff configuration."""
        section = self.config['tariff']
        
        return TariffConfig(
            off_peak_start_time=section.get('off_peak_start_time'),
            off_peak_end_time=section.get('off_peak_end_time')
        )

    @property
    def forecast(self) -> ForecastConfig:
        """Get validated forecast configuration."""
        section = self.config['forecast.solar']
        
        return ForecastConfig(
            location=section.get('location'),
            declination=section.getfloat('declination'),
            azimuth=section.getfloat('azimuth'),
            kw_power=section.getfloat('kw_power'),
            damping=section.getfloat('damping'),
            confidence=section.getfloat('confidence')
        )