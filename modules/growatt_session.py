"""Session handling for Growatt API."""

import requests
from typing import Dict, Any

def get_session() -> requests.Session:
    """
    Create a new session for Growatt API calls.
    
    Returns:
        Session object with default headers
    """
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    return session

def call_endpoint(session: requests.Session, url: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
    """
    Make an API call using the provided session.
    
    Args:
        session: Request session to use
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        **kwargs: Additional arguments for requests
        
    Returns:
        JSON response from API
        
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    response = session.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()