"""Growatt API wrapper with improved error handling and retries."""

import logging
from typing import Dict, Any, Optional

import growattServer

from ..utils.exceptions import GrowattAPIError, GrowattAuthError, GrowattDeviceError
from ..utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)

class GrowattAPI:
    """Wrapper for Growatt API with improved error handling and retries."""
    
    def __init__(self, server_url: str = "https://server.growatt.com/"):
        self.server_url = server_url
        self._api = None
        self._user_id = None
    
    def _init_api(self, agent_identifier: str) -> None:
        """Initialize the Growatt API client."""
        self._api = growattServer.GrowattApi(agent_identifier=agent_identifier)
        self._api.server_url = self.server_url
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to Growatt API with retry capability.
        
        Args:
            username: Growatt username
            password: Growatt password
            
        Returns:
            Dict containing login response
            
        Raises:
            GrowattAuthError: If login fails
        """
        try:
            if not self._api:
                self._init_api(username)  # Use username as agent identifier for consistency
                
            response = self._api.login(username, password)
            
            if not response.get('success'):
                raise GrowattAuthError(
                    f"Login failed: {response.get('msg', 'No error message provided')}"
                )
            
            self._user_id = response['user']['id']
            return response
            
        except Exception as e:
            raise GrowattAuthError(f"Login failed: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def get_plant_list(self) -> Dict[str, Any]:
        """
        Get list of plants with retry capability.
        
        Returns:
            Dict containing plant information
            
        Raises:
            GrowattAPIError: If API call fails
            GrowattAuthError: If not logged in
        """
        if not self._user_id:
            raise GrowattAuthError("Not logged in. Call login() first.")
            
        try:
            response = self._api.plant_list(self._user_id)
            
            if 'data' not in response or not response['data']:
                raise GrowattAPIError("No plant data returned from API")
                
            return response
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to get plant list: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def get_plant_info(self, plant_id: str) -> Dict[str, Any]:
        """
        Get plant information with retry capability.
        
        Args:
            plant_id: Plant ID to query
            
        Returns:
            Dict containing plant details
            
        Raises:
            GrowattAPIError: If API call fails
        """
        try:
            response = self._api.plant_info(plant_id)
            
            if not response:
                raise GrowattAPIError(f"No information returned for plant {plant_id}")
                
            return response
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to get plant info: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information with retry capability.
        
        Returns:
            Dict containing plant_id and device_sn
            
        Raises:
            GrowattAPIError: If API calls fail
            GrowattDeviceError: If no valid device found
        """
        try:
            # Get plant list
            plant_list = self.get_plant_list()
            plant_id = plant_list['data'][0]['plantId']
            
            # Get plant info
            plant_info = self.get_plant_info(plant_id)
            
            # Look for device in storage list first, then device list
            device_sn = None
            if 'storageList' in plant_info and plant_info['storageList']:
                device_sn = plant_info['storageList'][0]['deviceSn']
            elif 'deviceList' in plant_info and plant_info['deviceList']:
                device_sn = plant_info['deviceList'][0]['deviceSn']
            
            if not device_sn:
                raise GrowattDeviceError("No valid inverter or storage device found")
                
            return {
                'plant_id': plant_id,
                'device_sn': device_sn
            }
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to get device info: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def get_system_status(self, device_sn: str, plant_id: str) -> Dict[str, Any]:
        """
        Get system status with retry capability.
        
        Args:
            device_sn: Device serial number
            plant_id: Plant ID
            
        Returns:
            Dict containing system status
            
        Raises:
            GrowattAPIError: If API call fails
        """
        try:
            print(f"DEBUG: Getting data for device {device_sn}")
            
            try:
                print(f"DEBUG: Getting plant_info for plant {plant_id}")
                plant_info = self._api.plant_info(plant_id)
                print(f"DEBUG: Plant info: {plant_info}")
                
                # Look for our device in the storage list
                storage_list = plant_info.get('storageList', [])
                device_info = next((dev for dev in storage_list if dev.get('deviceSn', '').upper() == device_sn), None)
                
                if device_info:
                    print(f"DEBUG: Found device info in storageList: {device_info}")
                    
                    # The capacity field in plant_info appears to be the current battery percentage
                    capacity = device_info.get('capacity', '')
                    if capacity:
                        # Remove % if present and convert to number
                        capacity = capacity.rstrip('%')
                        try:
                            capacity = float(capacity)
                            device_info['SOC'] = capacity
                            return device_info
                        except (ValueError, TypeError):
                            print(f"DEBUG: Failed to parse capacity value: {capacity}")
                
                # If we couldn't get battery info from plant_info, try direct device methods
                print(f"DEBUG: Getting device status directly for {device_sn}")
                response = None
                error_message = None
                
                # Try methods that we know should work for battery/inverter systems
                try:
                    print(f"DEBUG: Trying storage_detail")
                    response = self._api.storage_detail(device_sn)
                    if not response:
                        raise Exception("Empty response")
                except Exception as e:
                    error_message = str(e)
                    print(f"DEBUG: storage_detail failed: {error_message}")
                
                if not response:
                    try:
                        print(f"DEBUG: Trying mix_system_status")
                        response = self._api.mix_system_status(device_sn, plant_id)
                        if not response:
                            raise Exception("Empty response")
                    except Exception as e:
                        error_message = str(e)
                        print(f"DEBUG: mix_system_status failed: {error_message}")
                
                # If we got a response from direct methods, try to find SOC in it
                if response:
                    print(f"DEBUG: Got response: {response}")
                    if isinstance(response, dict):
                        # Common field names for battery percentage
                        fields = ['SOC', 'capacity', 'soc', 'batteryCapacity', 'battery_capacity',
                                'bat_capacity', 'battery_soc', 'bat_soc', 'energy_soc', 'capacityPercent']
                        
                        # Helper function to search for fields
                        def find_soc(data):
                            if isinstance(data, dict):
                                # Check direct fields
                                for field in fields:
                                    value = data.get(field)
                                    if value is not None:
                                        try:
                                            if isinstance(value, str) and '%' in value:
                                                value = float(value.rstrip('%'))
                                            else:
                                                value = float(value)
                                            return value
                                        except (ValueError, TypeError):
                                            continue
                                
                                # Check nested structures
                                for key, value in data.items():
                                    if isinstance(value, dict):
                                        nested_soc = find_soc(value)
                                        if nested_soc is not None:
                                            return nested_soc
                            return None
                        
                        # Search through response and its nested structures
                        soc = find_soc(response)
                        if soc is not None:
                            response['SOC'] = soc
                            return response
                        
                        print(f"DEBUG: No battery percentage found in response data")
                
                # If we get here, we couldn't get valid data
                error_msg = "Could not find battery percentage data"
                if error_message:
                    error_msg += f" (Last error: {error_message})"
                raise GrowattAPIError(f"{error_msg} for device {device_sn}")
                
            except Exception as e:
                raise GrowattAPIError(f"Failed to get status for device {device_sn}: {str(e)}")
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to get system status: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def update_system_time(self, device_sn: str, timestamp: str) -> Dict[str, Any]:
        """
        Update system time with retry capability.
        
        Args:
            device_sn: Device serial number
            timestamp: Timestamp string in format YYYY-MM-DD HH:MM:SS
            
        Returns:
            Dict containing API response
            
        Raises:
            GrowattAPIError: If API call fails
        """
        try:
            response = self._api.update_mix_inverter_setting(
                device_sn,
                'mix_time_setting',
                {'param1': timestamp}
            )
            
            if not response.get('success'):
                raise GrowattAPIError(
                    f"Failed to update system time: {response.get('msg', 'No error message provided')}"
                )
                
            return response
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to update system time: {str(e)}")
    
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def update_charge_settings(
        self,
        device_sn: str,
        charge_rate: int,
        target_soc: int,
        schedule_start: tuple,
        schedule_end: tuple
    ) -> Dict[str, Any]:
        """
        Update charge settings with retry capability.
        
        Args:
            device_sn: Device serial number
            charge_rate: Charging power percentage (0-100)
            target_soc: Target state of charge percentage (0-100)
            schedule_start: Tuple of (hour, minute) for schedule start
            schedule_end: Tuple of (hour, minute) for schedule end
            
        Returns:
            Dict containing API response
            
        Raises:
            GrowattAPIError: If API call fails
            ValueError: If invalid parameters provided
        """
        # Validate inputs
        if not (0 <= charge_rate <= 100):
            raise ValueError("charge_rate must be between 0 and 100")
        if not (0 <= target_soc <= 100):
            raise ValueError("target_soc must be between 0 and 100")
            
        try:
            # Update AC charging settings for SPA device
            try:
                # Format times as strings
                start_time = f"{schedule_start[0]:02d}:{schedule_start[1]:02d}"
                end_time = f"{schedule_end[0]:02d}:{schedule_end[1]:02d}"
                
                # Format parameters for API call
                params = {
                    'param1': str(int(charge_rate)),      # Charge rate %
                    'param2': str(int(target_soc)),       # Stop SOC
                    'param3': f"{schedule_start[0]:02d}", # Start hour (slot 1)
                    'param4': f"{schedule_start[1]:02d}", # Start minute (slot 1)
                    'param5': f"{schedule_end[0]:02d}",   # End hour (slot 1)
                    'param6': f"{schedule_end[1]:02d}",   # End minute (slot 1)
                    'param7': "1",                        # Enable slot 1
                    'param8': "00",                       # Start hour (slot 2)
                    'param9': "00",                       # Start minute (slot 2)
                    'param10': "00",                      # End hour (slot 2)
                    'param11': "00",                      # End minute (slot 2)
                    'param12': "0",                       # Disable slot 2
                    'param13': "00",                      # Start hour (slot 3)
                    'param14': "00",                      # Start minute (slot 3)
                    'param15': "00",                      # End hour (slot 3)
                    'param16': "00",                      # End minute (slot 3)
                    'param17': "0"                        # Disable slot 3
                }
                
                # Use the API's method to update settings
                print(f"DEBUG: Updating AC inverter settings with params: {params}")
                response = self._api.update_ac_inverter_setting(
                    device_sn,
                    'spa_ac_charge_time_period',
                    params
                )
                
                print(f"DEBUG: API response: {response}")
                
                # Check response
                if not response or not response.get('success'):
                    error_msg = response.get('msg', 'Unknown error') if response else 'No response'
                    raise GrowattAPIError(f"Failed to update settings: {error_msg}")
                    
                return response
                
            except Exception as e:
                raise GrowattAPIError(f"Failed to update settings: {str(e)}")
            
            if not response.get('success'):
                raise GrowattAPIError(
                    f"Failed to update charge settings: {response.get('msg', 'No error message provided')}"
                )
                
            return response
            
        except Exception as e:
            raise GrowattAPIError(f"Failed to update charge settings: {str(e)}")